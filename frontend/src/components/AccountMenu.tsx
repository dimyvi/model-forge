import { t, useLanguage } from '../utils/language';
import { useEffect, useId, useRef, useState } from 'react';
import Icon from './Icon';
import LanguagePicker from './LanguagePicker';
import { saveTheme, themes } from '../utils/theme';
import type { Theme } from '../utils/theme';

type Props = {
  username: string;
  isLoggingOut: boolean;
  onLogout: () => void;
};

function AccountMenu({ username, isLoggingOut, onLogout }: Props) {
  useLanguage();
  const id = useId();
  const root = useRef<HTMLDivElement>(null);
  const trigger = useRef<HTMLButtonElement>(null);
  const [open, setOpen] = useState(false);
  const [theme, setTheme] = useState<Theme>(() =>
    themes.find((option) => option.id === document.documentElement.dataset.theme)?.id ?? 'steel',
  );

  useEffect(() => {
    if (!open) return;
    root.current?.querySelector<HTMLInputElement>('input:checked')?.focus();

    function closeOutside(event: Event) {
      if (!root.current?.contains(event.target as Node)) setOpen(false);
    }

    document.addEventListener('pointerdown', closeOutside);
    document.addEventListener('focusin', closeOutside);
    return () => {
      document.removeEventListener('pointerdown', closeOutside);
      document.removeEventListener('focusin', closeOutside);
    };
  }, [open]);

  function chooseTheme(nextTheme: Theme) {
    saveTheme(nextTheme);
    setTheme(nextTheme);
  }

  return (
    <div className="account-menu" ref={root} onKeyDown={(event) => {
      if (event.key === 'Escape' && open) {
        event.preventDefault();
        event.stopPropagation();
        setOpen(false);
        trigger.current?.focus();
      }
    }}>
      <button
        ref={trigger}
        type="button"
        className="account-trigger"
        aria-label={t('{name}: настройки интерфейса', { name: username || t('Аккаунт') })}
        aria-haspopup="dialog"
        aria-expanded={open}
        aria-controls={open ? `${id}-panel` : undefined}
        onClick={() => setOpen((current) => !current)}
      >
        <span className="account-indicator" aria-hidden="true" />
        <span className="account-name">{username || t('Аккаунт')}</span>
        <Icon name="chevron" size={14} />
      </button>

      {open && (
        <div id={`${id}-panel`} className="account-popover" role="dialog" aria-label={t('Настройки интерфейса')}>
          <div className="theme-picker">
            <h2 id={`${id}-title`}>{t("Цвет интерфейса")}</h2>
            <p className="theme-picker-hint">{t("Сохраняется в этом браузере.")}</p>
            <fieldset className="theme-options" aria-labelledby={`${id}-title`}>
              {themes.map((option) => (
                <label key={option.id} className="theme-option" data-theme={option.id}>
                  <input
                    className="visually-hidden"
                    type="radio"
                    name={`${id}-theme`}
                    value={option.id}
                    checked={theme === option.id}
                    onChange={() => chooseTheme(option.id)}
                  />
                  <span className="theme-option-card">
                    <span className="theme-preview" aria-hidden="true">
                      <span className="theme-preview-sidebar"><i /><i /><i /></span>
                      <span className="theme-preview-content"><i /><span><i /><i /></span><i /></span>
                    </span>
                    <span className="theme-option-label">
                      <span>{t(option.label)}</span>
                      <span className="theme-option-check"><Icon name="check" size={13} /></span>
                    </span>
                  </span>
                </label>
              ))}
            </fieldset>
          </div>
          <div className="account-language"><LanguagePicker /></div>
          <div className="account-menu-footer">
            <button type="button" className="account-logout" onClick={onLogout} disabled={isLoggingOut}>
              <Icon name="logout" size={16} />
              <span>{isLoggingOut ? t('Выход…') : t('Выйти из аккаунта')}</span>
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

export default AccountMenu;
