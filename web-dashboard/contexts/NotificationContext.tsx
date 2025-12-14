import React, { createContext, useContext, useEffect, useState } from 'react';
import { Snackbar, Alert, IconButton } from '@mui/material';
import { Close } from '@mui/icons-material';

export interface Notification {
  id: string;
  type: 'success' | 'error' | 'warning' | 'info';
  title: string;
  message: string;
  duration?: number;
  actions?: Array<{
    label: string;
    action: () => void;
  }>;
}

interface NotificationContextType {
  notifications: Notification[];
  addNotification: (notification: Omit<Notification, 'id'>) => string;
  removeNotification: (id: string) => void;
  clearAll: () => void;
  requestPermission: () => Promise<boolean>;
  sendPushNotification: (title: string, options?: NotificationOptions) => void;
  isSupported: boolean;
  permission: NotificationPermission;
}

const NotificationContext = createContext<NotificationContextType | undefined>(undefined);

interface NotificationProviderProps {
  children: React.ReactNode;
}

export const NotificationProvider: React.FC<NotificationProviderProps> = ({ children }) => {
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [permission, setPermission] = useState<NotificationPermission>('default');
  const [isSupported, setIsSupported] = useState(false);

  useEffect(() => {
    // Check if browser supports notifications
    const supported = 'Notification' in window;
    setIsSupported(supported);
    
    if (supported) {
      setPermission(Notification.permission);
    }

    // Register service worker for push notifications
    if ('serviceWorker' in navigator && 'PushManager' in window) {
      navigator.serviceWorker.register('/sw.js')
        .then((registration) => {
          console.log('Service Worker registered:', registration);
        })
        .catch((error) => {
          console.error('Service Worker registration failed:', error);
        });
    }
  }, []);

  const generateId = (): string => {
    return Date.now().toString(36) + Math.random().toString(36).substr(2);
  };

  const addNotification = (notification: Omit<Notification, 'id'>): string => {
    const id = generateId();
    const newNotification: Notification = {
      ...notification,
      id,
      duration: notification.duration ?? 5000,
    };

    setNotifications(prev => [...prev, newNotification]);

    // Auto-remove notification after duration
    if (newNotification.duration && newNotification.duration > 0) {
      setTimeout(() => {
        removeNotification(id);
      }, newNotification.duration);
    }

    return id;
  };

  const removeNotification = (id: string): void => {
    setNotifications(prev => prev.filter(notification => notification.id !== id));
  };

  const clearAll = (): void => {
    setNotifications([]);
  };

  const requestPermission = async (): Promise<boolean> => {
    if (!isSupported) {
      return false;
    }

    try {
      const result = await Notification.requestPermission();
      setPermission(result);
      return result === 'granted';
    } catch (error) {
      console.error('Failed to request notification permission:', error);
      return false;
    }
  };

  const sendPushNotification = (title: string, options?: NotificationOptions): void => {
    if (!isSupported || permission !== 'granted') {
      // Fallback to in-app notification
      addNotification({
        type: 'info',
        title: title,
        message: options?.body || '',
      });
      return;
    }

    try {
      new Notification(title, {
        icon: '/icons/icon-192x192.png',
        badge: '/icons/badge-72x72.png',
        tag: 'iot-network',
        requireInteraction: false,
        ...options,
      });
    } catch (error) {
      console.error('Failed to send push notification:', error);
      // Fallback to in-app notification
      addNotification({
        type: 'error',
        title: 'Notification Error',
        message: 'Failed to send push notification',
      });
    }
  };

  const contextValue: NotificationContextType = {
    notifications,
    addNotification,
    removeNotification,
    clearAll,
    requestPermission,
    sendPushNotification,
    isSupported,
    permission,
  };

  return (
    <NotificationContext.Provider value={contextValue}>
      {children}
      <NotificationContainer />
    </NotificationContext.Provider>
  );
};

const NotificationContainer: React.FC = () => {
  const context = useContext(NotificationContext);
  if (!context) return null;

  const { notifications, removeNotification } = context;

  return (
    <>
      {notifications.map((notification, index) => (
        <Snackbar
          key={notification.id}
          open={true}
          autoHideDuration={notification.duration}
          onClose={() => removeNotification(notification.id)}
          anchorOrigin={{ vertical: 'top', horizontal: 'right' }}
          sx={{
            mt: index * 8, // Stack notifications
          }}
        >
          <Alert
            severity={notification.type}
            onClose={() => removeNotification(notification.id)}
            action={
              <>
                {notification.actions?.map((action, actionIndex) => (
                  <IconButton
                    key={actionIndex}
                    size="small"
                    onClick={action.action}
                    color="inherit"
                  >
                    {action.label}
                  </IconButton>
                ))}
                <IconButton
                  size="small"
                  onClick={() => removeNotification(notification.id)}
                  color="inherit"
                >
                  <Close fontSize="small" />
                </IconButton>
              </>
            }
            sx={{ minWidth: '300px' }}
          >
            <strong>{notification.title}</strong>
            {notification.message && (
              <div style={{ marginTop: 4 }}>{notification.message}</div>
            )}
          </Alert>
        </Snackbar>
      ))}
    </>
  );
};

export const useNotification = (): NotificationContextType => {
  const context = useContext(NotificationContext);
  if (!context) {
    throw new Error('useNotification must be used within a NotificationProvider');
  }
  return context;
};

// Hook for device-specific notifications
export const useDeviceNotifications = () => {
  const { addNotification, sendPushNotification } = useNotification();

  const notifyDeviceOnline = (deviceId: string, deviceName: string) => {
    const title = 'Device Online';
    const message = `${deviceName} (${deviceId}) is now online`;
    
    addNotification({
      type: 'success',
      title,
      message,
    });
    
    sendPushNotification(title, {
      body: message,
      icon: '/icons/device-online.png',
    });
  };

  const notifyDeviceOffline = (deviceId: string, deviceName: string) => {
    const title = 'Device Offline';
    const message = `${deviceName} (${deviceId}) has gone offline`;
    
    addNotification({
      type: 'warning',
      title,
      message,
      duration: 8000,
    });
    
    sendPushNotification(title, {
      body: message,
      icon: '/icons/device-offline.png',
      requireInteraction: true,
    });
  };

  const notifyEarningsUpdate = (amount: string, device: string) => {
    const title = 'Earnings Update';
    const message = `Earned ${amount} tokens from ${device}`;
    
    addNotification({
      type: 'success',
      title,
      message,
    });
    
    sendPushNotification(title, {
      body: message,
      icon: '/icons/earnings.png',
    });
  };

  const notifyMaintenanceRequired = (deviceId: string, issue: string) => {
    const title = 'Maintenance Required';
    const message = `Device ${deviceId}: ${issue}`;
    
    addNotification({
      type: 'error',
      title,
      message,
      duration: 0, // Don't auto-dismiss
      actions: [
        {
          label: 'View Details',
          action: () => {
            window.location.href = `/devices/${deviceId}`;
          },
        },
      ],
    });
    
    sendPushNotification(title, {
      body: message,
      icon: '/icons/maintenance.png',
      requireInteraction: true,
    });
  };

  return {
    notifyDeviceOnline,
    notifyDeviceOffline,
    notifyEarningsUpdate,
    notifyMaintenanceRequired,
  };
};
