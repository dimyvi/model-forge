import { t, translateMessage, useLanguage } from '../utils/language';
import { useEffect, useRef, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import api, { getApiErrorMessage } from '../services/api';
import Icon from '../components/Icon';
import { algorithmLabels, getFilename, statusLabels } from '../utils/display';
import type { MessageKey } from '../utils/messages';
import { canEditExperiment, downloadExperimentModel, isExperimentActive } from '../services/experiments';
import type { Experiment, ExperimentResult, ExperimentStatus } from '../services/experiments';

type Dataset = { id: number; file: string; rows_count: number; columns: string[] };
const statusMessages: Record<ExperimentStatus, MessageKey> = {
  ready: 'Эксперимент готов к запуску обучения.',
  queued: 'Эксперимент в очереди. Статус обновляется автоматически.',
  running: 'Модели обучаются. Результаты появятся автоматически.',
  completed: 'Обучение завершено. Сравните метрики и скачайте модель.',
  failed: 'Обучение завершилось с ошибкой. Повторите запуск или измените настройки.',
};
const metricLabels: Record<string, MessageKey> = {
  accuracy: 'Точность', f1: 'F1-мера', f1_macro: 'F1-мера (macro)',
  recall: 'Полнота', precision: 'Точность (precision)',
  mae: 'Средняя абсолютная ошибка (MAE)', rmse: 'Корень средней квадратичной ошибки (RMSE)', r2: 'Коэффициент детерминации (R²)',
};

function ExperimentDetailPage() {
  const { locale } = useLanguage();
  const { id } = useParams();
  const [experiment, setExperiment] = useState<Experiment | null>(null);
  const [dataset, setDataset] = useState<Dataset | null>(null);
  const [error, setError] = useState('');
  const [pollError, setPollError] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const [isStarting, setIsStarting] = useState(false);
  const [downloadingId, setDownloadingId] = useState<number | null>(null);
  const requestController = useRef<AbortController | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    requestController.current = controller;
    setIsLoading(true);
    setExperiment(null);
    setDataset(null);
    setError('');
    setPollError('');
    setIsStarting(false);
    setDownloadingId(null);
    async function load() {
      try {
        const response = await api.get<Experiment>(`/experiments/${id}/`, { signal: controller.signal });
        const datasetResponse = await api.get<Dataset>(`/datasets/${response.data.dataset}/`, { signal: controller.signal });
        if (!controller.signal.aborted) {
          setExperiment(response.data);
          setDataset(datasetResponse.data);
        }
      } catch (requestError) {
        if (!controller.signal.aborted) setError(getApiErrorMessage(requestError, 'Не удалось загрузить просмотр эксперимента.'));
      } finally {
        if (!controller.signal.aborted) setIsLoading(false);
      }
    }
    load();
    return () => controller.abort();
  }, [id]);

  const experimentId = experiment?.id;
  const experimentStatus = experiment?.status;
  useEffect(() => {
    if (!experimentId || !experimentStatus || !isExperimentActive(experimentStatus)) return;
    const controller = new AbortController();
    let timer: ReturnType<typeof setTimeout>;
    async function poll() {
      let keepPolling = true;
      try {
        const response = await api.get<Experiment>(`/experiments/${experimentId}/`, { signal: controller.signal });
        if (controller.signal.aborted) return;
        setExperiment(response.data);
        setPollError('');
        keepPolling = isExperimentActive(response.data.status);
      } catch (requestError) {
        if (!controller.signal.aborted) setPollError(getApiErrorMessage(requestError, 'Не удалось обновить статус. Повторяем автоматически.'));
      }
      if (!controller.signal.aborted && keepPolling) timer = setTimeout(poll, 2000);
    }
    timer = setTimeout(poll, 2000);
    return () => { controller.abort(); clearTimeout(timer); };
  }, [experimentId, experimentStatus]);

  async function handleStart() {
    const signal = requestController.current?.signal;
    if (!experiment || !canEditExperiment(experiment.status) || isStarting || !signal || signal.aborted) return;
    setIsStarting(true);
    setError('');
    setPollError('');
    try {
      const response = await api.post<Experiment>(`/experiments/${experiment.id}/start/`, undefined, { signal });
      if (!signal.aborted) setExperiment(response.data);
    } catch (requestError) {
      if (signal.aborted) return;
      setError(getApiErrorMessage(requestError, 'Не удалось запустить обучение.'));
      // Refresh after conflicts or a lost response so actions use the server's status.
      try {
        const response = await api.get<Experiment>(`/experiments/${experiment.id}/`, { signal });
        if (!signal.aborted) setExperiment(response.data);
      } catch {
        // Keep the original start error if the refresh also fails.
      }
    } finally {
      if (!signal.aborted) setIsStarting(false);
    }
  }

  async function handleDownload(result: ExperimentResult) {
    const signal = requestController.current?.signal;
    if (!experiment || downloadingId !== null || !result.model_file || !signal || signal.aborted) return;
    setDownloadingId(result.id);
    setError('');
    try {
      await downloadExperimentModel(experiment.id, result, signal);
    } catch (requestError) {
      if (!signal.aborted) setError(getApiErrorMessage(requestError, 'Не удалось скачать модель.'));
    } finally {
      if (!signal.aborted) setDownloadingId(null);
    }
  }

  if (isLoading) return <p className="text-muted" role="status">{t('Загрузка просмотра…')}</p>;
  if (!experiment || !dataset) return <div className="alert alert-danger" role="alert">{translateMessage(error || 'Эксперимент не найден.')}</div>;

  const status = statusLabels[experiment.status] ? t(statusLabels[experiment.status]) : experiment.status;
  const formattedDate = (date: string) => new Date(date).toLocaleDateString(locale, { day: 'numeric', month: 'long', year: 'numeric' });
  const formattedTime = (date: string) => new Date(date).toLocaleString(locale, { day: 'numeric', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit', second: '2-digit' });
  const active = isExperimentActive(experiment.status);

  return (
    <div className="experiment-detail-page">
      <div className="page-heading experiment-detail-heading">
        <div>
          <Link to="/experiments" className="quiet-link detail-back"><Icon name="arrow" size={15} />{t('К списку экспериментов')}</Link>
          <h1>{t('Эксперимент #{id}', { id: experiment.id })}</h1>
          <p>{t('Просмотр эксперимента')}</p>
        </div>
        {canEditExperiment(experiment.status) && !isStarting && <Link to={`/experiments/${experiment.id}/edit`} className="btn btn-outline-secondary"><Icon name="plus" />{t('Редактировать настройки')}</Link>}
      </div>
      {error && <div className="alert alert-danger" role="alert">{translateMessage(error)}</div>}
      {pollError && <div className="alert alert-warning" role="alert">{translateMessage(pollError)}</div>}

      <div className="experiment-detail-grid">
        <div className="experiment-detail-main">
          <section className="card detail-status-card">
            <div className="detail-status-label">{t('Статус эксперимента')}</div>
            <div className="detail-status-row" role="status"><span className={`status-pill status-${experiment.status}`}>{status}</span><span className="detail-status-message">{t(statusMessages[experiment.status])}</span></div>
            {experiment.error_message && <div className="alert alert-danger mt-3 mb-0 text-break" role="alert" style={{ whiteSpace: 'pre-wrap' }}>{translateMessage(experiment.error_message)}</div>}
            {canEditExperiment(experiment.status) && <div className="mt-3"><button type="button" className="btn btn-primary" onClick={handleStart} disabled={isStarting}>{isStarting ? t('Запуск…') : experiment.status === 'failed' ? t('Повторить обучение') : t('Запустить обучение')}</button></div>}
          </section>

          <section className="card detail-panel">
            <div className="panel-heading"><h2>{t('Результаты')}</h2><span className="detail-panel-caption">{experiment.results.length ? t('Моделей: {count}', { count: experiment.results.length.toLocaleString(locale) }) : t('Результатов пока нет')}</span></div>
            {experiment.results.length === 0 ? (
              <div className="detail-empty-state"><span className="empty-icon"><Icon name="experiment" size={26} /></span><h3>{active ? t('Результаты готовятся') : experiment.status === 'failed' ? t('Обучение завершилось с ошибкой') : t('Модели пока не обучались')}</h3><p>{experiment.status === 'ready' ? t('Запустите обучение, чтобы получить метрики и модели.') : t(statusMessages[experiment.status])}</p></div>
            ) : (
              <div className="results-table-wrap"><table className="table results-table mb-0"><thead><tr><th>{t('Алгоритм')}</th><th>{t('Метрики')}</th><th>{t('Модель')}</th></tr></thead><tbody>{experiment.results.map((result) => <tr key={result.id}><td><strong>{algorithmLabels[result.algorithm] ?? result.algorithm}</strong>{result.is_best && <span className="result-best">{t('Лучшая модель')}</span>}</td><td><div className="metric-list">{Object.entries(result.metrics).map(([name, value]) => <span key={name}><small>{metricLabels[name] ? t(metricLabels[name]) : name}</small><strong>{typeof value === 'number' ? value.toFixed(3) : value}</strong></span>)}</div></td><td>{result.model_file ? <button type="button" className="btn btn-sm btn-outline-secondary" disabled={downloadingId !== null} onClick={() => handleDownload(result)}>{downloadingId === result.id ? t('Скачивание…') : t('Скачать модель')}</button> : <span className="text-muted">{t('Модель недоступна')}</span>}</td></tr>)}</tbody></table></div>
            )}
          </section>
        </div>

        <aside className="experiment-detail-side">
          <section className="card detail-panel"><div className="panel-heading"><h2>{t('Конфигурация')}</h2></div><dl className="detail-list"><div><dt>{t('Датасет')}</dt><dd><Link to={`/datasets/${dataset.id}`}>{getFilename(dataset.file)}</Link></dd></div><div><dt>{t('Задача')}</dt><dd>{experiment.task === 'classification' ? t('Классификация') : t('Регрессия')}</dd></div><div><dt>{t('Целевая колонка')}</dt><dd><code>{experiment.target_column}</code></dd></div><div><dt>{t('Выбранные алгоритмы')}</dt><dd><ul className="detail-algorithm-list">{experiment.algorithms.map((algorithm) => <li key={algorithm}>{algorithmLabels[algorithm] ?? algorithm}</li>)}</ul></dd></div></dl></section>
          <section className="card detail-panel"><div className="panel-heading"><h2>{t('Датасет и данные')}</h2></div><dl className="detail-list"><div><dt>{t('Файл')}</dt><dd>{getFilename(dataset.file)}</dd></div><div><dt>{t('Строк')}</dt><dd>{dataset.rows_count.toLocaleString(locale)}</dd></div><div><dt>{t('Колонок')}</dt><dd>{dataset.columns.length.toLocaleString(locale)}</dd></div></dl><Link to={`/datasets/${dataset.id}`} className="detail-side-link">{t('Открыть датасет')}<Icon name="arrow" size={15} /></Link></section>
          <p className="detail-dates">{t('Создан')}: {formattedDate(experiment.created_at)}<br />{t('Обновлён')}: {formattedDate(experiment.updated_at)}{experiment.queued_at && <><br />{t('Поставлен в очередь')}: {formattedTime(experiment.queued_at)}</>}{experiment.started_at && <><br />{t('Обучение начато')}: {formattedTime(experiment.started_at)}</>}{experiment.finished_at && <><br />{t('Обучение завершено')}: {formattedTime(experiment.finished_at)}</>}</p>
        </aside>
      </div>
    </div>
  );
}

export default ExperimentDetailPage;
