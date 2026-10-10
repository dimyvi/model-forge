# Model Forge

## Локальный запуск

Нужны Docker Compose и Node.js. Все команды ниже выполняются из корня проекта `/home/dv/Documents/model-forge`, даже если этот README открыт в папке `docs`.

1. Если `.env` ещё нет, создайте локальный файл настроек из примера. Существующий `.env` сохраняйте:

   ```bash
   cp .env.example .env
   ```

2. Из корня проекта запустите Django, PostgreSQL и ML-worker:

   ```bash
   docker compose -f local.docker-compose.yml up -d --build
   ```

   Django сам применит миграции. Worker запустится после готовности API. API будет доступно на `http://localhost:8000`; это сервер данных, React открывается отдельно.

   Посмотреть состояние и логи:

   ```bash
   docker compose -f local.docker-compose.yml ps
   docker compose -f local.docker-compose.yml logs -f backend ml-worker
   ```

3. В другом терминале запустите frontend:

   ```bash
   cd frontend
   npm ci
   npm run dev
   ```

   Откройте адрес, который покажет Vite (обычно `http://localhost:5173`).

Если Django уже запущен вручную на порту `8000`, остановите его перед запуском Compose, чтобы освободить порт.

PostgreSQL хранит данные в Docker volume `postgres_data`, файлы датасетов — в `backend/media/datasets`, модели — в `backend/media/artifacts`. Для остановки используйте `docker compose -f local.docker-compose.yml down`: данные сохраняются. Для очереди и нескольких workers используйте PostgreSQL; SQLite оставлен для простых локальных проверок.

## Как пользоваться обучением

1. Откройте React, зарегистрируйтесь или войдите.
2. В разделе «Новый эксперимент» загрузите CSV или выберите свой датасет. Для первого запуска подойдёт [classification.csv](examples/classification.csv).
3. Выберите целевую колонку `completed` и алгоритмы Logistic Regression / Random Forest. Сохраните эксперимент.
4. На странице эксперимента нажмите «Запустить обучение».
5. Статус будет обновляться автоматически: `ready → queued → running → completed` или `failed`.
6. На этой же странице появятся метрики, отметка лучшей модели и кнопки скачивания `.joblib`.

Текущий экран создания эксперимента настраивает классификацию. Регрессия также поддерживается движком и API: пример [regression.csv](examples/regression.csv), цель `price`, алгоритмы `linear_regression` / `random_forest`. На странице редактирования можно изменить задачу и алгоритмы.

Эксперимент со статусом `failed` можно исправить или запустить повторно. Для нового запуска завершённого эксперимента создайте новую конфигурацию. Во время ожидания/обучения настройки, эксперимент и его датасет защищены от изменения и удаления. При удалении завершённого эксперимента удаляются и его модели; удаление датасета удаляет связанные эксперименты и их модели.

Подробные запросы, ответы и действия в Postman: [API](api.md). Готовая коллекция: [Model Forge.postman_collection.json](postman/Model%20Forge.postman_collection.json).

## Где находятся модели и что внутри

```text
backend/media/artifacts/user_<id>/experiment_<id>/<run_uuid>/<algorithm>.joblib
```

Файл содержит обученный Pipeline: подготовку признаков, сам алгоритм и метаданные. Метрики и ссылка на файл хранятся в PostgreSQL. Скачивание требует токен владельца; публичного доступа через `/media/` нет. Папка `media/` не попадает в Git.

Для использования скачанной модели нужны зависимости из `backend/local.requirements.txt` и пакет `ml_engine` из этого проекта. Пример предсказаний и ограничения совместимости — в [документации ML-модуля](ml-engine.md#содержимое-модели-и-предсказания).

## Тесты

Тесты лежат рядом с Django-приложениями: например, `backend/users/tests/` и `backend/datasets/tests/`. Это удобно: тесты конкретного приложения находятся рядом с его кодом.

Запустить весь набор на PostgreSQL можно из корня проекта:

```bash
docker compose -f local.docker-compose.yml run --build --rm backend python manage.py test
```

Тестовая база создаётся отдельно и удаляется после завершения; рабочие данные не очищаются.

Чтобы запустить тесты с Coverage и вывести отчёт, выполни из корня проекта:

```bash
docker compose -f local.docker-compose.yml run --build --rm backend coverage run --rcfile=.coveragerc manage.py test --verbosity 2
docker compose -f local.docker-compose.yml run --rm backend coverage report --rcfile=.coveragerc
```

Coverage считает покрытие `users`, `datasets`, `experiments` и `ml_engine`; миграции и сами тесты в отчёт не входят. Отчёт показывает общий процент, а также непокрытые строки. Настроенный минимальный порог — 70%.

## Архитектура обучения

```text
React → Django API → очередь в PostgreSQL
                           ↓
                     ML-worker
                           ↓
                 отдельный ML-процесс
                           ↓
             метрики в БД + файлы в media
```

Django HTTP-запрос только сохраняет задачу и возвращает `202 Accepted`. `run_ml_worker` забирает задачу из БД, вызывает `ml_engine.runner` в отдельном процессе и сохраняет результат. Worker обрабатывает один эксперимент за раз. Блокировки PostgreSQL не дают двум workers забрать одну задачу; номер попытки не даёт устаревшему процессу перезаписать новые результаты.

В `.env` можно задать `ML_TRAINING_TIMEOUT` (по умолчанию 300 секунд) и `ML_WORKER_POLL_INTERVAL` (2 секунды). Неудачный запуск сохраняет понятную ошибку без частичных результатов. Если worker аварийно выключился, новый worker пометит старое обучение как ошибочное после таймаута с запасом 60 секунд; затем запуск можно повторить. Ожидающая задача останется `queued`, пока worker не запущен.

Основные файлы:

| Файл | Назначение |
| --- | --- |
| `backend/experiments/views.py` | Запросы API, права доступа, скачивание |
| `backend/experiments/services.py` | Правила состояний и постановка в очередь |
| `backend/experiments/worker.py` | Получение задачи, таймаут, сохранение результата |
| `backend/experiments/management/commands/run_ml_worker.py` | Команда запуска worker |
| `backend/ml_engine/` | Подготовка данных, обучение, метрики, сериализация |

Чтобы обработать одну задачу вручную вместо постоянного worker:

```bash
docker compose -f local.docker-compose.yml stop ml-worker
docker compose -f local.docker-compose.yml run --rm backend python manage.py run_ml_worker --once
docker compose -f local.docker-compose.yml start ml-worker
```

Redis/Celery не нужны для текущей небольшой очереди. Позже можно заменить механизм очереди и вынести файлы в объектное хранилище, сохранив независимый ML-модуль. Локальный Docker Compose использует development-сервер Django и не предназначен для production-развёртывания.

## Миграции

Миграция `0003_training_lifecycle` добавляет даты запуска/завершения, ошибку и идентификатор попытки. `0004_recover_legacy_runs` возвращает старые активные эксперименты без номера попытки в состояние `failed`, чтобы их можно было исправить и запустить заново. Рабочие пользователи, датасеты и эксперименты сохраняются.

```bash
docker compose -f local.docker-compose.yml exec backend python manage.py showmigrations experiments
docker compose -f local.docker-compose.yml exec backend python manage.py makemigrations --check --dry-run
```

Миграции применяются автоматически при старте backend. Тесты ML-модуля независимы от Django и БД; отдельные команды приведены в [документации ML-модуля](ml-engine.md).
