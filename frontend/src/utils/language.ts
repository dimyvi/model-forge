import { useSyncExternalStore } from 'react';
import { englishMessages } from './messages';
import type { MessageKey } from './messages';

export type Language = 'ru' | 'en';
const storageKey = 'model-forge.language';
const listeners = new Set<() => void>();

function readLanguage(): Language {
  try {
    return localStorage.getItem(storageKey) === 'en' ? 'en' : 'ru';
  } catch {
    return 'ru';
  }
}

let language = readLanguage();

export function getLanguage() {
  return language;
}

export function t(key: MessageKey, values: Record<string, string | number> = {}): string {
  const message = language === 'en' ? englishMessages[key] : key;
  return message.replace(/\{(\w+)\}/g, (placeholder, name: string) =>
    values[name] === undefined ? placeholder : String(values[name]),
  );
}

export function initializeLanguage() {
  document.documentElement.lang = language;
  document.title = t('Model Forge — данные и эксперименты');
}

export function setLanguage(next: Language) {
  language = next;
  initializeLanguage();
  try {
    localStorage.setItem(storageKey, next);
  } catch {
    // Keep the choice for this visit even when browser storage is unavailable.
  }
  listeners.forEach((listener) => listener());
}

function subscribe(listener: () => void) {
  listeners.add(listener);
  return () => { listeners.delete(listener); };
}

export function useLanguage() {
  const current = useSyncExternalStore(subscribe, getLanguage);
  return { language: current, locale: current === 'en' ? 'en-US' : 'ru-RU', setLanguage };
}

const englishKeys = new Map(Object.entries(englishMessages).map(([key, value]) => [value as string, key as MessageKey]));
const apiAliases: Record<string, MessageKey> = {
  'Authentication credentials were not provided.': 'Сессия истекла. Войдите снова.',
  'Invalid token.': 'Сессия истекла. Войдите снова.',
  'The submitted file is empty.': 'Файл пустой. Выберите CSV с данными.',
};

// Error messages stay in their original form in state, so an open error also
// changes language. Unknown server details are preserved rather than discarded.
export function translateMessage(message: string): string {
  return message.split('\n').map((line) => {
    const key = Object.prototype.hasOwnProperty.call(englishMessages, line)
      ? line as MessageKey : englishKeys.get(line) ?? apiAliases[line];
    if (key) return t(key);
    const minLength = line.match(/^Ensure this field has at least (\d+) characters\.$/);
    if (minLength) return t('Значение должно содержать не менее {count} символов.', { count: minLength[1] });
    const maxLength = line.match(/^Ensure this field has no more than (\d+) characters\.$/);
    if (maxLength) return t('Значение должно содержать не более {count} символов.', { count: maxLength[1] });
    if (line.startsWith('Не удалось прочитать CSV: ')) {
      return t('Не удалось прочитать CSV: {details}', { details: line.slice('Не удалось прочитать CSV: '.length) });
    }
    return line;
  }).join('\n');
}
