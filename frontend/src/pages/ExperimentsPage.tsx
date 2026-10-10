import { t, useLanguage, translateMessage } from '../utils/language';
import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import api, { getApiErrorMessage } from '../services/api';
import { algorithmLabels, getFilename, statusLabels } from '../utils/display';
import { canEditExperiment, isExperimentActive } from '../services/experiments';
import type { Experiment } from '../services/experiments';

type Dataset = { id: number; file: string };

function ExperimentsPage() {
  const { locale } = useLanguage();
  const [experiments, setExperiments] = useState<Experiment[]>([]);
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [pollError, setPollError] = useState('');
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

  const hasActiveExperiments = experiments.some((experiment) => isExperimentActive(experiment.status));
  useEffect(() => {
    if (!hasActiveExperiments || deletingId !== null) return;
    const controller = new AbortController();
    let timer: ReturnType<typeof setTimeout>;
    async function poll() {
      let keepPolling = true;
      try {
        const response = await api.get<Experiment[]>('/experiments/', { signal: controller.signal });
        if (controller.signal.aborted) return;
        setExperiments(response.data);
        setPollError('');
        keepPolling = response.data.some((experiment) => isExperimentActive(experiment.status));
      } catch (requestError) {
        if (!controller.signal.aborted) setPollError(getApiErrorMessage(requestError, 'Не удалось обновить статус. Повторяем автоматически.'));
      }
      if (!controller.signal.aborted && keepPolling) timer = setTimeout(poll, 2000);
    }
    timer = setTimeout(poll, 2000);
    return () => { controller.abort(); clearTimeout(timer); };
  }, [hasActiveExperiments, deletingId]);

  async function handleDelete(id: number) {
    const experiment = experiments.find((item) => item.id === id);
    if (!experiment || isExperimentActive(experiment.status) || deletingId !== null) return;
    if (pendingDeleteId !== id) { setPendingDeleteId(id); return; }
    setDeletingId(id);
    setError('');
    try {
      const latest = await api.get<Experiment>(`/experiments/${id}/`);
      setExperiments((current) => current.map((item) => item.id === id ? latest.data : item));
      if (isExperimentActive(latest.data.status)) {
        setPendingDeleteId(null);
        setError('Нельзя удалить эксперимент во время обучения или ожидания в очереди.');
        return;
      }
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
      {pollError && <div className="alert alert-warning" role="alert">{translateMessage(pollError)}</div>}
      {isLoading ? <p className="text-muted" role="status">{t("Загрузка экспериментов…")}</p>
        : experiments.length === 0 ? <div className="card"><div className="empty-state"><h2>{error ? t('Данные недоступны') : t('Экспериментов пока нет')}</h2><p>{t("Создайте первый эксперимент в разделе «Новый эксперимент».")}</p></div></div>
          : <div className="card shadow-sm"><div className="table-responsive"><table className="table table-hover align-middle mb-0 experiment-table"><thead><tr><th>{t('Эксперимент')}</th><th>{t('Датасет')}</th><th>{t('Параметры эксперимента')}</th><th>{t('Статус эксперимента')}</th><th>{t('Создан')}</th><th className="text-end">{t('Действия')}</th></tr></thead><tbody>{experiments.map((experiment) => (
            <tr key={experiment.id}>
              <td><Link className="experiment-table-title" to={`/experiments/${experiment.id}`}>{t('Эксперимент #{id}', { id: experiment.id })}</Link></td>
              <td><Link className="experiment-table-dataset" to={`/datasets/${experiment.dataset}`}>{getFilename(datasets.find((item) => item.id === experiment.dataset)?.file ?? t('Датасет #{id}', { id: experiment.dataset }))}</Link></td>
              <td><div className="experiment-table-settings"><span>{experiment.task === 'classification' ? t('Классификация') : t('Регрессия')}</span><small>{t('цель')}: <strong>{experiment.target_column}</strong></small><small>{experiment.algorithms.map((name) => algorithmLabels[name] ?? name).join(' · ')}</small></div></td>
              <td><span className={`status-pill status-${experiment.status}`}>{statusLabels[experiment.status] ? t(statusLabels[experiment.status]) : experiment.status}</span><small className="table-status-note">{isExperimentActive(experiment.status) ? t('Статус обновляется автоматически') : experiment.results.length ? t('Моделей: {count}', { count: experiment.results.length.toLocaleString(locale) }) : t('Результатов пока нет')}</small></td>
              <td className="table-date">{new Date(experiment.created_at).toLocaleDateString(locale, { day: 'numeric', month: 'short' })}</td>
              <td className="text-end"><div className="experiment-table-actions"><Link to={`/experiments/${experiment.id}`} className="btn btn-sm btn-outline-primary experiment-action-open">{t('Открыть')}</Link>{canEditExperiment(experiment.status) && <Link to={`/experiments/${experiment.id}/edit`} className="btn btn-sm btn-outline-secondary experiment-action-edit">{t("Изменить")}</Link>}{pendingDeleteId === experiment.id && !isExperimentActive(experiment.status) && <button type="button" className="btn btn-sm btn-secondary experiment-action-cancel" disabled={deletingId !== null} onClick={() => setPendingDeleteId(null)}>{t('Отмена')}</button>}<button type="button" className="btn btn-sm btn-outline-danger experiment-action-delete" disabled={deletingId !== null || isExperimentActive(experiment.status)} title={isExperimentActive(experiment.status) ? t('Нельзя удалить эксперимент во время обучения или ожидания в очереди.') : undefined} onClick={() => handleDelete(experiment.id)}>{deletingId === experiment.id ? t('Удаление…') : pendingDeleteId === experiment.id && !isExperimentActive(experiment.status) ? t('Подтвердить') : t('Удалить')}</button></div></td>
            </tr>
          ))}</tbody></table></div></div>}
    </div>
  );
}
export default ExperimentsPage;
