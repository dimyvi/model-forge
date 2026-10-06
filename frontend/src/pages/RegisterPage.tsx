import { useState } from 'react';
import type { FormEvent } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import api, { getApiErrorMessage } from '../services/api';

function RegisterPage() {
  const navigate = useNavigate();
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError('');
    setIsLoading(true);

    try {
      await api.post('/auth/register/', {
        username,
        email,
        password,
      });

      const loginResponse = await api.post('/auth/login/', {
        username,
        password,
      });

      localStorage.setItem('auth_token', loginResponse.data.token);
      navigate('/');
    } catch (requestError) {
      setError(
        getApiErrorMessage(
          requestError,
          'Не удалось зарегистрироваться. Проверь данные.',
        ),
      );
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <div className="container">
      <div className="row justify-content-center min-vh-100 align-items-center">
        <div className="col-12 col-md-6 col-lg-4">
          <div className="card shadow-sm">
            <div className="card-body p-4">
              <h1 className="h3 text-center mb-4">
                Регистрация
              </h1>

              {error && <div className="alert alert-danger">{error}</div>}

              <form onSubmit={handleSubmit}>
                <div className="mb-3">
                  <label htmlFor="username" className="form-label">
                    Имя пользователя
                  </label>

                  <input
                    id="username"
                    type="text"
                    className="form-control"
                    placeholder="Введите username"
                    value={username}
                    onChange={(event) => setUsername(event.target.value)}
                    required
                  />
                </div>

                <div className="mb-3">
                  <label htmlFor="email" className="form-label">
                    Email
                  </label>

                  <input
                    id="email"
                    type="email"
                    className="form-control"
                    placeholder="Введите email"
                    value={email}
                    onChange={(event) => setEmail(event.target.value)}
                    required
                  />
                </div>

                <div className="mb-3">
                  <label htmlFor="password" className="form-label">
                    Пароль
                  </label>

                  <input
                    id="password"
                    type="password"
                    className="form-control"
                    placeholder="Введите пароль"
                    value={password}
                    onChange={(event) => setPassword(event.target.value)}
                    required
                    minLength={8}
                  />
                </div>

                <button
                  type="submit"
                  className="btn btn-primary w-100"
                  disabled={isLoading}
                >
                  {isLoading ? 'Регистрация...' : 'Зарегистрироваться'}
                </button>
              </form>

              <div className="text-center mt-3">
                <span>Уже есть аккаунт? </span>
                <Link to="/login">Войти</Link>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default RegisterPage;
