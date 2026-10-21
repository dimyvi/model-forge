# CI/CD Model Forge

[Документация проекта](README.md)

Workflow `.github/workflows/ci-cd.yml` запускает проверки backend/frontend и обновляет DEV/PROD через Docker Compose.

Публикация образов в registry и развёртывание в K3s входят в [план миграции](kubernetes.md#план-миграции).

## События

| Событие | Проверки | Развёртывание |
| --- | --- | --- |
| Push в `DEV` | Django tests, ESLint, сборка React | Обновление DEV через Compose |
| Pull Request в `main` | Те же проверки | Только проверка |
| Merge или push в `main` | Те же проверки | Резервная копия БД и обновление PROD через Compose |

Если изменены только файлы в `docs/`, workflow не запускается. При изменении кода вместе с документацией проверки выполняются.

## Runners

Тесты выполняются на GitHub-hosted runner `ubuntu-latest`. Deploy-задания — на self-hosted runners соответствующих стендов.

| Стенд Compose | Ветка | Label runner | Каталог приложения | Compose project |
| --- | --- | --- | --- | --- |
| DEV | `DEV` | `model-forge-dev` | `/opt/model-forge` | `model-forge-dev` |
| PROD | `main` | `model-forge-prod` | `/opt/model-forge/model-forge` | `model-forge-prod` |

Службы runners работают от пользователя `admin` с доступом к Docker.

Проверка службы на соответствующем сервере:

```bash
cd /opt/actions-runner
sudo ./svc.sh status
```

Список в GitHub: `Settings → Actions → Runners`. Состояние свободного runner — `Idle`.

## Выпуск изменений

1. Внести изменения в `DEV`, выполнить локальные проверки и отправить ветку в GitHub.
2. Дождаться успешного workflow и проверить приложение на DEV.
3. Создать Pull Request из `DEV` в `main`, выполнить merge после проверок.
4. После обновления PROD пройти сценарий с тестовым CSV.

Push в `main` запускает обновление PROD независимо от наличия Pull Request. Ограничение прямых push задаётся правилами ветки GitHub.

Deploy-задание сохраняет текущие образы с тегом `previous`, обновляет код и выполняет `docker compose up -d --build`. После успешной HTTP-проверки API и frontend удаляются dangling-образы.

Для PROD перед этим дополнительно создаётся дамп PostgreSQL:

```text
/home/admin/model-forge-backups/db-YYYYMMDD-HHMMSS.sql.gz
```

Workflow проверяет непустой размер дампа. Проверка восстановления и резервное копирование датасетов/моделей выполняются отдельно.

## Диагностика

| Этап с ошибкой | Результат |
| --- | --- |
| Тесты | Deploy не запускается |
| Backup PROD | Обновление останавливается |
| Сборка или HTTP-проверка | Deploy завершается с ошибкой; автоматического отката нет |

Журнал выполнения в GitHub: `Actions → Model Forge CI/CD → запуск → шаг с ошибкой`.

На DEV Compose-сервере из `/opt/model-forge`:

```bash
docker compose -p model-forge-dev -f prod.docker-compose.yml ps -a
docker compose -p model-forge-dev -f prod.docker-compose.yml logs --tail=150
```

Для PROD команды выполняются из `/opt/model-forge/model-forge` с параметром `-p model-forge-prod`.

Тег `previous` сохраняет предыдущие образы для ручного восстановления. Откат образа не отменяет миграции базы. Для восстановления данных нужны дамп и проверенная процедура восстановления.

## Секреты и доступ

- `.env` находится на сервере и не попадает в Git. DEV и PROD используют разные секреты, базы и volumes.
- Регистрационные токены runners и токены подключения K3s хранятся вне репозитория.
- Pull Request запускает проверки на GitHub-hosted runner. Deploy-задания выполняются после push в `DEV` или `main` и могут выполнять команды на сервере.
