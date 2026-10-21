# ML-движок

[Документация проекта](README.md)

Пакет `backend/ml_engine` обучает табличные модели. Входные данные — `pandas.DataFrame` и настройки эксперимента. Результат — обученные Pipeline и метрики. Пакет не зависит от Django; очередь, доступ к БД и авторизация реализованы в приложении `experiments`.

Запуск через интерфейс: [первое обучение](README.md#первое-обучение). HTTP-запросы: [API](api.md).

## Файлы

| Файл | Назначение |
| --- | --- |
| `data.py` | Загрузка CSV в UTF-8, проверка схемы, целевой колонки и ограничений |
| `preprocessing.py` | Заполнение пропусков, масштабирование числовых и кодирование категориальных признаков |
| `algorithms.py` | Реестр алгоритмов, проверка идентификаторов и создание новых экземпляров моделей |
| `metrics.py` | Расчёт метрик и правила выбора лучшей модели |
| `training.py` | Разделение данных, обучение, предсказания и сравнение моделей |
| `artifacts.py` | Атомарное сохранение моделей в `.joblib` с метаданными и версиями библиотек |
| `runner.py` | Адаптер JSON stdin/stdout для изолированного процесса обучения |
| `errors.py` | Доменные ошибки, которые обрабатывает worker |
| `tests/` | Модульные тесты, проверки preprocessing, сохранения моделей и адаптера |

## Данные и алгоритмы

- CSV должен быть в UTF-8, допускается BOM и разделитель-запятая. Первая строка должна содержать уникальные непустые названия колонок.
- По умолчанию разрешены файл до 10 MiB, до 50 000 строк и до 100 колонок. Ограничения можно изменить через `DatasetLimits`; API загрузки отдельно ограничивает файл 10 MiB.
- Нужны хотя бы одна колонка признаков и одна целевая колонка. Отклоняются пропуски в цели, повторяющиеся названия, неправильное число значений в строке, комплексные и бесконечные числа.
- Пропуски числовых признаков заменяются медианами обучающей выборки. Числовые признаки стандартизируются. Пропуски категориальных признаков получают значение `__missing__`; новые категории допускаются при предсказании.
- Для классификации доступны `logistic_regression` и `random_forest`. Цель должна содержать категории или целочисленные метки, минимум два класса и достаточное количество строк для стратифицированного разделения.
- Для регрессии доступны `linear_regression` и `random_forest`. Целевая колонка должна быть числовой и содержать минимум два различных значения.

Все алгоритмы используют одинаковое разделение 75%/25% с seed 42 по умолчанию. Preprocessing обучается только на строках обучающей выборки. Целевая колонка исключается из признаков.

Для классификации рассчитываются accuracy и macro F1; лучшей считается модель с максимальным macro F1. Для регрессии рассчитываются MAE, RMSE и R²; лучшей считается модель с минимальным MAE. При равенстве выбирается первый запрошенный алгоритм. Метрики относятся к validation-выборке и не являются независимой финальной оценкой. Сохранённые Pipeline обучены только на тренировочной части; автоматического дообучения на всех строках сейчас нет.

## Прямой запуск из Python

Команды выполняются из `backend` при установленных зависимостях:

```python
from ml_engine.data import load_csv
from ml_engine.training import train_experiment
from ml_engine.artifacts import save_model

data = load_csv("../docs/examples/classification.csv", "completed")
results = train_experiment(
    data,
    target_column="completed",
    task="classification",
    algorithm_names=["logistic_regression", "random_forest"],
)
best = next(result for result in results if result.is_best)
save_model(
    best.model,
    "media/artifacts/demo.joblib",
    metadata={
        "task": "classification",
        "target_column": "completed",
        "metrics": best.metrics,
    },
)
```

`TrainingResult` содержит алгоритм, JSON-совместимые метрики, обученный Pipeline и признак `is_best`.

## Очередь обучения

1. Frontend отправляет `POST /api/experiments/{id}/start/`.
2. Django сохраняет задачу в PostgreSQL со статусом `queued` и возвращает HTTP 202.
3. Процесс `python manage.py run_ml_worker` забирает задачу и ставит `running`.
4. Worker запускает `python -m ml_engine.runner` в отдельном процессе.
5. Runner читает CSV, обучает модели и создаёт временные файлы.
6. Worker сохраняет модели, метрики и статус `completed`. При ошибке ставится `failed`.

HTTP-сервер не выполняет обучение. Очередь хранится в PostgreSQL, без Redis и Celery. Один экземпляр ML-worker обрабатывает одну задачу за раз; несколько экземпляров могут выполнять разные задачи параллельно. Для начального развёртывания в K3s предусмотрена одна реплика.

Задача выбирается в короткой транзакции через `select_for_update(skip_locked=True)`, поэтому два worker-процесса не забирают одну строку. Обучение выполняется вне транзакции. Идентификатор попытки `run_id` не даёт старому процессу перезаписать результат новой попытки.

| Переменная | По умолчанию | Назначение |
| --- | --- | --- |
| `ML_TRAINING_TIMEOUT` | `300` секунд | Максимальная длительность процесса обучения |
| `ML_WORKER_POLL_INTERVAL` | `2` секунды | Интервал проверки очереди |

При остановленном worker задачи остаются `queued`. Просроченные задачи `running` переводятся работающим worker в `failed` после таймаута с запасом 60 секунд. Повторный запуск выполняется пользователем.

Код очереди находится в `backend/experiments/services.py` и `worker.py`, команда запуска — в `management/commands/run_ml_worker.py`.

Обработка одной задачи вручную, из корня проекта:

```bash
docker compose -f local.docker-compose.yml stop ml-worker
docker compose -f local.docker-compose.yml run --rm backend python manage.py run_ml_worker --once
docker compose -f local.docker-compose.yml start ml-worker
```

## Хранение данных

Файлы моделей сохраняются по пути:

```text
backend/media/artifacts/user_<id>/experiment_<id>/<run_uuid>/<algorithm>.joblib
```

Скачивание идёт через авторизованный API, публичного маршрута `/media/` нет. Файлы сначала создаются во временной папке, затем публикуются в хранилище Django. При удалении эксперимента удаляются его модели; удаление датасета удаляет и связанные эксперименты. Удаление активного обучения заблокировано.

Backend и ML-worker используют общий каталог `media`: в локальном Compose — `backend/media`, в production — volume `media_data`. Worker обращается к датасету через `dataset.file.path`, поэтому ему нужен локальный файловый путь. Требования к хранилищу при переносе в K3s описаны в [ограничениях инфраструктуры](kubernetes.md#ограничения).

## Содержимое модели и предсказания

Файл модели содержит словарь с ключами `schema_version`, `pipeline` и `metadata`. В метаданных есть время создания, версии Python и библиотек, а также данные эксперимента. Для моделей из API дополнительно сохраняются признаки, целевая колонка, алгоритм, метрики, параметры разделения и идентификаторы запуска.

```python
import joblib
import pandas as pd

artifact = joblib.load("downloaded_model.joblib")
features = artifact["metadata"]["experiment"]["feature_columns"]
new_rows = pd.read_csv("new_rows.csv")
predictions = artifact["pipeline"].predict(new_rows[features])
print(predictions)
```

Для загрузки нужны совместимые версии Python и библиотек, а также доступный пакет `ml_engine`: Pipeline использует функции из `preprocessing.py`. Файл `.joblib` содержит сериализованные Python-объекты и использует pickle; источник файла должен быть доверенным. Загрузка готовых моделей в приложение не поддерживается.

## Расширение

Алгоритмы регистрируются в `ALGORITHM_REGISTRY` файла `algorithms.py`. Фабрика получает seed и возвращает новый estimator scikit-learn. Реестр используется движком и API. Новый алгоритм должен иметь тесты для его идентификатора и поддерживаемых задач.

Метрики определяются в `metrics.py`. Изменение критерия выбора требует согласованного обновления `SELECTION_METRICS` и `selection_score`. Преобразования данных находятся в `preprocessing.py`; проверка включает обучение и восстановление артефакта. Сериализуемые вспомогательные функции размещаются на уровне модуля.

Изменения механизма очереди относятся к `experiments/services.py` и `experiments/worker.py`. Интерфейс ML-движка от очереди не зависит.

## Тесты

Из папки `backend`:

```bash
../.venv/bin/python -m unittest discover -s ml_engine/tests -t .
```

Из корня проекта через Docker, без запуска PostgreSQL:

```bash
docker compose -f local.docker-compose.yml run --build --rm --no-deps backend python -m unittest discover -s ml_engine/tests -t .
```

Полный набор тестов и Coverage описан в [основной документации](README.md). Адаптер subprocess дополнительно проверяется API-тестами на реальном обучении моделей классификации и регрессии.

Справочники: [утечка данных и Pipeline](https://scikit-learn.org/stable/common_pitfalls.html), [сохранение моделей](https://scikit-learn.org/stable/model_persistence.html), [чтение CSV](https://pandas.pydata.org/docs/reference/api/pandas.read_csv.html).
