import { useId } from 'react';
import { t, useLanguage } from '../utils/language';

function LanguagePicker() {
  const id = useId();
  const { language, setLanguage } = useLanguage();

  return (
    <fieldset className="language-picker">
      <legend>{t('Язык интерфейса')}</legend>
      <div className="language-options">
        {([{ id: 'ru', label: 'Русский' }, { id: 'en', label: 'English' }] as const).map((option) => (
          <label key={option.id} className="language-option" lang={option.id}>
            <input
              type="radio"
              className="visually-hidden"
              name={`${id}-language`}
              value={option.id}
              checked={language === option.id}
              onChange={() => setLanguage(option.id)}
            />
            <span>{option.label}</span>
          </label>
        ))}
      </div>
    </fieldset>
  );
}

export default LanguagePicker;
