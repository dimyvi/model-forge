import { t, useLanguage } from '../utils/language';
import { useId } from 'react';
import type { AvailableAlgorithm } from '../services/experiments';
import type { MessageKey } from '../utils/messages';

const descriptions: Record<string, MessageKey> = {
  logistic_regression: 'Базовая модель для сравнения',
  random_forest: 'Ансамбль деревьев решений',
  linear_regression: 'Базовая модель для сравнения',
};

function AlgorithmChoices({ options, value, onChange, disabled = false }: { options: AvailableAlgorithm[]; value: string[]; onChange: (value: string[]) => void; disabled?: boolean }) {
  useLanguage();
  const id = useId();
  return (
    <fieldset className="algorithm-field">
      <legend className="form-label">{t("Алгоритмы для сравнения")}</legend>
      <div className="algorithm-grid">{options.map((algorithm) => (
        <label key={algorithm.id} className={`algorithm-choice ${value.includes(algorithm.id) ? 'is-selected' : ''}`} htmlFor={`${id}-${algorithm.id}`}>
          <input id={`${id}-${algorithm.id}`} type="checkbox" className="form-check-input" disabled={disabled} checked={value.includes(algorithm.id)} onChange={() => onChange(value.includes(algorithm.id) ? value.filter((item) => item !== algorithm.id) : [...value, algorithm.id])} />
          <span><strong>{algorithm.name}</strong>{descriptions[algorithm.id] && <small>{t(descriptions[algorithm.id])}</small>}</span>
        </label>
      ))}</div>
    </fieldset>
  );
}

export default AlgorithmChoices;
