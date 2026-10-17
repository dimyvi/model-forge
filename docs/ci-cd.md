# CI/CD Model Forge

Автоматизация находится в `.github/workflows/ci-cd.yml`. Она проверяет backend и frontend, а затем обновляет нужный стенд через отдельный self-hosted GitHub Actions Runner.

## Текущая схема

| Событие | Проверки | Результат |
| --- | --- | --- |
| Push в `DEV` | Django tests, ESLint, сборка React | Автоматическое обновление DEV |
| Pull Request в `main` | Django tests, ESLint, сборка React | Только проверка, без развёртывания |
| Merge или push в `main` | Django tests, ESLint, сборка React | Backup БД и автоматическое обновление PROD |

Если проверки завершаются с ошибкой, задание развёртывания не запускается.

Изменения, затрагивающие только файлы внутри `docs/`, не запускают workflow: документация не требует пересборки и повторного развёртывания приложения. Если один коммит меняет и документацию, и код или конфигурацию за пределами `docs/`, pipeline запускается как обычно.

```text
DEV ──push──> tests ──success──> model-forge-dev runner ──> DEV

DEV ──PR──> main ──tests──> merge ──tests──> model-forge-prod runner ──> PROD
```

## Серверы и runner'ы

| Стенд | Ветка | Runner label | Каталог приложения | Compose project |
| --- | --- | --- | --- | --- |
| DEV | `DEV` | `model-forge-dev` | `/opt/model-forge` | `model-forge-dev` |
| PROD | `main` | `model-forge-prod` | `/opt/model-forge/model-forge` | `model-forge-prod` |

Оба runner'а устанавливаются как systemd-службы от пользователя `admin`. Проверить службу на соответствующей ВМ можно командами:

```bash
cd /opt/actions-runner
sudo ./svc.sh status
```

На странице GitHub `Settings → Actions → Runners` оба runner'а должны иметь состояние `Idle`, когда не выполняют задание. Пользователь `admin` должен иметь доступ к Docker.

## Обычная работа

### Обновление DEV

Работа ведётся в ветке `DEV`:

```bash
git switch DEV
git pull --ff-only origin DEV

# внести изменения и проверить их локально

git add .
git commit -m "Описание изменения"
git push origin DEV
```

После push GitHub Actions:

1. запускает Django tests в Docker Compose;
2. выполняет `npm ci`, ESLint и production-сборку React;
3. передаёт deploy-задание runner'у `model-forge-dev`;
4. сохраняет текущие образы с тегом `previous`;
5. обновляет ветку `DEV` в `/opt/model-forge`;
6. пересобирает и запускает контейнеры;
7. проверяет backend и frontend;
8. после успешной проверки удаляет только dangling-образы.

Результат проверяется по адресу `https://dev.model-forge.ru`.

### Выпуск в PROD

После проверки DEV создаётся Pull Request из `DEV` в `main`. Pull Request запускает тесты, но не меняет PROD. После merge новый push в `main` повторно запускает проверки и автоматически обновляет production.

Прямой push в `main` также приводит к production deployment, поэтому основная ветка должна изменяться только через проверенный merge.

Перед обновлением workflow создаёт дамп PostgreSQL:

```text
/home/admin/model-forge-backups/db-YYYYMMDD-HHMMSS.sql.gz
```

Дамп проверяется на непустой размер. Если backup или тесты не созданы успешно, развёртывание не продолжается.

## Docker-образы

Перед каждой сборкой текущие образы получают тег `previous`. После успешной проверки `docker image prune -f` удаляет только более старые dangling-образы. В результате для приложения сохраняются текущая и предыдущая версии:

```text
model-forge-prod-backend:latest
model-forge-prod-backend:previous
model-forge-prod-frontend:latest
model-forge-prod-frontend:previous
```

Список образов можно проверить на нужной ВМ:

```bash
docker image ls | grep model-forge
```

Команда `docker system prune -a` в этом процессе не используется: она может удалить резервные образы и ресурсы других сервисов.

## Что происходит при ошибке

- Ошибка тестов останавливает pipeline до развёртывания.
- Ошибка backup останавливает обновление PROD.
- Ошибка сборки или healthcheck помечает deployment как failed.
- Очистка старых образов выполняется только после успешного healthcheck.
- Автоматического отката контейнеров пока нет: тег `previous` сохраняет прошлые образы для ручного восстановления.
- Откат Docker-образа не откатывает миграции PostgreSQL. Для изменений схемы нужно учитывать созданный перед deployment дамп БД.

Посмотреть причину ошибки можно в GitHub: `Actions → Model Forge CI/CD → нужный запуск → упавший шаг`.

На сервере доступны дополнительные проверки:

```bash
docker compose -p model-forge-dev -f prod.docker-compose.yml ps -a
docker compose -p model-forge-dev -f prod.docker-compose.yml logs --tail=150
```

Для PROD те же команды выполняются с проектом `model-forge-prod` из каталога `/opt/model-forge/model-forge`.

## Секреты и безопасность

- `.env` хранится отдельно на каждой ВМ и не попадает в Git.
- DEV и PROD используют разные PostgreSQL, секретные ключи, volumes и модели.
- Регистрационные токены GitHub Runner временные; их нельзя сохранять в репозитории или документации.
- Pull Request выполняет тесты на GitHub-hosted runner `ubuntu-latest`. Deploy-задания выполняются на self-hosted runner только после доверенного push в `DEV` или `main`.
- Файл workflow должен изменяться так же внимательно, как серверный код: он получает возможность выполнять команды на DEV и PROD.
