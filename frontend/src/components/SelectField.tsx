import { t, useLanguage } from '../utils/language';
import { useEffect, useId, useRef, useState } from 'react';
import type { KeyboardEvent } from 'react';
import Icon from './Icon';

type Option = { value: string; label: string; description?: string };
type Props = {
  label: string; value: string; options: Option[]; onChange: (value: string) => void;
  placeholder?: string; hint?: string; disabled?: boolean;
};

function SelectField({ label, value, options, onChange, placeholder = t('Выберите значение'), hint, disabled = false }: Props) {
  useLanguage();
  const id = useId();
  const root = useRef<HTMLDivElement>(null);
  const trigger = useRef<HTMLButtonElement>(null);
  const searchInput = useRef<HTMLInputElement>(null);
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState('');
  const [activeIndex, setActiveIndex] = useState(0);
  const selected = options.find((option) => option.value === value);
  const filtered = options.filter((option) => option.label.toLocaleLowerCase().includes(query.toLocaleLowerCase()));

  useEffect(() => {
    if (!open) return;
    searchInput.current?.focus();
    const closeOutside = (event: Event) => {
      if (!root.current?.contains(event.target as Node)) setOpen(false);
    };
    document.addEventListener('pointerdown', closeOutside);
    document.addEventListener('focusin', closeOutside);
    return () => {
      document.removeEventListener('pointerdown', closeOutside);
      document.removeEventListener('focusin', closeOutside);
    };
  }, [open]);

  useEffect(() => {
    if (open) document.getElementById(`${id}-option-${activeIndex}`)?.scrollIntoView({ block: 'nearest' });
  }, [activeIndex, id, open]);

  function choose(option: Option) {
    onChange(option.value);
    setOpen(false);
    setQuery('');
    trigger.current?.focus();
  }

  function handleKeyDown(event: KeyboardEvent<HTMLElement>) {
    if (event.key === 'Escape') {
      event.preventDefault();
      setOpen(false);
      trigger.current?.focus();
    } else if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
      event.preventDefault();
      if (!open) {
        setQuery('');
        setActiveIndex(Math.max(0, options.findIndex((option) => option.value === value)));
        setOpen(true);
      } else {
        setActiveIndex((current) => Math.max(0, Math.min(filtered.length - 1, current + (event.key === 'ArrowDown' ? 1 : -1))));
      }
    } else if (event.key === 'Enter' && open && filtered[activeIndex]) {
      event.preventDefault();
      choose(filtered[activeIndex]);
    }
  }

  return (
    <div className="select-field" ref={root}>
      <label htmlFor={`${id}-trigger`} id={`${id}-label`} className="form-label">{label}</label>
      <div className="select-control">
      <button ref={trigger} id={`${id}-trigger`} type="button" role="combobox" aria-expanded={open} aria-controls={`${id}-list`} aria-labelledby={`${id}-label`} aria-describedby={hint ? `${id}-hint` : undefined} aria-haspopup="listbox" className={`select-trigger ${selected ? '' : 'is-placeholder'}`} disabled={disabled} onKeyDown={handleKeyDown} onClick={() => {
        setQuery('');
        setActiveIndex(Math.max(0, options.findIndex((option) => option.value === value)));
        setOpen((current) => !current);
      }}>
        <span>{selected?.label ?? placeholder}</span><Icon name="chevron" />
      </button>
      {open && (
        <div className="select-popover">
          <div className="select-search"><Icon name="search" size={16} />
            <input ref={searchInput} value={query} aria-label={t('Поиск: {label}', { label })} role="combobox" aria-expanded={open} aria-controls={`${id}-list`} aria-autocomplete="list" aria-activedescendant={filtered[activeIndex] ? `${id}-option-${activeIndex}` : undefined} placeholder={t("Найти в списке…")} onKeyDown={handleKeyDown} onChange={(event) => { setQuery(event.target.value); setActiveIndex(0); }} />
          </div>
          <div id={`${id}-list`} role="listbox" aria-label={label} className="select-options">
            {filtered.map((option, index) => (
              <button key={option.value} id={`${id}-option-${index}`} type="button" role="option" aria-selected={option.value === value} tabIndex={-1} className={`select-option ${index === activeIndex ? 'is-active' : ''}`} onMouseEnter={() => setActiveIndex(index)} onClick={() => choose(option)}>
                <span><span className="option-label">{option.label}</span>{option.description && <small>{option.description}</small>}</span>
                {option.value === value && <Icon name="check" size={16} />}
              </button>
            ))}
            {filtered.length === 0 && <p className="select-empty">{t("Ничего не найдено")}</p>}
          </div>
        </div>
      )}
      </div>
      {hint && <p id={`${id}-hint`} className="field-hint">{hint}</p>}
    </div>
  );
}

export default SelectField;
