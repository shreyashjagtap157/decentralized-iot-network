import { useEffect, useCallback } from 'react';

/**
 * Keyboard shortcut definitions and hook for power users.
 */

export interface KeyboardShortcut {
  key: string;
  ctrl?: boolean;
  shift?: boolean;
  alt?: boolean;
  meta?: boolean;
  description: string;
  action: () => void;
}

/**
 * Hook for registering keyboard shortcuts.
 * 
 * @example
 * useKeyboardShortcuts([
 *   { key: 'n', ctrl: true, description: 'New device', action: () => openDialog() },
 *   { key: 'Escape', description: 'Close dialog', action: () => closeDialog() }
 * ]);
 */
export function useKeyboardShortcuts(shortcuts: KeyboardShortcut[], enabled: boolean = true) {
  const handleKeyDown = useCallback((event: KeyboardEvent) => {
    if (!enabled) return;
    
    // Ignore if typing in an input field
    const target = event.target as HTMLElement;
    if (
      target.tagName === 'INPUT' ||
      target.tagName === 'TEXTAREA' ||
      target.isContentEditable
    ) {
      // Allow Escape key even in inputs
      if (event.key !== 'Escape') return;
    }
    
    for (const shortcut of shortcuts) {
      const ctrlMatch = shortcut.ctrl ? (event.ctrlKey || event.metaKey) : !event.ctrlKey;
      const shiftMatch = shortcut.shift ? event.shiftKey : !event.shiftKey;
      const altMatch = shortcut.alt ? event.altKey : !event.altKey;
      const keyMatch = event.key.toLowerCase() === shortcut.key.toLowerCase();
      
      if (keyMatch && ctrlMatch && shiftMatch && altMatch) {
        event.preventDefault();
        shortcut.action();
        return;
      }
    }
  }, [shortcuts, enabled]);
  
  useEffect(() => {
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [handleKeyDown]);
}

/**
 * Pre-defined global shortcuts.
 */
export const globalShortcuts = {
  SEARCH: { key: 'k', ctrl: true, description: 'Open search' },
  NEW_DEVICE: { key: 'n', ctrl: true, description: 'Add new device' },
  REFRESH: { key: 'r', ctrl: true, description: 'Refresh data' },
  TOGGLE_THEME: { key: 'd', ctrl: true, shift: true, description: 'Toggle dark mode' },
  HELP: { key: '?', shift: true, description: 'Show keyboard shortcuts' },
  ESCAPE: { key: 'Escape', description: 'Close dialog/modal' },
  DASHBOARD: { key: '1', alt: true, description: 'Go to Dashboard' },
  DEVICES: { key: '2', alt: true, description: 'Go to Devices' },
  ANALYTICS: { key: '3', alt: true, description: 'Go to Analytics' },
  WALLET: { key: '4', alt: true, description: 'Go to Wallet' },
  SETTINGS: { key: 's', ctrl: true, shift: true, description: 'Go to Settings' },
};

/**
 * Format shortcut for display.
 */
export function formatShortcut(shortcut: Partial<KeyboardShortcut>): string {
  const parts: string[] = [];
  
  if (shortcut.ctrl) parts.push('Ctrl');
  if (shortcut.alt) parts.push('Alt');
  if (shortcut.shift) parts.push('Shift');
  if (shortcut.meta) parts.push('⌘');
  
  if (shortcut.key) {
    const keyDisplay = shortcut.key.length === 1 
      ? shortcut.key.toUpperCase() 
      : shortcut.key;
    parts.push(keyDisplay);
  }
  
  return parts.join(' + ');
}

/**
 * Component to display keyboard shortcut help.
 */
import React from 'react';

interface ShortcutHelpProps {
  shortcuts: KeyboardShortcut[];
}

export const ShortcutHelp: React.FC<ShortcutHelpProps> = ({ shortcuts }) => {
  return (
    <div style={{ 
      display: 'grid', 
      gridTemplateColumns: 'auto 1fr', 
      gap: '8px 16px',
      fontSize: '14px'
    }}>
      {shortcuts.map((shortcut, index) => (
        <React.Fragment key={index}>
          <kbd style={{
            padding: '4px 8px',
            borderRadius: '4px',
            backgroundColor: '#f0f0f0',
            border: '1px solid #ccc',
            fontFamily: 'monospace',
            fontSize: '12px'
          }}>
            {formatShortcut(shortcut)}
          </kbd>
          <span>{shortcut.description}</span>
        </React.Fragment>
      ))}
    </div>
  );
};
