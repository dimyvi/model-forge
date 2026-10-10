import { t, useLanguage, translateMessage } from '../utils/language';
import { useEffect, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import api, { getApiErrorMessage } from '../services/api';
import SelectField from '../components/SelectField';
import AlgorithmChoices from '../components/AlgorithmChoices';
import { getFilename } from '../utils/display';
import { canEditExperiment } from '../services/experiments';
import type { Experiment } from '../services/experiments';
import { useAvailableAlgorithms } from '../hooks/useAvailableAlgorithms';

type DatasetDetails = { file: string; columns: string[]; preview: Record<string, string | null>[] };

function ExperimentEditPage() {
  useLanguage();
  const { id } = useParams();
  const navigate = useNavigate();
  const algorithmOptions = useAvailableAlgorithms();
  const [experiment, setExperiment] = useState<Experiment | null>(null);
  const [dataset, setDataset] = useState<DatasetDetails | null>(null);
  const [targetColumn, setTargetColumn] = useState('');
  const [algorithms, setAlgorithms] = useState<string[]>([]);
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const availableAlgorithms = experiment ? algorithmOptions.available?.[experiment.task] ?? [] : [];
  const selectedAlgorithms = algorithms.filter((algorithm) => availableAlgorithms.some((option) => option.id === algorithm));

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
    if (!experiment || !canEditExperiment(experiment.status) || isSaving || algorithmOptions.isLoading) return;
    if (!dataset?.columns.includes(targetColumn) || selectedAlgorithms.length === 0) {
      setError('Выберите целевую колонку и хотя бы один алгоритм.');
      return;
    }
    setError('');
    setIsSaving(true);
    try {
      const latest = await api.get<Experiment>(`/experiments/${id}/`);
      setExperiment(latest.data);
      if (!canEditExperiment(latest.data.status)) {
        setError('Настройки можно менять до запуска или после ошибки обучения.');
        return;
      }
      await api.patch(`/experiments/${id}/`, { task: experiment.task, target_column: targetColumn, algorithms: selectedAlgorithms });
      navigate(`/experiments/${id}`);
    } catch (requestError) {
      setError(getApiErrorMessage(requestError, 'Не удалось сохранить изменения.'));
    } finally { setIsSaving(false); }
  }

  if (isLoading) return <p className="text-muted" role="status">{t("Загрузка эксперимента…")}</p>;
  if (!experiment || !dataset) return <div className="alert alert-danger" role="alert">{translateMessage(error)}</div>;
  const locked = !canEditExperiment(experiment.status);

  return (
    <div className="experiment-builder">
      <div className="page-heading"><div><h1>{t('Эксперимент #{id}', { id: experiment.id })}</h1><p>{t('{file} · редактирование настроек', { file: getFilename(dataset.file) })}</p></div><Link to="/experiments" className="btn btn-outline-secondary">{t("К экспериментам")}</Link></div>
      <section className="card builder-section">
        <div className="builder-section-heading"><div><h2>{t("Настройки эксперимента")}</h2><p>{t("Измените целевую колонку или набор алгоритмов.")}</p></div></div>
        {error && <div className="alert alert-danger" role="alert">{translateMessage(error)}</div>}
        {algorithmOptions.error && <div className="alert alert-danger" role="alert">{translateMessage(algorithmOptions.error)} <button type="button" className="btn btn-sm btn-outline-secondary" onClick={algorithmOptions.reload}>{t('Повторить загрузку алгоритмов')}</button></div>}
        {locked && <div className="alert alert-info">{t('Настройки можно менять до запуска или после ошибки обучения.')}</div>}
        {experiment.status === 'failed' && <div className="alert alert-info">{t('Сохранение изменений подготовит эксперимент к повторному запуску.')}</div>}
        <div className="settings-grid">
          <SelectField label={t("Целевая колонка")} value={targetColumn} options={dataset.columns.map((column) => ({ value: column, label: column, description: t('Примеры: {values}', { values: [...new Set(dataset.preview.map((row) => row[column]).filter((value) => value != null && value !== ''))].slice(0, 3).join(', ') || t('нет значений в предпросмотре') }) }))} onChange={setTargetColumn} disabled={isSaving || locked} placeholder={t("Выберите колонку")} hint={t("Остальные колонки будут использоваться как признаки.")} />
          <div><span className="form-label d-block">{t("Задача")}</span><div className="task-value">{experiment.task === 'classification' ? t('Классификация') : t('Регрессия')}<span>{experiment.task === 'classification' ? t('Категория или класс') : t('Числовое значение')}</span></div></div>
        </div>
        {algorithmOptions.isLoading ? <p className="field-hint" role="status">{t('Загрузка алгоритмов…')}</p> : <AlgorithmChoices options={availableAlgorithms} value={selectedAlgorithms} onChange={setAlgorithms} disabled={isSaving || locked} />}
        <div className="builder-footer"><Link to="/experiments" className="quiet-link">{t("Отмена")}</Link><button type="button" className="btn btn-primary" onClick={handleSave} disabled={isSaving || locked || algorithmOptions.isLoading || !targetColumn || selectedAlgorithms.length === 0}>{isSaving ? t('Сохранение…') : t('Сохранить изменения')}</button></div>
      </section>
    </div>
  );
}
export default ExperimentEditPage;
