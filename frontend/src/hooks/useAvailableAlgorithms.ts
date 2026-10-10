import { useEffect, useState } from 'react';
import api, { getApiErrorMessage } from '../services/api';
import type { AvailableAlgorithms } from '../services/experiments';

export function useAvailableAlgorithms() {
  const [available, setAvailable] = useState<AvailableAlgorithms | null>(null);
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const [retry, setRetry] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    setIsLoading(true);
    setError('');
    api.get<AvailableAlgorithms>('/experiments/algorithms/', { signal: controller.signal }).then((response) => {
      if (!controller.signal.aborted) setAvailable(response.data);
    }).catch((requestError: unknown) => {
      if (!controller.signal.aborted) setError(getApiErrorMessage(requestError, 'Не удалось загрузить алгоритмы.'));
    }).finally(() => {
      if (!controller.signal.aborted) setIsLoading(false);
    });
    return () => controller.abort();
  }, [retry]);

  return { available, error, isLoading, reload: () => setRetry((current) => current + 1) };
}
