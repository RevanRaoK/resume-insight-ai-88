import { useToast } from '@/hooks/use-toast';
import {
  getErrorMessage,
  getSupabaseErrorMessage,
  getNetworkErrorMessage,
} from '@/lib/utils';

export interface ToastOptions {
  title?: string;
  description?: string;
  duration?: number;
}

export const useEnhancedToast = () => {
  const { toast } = useToast();

  const showSuccess = (message: string, options?: ToastOptions) => {
    toast({
      title: options?.title || 'Success',
      description: message,
      duration: options?.duration || 4000,
      ...options,
    });
  };

  const showError = (error: unknown, options?: ToastOptions) => {
    const message = getErrorMessage(error);
    toast({
      title: options?.title || 'Error',
      description: message,
      variant: 'destructive',
      duration: options?.duration || 6000,
      ...options,
    });
  };

  const showSupabaseError = (error: unknown, options?: ToastOptions) => {
    const message = getSupabaseErrorMessage(error);
    toast({
      title: options?.title || 'Database Error',
      description: message,
      variant: 'destructive',
      duration: options?.duration || 6000,
      ...options,
    });
  };

  const showNetworkError = (error: unknown, options?: ToastOptions) => {
    const message = getNetworkErrorMessage(error);
    toast({
      title: options?.title || 'Network Error',
      description: message,
      variant: 'destructive',
      duration: options?.duration || 6000,
      ...options,
    });
  };

  const showValidationError = (message: string, options?: ToastOptions) => {
    toast({
      title: options?.title || 'Validation Error',
      description: message,
      variant: 'destructive',
      duration: options?.duration || 5000,
      ...options,
    });
  };

  const showWarning = (message: string, options?: ToastOptions) => {
    toast({
      title: options?.title || 'Warning',
      description: message,
      variant: 'default', // Using default as there's no warning variant
      duration: options?.duration || 5000,
      ...options,
    });
  };

  const showInfo = (message: string, options?: ToastOptions) => {
    toast({
      title: options?.title || 'Information',
      description: message,
      duration: options?.duration || 4000,
      ...options,
    });
  };

  // Specific operation toasts
  const showLoadingToast = (message: string = 'Loading...') => {
    return toast({
      title: 'Please wait',
      description: message,
      duration: 30000, // Long duration for loading states
    });
  };

  const showOperationSuccess = (operation: string, item?: string) => {
    const message = item
      ? `${item} ${operation} successfully`
      : `${operation} completed successfully`;

    showSuccess(message);
  };

  const showOperationError = (
    operation: string,
    error: unknown,
    item?: string
  ) => {
    const baseMessage = item
      ? `Failed to ${operation.toLowerCase()} ${item}`
      : `Failed to ${operation.toLowerCase()}`;

    const errorMessage = getErrorMessage(error);
    const fullMessage = `${baseMessage}. ${errorMessage}`;

    showError(fullMessage, { title: `${operation} Failed` });
  };

  return {
    toast, // Original toast function
    showSuccess,
    showError,
    showSupabaseError,
    showNetworkError,
    showValidationError,
    showWarning,
    showInfo,
    showLoadingToast,
    showOperationSuccess,
    showOperationError,
  };
};
