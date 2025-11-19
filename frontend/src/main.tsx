import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import App from './App.tsx';
import { AuthProvider } from './contexts/AuthContext';
import './index.css';

// Initialize dark mode immediately to prevent flash of light mode
(function() {
  const saved = localStorage.getItem('darkMode');
  const isDark = saved !== null ? saved === 'true' : true; // Default to dark
  if (isDark) {
    document.documentElement.classList.add('dark');
  }
})();

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <AuthProvider>
      <App />
    </AuthProvider>
  </StrictMode>
);
