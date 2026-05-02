import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import './index.css';
import AppWithRouter from './AppWithRouter.tsx';
import { ThemeProvider } from './context/ThemeContext';

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <ThemeProvider>
      <AppWithRouter />
    </ThemeProvider>
  </StrictMode>,
);