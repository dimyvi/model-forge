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
