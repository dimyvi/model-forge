import type { MessageKey } from './messages';

export function getFilename(path: string) {
  const name = path.split('/').pop() ?? path;
  try { return decodeURIComponent(name); } catch { return name; }
}

export const algorithmLabels: Record<string, string> = {
  logistic_regression: 'Logistic Regression',
  random_forest: 'Random Forest',
};

export const statusLabels: Record<string, MessageKey> = {
  ready: 'Настроен', queued: 'В очереди', running: 'Обучается', completed: 'Завершён', failed: 'Ошибка',
};
