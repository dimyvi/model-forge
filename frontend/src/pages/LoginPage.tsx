import { t, useLanguage, translateMessage } from '../utils/language';
import { useState } from 'react';
import type { FormEvent } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import api, { getApiErrorMessage } from '../services/api';
import Icon from '../components/Icon';
import LanguagePicker from '../components/LanguagePicker';

function LoginPage() {
  useLanguage();
  const navigate = useNavigate();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError('');
    setIsLoading(true);

    try {
      const response = await api.post('/auth/login/', {
        username,
        password,
      });

      localStorage.setItem('auth_token', response.data.token);
      navigate('/');
    } catch (requestError) {
      setError(
        getApiErrorMessage(
          requestError,
          'Неверное имя пользователя или пароль.',
        ),
      );
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <div className="auth-page container-fluid">
      <div className="row justify-content-center min-vh-100 align-items-center g-0">
        <div className="col-12 col-md-6 col-lg-4">
          <div className="card auth-card">
            <div className="card-body p-4 p-lg-5">
              <div className="auth-brand mb-4">
                <span className="brand-mark"><Icon name="experiment" size={21} /></span>
                <span>Model Forge</span>
              </div>
              <h1 className="h2 mb-2">{t("С возвращением")}</h1>
              <p className="text-muted mb-4">{t("Войдите, чтобы продолжить работу с данными.")}</p>

              {error && <div className="alert alert-danger">{translateMessage(error)}</div>}

              <form onSubmit={handleSubmit}>
                <div className="mb-3">
                  <label htmlFor="username" className="form-label">{t("Имя пользователя")}</label>

                  <input
                    id="username"
                    type="text"
                    className="form-control"
                    placeholder={t("Введите username")}
                    autoComplete="username"
                    value={username}
                    onChange={(event) => setUsername(event.target.value)}
                    required
                  />
                </div>

                <div className="mb-3">
                  <label htmlFor="password" className="form-label">{t("Пароль")}</label>

                  <input
                    id="password"
                    type="password"
                    className="form-control"
                    placeholder={t("Введите пароль")}
                    autoComplete="current-password"
                    value={password}
                    onChange={(event) => setPassword(event.target.value)}
                    required
                  />
                </div>

                <button
                  type="submit"
                  className="btn btn-primary w-100"
                  disabled={isLoading}
                >
                  {isLoading ? t('Вход...') : t('Войти')}
                </button>
              </form>

              <div className="text-center mt-3">
                <span>{t("Нет аккаунта?")}</span>{' '}
                <Link to="/register">{t("Зарегистрироваться")}</Link>
              </div>
              <div className="auth-language"><LanguagePicker /></div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default LoginPage;
