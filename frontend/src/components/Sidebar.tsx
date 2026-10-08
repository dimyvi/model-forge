import { t, useLanguage } from '../utils/language';
import { NavLink } from 'react-router-dom';
import Icon from './Icon';

function Sidebar({ onNavigate }: { onNavigate: () => void }) {
  useLanguage();
  return (
    <aside className="sidebar">
      <div className="sidebar-brand"><span className="brand-mark"><Icon name="experiment" size={21} /></span><span className="brand-name">Model Forge</span></div>
      <div className="sidebar-section-label">{t("Рабочее пространство")}</div>
      <nav className="nav flex-column" aria-label={t("Основная навигация")}>
        <NavLink to="/" end className="nav-link" onClick={onNavigate}><Icon name="overview" /><span>{t("Обзор")}</span></NavLink>
        <NavLink to="/train" className="nav-link" onClick={onNavigate}><Icon name="plus" /><span>{t("Новый эксперимент")}</span></NavLink>
        <NavLink to="/datasets" className="nav-link" onClick={onNavigate}><Icon name="dataset" /><span>{t("Датасеты")}</span></NavLink>
        <NavLink to="/experiments" className="nav-link" onClick={onNavigate}><Icon name="experiment" /><span>{t("Эксперименты")}</span></NavLink>
      </nav>
      <div className="sidebar-footer">
        <NavLink to="/help" className="nav-link" onClick={onNavigate}><Icon name="help" /><span>{t("Как пользоваться")}</span></NavLink>
        <p>{t("Данные и эксперименты")}<br />{t("в одном месте.")}</p>
      </div>
    </aside>
  );
}
export default Sidebar;
