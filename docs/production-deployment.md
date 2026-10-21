# Развёртывание через Docker Compose

[К документации проекта](README.md) · [Автоматические обновления](ci-cd.md) · [План перехода на Kubernetes](kubernetes.md)

Эта инструкция описывает прежний Compose-стенд. По записи от 17 октября 2026 года PROD использовал `192.168.1.169`, DEV — `192.168.1.221`; PROD-домен — `model-forge.ru`, DEV — `dev.model-forge.ru`. Их доступность сейчас отдельно не проверялась. Новые ВМ K3s имеют другие адреса и перечислены в [разделе Kubernetes](kubernetes.md#наши-пять-вм).

Здесь приложение запускает Docker Compose, а системный Nginx принимает HTTP/HTTPS. Эти команды не устанавливают приложение в K3s. Обычные обновления существующего Compose-стенда выполняет [CI/CD](ci-cd.md).

## Как устроен запуск

| Сервис | Назначение |
| --- | --- |
| `db` | PostgreSQL, без публикации порта на хосте |
| `migrate` | Применяет миграции и собирает Django-статику, затем завершается |
| `backend` | Django API через Gunicorn, `127.0.0.1:8000` |
| `ml-worker` | Выполняет обучение из очереди PostgreSQL |
| `frontend` | Nginx с собранным React и Django-статикой, `127.0.0.1:8080` |

Внешний Nginx отправляет `/api/` и `/admin/` в backend, остальные пути — во frontend. `/media/` закрыт; модели скачиваются через API с авторизацией. На роутере публикуются только 80/443 входного Nginx.

В Dockerfile используются `python:3.12-slim` для Django/ML, `node:20-alpine` для сборки React и `nginx:alpine` для его раздачи. PostgreSQL использует `postgres:16-alpine`. Python Slim выбран для совместимости с готовыми пакетами ML-библиотек.

## 1. Проверить сервер и код

На Compose-сервере должны быть установлены Docker с Compose, Nginx и Git. Репозиторий уже должен быть клонирован. Для принятого в workflow PROD-пути:

```bash
cd /opt/model-forge/model-forge
git pull --ff-only origin main
```

Все следующие команды Compose выполняются из этого каталога. Используются `prod.docker-compose.yml`, `backend/prod.Dockerfile`, `frontend/prod.Dockerfile` и конфигурации Nginx из репозитория.

## 2. Подготовить настройки

Только если `.env` ещё нет:

```bash
cp .env.prod.example .env
chmod 600 .env
```

В редакторе заполните `POSTGRES_PASSWORD` и `DJANGO_SECRET_KEY`. Проверьте `DJANGO_ALLOWED_HOSTS` и `DJANGO_CSRF_TRUSTED_ORIGINS` для своих доменов. Для генерации случайного значения:

```bash
python3 -c 'import secrets; print(secrets.token_urlsafe(64))'
```

Существующий `.env` сохраняйте. Смена пароля PostgreSQL только в `.env` не меняет пароль пользователя уже созданной базы. Настройки `DJANGO_EMAIL_*` оставлены для будущей почты: отправка писем в приложении пока не реализована.

Проверьте конфигурацию без вывода секретов:

```bash
docker compose -f prod.docker-compose.yml config --quiet
```

## 3. Запустить и проверить контейнеры

```bash
docker compose -f prod.docker-compose.yml up -d --build
docker compose -f prod.docker-compose.yml ps -a
```

`db`, `backend`, `ml-worker` и `frontend` должны работать. Завершение `migrate` с кодом `0` — нормальный результат.

```bash
curl -f http://127.0.0.1:8000/api/health/
curl -fI http://127.0.0.1:8080/
```

Это проверяет HTTP-ответы. Для проверки базы, файлов и ML-worker после настройки HTTPS пройдите [первое обучение](README.md#первое-обучение).

Если сервис не запустился:

```bash
docker compose -f prod.docker-compose.yml logs --tail=100 db migrate backend ml-worker frontend
```

## 4. Подключить Nginx и HTTPS

При первом развёртывании установите HTTP-конфигурацию:

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

Получите сертификат после успешной проверки HTTP:

```bash
sudo dnf install -y certbot python3-certbot-nginx
sudo certbot --nginx -d model-forge.ru -d www.model-forge.ru --redirect
sudo nginx -t
sudo certbot renew --dry-run
```

Certbot добавит TLS в установленную конфигурацию. **При обновлении приложения не копируйте HTTP-шаблон поверх работающей HTTPS-конфигурации.** Проверьте сертификаты командой `sudo certbot certificates` и настройку автоматического продления в systemd/cron.

Откройте `https://model-forge.ru/` и `https://model-forge.ru/api/health/`. Если сайт не открывается из домашней LAN, проверьте через мобильный интернет: роутер может не поддерживать обращение из LAN к своему внешнему IP.

## Django Admin

Для первого администратора:

```bash
docker compose -f prod.docker-compose.yml exec backend python manage.py createsuperuser
```

Панель доступна по `/admin/`. Обычная регистрация не даёт административных прав. Сейчас там зарегистрированы пользователи и группы Django; датасеты и эксперименты управляются через приложение и API.

## Данные, обновление и восстановление

Production Compose использует volumes `model-forge-prod_postgres_data`, `model-forge-prod_media_data` и `model-forge-prod_static_data`. `docker compose down` сохраняет их, `down -v` удаляет.

При обновлении через CI/CD создаётся дамп PostgreSQL в `/home/admin/model-forge-backups` и сохраняются предыдущие образы. Файлы CSV и моделей в дамп не входят: копируйте `media_data` отдельно, храните backup вне ВМ и проверяйте восстановление. Автоматического отката сейчас нет.

Ручное обновление через `git pull --ff-only origin main` и `docker compose -f prod.docker-compose.yml up -d --build` не выполняет backup вместо вас. Используйте его только после отдельной резервной копии и проверки изменений.

В прежней схеме внешний Nginx PROD также направлял `dev.model-forge.ru` на отдельный DEV Compose-сервер. Такой маршрут нужно настраивать отдельно: шаблон `deploy/nginx/model-forge.conf` содержит только production-домены. DEV и PROD должны использовать разные `.env`, базы и volumes.
