import { t, useLanguage } from '../utils/language';
import { useId } from 'react';

const algorithms = [
  { value: 'logistic_regression', label: 'Logistic Regression', description: 'Базовая модель для сравнения' },
  { value: 'random_forest', label: 'Random Forest', description: 'Ансамбль деревьев решений' },
] as const;

function AlgorithmChoices({ value, onChange, disabled = false }: { value: string[]; onChange: (value: string[]) => void; disabled?: boolean }) {
  useLanguage();
  const id = useId();
  return (
    <fieldset className="algorithm-field">
      <legend className="form-label">{t("Алгоритмы для сравнения")}</legend>
      <div className="algorithm-grid">{algorithms.map((algorithm) => (
        <label key={algorithm.value} className={`algorithm-choice ${value.includes(algorithm.value) ? 'is-selected' : ''}`} htmlFor={`${id}-${algorithm.value}`}>
          <input id={`${id}-${algorithm.value}`} type="checkbox" className="form-check-input" disabled={disabled} checked={value.includes(algorithm.value)} onChange={() => onChange(value.includes(algorithm.value) ? value.filter((item) => item !== algorithm.value) : [...value, algorithm.value])} />
          <span><strong>{algorithm.label}</strong><small>{t(algorithm.description)}</small></span>
        </label>
      ))}</div>
    </fieldset>
  );
}

export default AlgorithmChoices;
