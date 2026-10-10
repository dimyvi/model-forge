import { t, useLanguage, translateMessage } from '../utils/language';
import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import api, { getApiErrorMessage } from '../services/api';
import Icon from '../components/Icon';
import { getFilename, statusLabels } from '../utils/display';
import type { Experiment } from '../services/experiments';

type Dataset = { id: number; file: string };

function HomePage() {
  const { locale } = useLanguage();
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [experiments, setExperiments] = useState<Experiment[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    let cancelled = false;
    async function loadDashboard() {
      try {
        const [data, history] = await Promise.all([api.get<Dataset[]>('/datasets/'), api.get<Experiment[]>('/experiments/')]);
        if (!cancelled) { setDatasets(data.data); setExperiments(history.data); }
      } catch (requestError) {
        if (!cancelled) setError(getApiErrorMessage(requestError, 'Не удалось загрузить обзор. Обновите страницу.'));
      } finally { if (!cancelled) setIsLoading(false); }
    }
    loadDashboard();
    return () => { cancelled = true; };
  }, []);

  const recent = [...experiments].sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()).slice(0, 4);

  return (
    <div className="overview-page">
      <div className="page-heading"><div><h1>{t("Обзор")}</h1><p>{t("Ваши данные и последние эксперименты.")}</p></div><Link to="/train" className="btn btn-primary"><Icon name="plus" />{t("Новый эксперимент")}</Link></div>
      {error && <div className="alert alert-danger" role="alert">{translateMessage(error)}</div>}
      <div className="overview-stats" aria-label={t("Статистика рабочего пространства")}>
        <Link to="/datasets" className="overview-stat"><Icon name="dataset" size={20} /><span><span className="stat-label">{t("Датасеты")}</span><strong>{isLoading ? '—' : datasets.length}</strong></span><Icon name="arrow" size={16} /></Link>
        <Link to="/experiments" className="overview-stat"><Icon name="experiment" size={20} /><span><span className="stat-label">{t("Эксперименты")}</span><strong>{isLoading ? '—' : experiments.length}</strong></span><Icon name="arrow" size={16} /></Link>
      </div>
      <div className="overview-grid">
        <section className="card recent-panel">
          <div className="panel-heading"><h2>{t("Последние эксперименты")}</h2><Link to="/experiments" className="quiet-link">{t("Все эксперименты")}<Icon name="arrow" size={15} /></Link></div>
          {isLoading ? <div className="empty-state" role="status">{t("Загружаем эксперименты…")}</div>
            : recent.length === 0 ? <div className="empty-state"><span className="empty-icon"><Icon name="experiment" size={28} /></span><h3>{error ? t('Данные недоступны') : t('Здесь появятся ваши эксперименты')}</h3><p>{error ? t('Попробуйте обновить страницу немного позже.') : t('Начните с CSV-файла, выберите целевую колонку и сохраните настройки.')}</p></div>
              : <div className="recent-list">{recent.map((experiment) => (
                <Link to={`/experiments/${experiment.id}`} key={experiment.id} className="recent-item">
                  <span className="recent-item-icon"><Icon name="experiment" /></span>
                  <span className="recent-item-details"><strong>{t('Эксперимент #{id}', { id: experiment.id })}</strong><span>{getFilename(datasets.find((item) => item.id === experiment.dataset)?.file ?? t('Датасет #{id}', { id: experiment.dataset }))} · {t('цель')}: {experiment.target_column}</span></span>
                  <span className="recent-item-meta"><span className={`status-pill status-${experiment.status}`}>{statusLabels[experiment.status] ? t(statusLabels[experiment.status]) : experiment.status}</span><small>{new Date(experiment.created_at).toLocaleDateString(locale, { day: 'numeric', month: 'short' })}</small></span>
                </Link>
              ))}</div>}
        </section>
        <aside className="getting-started"><div className="section-kicker">{t("С чего начать")}</div><h2>{t("От данных к эксперименту")}</h2>
          <ol className="guide-steps"><li><strong>{t("Подготовьте CSV")}</strong><p>{t("Названия колонок — в первой строке.")}</p></li><li><strong>{t("Выберите цель")}</strong><p>{t("Какую колонку должна предсказывать модель?")}</p></li><li><strong>{t('Сохраните и запустите эксперимент')}</strong><p>{t('Сравните метрики и скачайте обученную модель.')}</p></li></ol>
          <Link to="/help" className="quiet-link">{t("Инструкция по работе")}<Icon name="arrow" size={15} /></Link>
        </aside>
      </div>
      <p className="workspace-note">{t('Загрузите данные, запустите обучение и скачайте модель на странице эксперимента.')}</p>
    </div>
  );
}
export default HomePage;
