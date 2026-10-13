# Frontend Model Forge

Frontend построен на React, TypeScript и Vite.

## Основные команды

Команды выполняются из папки `frontend`:

```bash
npm ci
npm run dev
npm run build
npm run lint
```

- `npm run dev` запускает локальный сервер разработки с автоматическим обновлением страницы.
- `npm run build` проверяет TypeScript и собирает production-версию.
- `npm run lint` проверяет код по правилам ESLint.

## Структура

- `src/` — исходный код React-приложения.
- `src/pages/` — страницы приложения.
- `src/components/` — переиспользуемые компоненты интерфейса.
- `src/services/` — запросы к Django API.
- `src/types/` — типы TypeScript.
- `public/` — статические файлы, которые не обрабатываются сборщиком.

Документация проекта находится в папке `docs`. Backend и frontend общаются через REST API Django.

## Основные экраны

Скриншоты интерфейса хранятся в [docs/screenshots](screenshots) и подключены к [основной документации](README.md#интерфейс-приложения):

- `01-login.png` — вход пользователя;
- `02-dashboard.png` — обзор проекта;
- `03-datasets.png` — датасеты;
- `04-experiments.png` — эксперименты;
- `05-result_experiment.png` — метрики и результат обучения.

Эти изображения описывают текущий пользовательский поток. При изменении интерфейса соответствующий скриншот нужно заменить, сохранив понятное имя файла.

## Запуск через Docker Compose

Frontend входит в общий локальный Compose-запуск проекта. Из корня проекта выполните:

```bash
docker compose -f local.docker-compose.yml up --build
```

После запуска откройте `http://localhost:5173`. Vite проксирует запросы `/api` к контейнеру Django `backend`.
