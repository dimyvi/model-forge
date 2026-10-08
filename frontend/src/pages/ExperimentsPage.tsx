import { t, useLanguage, translateMessage } from '../utils/language';
import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import api, { getApiErrorMessage } from '../services/api';
import { algorithmLabels, getFilename, statusLabels } from '../utils/display';

type Experiment = {
  id: number; dataset: number; task: string; target_column: string; algorithms: string[];
  status: string; created_at: string;
  results: { algorithm: string; metrics: Record<string, number>; model_file: string | null; is_best: boolean }[];
};
type Dataset = { id: number; file: string };

function ExperimentsPage() {
  const { locale } = useLanguage();
  const [experiments, setExperiments] = useState<Experiment[]>([]);
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [pendingDeleteId, setPendingDeleteId] = useState<number | null>(null);
  const [deletingId, setDeletingId] = useState<number | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    async function loadExperiments() {
      try {
        const [history, data] = await Promise.all([
          api.get<Experiment[]>('/experiments/', { signal: controller.signal }),
          api.get<Dataset[]>('/datasets/', { signal: controller.signal }),
        ]);
        if (!controller.signal.aborted) { setExperiments(history.data); setDatasets(data.data); }
      } catch (requestError) {
        if (!controller.signal.aborted) setError(getApiErrorMessage(requestError, 'Не удалось загрузить эксперименты.'));
      } finally { if (!controller.signal.aborted) setIsLoading(false); }
    }
    loadExperiments();
    return () => controller.abort();
  }, []);

  async function handleDelete(id: number) {
    if (pendingDeleteId !== id) { setPendingDeleteId(id); return; }
    setDeletingId(id);
    setError('');
    try {
      await api.delete(`/experiments/${id}/`);
      setExperiments((current) => current.filter((experiment) => experiment.id !== id));
      setPendingDeleteId(null);
    } catch (requestError) {
      setError(getApiErrorMessage(requestError, 'Не удалось удалить эксперимент.'));
    } finally { setDeletingId(null); }
  }

  return (
    <div>
      <div className="page-heading"><div><h1>{t("Эксперименты")}</h1><p>{t("Сохранённые настройки и результаты обучения.")}</p></div></div>
      {error && <div className="alert alert-danger" role="alert">{translateMessage(error)}</div>}
      {isLoading ? <p className="text-muted" role="status">{t("Загрузка экспериментов…")}</p>
        : experiments.length === 0 ? <div className="card"><div className="empty-state"><h2>{error ? t('Данные недоступны') : t('Экспериментов пока нет')}</h2><p>{t("Создайте первый эксперимент в разделе «Новый эксперимент».")}</p></div></div>
          : <div className="experiment-list">{experiments.map((experiment) => (
            <article className="experiment-row" key={experiment.id}>
              <div className="experiment-identity"><h2>{t('Эксперимент #{id}', { id: experiment.id })}</h2><Link to={`/datasets/${experiment.dataset}`}>{getFilename(datasets.find((item) => item.id === experiment.dataset)?.file ?? t('Датасет #{id}', { id: experiment.dataset }))}</Link></div>
              <div className="experiment-parameters"><span>{experiment.task === 'classification' ? t('Классификация') : t('Регрессия')} · {t('цель')}: <strong>{experiment.target_column}</strong></span><small>{experiment.algorithms.map((name) => algorithmLabels[name] ?? name).join(' · ')}</small></div>
              <div className="experiment-status"><span className={`status-pill status-${experiment.status}`}>{statusLabels[experiment.status] ? t(statusLabels[experiment.status]) : experiment.status}</span><small>{experiment.results.length ? t('Моделей: {count}', { count: experiment.results.length.toLocaleString(locale) }) : t('Результатов пока нет')}</small></div>
              <div className="experiment-actions">
                <span className="experiment-date">{new Date(experiment.created_at).toLocaleDateString(locale, { day: 'numeric', month: 'short' })}</span>
                {experiment.status === 'ready' && <Link to={`/experiments/${experiment.id}/edit`} className="quiet-link">{t("Изменить")}</Link>}
                {pendingDeleteId === experiment.id && <button type="button" className="text-button" disabled={deletingId === experiment.id} onClick={() => setPendingDeleteId(null)}>{t("Отмена")}</button>}
                <button type="button" className="text-button delete-button" disabled={deletingId === experiment.id} onClick={() => handleDelete(experiment.id)}>{deletingId === experiment.id ? t('Удаление…') : pendingDeleteId === experiment.id ? t('Подтвердить') : t('Удалить')}</button>
              </div>
            </article>
          ))}</div>}
    </div>
  );
}
export default ExperimentsPage;
