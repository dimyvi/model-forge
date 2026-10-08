import { t, useLanguage, translateMessage } from '../utils/language';
import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import api, { getApiErrorMessage } from '../services/api';
import Icon from '../components/Icon';
import FileDropzone from '../components/FileDropzone';
import SelectField from '../components/SelectField';
import AlgorithmChoices from '../components/AlgorithmChoices';
import { getFilename } from '../utils/display';

type Dataset = { id: number; file: string; uploaded_at: string };
type DatasetDetails = Dataset & { columns: string[]; rows_count: number; preview: Record<string, string | null>[] };

function TrainPage() {
  const { locale } = useLanguage();
  const navigate = useNavigate();
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [sourceMode, setSourceMode] = useState<'existing' | 'new'>('existing');
  const [selectedDatasetId, setSelectedDatasetId] = useState('');
  const [file, setFile] = useState<File | null>(null);
  const [datasetDetails, setDatasetDetails] = useState<DatasetDetails | null>(null);
  const [targetColumn, setTargetColumn] = useState('');
  const [algorithms, setAlgorithms] = useState(['logistic_regression', 'random_forest']);
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const [isLoadingDetails, setIsLoadingDetails] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [isCreating, setIsCreating] = useState(false);
  const [retry, setRetry] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    api.get<Dataset[]>('/datasets/', { signal: controller.signal }).then((response) => {
      setDatasets(response.data);
      if (response.data.length === 0) setSourceMode('new');
    }).catch((requestError: unknown) => {
      if (!controller.signal.aborted) setError(getApiErrorMessage(requestError, 'Не удалось загрузить список датасетов.'));
    }).finally(() => { if (!controller.signal.aborted) setIsLoading(false); });
    return () => controller.abort();
  }, []);

  useEffect(() => {
    if (!selectedDatasetId) return;
    const controller = new AbortController();
    async function loadDetails() {
      setIsLoadingDetails(true);
      try {
        const response = await api.get<DatasetDetails>(`/datasets/${selectedDatasetId}/`, { signal: controller.signal });
        if (!controller.signal.aborted) setDatasetDetails(response.data);
      } catch (requestError) {
        if (!controller.signal.aborted) setError(getApiErrorMessage(requestError, 'Не удалось прочитать данные. Попробуйте ещё раз.'));
      } finally { if (!controller.signal.aborted) setIsLoadingDetails(false); }
    }
    loadDetails();
    return () => controller.abort();
  }, [selectedDatasetId, retry]);

  function resetSelection() {
    setSelectedDatasetId('');
    setDatasetDetails(null);
    setTargetColumn('');
    setError('');
    setIsLoadingDetails(false);
  }

  function changeSource(mode: 'existing' | 'new') {
    if (mode === sourceMode) return;
    resetSelection();
    setSourceMode(mode);
  }

  async function handleUpload() {
    if (!file || isUploading) return;
    setError('');
    setIsUploading(true);
    const formData = new FormData();
    formData.append('file', file);
    try {
      const response = await api.post<Dataset>('/datasets/', formData);
      setDatasets((current) => [response.data, ...current]);
      setSelectedDatasetId(String(response.data.id));
    } catch (requestError) {
      setError(getApiErrorMessage(requestError, 'Не удалось загрузить файл.'));
    } finally { setIsUploading(false); }
  }

  async function handleCreateExperiment() {
    if (!datasetDetails || !datasetDetails.columns.includes(targetColumn) || algorithms.length === 0) {
      setError('Выберите целевую колонку и хотя бы один алгоритм.');
      return;
    }
    setError('');
    setIsCreating(true);
    try {
      await api.post('/experiments/', { dataset: datasetDetails.id, task: 'classification', target_column: targetColumn, algorithms });
      navigate('/experiments');
    } catch (requestError) {
      setError(getApiErrorMessage(requestError, 'Не удалось создать эксперимент.'));
    } finally { setIsCreating(false); }
  }

  const busy = isUploading || isCreating;
  const ready = datasetDetails && String(datasetDetails.id) === selectedDatasetId;
  const targetOptions = datasetDetails?.columns.map((column) => ({
    value: column, label: column,
    description: t('Примеры: {values}', { values: [...new Set(datasetDetails.preview.map((row) => row[column]).filter((value) => value != null && value !== ''))].slice(0, 3).join(', ') || t('нет значений в предпросмотре') }),
  })) ?? [];

  return (
    <div className="experiment-builder">
      <div className="page-heading"><div><h1>{t("Новый эксперимент")}</h1><p>{t("Выберите данные и сохраните параметры будущего обучения.")}</p></div></div>
      {error && <div className="alert alert-danger" role="alert">{translateMessage(error)}</div>}
      <section className="card builder-section">
        <div className="builder-section-heading"><span className="step-number">1</span><div><h2>{t("Данные")}</h2><p>{t("Загрузите новый CSV или выберите файл из своего пространства.")}</p></div></div>
        <div className="source-switch" role="group" aria-label={t("Источник данных")}>
          <button type="button" className={sourceMode === 'new' ? 'is-active' : ''} aria-pressed={sourceMode === 'new'} disabled={busy || isLoading} onClick={() => changeSource('new')}><Icon name="upload" size={16} />{t("Новый файл")}</button>
          <button type="button" className={sourceMode === 'existing' ? 'is-active' : ''} aria-pressed={sourceMode === 'existing'} disabled={busy || isLoading} onClick={() => changeSource('existing')}><Icon name="dataset" size={16} />{t("Мои датасеты")}<span className="source-count">{datasets.length}</span></button>
        </div>
        {isLoading ? <p className="field-hint" role="status">{t("Загружаем список датасетов…")}</p> : sourceMode === 'new' ? (
          <div>
            <FileDropzone file={file} disabled={busy} onError={setError} onChange={(nextFile) => { resetSelection(); setFile(nextFile); }} />
            <div className="upload-footer"><p className="field-hint">{t("Первая строка — названия колонок. Файл сохранится в разделе «Датасеты» после загрузки.")}</p>
              {selectedDatasetId ? <span className="inline-status"><Icon name="check" size={16} />{t("Файл сохранён")}</span> : <button type="button" className="btn btn-primary" disabled={!file || busy} onClick={handleUpload}>{isUploading ? t('Загрузка…') : t('Загрузить данные')}</button>}
            </div>
          </div>
        ) : datasets.length === 0 ? <p className="field-hint">{t("Загруженных датасетов пока нет. Выберите «Новый файл», чтобы добавить CSV.")}</p> : (
          <SelectField label={t("Датасет")} value={selectedDatasetId} options={datasets.map((item) => ({ value: String(item.id), label: getFilename(item.file), description: t('Загружен {date}', { date: new Date(item.uploaded_at).toLocaleDateString(locale) }) }))} placeholder={t("Выберите датасет из списка")} disabled={busy} onChange={(id) => { resetSelection(); setSelectedDatasetId(id); }} />
        )}
        {isLoadingDetails && <p className="field-hint mt-3" role="status">{t("Читаем колонки и первые строки…")}</p>}
        {selectedDatasetId && !ready && !isLoadingDetails && error && <button type="button" className="btn btn-outline-secondary mt-3" onClick={() => { setError(''); setRetry((current) => current + 1); }}>{t("Повторить чтение данных")}</button>}
        {ready && <div className="dataset-summary"><Icon name="file" size={19} /><strong>{getFilename(datasetDetails.file)}</strong><span>{t('Строк: {count}', { count: datasetDetails.rows_count.toLocaleString(locale) })} · {t('Колонок: {count}', { count: datasetDetails.columns.length.toLocaleString(locale) })}</span></div>}
      </section>
      <section className={`card builder-section ${!ready ? 'is-waiting' : ''}`}>
        <div className="builder-section-heading"><span className="step-number">2</span><div><h2>{t("Настройки эксперимента")}</h2><p>{ready ? t('Укажите, что должна предсказывать модель и какие алгоритмы сравнить.') : t('Настройки станут доступны после выбора данных.')}</p></div></div>
        {ready && <div>
          <div className="settings-grid">
            <SelectField label={t("Целевая колонка")} value={targetColumn} options={targetOptions} onChange={setTargetColumn} placeholder={t("Какую колонку предсказывать?")} hint={t("Остальные колонки будут использоваться как признаки.")} disabled={busy} />
            <div><span className="form-label d-block">{t("Задача")}</span><div className="task-value">{t("Классификация")}<span>{t("Категория или класс")}</span></div></div>
          </div>
          <AlgorithmChoices value={algorithms} onChange={setAlgorithms} disabled={busy} />
          <details className="dataset-preview">
            <summary>{t("Первые строки данных")}<span>{t('Строк: {count}', { count: Math.min(datasetDetails.preview.length, 5) })}<Icon name="chevron" size={16} /></span></summary>
            <div className="table-responsive"><table className="table preview-table mb-0"><thead><tr>{datasetDetails.columns.map((column) => <th key={column} className={column === targetColumn ? 'target-cell' : ''}>{column}{column === targetColumn && <span className="target-label">{t("цель")}</span>}</th>)}</tr></thead><tbody>{datasetDetails.preview.slice(0, 5).map((row, index) => <tr key={index}>{datasetDetails.columns.map((column) => <td key={column} className={column === targetColumn ? 'target-cell' : ''}>{row[column] ?? '—'}</td>)}</tr>)}</tbody></table></div>
          </details>
          <div className="builder-footer"><p>{t("Вы сохраните настройки. Обучение будет доступно позже.")}</p><button type="button" className="btn btn-primary" onClick={handleCreateExperiment} disabled={busy || !targetColumn || algorithms.length === 0}>{isCreating ? t('Сохранение…') : t('Сохранить эксперимент')}</button></div>
        </div>}
      </section>
    </div>
  );
}
export default TrainPage;
