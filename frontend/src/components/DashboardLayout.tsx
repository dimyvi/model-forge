import { t, useLanguage, translateMessage } from '../utils/language';
import { useEffect, useState } from 'react';
import { isAxiosError } from 'axios';
import { Navigate, Outlet, useLocation, useNavigate } from 'react-router-dom';
import api, { getApiErrorMessage } from '../services/api';
import Sidebar from './Sidebar';
import Icon from './Icon';
import AccountMenu from './AccountMenu';

function DashboardLayout() {
  useLanguage();
  const token = localStorage.getItem('auth_token');
  const navigate = useNavigate();
  const location = useLocation();
  const [username, setUsername] = useState('');
  const [error, setError] = useState('');
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [isLoggingOut, setIsLoggingOut] = useState(false);

  useEffect(() => {
    if (!token) return;
    let cancelled = false;
    api.get<{ username: string }>('/auth/me/').then((response) => {
      if (!cancelled) setUsername(response.data.username);
    }).catch((requestError: unknown) => {
      if (cancelled) return;
      if (isAxiosError(requestError) && requestError.response?.status === 401) {
        localStorage.removeItem('auth_token');
        navigate('/login', { replace: true });
      } else {
        setError(getApiErrorMessage(requestError, 'Не удалось проверить аккаунт. Обновите страницу.'));
      }
    });
    return () => { cancelled = true; };
  }, [navigate, token]);

  useEffect(() => {
    if (!sidebarOpen) return;
    const closeOnEscape = (event: KeyboardEvent) => { if (event.key === 'Escape') setSidebarOpen(false); };
    document.addEventListener('keydown', closeOnEscape);
    return () => document.removeEventListener('keydown', closeOnEscape);
  }, [sidebarOpen]);

  async function handleLogout() {
    setIsLoggingOut(true);
    try { await api.post('/auth/logout/'); } catch {
      // Local sign-out remains available when the server cannot be reached.
    } finally {
      localStorage.removeItem('auth_token');
      navigate('/login', { replace: true });
    }
  }

  if (!token) return <Navigate to="/login" replace />;

  const section = location.pathname.startsWith('/datasets') ? t('Датасеты')
    : location.pathname.startsWith('/experiments') ? t('Эксперименты')
    : location.pathname === '/train' ? t('Новый эксперимент')
    : location.pathname === '/help' ? t('Как пользоваться') : t('Обзор');

  return (
    <div className={`dashboard-shell ${sidebarOpen ? 'sidebar-open' : ''}`}>
      <a href="#main-content" className="skip-link">{t("К содержимому")}</a>
      <div className="sidebar-wrap" id="workspace-navigation"><Sidebar onNavigate={() => setSidebarOpen(false)} /></div>
      {sidebarOpen && <button type="button" className="sidebar-backdrop" aria-label={t("Закрыть меню")} onClick={() => setSidebarOpen(false)} />}
      <div className="workspace-content">
        <header className="workspace-header">
          <button type="button" className="icon-button menu-toggle" aria-label={sidebarOpen ? t('Закрыть меню') : t('Открыть меню')} aria-expanded={sidebarOpen} aria-controls="workspace-navigation" onClick={() => setSidebarOpen((current) => !current)}><Icon name="menu" /></button>
          <div className="breadcrumb-label"><span>{t("Рабочее пространство")}</span><span aria-hidden="true">/</span><span>{section}</span></div>
          <AccountMenu key={location.pathname} username={username} isLoggingOut={isLoggingOut} onLogout={handleLogout} />
        </header>
        <main className="main-content" id="main-content">{error && <div className="alert alert-danger" role="alert">{translateMessage(error)}</div>}<Outlet /></main>
      </div>
    </div>
  );
}
export default DashboardLayout;
