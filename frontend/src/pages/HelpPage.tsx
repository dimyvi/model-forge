import { t, useLanguage } from '../utils/language';
function HelpPage() {
  useLanguage();
  return (
    <div className="help-page">
      <div className="page-heading">
        <div>
        <h1 className="h2">{t("Как пользоваться Model Forge")}</h1>
        <p className="text-muted">{t("Краткая инструкция по работе с платформой")}</p>
        </div>
      </div>

      <div className="card shadow-sm mb-4">
        <div className="card-body">
          <h2 className="h4">{t("1. Подготовьте данные")}</h2>

          <p>{t('Платформа принимает CSV-файлы.')}</p>

          <ul>
            <li>{t("первая строка содержит названия колонок;")}</li>
            <li>{t("одна колонка содержит целевой результат;")}</li>
            <li>{t("признаки должны быть числовыми;")}</li>
            <li>{t("файл не должен быть пустым.")}</li>
          </ul>
        </div>
      </div>

      <div className="card shadow-sm mb-4">
        <div className="card-body">
          <h2 className="h4">{t("2. Загрузите датасет")}</h2>

          <p>{t("Перейдите в раздел «Новый эксперимент» и выберите CSV-файл или уже загруженный датасет. Первые строки можно раскрыть в блоке настроек. Загруженные файлы сохраняются в разделе «Датасеты».")}</p>
        </div>
      </div>

      <div className="card shadow-sm mb-4">
        <div className="card-body">
          <h2 className="h4">{t("3. Выберите параметры обучения")}</h2>

          <p>{t("Выберите задачу, целевую колонку и алгоритмы, которые нужно сравнить.")}</p>

          <ul>
            <li>{t("классификация;")}</li>
            <li>Logistic Regression;</li>
            <li>Random Forest.</li>
          </ul>
        </div>
      </div>

      <div className="card shadow-sm">
        <div className="card-body">
          <h2 className="h4">{t('4. Сохраните и запустите эксперимент')}</h2>

          <p>{t('Сохраните настройки и нажмите «Запустить обучение» на странице эксперимента. Статус очереди и обучения обновляется автоматически. После завершения сравните метрики и скачайте модель.')}</p>
          <p>{t('После ошибки можно повторить обучение или изменить настройки. Во время ожидания в очереди и обучения редактирование и удаление недоступны.')}</p>
        </div>
      </div>
    </div>
  );
}

export default HelpPage;
