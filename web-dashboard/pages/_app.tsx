import React from 'react';
import { AppProps } from 'next/app';
import CssBaseline from '@mui/material/CssBaseline';
import { AuthProvider } from '../contexts/AuthContext';
import { ThemeProvider } from '../contexts/ThemeContext';
import Navigation from '../components/Navigation';
import { useRouter } from 'next/router';
import ErrorBoundary from '../components/ErrorBoundary';

// Pages that don't need navigation
const noNavPages = ['/login', '/register', '/'];

function MyApp({ Component, pageProps }: AppProps) {
  const router = useRouter();
  const showNav = !noNavPages.includes(router.pathname);

  return (
    <ThemeProvider>
      <CssBaseline />
      <ErrorBoundary>
        <AuthProvider>
          {showNav ? (
            <Navigation>
              <Component {...pageProps} />
            </Navigation>
          ) : (
            <Component {...pageProps} />
          )}
        </AuthProvider>
      </ErrorBoundary>
    </ThemeProvider>
  );
}

export default MyApp;
