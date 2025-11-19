import { useState, useEffect } from 'react';

/**
 * Custom hook for managing dark mode with localStorage persistence
 * Defaults to dark mode on first load
 */
export function useDarkMode() {
  const [isDark, setIsDark] = useState<boolean>(() => {
    // Check localStorage first
    if (typeof window !== 'undefined') {
      const saved = localStorage.getItem('darkMode');
      if (saved !== null) {
        return saved === 'true';
      }
    }
    // Default to dark mode
    return true;
  });

  useEffect(() => {
    const root = document.documentElement;
    if (isDark) {
      root.classList.add('dark');
    } else {
      root.classList.remove('dark');
    }
    // Persist to localStorage
    localStorage.setItem('darkMode', String(isDark));
  }, [isDark]);

  const toggleDarkMode = () => {
    setIsDark((prev) => !prev);
  };

  const setDarkMode = (value: boolean) => {
    setIsDark(value);
  };

  return {
    isDark,
    toggleDarkMode,
    setDarkMode,
  };
}

