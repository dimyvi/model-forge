type IconName = 'overview' | 'dataset' | 'experiment' | 'plus' | 'help' | 'logout' | 'chevron' | 'arrow' | 'upload' | 'file' | 'check' | 'close' | 'search' | 'menu';

const paths: Record<IconName, string> = {
  overview: 'M3 3h7v7H3z M14 3h7v7h-7z M3 14h7v7H3z M14 14h7v7h-7z',
  dataset: 'M4 4h16v16H4z M4 9h16 M4 14h16 M9 4v16',
  experiment: 'M4 4h16v7H4z M10 11h4v10h-4z',
  plus: 'M12 5v14 M5 12h14',
  help: 'M12 17h.01 M9.5 9a2.5 2.5 0 1 1 4 2c-1 .6-1.5 1-1.5 2 M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0',
  logout: 'M9 4H4v16h5 M9 12h12 M17 8l4 4-4 4',
  chevron: 'M6 9l6 6 6-6',
  arrow: 'M5 12h14 M14 7l5 5-5 5',
  upload: 'M12 16V3 M7 8l5-5 5 5 M4 15v6h16v-6',
  file: 'M14 3H5v18h14V8z M14 3v5h5 M8 12h8 M8 16h5',
  check: 'M5 12l4 4L19 6',
  close: 'M6 6l12 12 M6 18L18 6',
  search: 'M16 16l5 5 M18 10a8 8 0 1 1-16 0 8 8 0 0 1 16 0',
  menu: 'M4 6h16 M4 12h16 M4 18h16',
};

function Icon({ name, size = 18 }: { name: IconName; size?: number }) {
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" className="ui-icon"><path d={paths[name]} transform={name === 'experiment' ? 'rotate(35 12 12)' : undefined} /></svg>;
}

export default Icon;
