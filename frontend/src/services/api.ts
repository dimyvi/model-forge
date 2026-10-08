import axios from 'axios';
import { getLanguage } from '../utils/language';

const api = axios.create({
  baseURL: '/api',
});

api.interceptors.request.use((config) => {
  config.headers['Accept-Language'] = getLanguage();
  const token = localStorage.getItem('auth_token');

  if (token) {
    config.headers.Authorization = `Token ${token}`;
  }

  return config;
});

export function getApiErrorMessage(error: unknown, fallback: string) {
  if (!axios.isAxiosError(error)) {
    return fallback;
  }

  const data = error.response?.data as Record<string, unknown> | undefined;

  if (!data) {
    return fallback;
  }

  function collectMessages(value: unknown): string[] {
    if (typeof value === 'string') return [value];
    if (Array.isArray(value)) return value.flatMap(collectMessages);
    if (value && typeof value === 'object') return Object.values(value).flatMap(collectMessages);
    return [];
  }

  return collectMessages(data).join('\n') || fallback;
}

export default api;
