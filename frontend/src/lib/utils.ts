import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

// Error handling utilities
export interface AppError {
  message: string;
  code?: string;
  details?: unknown;
}

export const createAppError = (
  message: string,
  code?: string,
  details?: unknown
): AppError => ({
  message,
  code,
  details,
});

export const getErrorMessage = (error: unknown): string => {
  if (error instanceof Error) {
    return error.message;
  }

  if (typeof error === 'string') {
    return error;
  }

  if (error && typeof error === 'object' && 'message' in error) {
    return String(error.message);
  }

  return 'An unexpected error occurred';
};

export const getSupabaseErrorMessage = (error: unknown): string => {
  // Handle Supabase specific error formats
  if (
    error &&
    typeof error === 'object' &&
    'message' in error &&
    typeof error.message === 'string'
  ) {
    // Common Supabase error patterns
    if (error.message.includes('JWT')) {
      return 'Authentication session expired. Please log in again.';
    }

    if (error.message.includes('Row Level Security')) {
      return 'Access denied. You can only access your own data.';
    }

    if (error.message.includes('duplicate key')) {
      return 'This record already exists.';
    }

    if (error.message.includes('foreign key')) {
      return 'Cannot complete operation due to data dependencies.';
    }

    if (error.message.includes('not found')) {
      return 'The requested data was not found.';
    }

    return error.message;
  }

  return getErrorMessage(error);
};

export const getNetworkErrorMessage = (error: unknown): string => {
  if (error && typeof error === 'object') {
    if (
      ('name' in error && error.name === 'NetworkError') ||
      ('message' in error &&
        typeof error.message === 'string' &&
        error.message.includes('fetch'))
    ) {
      return 'Network connection failed. Please check your internet connection and try again.';
    }

    if ('status' in error && typeof error.status === 'number') {
      switch (error.status) {
        case 400:
          return 'Invalid request. Please check your input and try again.';
        case 401:
          return 'Authentication required. Please log in and try again.';
        case 403:
          return 'Access denied. You do not have permission to perform this action.';
        case 404:
          return 'The requested resource was not found.';
        case 429:
          return 'Too many requests. Please wait a moment and try again.';
        case 500:
          return 'Server error. Please try again later or contact support.';
        case 503:
          return 'Service temporarily unavailable. Please try again later.';
        default:
          return `Request failed with status ${error.status}. Please try again.`;
      }
    }
  }

  return getErrorMessage(error);
};

// Form validation utilities
export const validateRequired = (
  value: string,
  fieldName: string
): string | null => {
  if (!value || !value.trim()) {
    return `${fieldName} is required`;
  }
  return null;
};

export const validateMinLength = (
  value: string,
  minLength: number,
  fieldName: string
): string | null => {
  if (value && value.trim().length < minLength) {
    return `${fieldName} must be at least ${minLength} characters long`;
  }
  return null;
};

export const validateMaxLength = (
  value: string,
  maxLength: number,
  fieldName: string
): string | null => {
  if (value && value.length > maxLength) {
    return `${fieldName} must be no more than ${maxLength} characters long`;
  }
  return null;
};

export const validateFileType = (
  file: File,
  allowedTypes: readonly string[] | string[]
): string | null => {
  if (!allowedTypes.includes(file.type)) {
    const typeNames = allowedTypes
      .map((type) => {
        switch (type) {
          case 'application/pdf':
            return 'PDF';
          case 'application/vnd.openxmlformats-officedocument.wordprocessingml.document':
            return 'DOCX';
          case 'text/plain':
            return 'TXT';
          default:
            return type;
        }
      })
      .join(', ');
    return `Please upload ${typeNames} files only`;
  }
  return null;
};

export const validateFileSize = (
  file: File,
  maxSizeInMB: number
): string | null => {
  const maxSizeInBytes = maxSizeInMB * 1024 * 1024;
  if (file.size > maxSizeInBytes) {
    return `File size must be less than ${maxSizeInMB}MB`;
  }
  return null;
};
