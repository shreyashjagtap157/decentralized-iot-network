import React, { createContext, useContext, useEffect, useState } from 'react';

interface AccessibilityPreferences {
  // Visual preferences
  highContrast: boolean;
  reducedMotion: boolean;
  largeText: boolean;
  
  // Navigation preferences
  keyboardNavigation: boolean;
  screenReaderOptimized: boolean;
  
  // Interaction preferences
  autoplay: boolean;
  timeout: number; // in seconds
  
  // Language and localization
  language: string;
  rtlLayout: boolean;
}

interface AccessibilityContextType {
  preferences: AccessibilityPreferences;
  updatePreference: <K extends keyof AccessibilityPreferences>(
    key: K,
    value: AccessibilityPreferences[K]
  ) => void;
  resetPreferences: () => void;
  announceToScreenReader: (message: string) => void;
}

const defaultPreferences: AccessibilityPreferences = {
  highContrast: false,
  reducedMotion: false,
  largeText: false,
  keyboardNavigation: true,
  screenReaderOptimized: false,
  autoplay: false,
  timeout: 30,
  language: 'en',
  rtlLayout: false,
};

const AccessibilityContext = createContext<AccessibilityContextType | undefined>(undefined);

interface AccessibilityProviderProps {
  children: React.ReactNode;
}

export const AccessibilityProvider: React.FC<AccessibilityProviderProps> = ({ children }) => {
  const [preferences, setPreferences] = useState<AccessibilityPreferences>(defaultPreferences);
  const [announcer, setAnnouncer] = useState<HTMLElement | null>(null);

  useEffect(() => {
    // Load preferences from localStorage
    const saved = localStorage.getItem('accessibility-preferences');
    if (saved) {
      try {
        setPreferences({ ...defaultPreferences, ...JSON.parse(saved) });
      } catch (error) {
        console.error('Failed to parse accessibility preferences:', error);
      }
    }

    // Detect system preferences
    const detectSystemPreferences = () => {
      const mediaQueries = {
        reducedMotion: window.matchMedia('(prefers-reduced-motion: reduce)'),
        highContrast: window.matchMedia('(prefers-contrast: high)'),
      };

      const updateFromSystem = () => {
        setPreferences(prev => ({
          ...prev,
          reducedMotion: mediaQueries.reducedMotion.matches,
          highContrast: mediaQueries.highContrast.matches,
        }));
      };

      // Initial check
      updateFromSystem();

      // Listen for changes
      Object.values(mediaQueries).forEach(mq => {
        mq.addEventListener('change', updateFromSystem);
      });

      return () => {
        Object.values(mediaQueries).forEach(mq => {
          mq.removeEventListener('change', updateFromSystem);
        });
      };
    };

    const cleanup = detectSystemPreferences();

    // Create screen reader announcer element
    const announcerElement = document.createElement('div');
    announcerElement.setAttribute('aria-live', 'polite');
    announcerElement.setAttribute('aria-atomic', 'true');
    announcerElement.style.position = 'absolute';
    announcerElement.style.left = '-10000px';
    announcerElement.style.width = '1px';
    announcerElement.style.height = '1px';
    announcerElement.style.overflow = 'hidden';
    document.body.appendChild(announcerElement);
    setAnnouncer(announcerElement);

    return () => {
      cleanup();
      if (announcerElement.parentNode) {
        announcerElement.parentNode.removeChild(announcerElement);
      }
    };
  }, []);

  useEffect(() => {
    // Apply CSS custom properties based on preferences
    const root = document.documentElement;
    
    // High contrast
    if (preferences.highContrast) {
      root.style.setProperty('--text-contrast', '1');
      root.style.setProperty('--border-contrast', '2px');
    } else {
      root.style.removeProperty('--text-contrast');
      root.style.removeProperty('--border-contrast');
    }

    // Large text
    if (preferences.largeText) {
      root.style.setProperty('--font-scale', '1.2');
    } else {
      root.style.removeProperty('--font-scale');
    }

    // Reduced motion
    if (preferences.reducedMotion) {
      root.style.setProperty('--animation-duration', '0.01ms');
      root.style.setProperty('--transition-duration', '0.01ms');
    } else {
      root.style.removeProperty('--animation-duration');
      root.style.removeProperty('--transition-duration');
    }

    // RTL layout
    if (preferences.rtlLayout) {
      document.dir = 'rtl';
    } else {
      document.dir = 'ltr';
    }

    // Save preferences
    localStorage.setItem('accessibility-preferences', JSON.stringify(preferences));
  }, [preferences]);

  const updatePreference = <K extends keyof AccessibilityPreferences>(
    key: K,
    value: AccessibilityPreferences[K]
  ) => {
    setPreferences(prev => ({ ...prev, [key]: value }));
  };

  const resetPreferences = () => {
    setPreferences(defaultPreferences);
    localStorage.removeItem('accessibility-preferences');
  };

  const announceToScreenReader = (message: string) => {
    if (announcer) {
      announcer.textContent = message;
      // Clear after announcing
      setTimeout(() => {
        if (announcer) {
          announcer.textContent = '';
        }
      }, 1000);
    }
  };

  const contextValue: AccessibilityContextType = {
    preferences,
    updatePreference,
    resetPreferences,
    announceToScreenReader,
  };

  return (
    <AccessibilityContext.Provider value={contextValue}>
      {children}
    </AccessibilityContext.Provider>
  );
};

export const useAccessibility = (): AccessibilityContextType => {
  const context = useContext(AccessibilityContext);
  if (!context) {
    throw new Error('useAccessibility must be used within an AccessibilityProvider');
  }
  return context;
};

// Hook for keyboard navigation
export const useKeyboardNavigation = () => {
  const { preferences } = useAccessibility();

  useEffect(() => {
    if (!preferences.keyboardNavigation) return;

    const handleKeyDown = (event: KeyboardEvent) => {
      // Skip to main content with Alt+M
      if (event.altKey && event.key.toLowerCase() === 'm') {
        event.preventDefault();
        const main = document.querySelector('main') || document.querySelector('[role="main"]');
        if (main instanceof HTMLElement) {
          main.focus();
        }
      }

      // Skip to navigation with Alt+N
      if (event.altKey && event.key.toLowerCase() === 'n') {
        event.preventDefault();
        const nav = document.querySelector('nav') || document.querySelector('[role="navigation"]');
        if (nav instanceof HTMLElement) {
          nav.focus();
        }
      }

      // Escape key to close modals/menus
      if (event.key === 'Escape') {
        const activeModal = document.querySelector('[role="dialog"][aria-modal="true"]');
        if (activeModal) {
          const closeButton = activeModal.querySelector('[aria-label*="close"], [aria-label*="Close"]');
          if (closeButton instanceof HTMLElement) {
            closeButton.click();
          }
        }
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [preferences.keyboardNavigation]);
};

// Hook for focus management
export const useFocusManagement = () => {
  const [focusHistory, setFocusHistory] = useState<HTMLElement[]>([]);

  const saveFocus = () => {
    const activeElement = document.activeElement as HTMLElement;
    if (activeElement && activeElement !== document.body) {
      setFocusHistory(prev => [...prev, activeElement]);
    }
  };

  const restoreFocus = () => {
    const lastFocused = focusHistory[focusHistory.length - 1];
    if (lastFocused && document.contains(lastFocused)) {
      lastFocused.focus();
      setFocusHistory(prev => prev.slice(0, -1));
    }
  };

  const trapFocus = (container: HTMLElement) => {
    const focusableElements = container.querySelectorAll(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
    );
    const firstElement = focusableElements[0] as HTMLElement;
    const lastElement = focusableElements[focusableElements.length - 1] as HTMLElement;

    const handleTabKey = (event: KeyboardEvent) => {
      if (event.key !== 'Tab') return;

      if (event.shiftKey) {
        if (document.activeElement === firstElement) {
          event.preventDefault();
          lastElement?.focus();
        }
      } else {
        if (document.activeElement === lastElement) {
          event.preventDefault();
          firstElement?.focus();
        }
      }
    };

    container.addEventListener('keydown', handleTabKey);
    firstElement?.focus();

    return () => {
      container.removeEventListener('keydown', handleTabKey);
    };
  };

  return {
    saveFocus,
    restoreFocus,
    trapFocus,
  };
};
