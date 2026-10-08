import { t, useLanguage, translateMessage } from '../utils/language';
import { useEffect, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import api, { getApiErrorMessage } from '../services/api';
import SelectField from '../components/SelectField';
import AlgorithmChoices from '../components/AlgorithmChoices';
import { getFilename } from '../utils/display';

type Experiment = { id: number; dataset: number; task: string; target_column: string; algorithms: string[]; status: string };
type DatasetDetails = { file: string; columns: string[]; preview: Record<string, string | null>[] };

function ExperimentEditPage() {
  useLanguage();
  const { id } = useParams();
  const navigate = useNavigate();
  const [experiment, setExperiment] = useState<Experiment | null>(null);
  const [dataset, setDataset] = useState<DatasetDetails | null>(null);
  const [targetColumn, setTargetColumn] = useState('');
  const [algorithms, setAlgorithms] = useState<string[]>([]);
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);

  useEffect(() => {
    const controller = new AbortController();
    async function loadExperiment() {
      try {
        const response = await api.get<Experiment>(`/experiments/${id}/`, { signal: controller.signal });
        const data = await api.get<DatasetDetails>(`/datasets/${response.data.dataset}/`, { signal: controller.signal });
        if (controller.signal.aborted) return;
        setExperiment(response.data);
        setDataset(data.data);
        setTargetColumn(response.data.target_column);
        setAlgorithms(response.data.algorithms);
      } catch (requestError) {
        if (!controller.signal.aborted) setError(getApiErrorMessage(requestError, 'Не удалось загрузить эксперимент.'));
      } finally { if (!controller.signal.aborted) setIsLoading(false); }
    }
    loadExperiment();
    return () => controller.abort();
  }, [id]);

  async function handleSave() {
    if (!dataset?.columns.includes(targetColumn) || algorithms.length === 0) {
      setError('Выберите целевую колонку и хотя бы один алгоритм.');
      return;
    }
    setError('');
    setIsSaving(true);
    try {
      await api.patch(`/experiments/${id}/`, { task: experiment?.task, target_column: targetColumn, algorithms });
      navigate('/experiments');
    } catch (requestError) {
      setError(getApiErrorMessage(requestError, 'Не удалось сохранить изменения.'));
    } finally { setIsSaving(false); }
  }

  if (isLoading) return <p className="text-muted" role="status">{t("Загрузка эксперимента…")}</p>;
  if (!experiment || !dataset) return <div className="alert alert-danger" role="alert">{translateMessage(error)}</div>;
  const locked = experiment.status !== 'ready';

  return (
    <div className="experiment-builder">
      <div className="page-heading"><div><h1>{t('Эксперимент #{id}', { id: experiment.id })}</h1><p>{t('{file} · редактирование настроек', { file: getFilename(dataset.file) })}</p></div><Link to="/experiments" className="btn btn-outline-secondary">{t("К экспериментам")}</Link></div>
      <section className="card builder-section">
        <div className="builder-section-heading"><div><h2>{t("Настройки эксперимента")}</h2><p>{t("Измените целевую колонку или набор алгоритмов.")}</p></div></div>
        {error && <div className="alert alert-danger" role="alert">{translateMessage(error)}</div>}
        {locked && <div className="alert alert-info">{t("Настройки можно менять только до запуска обучения.")}</div>}
        <div className="settings-grid">
          <SelectField label={t("Целевая колонка")} value={targetColumn} options={dataset.columns.map((column) => ({ value: column, label: column, description: t('Примеры: {values}', { values: [...new Set(dataset.preview.map((row) => row[column]).filter((value) => value != null && value !== ''))].slice(0, 3).join(', ') || t('нет значений в предпросмотре') }) }))} onChange={setTargetColumn} disabled={isSaving || locked} placeholder={t("Выберите колонку")} hint={t("Остальные колонки будут использоваться как признаки.")} />
          <div><span className="form-label d-block">{t("Задача")}</span><div className="task-value">{experiment.task === 'classification' ? t('Классификация') : experiment.task}<span>{t("Категория или класс")}</span></div></div>
        </div>
        <AlgorithmChoices value={algorithms} onChange={setAlgorithms} disabled={isSaving || locked} />
        <div className="builder-footer"><Link to="/experiments" className="quiet-link">{t("Отмена")}</Link><button type="button" className="btn btn-primary" onClick={handleSave} disabled={isSaving || locked || !targetColumn || algorithms.length === 0}>{isSaving ? t('Сохранение…') : t('Сохранить изменения')}</button></div>
      </section>
    </div>
  );
}
export default ExperimentEditPage;
