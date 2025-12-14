/**
 * Accessibility utilities and components.
 * Follows WCAG 2.1 AA guidelines.
 */

import React, { useEffect, useRef, ReactNode } from 'react';

/**
 * Announce a message to screen readers.
 */
export function announceToScreenReader(message: string, priority: 'polite' | 'assertive' = 'polite') {
  const announcer = document.getElementById('sr-announcer') || createAnnouncer();
  announcer.setAttribute('aria-live', priority);
  announcer.textContent = message;
  
  // Clear after announcement
  setTimeout(() => {
    announcer.textContent = '';
  }, 1000);
}

function createAnnouncer(): HTMLElement {
  const announcer = document.createElement('div');
  announcer.id = 'sr-announcer';
  announcer.setAttribute('aria-live', 'polite');
  announcer.setAttribute('aria-atomic', 'true');
  announcer.style.cssText = `
    position: absolute;
    width: 1px;
    height: 1px;
    padding: 0;
    margin: -1px;
    overflow: hidden;
    clip: rect(0, 0, 0, 0);
    white-space: nowrap;
    border: 0;
  `;
  document.body.appendChild(announcer);
  return announcer;
}

/**
 * Visually hidden component for screen reader only content.
 */
export const VisuallyHidden: React.FC<{ children: ReactNode }> = ({ children }) => (
  <span
    style={{
      position: 'absolute',
      width: '1px',
      height: '1px',
      padding: 0,
      margin: '-1px',
      overflow: 'hidden',
      clip: 'rect(0, 0, 0, 0)',
      whiteSpace: 'nowrap',
      border: 0,
    }}
  >
    {children}
  </span>
);

/**
 * Skip to main content link for keyboard users.
 */
export const SkipLink: React.FC<{ targetId?: string }> = ({ targetId = 'main-content' }) => (
  <a
    href={`#${targetId}`}
    style={{
      position: 'absolute',
      left: '-9999px',
      top: 'auto',
      width: '1px',
      height: '1px',
      overflow: 'hidden',
    }}
    onFocus={(e) => {
      e.currentTarget.style.left = '0';
      e.currentTarget.style.width = 'auto';
      e.currentTarget.style.height = 'auto';
      e.currentTarget.style.padding = '16px';
      e.currentTarget.style.backgroundColor = '#667eea';
      e.currentTarget.style.color = 'white';
      e.currentTarget.style.zIndex = '9999';
      e.currentTarget.style.textDecoration = 'none';
      e.currentTarget.style.fontWeight = 'bold';
    }}
    onBlur={(e) => {
      e.currentTarget.style.left = '-9999px';
      e.currentTarget.style.width = '1px';
      e.currentTarget.style.height = '1px';
    }}
  >
    Skip to main content
  </a>
);

/**
 * Focus trap for modals and dialogs.
 */
interface FocusTrapProps {
  children: ReactNode;
  active?: boolean;
}

export const FocusTrap: React.FC<FocusTrapProps> = ({ children, active = true }) => {
  const containerRef = useRef<HTMLDivElement>(null);
  
  useEffect(() => {
    if (!active) return;
    
    const container = containerRef.current;
    if (!container) return;
    
    const focusableElements = container.querySelectorAll<HTMLElement>(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
    );
    
    const firstElement = focusableElements[0];
    const lastElement = focusableElements[focusableElements.length - 1];
    
    // Focus first element on mount
    firstElement?.focus();
    
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key !== 'Tab') return;
      
      if (e.shiftKey) {
        if (document.activeElement === firstElement) {
          e.preventDefault();
          lastElement?.focus();
        }
      } else {
        if (document.activeElement === lastElement) {
          e.preventDefault();
          firstElement?.focus();
        }
      }
    };
    
    container.addEventListener('keydown', handleKeyDown);
    return () => container.removeEventListener('keydown', handleKeyDown);
  }, [active]);
  
  return <div ref={containerRef}>{children}</div>;
};

/**
 * Hook to manage focus on route change.
 */
export function useFocusOnRouteChange() {
  useEffect(() => {
    const mainContent = document.getElementById('main-content');
    if (mainContent) {
      mainContent.focus();
    }
  }, []);
}

/**
 * ARIA-compliant loading indicator.
 */
interface LoadingIndicatorProps {
  loading: boolean;
  label?: string;
  children: ReactNode;
}

export const LoadingIndicator: React.FC<LoadingIndicatorProps> = ({
  loading,
  label = 'Loading...',
  children,
}) => (
  <div
    aria-busy={loading}
    aria-live="polite"
    aria-label={loading ? label : undefined}
  >
    {children}
  </div>
);

/**
 * Generate unique IDs for form accessibility.
 */
let idCounter = 0;
export function generateId(prefix: string = 'a11y'): string {
  return `${prefix}-${++idCounter}`;
}

/**
 * Hook for managing accessible form fields.
 */
export function useAccessibleField(label: string) {
  const id = useRef(generateId('field')).current;
  const descriptionId = `${id}-description`;
  const errorId = `${id}-error`;
  
  return {
    id,
    labelProps: {
      htmlFor: id,
    },
    inputProps: {
      id,
      'aria-describedby': descriptionId,
      'aria-errormessage': errorId,
    },
    descriptionId,
    errorId,
  };
}

/**
 * Reduce motion preference detection.
 */
export function prefersReducedMotion(): boolean {
  if (typeof window === 'undefined') return false;
  return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
}

/**
 * Apply ARIA attributes to a table for accessibility.
 */
export function getTableA11yProps(caption: string) {
  return {
    role: 'table',
    'aria-label': caption,
    'aria-describedby': undefined,
  };
}
