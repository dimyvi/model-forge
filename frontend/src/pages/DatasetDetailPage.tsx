import { t, useLanguage, translateMessage } from '../utils/language';
import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import api, { getApiErrorMessage } from '../services/api';
import { getFilename } from '../utils/display';

type DatasetDetails = {
  id: number;
  file: string;
  uploaded_at: string;
  columns: string[];
  rows_count: number;
  preview: Record<string, string | null>[];
};

function DatasetDetailPage() {
  const { locale } = useLanguage();
  const { id } = useParams();
  const [dataset, setDataset] = useState<DatasetDetails | null>(null);
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    async function loadDataset() {
      try {
        const response = await api.get<DatasetDetails>(`/datasets/${id}/`);
        setDataset(response.data);
      } catch (requestError) {
        setError(
          getApiErrorMessage(
            requestError,
            'Не удалось загрузить датасет.',
          ),
        );
      } finally {
        setIsLoading(false);
      }
    }

    loadDataset();
  }, [id]);

  if (isLoading) {
    return <p>{t("Загрузка датасета...")}</p>;
  }

  if (!dataset) {
    return <div className="alert alert-danger">{translateMessage(error)}</div>;
  }

  return (
    <div>
      <div className="page-heading">
        <div>
          <h1 className="h2 mb-1">{getFilename(dataset.file)}</h1>
          <p className="text-muted mb-0">
            {t('Строк: {count}', { count: dataset.rows_count.toLocaleString(locale) })} · {t('Колонок: {count}', { count: dataset.columns.length.toLocaleString(locale) })}
          </p>
        </div>
        <Link to="/datasets" className="btn btn-outline-secondary">{t("Назад к датасетам")}</Link>
      </div>

      <div className="card shadow-sm">
        <div className="card-body">
          <h2 className="h5">{t("Первые строки")}</h2>
          <div className="table-responsive">
            <table className="table table-sm table-bordered align-middle mb-0">
              <thead className="table-light">
                <tr>
                  {dataset.columns.map((column) => (
                    <th key={column}>{column}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {dataset.preview.map((row, rowIndex) => (
                  <tr key={rowIndex}>
                    {dataset.columns.map((column) => (
                      <td key={column}>{row[column] ?? ''}</td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}

export default DatasetDetailPage;
