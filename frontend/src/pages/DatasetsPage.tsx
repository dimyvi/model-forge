import { t, useLanguage, translateMessage } from '../utils/language';
import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import api, { getApiErrorMessage } from '../services/api';
import Icon from '../components/Icon';
import { getFilename } from '../utils/display';

type Dataset = {
  id: number;
  file: string;
  uploaded_at: string;
};

function DatasetsPage() {
  const { locale } = useLanguage();
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [pendingDeleteId, setPendingDeleteId] = useState<number | null>(null);

  async function loadDatasets() {
    try {
      setError('');
      const response = await api.get<Dataset[]>('/datasets/');
      setDatasets(response.data);
    } catch (requestError) {
      setError(
        getApiErrorMessage(
          requestError,
          'Не удалось загрузить список датасетов.',
        ),
      );
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    loadDatasets();
  }, []);

  async function handleDelete(id: number) {
    if (pendingDeleteId !== id) {
      setPendingDeleteId(id);
      return;
    }

    try {
      await api.delete(`/datasets/${id}/`);
      setDatasets((current) => current.filter((dataset) => dataset.id !== id));
      setPendingDeleteId(null);
    } catch (requestError) {
      setError(
        getApiErrorMessage(requestError, 'Не удалось удалить датасет.'),
      );
    }
  }

  if (isLoading) {
    return <p>{t("Загрузка датасетов...")}</p>;
  }

  return (
    <div>
      <div className="page-heading">
        <div>
          <h1 className="h2 mb-1">{t("Датасеты")}</h1>
          <p className="text-muted mb-0">{t("Загруженные вами файлы с данными")}</p>
        </div>

      </div>

      {error && <div className="alert alert-danger">{translateMessage(error)}</div>}

      {datasets.length === 0 ? (
        <div className="card shadow-sm">
          <div className="card-body text-center py-5">
            <h2 className="h5">{t("Датасетов пока нет")}</h2>
            <p className="text-muted">{t("Загрузить новый файл можно при создании эксперимента.")}</p>
          </div>
        </div>
      ) : (
        <div className="card shadow-sm">
          <div className="table-responsive">
            <table className="table table-hover align-middle mb-0">
              <thead>
                <tr>
                  <th>{t("Файл")}</th>
                  <th>{t("Дата загрузки")}</th>
                  <th className="text-end">{t("Действия")}</th>
                </tr>
              </thead>
              <tbody>
                {datasets.map((dataset) => (
                  <tr key={dataset.id}>
                    <td><div className="table-file"><Icon name="file" /><Link to={`/datasets/${dataset.id}`}>{getFilename(dataset.file)}</Link></div></td>
                    <td>
                      {new Date(dataset.uploaded_at).toLocaleString(locale)}
                    </td>
                    <td className="text-end">
                      <Link
                        to={`/datasets/${dataset.id}`}
                        className="btn btn-sm btn-outline-primary me-2"
                      >{t("Открыть")}</Link>
                      {pendingDeleteId === dataset.id && (
                        <button
                          type="button"
                          className="btn btn-sm btn-secondary me-2"
                          onClick={() => setPendingDeleteId(null)}
                        >{t("Отмена")}</button>
                      )}
                      <button
                        type="button"
                        className="btn btn-sm btn-outline-danger"
                        onClick={() => handleDelete(dataset.id)}
                      >
                        {pendingDeleteId === dataset.id
                          ? t('Подтвердить удаление')
                          : t('Удалить')}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

export default DatasetsPage;
