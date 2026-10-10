# API Model Forge: обучение

Локальный адрес API: `http://localhost:8000/api`. Запустите Docker-сервисы и React по [основной инструкции](README.md). Для защищённых запросов нужен заголовок:

```http
Authorization: Token YOUR_LOGIN_TOKEN
```

В Postman выберите **Authorization → API Key**, укажите ключ `Authorization`, значение `Token <token>` и добавление в Header. Используется префикс `Token`, а не `Bearer`. JSON отправляется через **Body → raw → JSON**, загрузка файлов — через **Body → form-data**. Заголовок multipart Postman установит самостоятельно.

Импортируйте [коллекцию Model Forge](postman/Model%20Forge.postman_collection.json). Переменные коллекции сохраняют токен и идентификаторы датасета, эксперимента и результата. Укажите `username`, `password` и `email`, затем зарегистрируйтесь и войдите. Файл после импорта коллекции нужно выбрать на компьютере. Регистрация токен не возвращает — токен выдаётся при входе.

## Эндпоинты

| Метод | Путь | Назначение / успешный ответ |
| --- | --- | --- |
| GET | `/health/` | Открытая проверка готовности, 200 |
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

В этой версии нет HTTP-эндпоинта для тяжёлого синхронного обучения, запуска загруженных моделей или предсказаний.

## Проверка через Postman

1. **Вход**: `POST /auth/login/` с телом `{"username":"your-user","password":"your-password"}`. Скопируйте `token` из ответа или используйте автоматическую переменную коллекции.
2. **Загрузка CSV**: `POST /datasets/`, в form-data добавьте ключ **`file`** (нижний регистр), тип **File**, выберите `docs/examples/classification.csv`. Ожидается 201.
3. **Просмотр**: `GET /datasets/{id}/` без тела. Ответ содержит колонки, число строк и первые десять строк.
4. **Создание эксперимента**: `POST /experiments/` с JSON ниже. Ожидается 201, `status: "ready"` и пустой `results`.
5. **Запуск**: `POST /experiments/{id}/start/` без тела. Ожидается 202 и `status: "queued"`. Это означает «принято», а не «завершено».
6. **Результат**: повторяйте `GET /experiments/{id}/`. Worker переведёт эксперимент через `running` в `completed`. При `failed` смотрите `error_message`.
7. **Скачивание**: отправьте GET на путь `model_file` результата с тем же токеном. В Postman используйте **Send and Download**, чтобы сохранить `.joblib`.

Для классификации:

```json
{
  "dataset": 1,
  "task": "classification",
  "target_column": "completed",
  "algorithms": ["logistic_regression", "random_forest"]
}
```

Замените `dataset` на свой идентификатор. Для регрессии загрузите [regression.csv](examples/regression.csv) и используйте:

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

Для каждого выбранного алгоритма создаётся результат и файл модели. В JSON accuracy и F1 находятся в диапазоне от 0 до 1 и не являются процентами. Для классификации выигрывает максимальный F1 macro, для регрессии — минимальный MAE. Метрики считаются на общей validation-выборке, а не на независимом финальном тесте.

## Статусы и ошибки

- `ready`: эксперимент можно изменить, удалить или запустить.
- `queued` / `running`: можно только смотреть статус; изменение, удаление и повторный запуск заблокированы.
- `completed`: можно смотреть результаты, скачивать модели и удалить эксперимент; для другой конфигурации создайте новый.
- `failed`: изучите `error_message`, повторите запуск или измените эксперимент; изменение возвращает статус в `ready`.

Датасет существующего эксперимента нельзя заменить через PATCH. Статус, результаты, даты и ошибки управляются сервером.

Проверьте в Postman негативные сценарии:

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

Если worker остановлен, очередь остаётся в PostgreSQL, а задача будет ждать. По умолчанию попытка обучения ограничена 300 секундами. После перезапуска worker устаревшие запуски восстанавливаются после таймаута с запасом 60 секунд.

## Как устроена реализация

API-представления проверяют владельца и вызывают сервисы жизненного цикла. Worker получает строки в короткой транзакции через PostgreSQL `select_for_update(skip_locked=True)`, обучает модель вне транзакции в отдельном процессе и затем атомарно публикует результаты. Файлы сначала создаются во временной папке и попадают в хранилище Django только после успешного обучения.

Ссылка `model_file` — защищённый API-эндпоинт. React скачивает бинарный ответ через Axios с токеном и сохраняет Blob локально; обычная ссылка без авторизации не сработает.

Полезные материалы: [блокировки строк Django](https://docs.djangoproject.com/en/6.0/ref/models/querysets/#select-for-update), [FileResponse Django](https://docs.djangoproject.com/en/6.0/ref/request-response/#fileresponse), [Token Authentication DRF](https://www.django-rest-framework.org/api-guide/authentication/#tokenauthentication).
