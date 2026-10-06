import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../services/api';

type User = {
  id: number;
  username: string;
  email: string;
};

function HomePage() {
  const navigate = useNavigate();
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    async function loadUser() {
      try {
        const response = await api.get<User>('/auth/me/');
        setUser(response.data);
      } catch {
        localStorage.removeItem('auth_token');
        navigate('/login', { replace: true });
      } finally {
        setIsLoading(false);
      }
    }

    loadUser();
  }, [navigate]);

  async function handleLogout() {
    try {
      await api.post('/auth/logout/');
    } finally {
      localStorage.removeItem('auth_token');
      navigate('/login', { replace: true });
    }
  }

  if (isLoading) {
    return (
      <div className="container py-5">
        <p>Загрузка...</p>
      </div>
    );
  }

  if (!user) {
    return null;
  }

  return (
    <div className="container py-5">
      <nav className="navbar navbar-light bg-white rounded shadow-sm px-3 mb-4">
        <span className="navbar-brand mb-0 h1">Model Forge</span>
        <button className="btn btn-outline-danger" onClick={handleLogout}>
          Выйти
        </button>
      </nav>

      <div className="p-4 bg-white rounded shadow-sm">
        <h1 className="display-6">Добро пожаловать, {user.username}!</h1>
        <p className="text-muted mb-0">
          Это главная страница Model Forge. Здесь появятся проекты, датасеты и
          эксперименты.
        </p>
      </div>
    </div>
  );
}

export default HomePage;
