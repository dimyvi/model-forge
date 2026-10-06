import axios from 'axios';

const api = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json',
  },
});

api.interceptors.request.use((config) => {
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

  const messages = Object.values(data).flatMap((value) => {
    if (Array.isArray(value)) {
      return value.map(String);
    }

    return [String(value)];
  });

  return messages.join(' ') || fallback;
}

export default api;
