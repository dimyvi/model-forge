# CI/CD Model Forge

[К документации проекта](README.md)

CI/CD — проверки кода и автоматическое обновление приложения. Настройки находятся в `.github/workflows/ci-cd.yml`.

**Сейчас workflow разворачивает Docker Compose на прежних стендах.** Он ещё не публикует образы в GHCR и не обновляет новые кластеры K3s. План следующего этапа описан в [Kubernetes](kubernetes.md#порядок-переноса-model-forge).

## Когда запускается workflow

| Событие | Проверки | Что происходит после успеха |
| --- | --- | --- |
| Push в `DEV` | Django tests, ESLint, сборка React | Обновление DEV через Compose |
| Pull Request в `main` | Те же проверки | Только проверка |
| Merge или push в `main` | Те же проверки | Резервная копия БД и обновление PROD через Compose |

Если изменены только файлы в `docs/`, workflow не запускается. При изменении кода вместе с документацией проверки выполняются.

## Где выполняются задания

Тесты идут на GitHub-hosted runner `ubuntu-latest`. Развёртывание — на self-hosted runner: это служба на сервере, которая получает задания из GitHub.

| Стенд Compose | Ветка | Label runner | Каталог приложения | Compose project |
| --- | --- | --- | --- | --- |
| DEV | `DEV` | `model-forge-dev` | `/opt/model-forge` | `model-forge-dev` |
| PROD | `main` | `model-forge-prod` | `/opt/model-forge/model-forge` | `model-forge-prod` |

Эти пути взяты из workflow; это не пути установки K3s. Runner работает от `admin`, которому нужен доступ к Docker.

Проверка службы на соответствующем сервере:

```bash
cd /opt/actions-runner
sudo ./svc.sh status
```

В GitHub список находится в `Settings → Actions → Runners`. Свободный runner отображается как `Idle`.

## Как выпустить изменение

1. Внесите изменения в `DEV`, проверьте их локально и отправьте ветку в GitHub.
2. Дождитесь успешного workflow и проверьте приложение на DEV.
3. Создайте Pull Request из `DEV` в `main` и дождитесь проверок.
4. После merge workflow обновит PROD. Проверьте полный сценарий с тестовым CSV.

Прямой push в `main` тоже запускает обновление PROD. Ограничение таких push настраивается в правилах ветки GitHub; сам workflow их не запрещает.

Перед обновлением deploy-задание сохраняет образы приложения с тегом `previous`, обновляет код и выполняет `docker compose up -d --build`. Затем проверяет ответы API и frontend и удаляет dangling-образы — образы без тега.

Для PROD перед этим дополнительно создаётся дамп PostgreSQL:

```text
/home/admin/model-forge-backups/db-YYYYMMDD-HHMMSS.sql.gz
```

Workflow проверяет, что файл непустой. Это не проверка восстановления. Файлы датасетов и моделей в этот дамп не входят.

## Если обновление не удалось

| Где ошибка | Результат |
| --- | --- |
| Тесты | Deploy не запускается |
| Backup PROD | Обновление останавливается |
| Сборка или HTTP-проверка | Deploy завершается с ошибкой; автоматического отката нет |

Сначала откройте `Actions → Model Forge CI/CD → нужный запуск → упавший шаг`.

На DEV Compose-сервере из `/opt/model-forge`:

```bash
docker compose -p model-forge-dev -f prod.docker-compose.yml ps -a
docker compose -p model-forge-dev -f prod.docker-compose.yml logs --tail=150
```

На PROD из `/opt/model-forge/model-forge` замените `model-forge-dev` на `model-forge-prod`.

Тег `previous` сохраняет предыдущие образы для ручного восстановления. Откат образа не отменяет миграции базы. Для восстановления данных нужны дамп и проверенная процедура восстановления.

## Что хранится отдельно

- `.env` находится на сервере и не попадает в Git. DEV и PROD используют разные секреты, базы и volumes.
- Регистрационные токены runner и токены подключения K3s не записываются в документацию.
- Pull Request запускает проверки на GitHub-hosted runner. Deploy-задания выполняются после push в `DEV` или `main` и могут выполнять команды на сервере.
- Изменение только документации не переносит runner и приложение в Kubernetes: для этого позже потребуется отдельное изменение workflow.
