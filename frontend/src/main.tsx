import React from 'react';
import ReactDOM from 'react-dom/client';
import 'bootstrap/dist/css/bootstrap.min.css';
import './index.css';
import App from './App.tsx';
import { applyTheme, readTheme } from './utils/theme';
import { initializeLanguage } from './utils/language';

applyTheme(readTheme());
initializeLanguage();

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
