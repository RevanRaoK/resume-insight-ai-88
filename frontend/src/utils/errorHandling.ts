/**
 * Error handling utilities for type-safe error management
 */

import {
  AppError,
  SupabaseError,
  APIError,
  ErrorResult,
  isSupabaseError,
  isAPIError,
} from '@/types';

/**
 * Wraps a function call in error handling and returns a typed result
 */
export async function withErrorHandling<T>(
  operation: () => Promise<T>,
  context?: string
): Promise<ErrorResult<T>> {
  try {
    const data = await operation();
    return { success: true, data };
  } catch (error) {
    const appError = normalizeError(error, context);
    return { success: false, error: appError };
  }
}

/**
 * Normalizes different error types into a consistent AppError format
 */
export function normalizeError(error: unknown, context?: string): AppError {
  // Handle Supabase errors
  if (isSupabaseError(error)) {
    return {
      message: error.message,
      code: error.code,
      details: {
        hint: error.hint,
        details: error.details,
        context,
      },
    };
  }

  // Handle API errors
  if (isAPIError(error)) {
    return {
      message: error.detail?.message || error.message || 'API request failed',
      code: error.status?.toString(),
      details: {
        context,
        originalError: error,
      },
    };
  }

  // Handle standard Error objects
  if (error instanceof Error) {
    return {
      message: error.message,
      details: {
        context,
        stack: error.stack,
      },
    };
  }

  // Handle unknown error types
  return {
    message: typeof error === 'string' ? error : 'An unknown error occurred',
    details: {
      context,
      originalError: error,
    },
  };
}

/**
 * Creates a user-friendly error message from an AppError
 */
export function formatErrorMessage(error: AppError): string {
  if (error.code === '404') {
    return 'The requested resource was not found.';
  }

  if (error.code === '401' || error.code === '403') {
    return 'You are not authorized to perform this action. Please log in and try again.';
  }

  if (error.code === '500') {
    return 'A server error occurred. Please try again later.';
  }

  // Return the original message for other cases
  return error.message;
}

/**
 * Logs an error with context information
 */
export function logError(error: AppError, context?: string): void {
  console.error(`Error${context ? ` in ${context}` : ''}:`, {
    message: error.message,
    code: error.code,
    details: error.details,
  });
}

/**
 * Creates a standardized error for validation failures
 */
export function createValidationError(
  field: string,
  message: string
): AppError {
  return {
    message: `Validation failed for ${field}: ${message}`,
    code: 'VALIDATION_ERROR',
    details: {
      field,
      validationMessage: message,
    },
  };
}

/**
 * Creates a standardized error for network failures
 */
export function createNetworkError(operation: string): AppError {
  return {
    message: `Network error during ${operation}. Please check your connection and try again.`,
    code: 'NETWORK_ERROR',
    details: {
      operation,
    },
  };
}

/**
 * Creates a standardized error for authentication failures
 */
export function createAuthError(message?: string): AppError {
  return {
    message: message || 'Authentication required. Please log in and try again.',
    code: 'AUTH_ERROR',
    details: {
      requiresAuth: true,
    },
  };
}

/**
 * Retry wrapper for operations that might fail temporarily
 */
export async function withRetry<T>(
  operation: () => Promise<T>,
  maxRetries: number = 3,
  delay: number = 1000
): Promise<T> {
  let lastError: unknown;

  for (let attempt = 1; attempt <= maxRetries; attempt++) {
    try {
      return await operation();
    } catch (error) {
      lastError = error;

      if (attempt === maxRetries) {
        throw error;
      }

      // Wait before retrying
      await new Promise((resolve) => setTimeout(resolve, delay * attempt));
    }
  }

  throw lastError;
}
