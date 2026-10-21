# API Model Forge

[Документация проекта](README.md)

Базовый адрес при локальном запуске: `http://localhost:8000/api`. Пути в таблицах указаны относительно него. Запуск сервисов описан в [README](README.md#локальный-запуск).

## Авторизация

Защищённые запросы используют Token Authentication:

```http
Authorization: Token YOUR_LOGIN_TOKEN
```

Настройка Postman: **Authorization → API Key**, ключ `Authorization`, значение `Token <token>`, расположение Header. Префикс — `Token`. JSON передаётся через **Body → raw → JSON**, файлы — через **Body → form-data** с автоматически сформированным multipart-заголовком.

[Коллекция Model Forge](postman/Model%20Forge.postman_collection.json) сохраняет токен и идентификаторы объектов в переменных. Перед запросами регистрации и входа заполняются `username`, `password` и `email`. Файл CSV выбирается после импорта коллекции. Токен выдаётся при входе; ответ регистрации его не содержит.

## Эндпоинты

| Метод | Путь | Назначение / успешный ответ |
| --- | --- | --- |
| GET | `/health/` | Открытая проверка ответа HTTP-сервера, 200 |
| POST | `/auth/register/` | Создание аккаунта, 201 |
| POST | `/auth/login/` | Получение токена и текущего пользователя, 200 |
| GET | `/auth/me/` | Данные текущего пользователя, 200 |
| POST | `/auth/logout/` | Отзыв текущего токена, 200 |
| GET / POST | `/datasets/` | Список / загрузка своего CSV, 200 / 201 |
| GET / DELETE | `/datasets/{id}/` | Просмотр / удаление своего датасета, 200 / 204 |
| GET | `/experiments/algorithms/` | Доступные задачи и идентификаторы алгоритмов, 200 |
| GET / POST | `/experiments/` | Список / создание своих экспериментов, 200 / 201 |
| GET / PATCH / DELETE | `/experiments/{id}/` | Просмотр / изменение / удаление, 200 / 200 / 204 |
| POST | `/experiments/{id}/start/` | Постановка обучения в очередь, 202 |
| GET | `/experiments/{id}/results/{result_id}/download/` | Скачивание своей модели, 200 binary |

`/health/` возвращает `{"status":"ok"}` и проверяет только ответ HTTP-сервера. Проверка PostgreSQL, файлового хранилища и ML-worker выполняется полным сценарием обучения на тестовом CSV.

Синхронное обучение, загрузка готовых моделей и предсказания через HTTP API не поддерживаются.

## Проверка через Postman

Сценарий для зарегистрированного пользователя:

1. Вход: `POST /auth/login/`, тело `{"username":"your-user","password":"your-password"}`. Коллекция сохраняет `token` из ответа.
2. Загрузка CSV: `POST /datasets/`, form-data с ключом `file` типа File. Пример — `docs/examples/classification.csv`. Ответ: 201.
3. Просмотр датасета: `GET /datasets/{id}/`. Ответ содержит колонки, число строк и первые десять строк.
4. Создание эксперимента: `POST /experiments/` с JSON из примера ниже. Ответ: 201, `status: "ready"`, пустой `results`.
5. Постановка в очередь: `POST /experiments/{id}/start/` без тела. Ответ: 202, `status: "queued"`.
6. Получение статуса: `GET /experiments/{id}/`. Во время обучения статус — `running`, после завершения — `completed` или `failed`. Причина ошибки находится в `error_message`.
7. Скачивание: GET по пути `model_file` с тем же токеном. В Postman команда **Send and Download** сохраняет файл `.joblib`.

Для классификации:

```json
{
  "dataset": 1,
  "task": "classification",
  "target_column": "completed",
  "algorithms": ["logistic_regression", "random_forest"]
}
```

Значение `dataset` — идентификатор загруженного датасета. Пример регрессии для [regression.csv](examples/regression.csv):

```json
{
  "dataset": 2,
  "task": "regression",
  "target_column": "price",
  "algorithms": ["linear_regression", "random_forest"]
}
```

## Ответ завершённого эксперимента

```json
{
  "id": 1,
  "dataset": 1,
  "task": "classification",
  "target_column": "completed",
  "algorithms": ["logistic_regression", "random_forest"],
  "status": "completed",
  "error_message": "",
  "queued_at": "2026-10-10T12:00:00Z",
  "started_at": "2026-10-10T12:00:02Z",
  "finished_at": "2026-10-10T12:00:04Z",
  "created_at": "2026-10-10T11:59:00Z",
  "updated_at": "2026-10-10T12:00:04Z",
  "results": [
    {
      "id": 1,
      "algorithm": "logistic_regression",
      "metrics": {"accuracy": 1.0, "f1_macro": 1.0},
      "is_best": true,
      "model_file": "/api/experiments/1/results/1/download/",
      "created_at": "2026-10-10T12:00:04Z"
    }
  ]
}
```

Каждому алгоритму соответствует результат и файл модели. Accuracy и F1 передаются числами от 0 до 1. Критерий лучшей модели: максимальный F1 macro для классификации, минимальный MAE для регрессии. Метрики рассчитываются на общей validation-выборке; независимый финальный тест не выполняется.

## Статусы и ошибки

| Статус | Состояние | Доступные действия |
| --- | --- | --- |
| `ready` | Настройки сохранены | Изменить, удалить, запустить |
| `queued` | Задача ждёт ML-worker | Смотреть статус |
| `running` | Идёт обучение | Смотреть статус |
| `completed` | Результаты готовы | Скачать модели, удалить; для нового запуска создать другой эксперимент |
| `failed` | Обучение не завершилось | Прочитать `error_message`, повторить запуск или изменить настройки |

Изменение неудачного эксперимента возвращает статус в `ready`.

Датасет существующего эксперимента нельзя заменить через PATCH. Статус, результаты, даты и ошибки управляются сервером.

Ответы на некорректные запросы:

| Сценарий | Ожидаемый ответ |
| --- | --- |
| Отсутствующий или неверный токен | 401 |
| Объект другого пользователя | 404 |
| Пустые, повторяющиеся, неизвестные или несовместимые алгоритмы | 400 |
| Целевая колонка отсутствует в CSV | 400 при создании/изменении |
| Неверные данные или слишком мало строк | запуск принят, затем worker устанавливает `failed` |
| Повторный запуск `queued` / `running` / `completed` | 409 |
| Изменение активного эксперимента | 400 |
| Удаление активного эксперимента или его датасета | 409 |
| Отсутствующий файл модели | 404 |
| Прямой доступ к `/media/artifacts/...` | 404 |

Если ML-worker остановлен, задача остаётся `queued` в PostgreSQL. По умолчанию обучение ограничено 300 секундами. Работающий worker помечает зависшие `running` как `failed` после этого таймаута с запасом 60 секунд; автоматического повторного запуска нет.

## Реализация

Представления API проверяют владельца и передают задачу в сервисы приложения `experiments`. Очередь, таймауты и сохранение результатов описаны в [ML-движке](ml-engine.md#очередь-обучения).

`model_file` указывает на защищённый API-эндпоинт. React получает бинарный ответ через Axios с токеном и сохраняет Blob на компьютере пользователя. Запрос без авторизации отклоняется.

Справочники: [блокировки строк Django](https://docs.djangoproject.com/en/6.0/ref/models/querysets/#select-for-update), [FileResponse Django](https://docs.djangoproject.com/en/6.0/ref/request-response/#fileresponse), [Token Authentication DRF](https://www.django-rest-framework.org/api-guide/authentication/#tokenauthentication).
