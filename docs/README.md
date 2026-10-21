# Model Forge

Веб-приложение для обучения моделей на CSV-данных. Поддерживает классификацию и регрессию, сравнение алгоритмов и скачивание обученных моделей в формате `.joblib`.

Стек: Django REST Framework, React, PostgreSQL и scikit-learn. Обучение выполняет отдельный ML-worker. Приложение разворачивается через Docker Compose; [миграция в K3s](kubernetes.md) находится в работе.

## Документация

| Раздел | Содержание |
| --- | --- |
| [Frontend](frontend.md) | Локальная разработка, структура, экраны приложения |
| [API](api.md) | Авторизация, запросы, ответы и коллекция Postman |
| [ML-движок](ml-engine.md) | Алгоритмы, очередь обучения, метрики и файлы моделей |
| [Развёртывание Compose](production-deployment.md) | Настройка сервера, Nginx, HTTPS и хранение данных |
| [CI/CD](ci-cd.md) | Проверки и обновление DEV/PROD через GitHub Actions |
| [Kubernetes](kubernetes.md) | Инфраструктура, план миграции и материалы для изучения |
| [Установка K3s](k3s-installation.md) | Подготовка нод, установка Server/Agent и диагностика |

## Локальный запуск

Требования: Docker и плагин Docker Compose. Для запуска frontend вне Docker дополнительно нужен Node.js.

Команды выполняются из корня репозитория:

```bash
cd /home/dv/Documents/model-forge
test -f .env || cp .env.example .env
docker compose -f local.docker-compose.yml up -d --build
```

Compose запускает PostgreSQL, Django API, ML-worker и React. Миграции применяются при старте backend.

| Сервис | Адрес |
| --- | --- |
| Frontend | `http://localhost:5173` |
| API | `http://localhost:8000/api/` |
| Healthcheck | `http://localhost:8000/api/health/` |

Порты 8000 и 5173 должны быть свободны. Frontend-контейнер уже запускает Vite и проксирует `/api` к backend.

Состояние и логи:

```bash
docker compose -f local.docker-compose.yml ps
docker compose -f local.docker-compose.yml logs -f backend ml-worker
```

Остановка с сохранением данных:

```bash
docker compose -f local.docker-compose.yml down
```

PostgreSQL хранит данные в volume `postgres_data`, датасеты — в `backend/media/datasets`, модели — в `backend/media/artifacts`. Параметр `down -v` удаляет volumes.

## Первое обучение

1. Зарегистрироваться или войти в приложение.
2. В разделе «Новый эксперимент» загрузить [classification.csv](examples/classification.csv).
3. Выбрать целевую колонку `completed` и алгоритмы Logistic Regression / Random Forest. Сохранить эксперимент.
4. На странице эксперимента нажать «Запустить обучение».
5. После завершения проверить метрики и скачать `.joblib`.

Статусы обучения: `ready → queued → running → completed`. При ошибке устанавливается `failed`, причина доступна в `error_message`.

Форма создания поддерживает классификацию. Для регрессии используется [API](api.md#проверка-через-postman): [regression.csv](examples/regression.csv), цель `price`, алгоритмы `linear_regression` / `random_forest`. Экран редактирования позволяет менять целевую колонку и алгоритмы без смены типа задачи.

Активный эксперимент и его датасет защищены от удаления. Эксперимент со статусом `failed` допускает исправление и повторный запуск. Повторное обучение после `completed` требует нового эксперимента.

## Архитектура

```text
React → Django API → PostgreSQL
                        ↑
                    ML-worker → процесс обучения
                        ↓
                  модели и CSV в media
```

API сохраняет задачу в PostgreSQL и возвращает `202 Accepted`. ML-worker забирает её из очереди, запускает обучение в отдельном процессе и сохраняет результат. Один экземпляр worker выполняет одну задачу за раз; несколько экземпляров могут обучать разные эксперименты параллельно.

Redis и Celery не используются. Backend и worker работают с общим каталогом `media`. Скачивание моделей доступно владельцу через API с авторизацией; маршрут `/media/` закрыт. Формат файлов и пример предсказания приведены в [документации ML-движка](ml-engine.md#содержимое-модели-и-предсказания).

## Тесты

Backend-тесты на PostgreSQL:

```bash
docker compose -f local.docker-compose.yml run --build --rm backend python manage.py test
```

Для тестов создаётся отдельная база. Отчёт о покрытии:

```bash
docker compose -f local.docker-compose.yml run --build --rm backend coverage run --rcfile=.coveragerc manage.py test --verbosity 2
docker compose -f local.docker-compose.yml run --rm backend coverage report --rcfile=.coveragerc
```

Coverage учитывает `users`, `datasets`, `experiments` и `ml_engine`. Порог в `.coveragerc` — 70%; текущий CI запускает Django tests без проверки покрытия. Проверки frontend описаны в [отдельном разделе](frontend.md#разработка-без-docker).

Проверка миграций:

```bash
docker compose -f local.docker-compose.yml exec backend python manage.py showmigrations experiments
docker compose -f local.docker-compose.yml exec backend python manage.py makemigrations --check --dry-run
```

Локальный Compose использует сервер разработки Django. Серверное развёртывание описано в [production Compose](production-deployment.md).
