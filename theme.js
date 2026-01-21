const themeToggle = document.getElementById('themeToggle');
const root = document.documentElement;
const themeStorageKey = 'theme';

const getSystemTheme = () =>
  window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';

const updateToggleLabel = (theme) => {
  if (!themeToggle) {
    return;
  }
  themeToggle.textContent = theme === 'dark' ? 'Light mode' : 'Dark mode';
};

const applyTheme = (theme) => {
  root.dataset.theme = theme;
  updateToggleLabel(theme);
};

const storedTheme = localStorage.getItem(themeStorageKey);
applyTheme(storedTheme || getSystemTheme());

if (themeToggle) {
  themeToggle.addEventListener('click', () => {
    const nextTheme = root.dataset.theme === 'dark' ? 'light' : 'dark';
    localStorage.setItem(themeStorageKey, nextTheme);
    applyTheme(nextTheme);
  });
}

const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
mediaQuery.addEventListener('change', (event) => {
  if (localStorage.getItem(themeStorageKey)) {
    return;
  }
  applyTheme(event.matches ? 'dark' : 'light');
});
