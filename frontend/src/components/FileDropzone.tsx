import { t, useLanguage } from '../utils/language';
import { useId, useRef, useState } from 'react';
import Icon from './Icon';

type Props = { file: File | null; onChange: (file: File | null) => void; disabled: boolean; onError: (message: string) => void };

function FileDropzone({ file, onChange, disabled, onError }: Props) {
  const { locale } = useLanguage();
  const id = useId();
  const input = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);

  function selectFile(files: File[]) {
    if (files.length !== 1) { onError('Выберите один CSV-файл.'); return; }
    if (!files[0].name.toLowerCase().endsWith('.csv')) { onError('Поддерживается формат CSV. Выберите файл с расширением .csv.'); return; }
    if (files[0].size === 0) { onError('Файл пустой. Выберите CSV с данными.'); return; }
    onError('');
    onChange(files[0]);
  }

  return (
    <div
      className={`file-dropzone ${dragging ? 'is-dragging' : ''} ${file ? 'has-file' : ''}`}
      role="button"
      tabIndex={disabled ? -1 : 0}
      aria-disabled={disabled}
      aria-label={t('Зона выбора CSV-файла')}
      onClick={(event) => { if (!disabled && !(event.target as HTMLElement).closest('button')) input.current?.click(); }}
      onKeyDown={(event) => { if (!disabled && (event.key === 'Enter' || event.key === ' ')) { event.preventDefault(); input.current?.click(); } }}
      onDragOver={(event) => { event.preventDefault(); if (!disabled) setDragging(true); }}
      onDragLeave={(event) => { if (!event.currentTarget.contains(event.relatedTarget as Node)) setDragging(false); }}
      onDrop={(event) => { event.preventDefault(); setDragging(false); if (!disabled) selectFile(Array.from(event.dataTransfer.files)); }}
    >
      <input ref={input} id={id} type="file" accept=".csv,text/csv" className="visually-hidden" tabIndex={-1} aria-label={t("CSV-файл")} disabled={disabled} onChange={(event) => { if (event.target.files?.length) selectFile(Array.from(event.target.files)); event.target.value = ''; }} />
      <span className="file-icon"><Icon name={file ? 'file' : 'upload'} size={24} /></span>
      <div className="file-description"><strong>{file ? file.name : t('Перетащите CSV-файл сюда')}</strong><span>{file ? `${t('Нажмите, чтобы заменить файл')} · ${new Intl.NumberFormat(locale, { maximumFractionDigits: 1 }).format(file.size < 1024 ? file.size : file.size / 1024)} ${file.size < 1024 ? t('Б') : t('КБ')} · CSV` : t('или нажмите, чтобы выбрать файл')}</span></div>
      {file && <div className="file-actions"><button type="button" className="icon-button" aria-label={t("Убрать выбранный файл")} disabled={disabled} onClick={() => onChange(null)}><Icon name="close" /></button></div>}
    </div>
  );
}

export default FileDropzone;
