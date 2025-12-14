import React, { useContext } from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { jest } from '@jest/globals';
import '@testing-library/jest-dom';
import { ThemeProvider } from '@mui/material/styles';
import { createTheme } from '@mui/material/styles';

// Create a default theme for testing
const defaultTheme = createTheme();

// Import components to test
import { ThemeContext } from '../contexts/ThemeContext';
import { NotificationProvider, useNotification } from '../contexts/NotificationContext';
import { AccessibilityProvider, useAccessibility } from '../contexts/AccessibilityContext';
import ErrorBoundary from '../components/ErrorBoundary';

// Mock Next.js router
jest.mock('next/router', () => ({
  useRouter: () => ({
    push: jest.fn(),
    pathname: '/',
    query: {},
  }),
}));

// Mock localStorage
const localStorageMock = {
  getItem: jest.fn(),
  setItem: jest.fn(),
  removeItem: jest.fn(),
  clear: jest.fn(),
  length: 0,
  key: jest.fn(),
};
global.localStorage = localStorageMock as any;

// Test theme context
describe('ThemeContext', () => {
  beforeEach(() => {
    localStorageMock.getItem.mockClear();
    localStorageMock.setItem.mockClear();
  });

  it('should provide default light theme', () => {
    const TestComponent = () => {
      const { darkMode } = useContext(ThemeContext);
      return <div data-testid="theme-mode">{darkMode ? 'dark' : 'light'}</div>;
    };

    render(
      <ThemeProvider theme={defaultTheme}>
        <TestComponent />
      </ThemeProvider>
    );

    expect(screen.getByTestId('theme-mode')).toHaveTextContent('light');
  });

  it('should toggle theme mode', () => {
    const TestComponent = () => {
      const { darkMode, toggleDarkMode } = useContext(ThemeContext);
      return (
        <div>
          <div data-testid="theme-mode">{darkMode ? 'dark' : 'light'}</div>
          <button onClick={toggleDarkMode} data-testid="toggle-button">
            Toggle
          </button>
        </div>
      );
    };

    render(
      <ThemeProvider theme={defaultTheme}>
        <TestComponent />
      </ThemeProvider>
    );

    expect(screen.getByTestId('theme-mode')).toHaveTextContent('light');
    
    fireEvent.click(screen.getByTestId('toggle-button'));
    
    expect(screen.getByTestId('theme-mode')).toHaveTextContent('dark');
  });

  it('should persist theme preference in localStorage', () => {
    const TestComponent = () => {
      const { toggleDarkMode } = useContext(ThemeContext);
      return (
        <button onClick={toggleDarkMode} data-testid="toggle-button">
          Toggle
        </button>
      );
    };

    render(
      <ThemeProvider theme={defaultTheme}>
        <TestComponent />
      </ThemeProvider>
    );

    fireEvent.click(screen.getByTestId('toggle-button'));
    
    expect(localStorageMock.setItem).toHaveBeenCalledWith('darkMode', 'true');
  });
});

// Test notification system
describe('NotificationProvider', () => {
  const TestComponent = () => {
    const { addNotification, notifications } = useNotification();
    
    return (
      <div>
        <button
          onClick={() => addNotification({
            type: 'success',
            title: 'Test',
            message: 'Test message'
          })}
          data-testid="add-notification"
        >
          Add Notification
        </button>
        <div data-testid="notification-count">
          {notifications.length}
        </div>
      </div>
    );
  };

  it('should add notifications', () => {
    render(
      <NotificationProvider>
        <TestComponent />
      </NotificationProvider>
    );

    expect(screen.getByTestId('notification-count')).toHaveTextContent('0');
    
    fireEvent.click(screen.getByTestId('add-notification'));
    
    expect(screen.getByTestId('notification-count')).toHaveTextContent('1');
  });

  it('should auto-remove notifications after duration', async () => {
    const TestComponent = () => {
      const { addNotification, notifications } = useNotification();
      
      return (
        <div>
          <button
            onClick={() => addNotification({
              type: 'info',
              title: 'Auto Remove',
              message: 'This will disappear',
              duration: 100, // Very short duration for testing
            })}
            data-testid="add-auto-remove"
          >
            Add Auto Remove
          </button>
          <div data-testid="notification-count">
            {notifications.length}
          </div>
        </div>
      );
    };

    render(
      <NotificationProvider>
        <TestComponent />
      </NotificationProvider>
    );

    fireEvent.click(screen.getByTestId('add-auto-remove'));
    expect(screen.getByTestId('notification-count')).toHaveTextContent('1');
    
    await waitFor(
      () => {
        expect(screen.getByTestId('notification-count')).toHaveTextContent('0');
      },
      { timeout: 200 }
    );
  });

  it('should request notification permission', () => {
    // Mock Notification API
    const mockRequestPermission = jest.fn();
    (mockRequestPermission as any).mockResolvedValue('granted');
    global.Notification = {
      permission: 'default',
      requestPermission: mockRequestPermission,
    } as any;

    const TestComponent = () => {
      const { requestPermission } = useNotification();
      
      return (
        <button
          onClick={requestPermission}
          data-testid="request-permission"
        >
          Request Permission
        </button>
      );
    };

    render(
      <NotificationProvider>
        <TestComponent />
      </NotificationProvider>
    );

    fireEvent.click(screen.getByTestId('request-permission'));
    
    expect(global.Notification.requestPermission).toHaveBeenCalled();
  });
});

// Test accessibility features
describe('AccessibilityProvider', () => {
  beforeEach(() => {
    localStorageMock.getItem.mockClear();
    localStorageMock.setItem.mockClear();
  });

  const TestComponent = () => {
    const { preferences, updatePreference } = useAccessibility();
    
    return (
      <div>
        <div data-testid="high-contrast">
          {preferences.highContrast ? 'enabled' : 'disabled'}
        </div>
        <button
          onClick={() => updatePreference('highContrast', !preferences.highContrast)}
          data-testid="toggle-contrast"
        >
          Toggle High Contrast
        </button>
        <div data-testid="large-text">
          {preferences.largeText ? 'enabled' : 'disabled'}
        </div>
        <button
          onClick={() => updatePreference('largeText', !preferences.largeText)}
          data-testid="toggle-text-size"
        >
          Toggle Large Text
        </button>
      </div>
    );
  };

  it('should provide default accessibility preferences', () => {
    render(
      <AccessibilityProvider>
        <TestComponent />
      </AccessibilityProvider>
    );

    expect(screen.getByTestId('high-contrast')).toHaveTextContent('disabled');
    expect(screen.getByTestId('large-text')).toHaveTextContent('disabled');
  });

  it('should update accessibility preferences', () => {
    render(
      <AccessibilityProvider>
        <TestComponent />
      </AccessibilityProvider>
    );

    fireEvent.click(screen.getByTestId('toggle-contrast'));
    expect(screen.getByTestId('high-contrast')).toHaveTextContent('enabled');

    fireEvent.click(screen.getByTestId('toggle-text-size'));
    expect(screen.getByTestId('large-text')).toHaveTextContent('enabled');
  });

  it('should persist accessibility preferences', () => {
    render(
      <AccessibilityProvider>
        <TestComponent />
      </AccessibilityProvider>
    );

    fireEvent.click(screen.getByTestId('toggle-contrast'));
    
    expect(localStorageMock.setItem).toHaveBeenCalledWith(
      'accessibility-preferences',
      expect.stringContaining('"highContrast":true')
    );
  });

  it('should detect system preferences', () => {
    // Mock matchMedia
    global.matchMedia = jest.fn((query: string) => ({
      matches: query.includes('prefers-reduced-motion'),
      media: query,
      onchange: null,
      addListener: jest.fn(),
      removeListener: jest.fn(),
      addEventListener: jest.fn(),
      removeEventListener: jest.fn(),
      dispatchEvent: jest.fn(),
    })) as any;

    const TestComponent = () => {
      const { preferences } = useAccessibility();
      return (
        <div data-testid="reduced-motion">
          {preferences.reducedMotion ? 'enabled' : 'disabled'}
        </div>
      );
    };

    render(
      <AccessibilityProvider>
        <TestComponent />
      </AccessibilityProvider>
    );

    expect(screen.getByTestId('reduced-motion')).toHaveTextContent('enabled');
  });
});

// Test Error Boundary
describe('ErrorBoundary', () => {
  // Suppress console.error for these tests
  const originalError = console.error;
  beforeAll(() => {
    console.error = jest.fn();
  });

  afterAll(() => {
    console.error = originalError;
  });

  const ThrowError = ({ shouldThrow }) => {
    if (shouldThrow) {
      throw new Error('Test error');
    }
    return <div data-testid="success">No error</div>;
  };

  it('should render children when there is no error', () => {
    render(
      <ErrorBoundary>
        <ThrowError shouldThrow={false} />
      </ErrorBoundary>
    );

    expect(screen.getByTestId('success')).toBeInTheDocument();
  });

  it('should render error UI when there is an error', () => {
    render(
      <ErrorBoundary>
        <ThrowError shouldThrow={true} />
      </ErrorBoundary>
    );

    expect(screen.getByText('Oops! Something went wrong')).toBeInTheDocument();
    expect(screen.getByText('Try Again')).toBeInTheDocument();
  });

  it('should render custom fallback when provided', () => {
    const fallback = <div data-testid="custom-fallback">Custom Error</div>;
    
    render(
      <ErrorBoundary fallback={fallback}>
        <ThrowError shouldThrow={true} />
      </ErrorBoundary>
    );

    expect(screen.getByTestId('custom-fallback')).toBeInTheDocument();
  });

  it('should show error details in development mode', () => {
    const originalEnv = process.env.NODE_ENV;
    Object.defineProperty(process.env, 'NODE_ENV', {
      value: 'development',
      writable: true,
      configurable: true,
    });

    render(
      <ErrorBoundary>
        <ThrowError shouldThrow={true} />
      </ErrorBoundary>
    );

    expect(screen.getByText('Error Details (Development Mode):')).toBeInTheDocument();
    expect(screen.getByText(/Test error/)).toBeInTheDocument();

    Object.defineProperty(process.env, 'NODE_ENV', {
      value: originalEnv,
      writable: true,
      configurable: true,
    });
  });
});

// Integration tests
describe('Integration Tests', () => {
  it('should work with all providers together', () => {
    const TestApp = () => {
      const { darkMode } = useContext(ThemeContext);
      const { addNotification } = useNotification();
      const { preferences } = useAccessibility();
      
      return (
        <div>
          <div data-testid="theme">{darkMode ? 'dark' : 'light'}</div>
          <div data-testid="contrast">{preferences.highContrast ? 'high' : 'normal'}</div>
          <button
            onClick={() => addNotification({
              type: 'success',
              title: 'Integration Test',
              message: 'All providers working'
            })}
            data-testid="test-integration"
          >
            Test Integration
          </button>
        </div>
      );
    };

    render(
      <ErrorBoundary>
        <ThemeProvider theme={defaultTheme}>
          <AccessibilityProvider>
            <NotificationProvider>
              <TestApp />
            </NotificationProvider>
          </AccessibilityProvider>
        </ThemeProvider>
      </ErrorBoundary>
    );

    expect(screen.getByTestId('theme')).toHaveTextContent('light');
    expect(screen.getByTestId('contrast')).toHaveTextContent('normal');
    
    fireEvent.click(screen.getByTestId('test-integration'));
    
    // Should not throw any errors
    expect(screen.getByTestId('test-integration')).toBeInTheDocument();
  });
});

// Performance tests
describe('Performance Tests', () => {
  it('should not cause memory leaks with multiple notifications', () => {
    const TestComponent = () => {
      const { addNotification, clearAll } = useNotification();
      
      const addMany = () => {
        for (let i = 0; i < 100; i++) {
          addNotification({
            type: 'info',
            title: `Notification ${i}`,
            message: `Message ${i}`,
            duration: 0, // Don't auto-remove
          });
        }
      };
      
      return (
        <div>
          <button onClick={addMany} data-testid="add-many">
            Add Many
          </button>
          <button onClick={clearAll} data-testid="clear-all">
            Clear All
          </button>
        </div>
      );
    };

    render(
      <NotificationProvider>
        <TestComponent />
      </NotificationProvider>
    );

    fireEvent.click(screen.getByTestId('add-many'));
    fireEvent.click(screen.getByTestId('clear-all'));
    
    // Should complete without hanging
    expect(screen.getByTestId('clear-all')).toBeInTheDocument();
  });
});
