/**
 * Hook that enforces dark mode - always applies dark class to document root
 * Dark mode cannot be toggled off
 * Note: Dark mode is also enforced in index.html and main.tsx for immediate application
 */
export function useDarkMode() {
  // Ensure dark mode is applied (redundant but safe)
  if (typeof document !== 'undefined') {
    document.documentElement.classList.add('dark');
    localStorage.setItem('darkMode', 'true');
  }

  return {
    isDark: true,
  };
}
