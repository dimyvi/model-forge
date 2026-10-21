# Развёртывание через Docker Compose

[Документация проекта](README.md) · [CI/CD](ci-cd.md) · [Kubernetes](kubernetes.md)

Конфигурация Compose-стендов до миграции в Kubernetes:

| Стенд | IP | Домен |
| --- | --- | --- |
| PROD | `192.168.1.169` | `model-forge.ru` |
| DEV | `192.168.1.221` | `dev.model-forge.ru` |

Приложение работает в Docker Compose, внешний HTTP/HTTPS принимает системный Nginx. Обновления выполняет [GitHub Actions](ci-cd.md). Состав новой инфраструктуры описан в [Kubernetes](kubernetes.md#виртуальные-машины).

## Сервисы

| Сервис | Назначение |
| --- | --- |
| `db` | PostgreSQL, без публикации порта на хосте |
| `migrate` | Применяет миграции и собирает Django-статику, затем завершается |
| `backend` | Django API через Gunicorn, `127.0.0.1:8000` |
| `ml-worker` | Выполняет обучение из очереди PostgreSQL |
| `frontend` | Nginx с собранным React и Django-статикой, `127.0.0.1:8080` |

Внешний Nginx отправляет `/api/` и `/admin/` в backend, остальные пути — во frontend. `/media/` закрыт; модели скачиваются через API с авторизацией. На роутере публикуются только 80/443 входного Nginx.

В Dockerfile используются `python:3.12-slim` для Django/ML, `node:20-alpine` для сборки React и `nginx:alpine` для его раздачи. PostgreSQL использует `postgres:16-alpine`. Python Slim выбран для совместимости с готовыми пакетами ML-библиотек.

## Подготовка сервера

Требования: Docker с Compose, Nginx, Git и клонированный репозиторий. Каталог PROD, используемый workflow:

```bash
cd /opt/model-forge/model-forge
git pull --ff-only origin main
```

Далее команды выполняются из этого каталога. Конфигурация: `prod.docker-compose.yml`, `backend/prod.Dockerfile`, `frontend/prod.Dockerfile` и файлы Nginx в репозитории.

## Переменные окружения

Только если `.env` ещё нет:

```bash
cp .env.prod.example .env
chmod 600 .env
```

Обязательные настройки: `POSTGRES_PASSWORD`, `DJANGO_SECRET_KEY`, `DJANGO_ALLOWED_HOSTS` и `DJANGO_CSRF_TRUSTED_ORIGINS`. Генерация случайного значения для пароля или ключа:

```bash
python3 -c 'import secrets; print(secrets.token_urlsafe(64))'
```

Существующий `.env` сохраняется при обновлении. Изменение `POSTGRES_PASSWORD` не меняет пароль пользователя уже созданной базы. Переменные `DJANGO_EMAIL_*` зарезервированы для почты; отправка писем не реализована.

Проверка конфигурации без вывода значений:

```bash
docker compose -f prod.docker-compose.yml config --quiet
```

## Запуск

```bash
docker compose -f prod.docker-compose.yml up -d --build
docker compose -f prod.docker-compose.yml ps -a
```

Ожидаемое состояние: `db`, `backend`, `ml-worker` и `frontend` запущены, `migrate` завершён с кодом `0`.

```bash
curl -f http://127.0.0.1:8000/api/health/
curl -fI http://127.0.0.1:8080/
```

Команды проверяют HTTP-ответы. Проверка БД, файлов и ML-worker — [обучение на тестовом CSV](README.md#первое-обучение) после настройки HTTPS.

Журналы сервисов:

```bash
docker compose -f prod.docker-compose.yml logs --tail=100 db migrate backend ml-worker frontend
```

## Nginx и HTTPS

Первоначальная HTTP-конфигурация:

```bash
sudo cp deploy/nginx/model-forge.conf /etc/nginx/conf.d/model-forge.conf
sudo setsebool -P httpd_can_network_connect on
sudo nginx -t
sudo systemctl reload nginx
```

`setsebool` разрешает системному Nginx на Rocky Linux с SELinux подключаться к портам контейнеров. DNS-имена должны указывать на внешний IP роутера, TCP 80/443 — направляться на эту ВМ.

```bash
curl -fI http://model-forge.ru/
curl -f http://model-forge.ru/api/health/
```

Выпуск сертификата после проверки HTTP:

```bash
sudo dnf install -y certbot python3-certbot-nginx
sudo certbot --nginx -d model-forge.ru -d www.model-forge.ru --redirect
sudo nginx -t
sudo certbot renew --dry-run
```

Certbot добавляет TLS в установленную конфигурацию Nginx. HTTP-шаблон из репозитория используется только при первоначальной настройке и не должен заменять действующую HTTPS-конфигурацию. Просмотр сертификатов: `sudo certbot certificates`. Автоматическое продление настраивается через systemd/cron.

Проверка: `https://model-forge.ru/` и `https://model-forge.ru/api/health/`. При отсутствии NAT loopback на роутере публичный адрес проверяется из внешней сети, например через мобильный интернет.

## Django Admin

Создание суперпользователя:

```bash
docker compose -f prod.docker-compose.yml exec backend python manage.py createsuperuser
```

Панель доступна по `/admin/`. Зарегистрированы стандартные пользователи и группы Django. Датасеты и эксперименты управляются через приложение и API. Обычная регистрация не предоставляет административных прав.

## Данные, обновление и восстановление

Production Compose использует volumes `model-forge-prod_postgres_data`, `model-forge-prod_media_data` и `model-forge-prod_static_data`. `docker compose down` сохраняет их, `down -v` удаляет.

При обновлении через CI/CD создаётся дамп PostgreSQL в `/home/admin/model-forge-backups` и сохраняются предыдущие образы. CSV и модели резервируются отдельно из `media_data`. Копии должны храниться вне ВМ и проходить проверку восстановления. Автоматический откат не реализован.

Перед ручным обновлением требуется резервная копия данных. Затем выполняются `git pull --ff-only origin main` и `docker compose -f prod.docker-compose.yml up -d --build`.

Для Compose-стендов маршрут `dev.model-forge.ru` через внешний Nginx PROD настраивается отдельно: шаблон `deploy/nginx/model-forge.conf` содержит только production-домены. DEV и PROD используют разные `.env`, базы и volumes.
