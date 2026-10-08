export const themes = [
  { id: 'steel', label: 'Сталь' },
  { id: 'copper', label: 'Медь' },
  { id: 'amber', label: 'Янтарь' },
  { id: 'pine', label: 'Хвоя' },
] as const;

export type Theme = typeof themes[number]['id'];
const storageKey = 'model-forge.theme';

export function readTheme(): Theme {
  try {
    const saved = localStorage.getItem(storageKey);
    return themes.find((theme) => theme.id === saved)?.id ?? 'steel';
  } catch {
    return 'steel';
  }
}

export function applyTheme(theme: Theme) {
  document.documentElement.dataset.theme = theme;
  const background = getComputedStyle(document.documentElement).getPropertyValue('--page-bg').trim();
  document.querySelector('meta[name="theme-color"]')?.setAttribute('content', background);
}

export function saveTheme(theme: Theme) {
  applyTheme(theme);
  try {
    localStorage.setItem(storageKey, theme);
  } catch {
    // The selection still works for this visit if browser storage is unavailable.
  }
}
