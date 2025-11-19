import { Bell } from 'lucide-react';
import { toast } from '@/hooks/use-toast';

export interface Notification {
  id: string;
  type: 'success' | 'error' | 'info' | 'warning';
  title: string;
  message: string;
  timestamp: Date;
  read: boolean;
}

// Helper function to show toast notifications
export function showNotification(type: Notification['type'], title: string, message: string) {
  const getVariant = (type: Notification['type']) => {
    switch (type) {
      case 'error':
        return 'destructive';
      default:
        return 'default';
    }
  };

  toast({
    variant: getVariant(type),
    title,
    description: message,
  });
}

// Backward compatibility wrapper - this component is now just a placeholder
// The actual notifications are handled by the Toaster component in App.tsx
interface NotificationCenterProps {
  notifications: Notification[];
  onDismiss: (id: string) => void;
}

export function NotificationCenter({ notifications, onDismiss }: NotificationCenterProps) {
  // This component is kept for backward compatibility but doesn't render anything
  // The Toaster component in App.tsx handles all toast display
  return null;
}

export function NotificationBell({ count }: { count: number }) {
  return (
    <div className="relative">
      <Bell className="w-6 h-6 text-slate-700 dark:text-slate-300 hover:text-slate-900 dark:text-slate-100 cursor-pointer transition-colors" />
      {count > 0 && (
        <span className="absolute -top-2 -right-2 bg-red-500 text-white text-xs font-bold rounded-full w-5 h-5 flex items-center justify-center">
          {count > 9 ? '9+' : count}
        </span>
      )}
    </div>
  );
}
