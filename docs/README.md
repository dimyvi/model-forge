# Model Forge

Model Forge — приложение для обучения моделей на CSV-данных. Пользователь загружает датасет, выбирает целевую колонку и алгоритмы, запускает эксперимент и скачивает готовую модель.

## С чего начать

| Задача | Инструкция |
| --- | --- |
| Запустить приложение на компьютере | [Локальный запуск](#локальный-запуск) |
| Пройти первый эксперимент | [Первое обучение](#первое-обучение) |
| Изучить интерфейс и frontend | [Frontend](frontend.md) |
| Проверить запросы в Postman | [API](api.md) |
| Разобраться в обучении и ML-worker | [ML-движок](ml-engine.md) |
| Развернуть приложение через Docker Compose | [Развёртывание Compose](production-deployment.md) |
| Понять автоматические обновления | [CI/CD](ci-cd.md) |
| Изучить Kubernetes и план переноса проекта | [Kubernetes](kubernetes.md) |
| Повторить установку K3s или проверить ноды | [Установка и проверка K3s](k3s-installation.md) |

В репозитории пока реализовано развёртывание через Docker Compose. По результатам ручной проверки 22 октября 2026 года отдельно подготовлены DEV- и PROD-кластеры K3s. Перенос Model Forge в них ещё предстоит: Kubernetes-манифестов и deploy в K3s в текущем CI/CD нет.

## Локальный запуск

Нужен Docker с плагином Compose. Node.js на компьютере нужен только при запуске frontend без контейнера.

Все команды в этом разделе выполняются из корня проекта:

```bash
cd /home/dv/Documents/model-forge
```

Если `.env` ещё нет, создайте его из примера. Существующий файл не заменяйте:

```bash
cp .env.example .env
```

Запустите приложение:

```bash
docker compose -f local.docker-compose.yml up -d --build
```

Compose запустит PostgreSQL, Django API, ML-worker и React. Django применит миграции автоматически.

| Что открыть | Адрес |
| --- | --- |
| Приложение | `http://localhost:5173` |
| API | `http://localhost:8000/api/` |
| Проверка HTTP-сервера | `http://localhost:8000/api/health/` |

Если порт 8000 уже занят запущенным вручную Django, сначала остановите этот процесс. Отдельно запускать `npm run dev` при работающем frontend-контейнере не нужно.

Основные команды:

```bash
# Состояние контейнеров
docker compose -f local.docker-compose.yml ps

# Логи API и обучения; Ctrl+C завершает просмотр логов
docker compose -f local.docker-compose.yml logs -f backend ml-worker

# Остановка с сохранением данных
docker compose -f local.docker-compose.yml down
```

База хранится в Docker volume `postgres_data`. Датасеты находятся в `backend/media/datasets`, модели — в `backend/media/artifacts`. Команда `down -v` удаляет volumes, поэтому для обычной остановки она не нужна.

## Первое обучение

1. Откройте приложение и зарегистрируйтесь или войдите.
2. Перейдите в «Новый эксперимент» и загрузите [classification.csv](examples/classification.csv).
3. Выберите целевую колонку `completed`, алгоритмы Logistic Regression и Random Forest. Сохраните эксперимент.
4. На странице эксперимента нажмите «Запустить обучение».
5. Дождитесь перехода `ready → queued → running → completed`. При `failed` прочитайте сообщение об ошибке.
6. Посмотрите метрики и скачайте модель `.joblib`.

Форма создания сейчас поддерживает классификацию. Регрессия доступна через [API](api.md#проверка-через-postman): используйте [regression.csv](examples/regression.csv), цель `price` и алгоритмы `linear_regression` / `random_forest`. Экран редактирования меняет целевую колонку и алгоритмы, но не тип задачи.

Пока эксперимент находится в очереди или обучается, его и исходный датасет нельзя удалить. Неудачный эксперимент можно исправить и запустить снова. Для нового обучения после `completed` создайте новый эксперимент.

## Как устроено приложение

```text
Браузер с React → Django API → PostgreSQL: пользователи, эксперименты, очередь
                                     ↑
                                 ML-worker → отдельный процесс обучения
                                     ↓
                              модели и CSV в media
```

Django принимает запрос и сохраняет задачу. Отдельный ML-worker запускает обучение и записывает результат. **Worker Kubernetes** — это ВМ для запуска Pod, а **ML-worker** — процесс приложения для обучения моделей; это разные роли.

Один процесс `run_ml_worker` обрабатывает одну задачу за раз. Если запустить несколько таких процессов, они смогут обучать разные эксперименты параллельно. Для первого стенда оставляем один ML-worker. Redis и Celery в текущем коде не используются.

Файлы моделей скачиваются через API с токеном владельца. Публичного доступа к `/media/` нет. Содержимое `.joblib` и пример предсказания описаны в [ML-движке](ml-engine.md#содержимое-модели-и-предсказания).

## Проверки перед изменениями

Из корня проекта запустите backend-тесты на PostgreSQL:

```bash
docker compose -f local.docker-compose.yml run --build --rm backend python manage.py test
```

Тестовая база создаётся отдельно; рабочие данные не очищаются. Для отчёта о покрытии:

```bash
docker compose -f local.docker-compose.yml run --build --rm backend coverage run --rcfile=.coveragerc manage.py test --verbosity 2
docker compose -f local.docker-compose.yml run --rm backend coverage report --rcfile=.coveragerc
```

Coverage проверяет `users`, `datasets`, `experiments` и `ml_engine`; порог в конфигурации — 70%. Текущий CI запускает Django tests без проверки этого порога. Команды проверки frontend приведены в [его инструкции](frontend.md#команды-без-docker).

Проверить миграции:

```bash
docker compose -f local.docker-compose.yml exec backend python manage.py showmigrations experiments
docker compose -f local.docker-compose.yml exec backend python manage.py makemigrations --check --dry-run
```

Локальный Compose использует сервер разработки Django. Для серверного запуска предназначены [production Compose](production-deployment.md) и будущий [перенос в K3s](kubernetes.md#порядок-переноса-model-forge).
