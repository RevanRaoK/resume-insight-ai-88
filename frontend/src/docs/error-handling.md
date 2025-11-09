# Error Handling Implementation

This document describes the comprehensive error handling and user feedback system implemented in the application.

## Overview

The error handling system provides:

- Consistent error messaging across all components
- Enhanced toast notifications for different error types
- Form validation with real-time feedback
- Loading states for all async operations
- Error boundaries for component error handling
- Proper error recovery mechanisms

## Components

### 1. ErrorBoundary Component (`src/components/ErrorBoundary.tsx`)

A React error boundary that catches JavaScript errors anywhere in the component tree and displays a fallback UI.

**Features:**

- Catches and logs component errors
- Shows user-friendly error messages
- Provides retry and refresh options
- Shows detailed error information in development mode
- Includes `useErrorHandler` hook for functional components

**Usage:**

```tsx
<ErrorBoundary>
  <YourComponent />
</ErrorBoundary>
```

### 2. Enhanced Toast Hook (`src/hooks/use-enhanced-toast.ts`)

Provides specialized toast functions for different types of messages and errors.

**Functions:**

- `showSuccess(message, options?)` - Success notifications
- `showError(error, options?)` - General error handling
- `showSupabaseError(error, options?)` - Database-specific errors
- `showNetworkError(error, options?)` - Network-related errors
- `showValidationError(message, options?)` - Form validation errors
- `showWarning(message, options?)` - Warning messages
- `showInfo(message, options?)` - Information messages
- `showOperationSuccess(operation, item?)` - Operation success messages
- `showOperationError(operation, error, item?)` - Operation failure messages

**Usage:**

```tsx
const { showSuccess, showError } = useEnhancedToast();

// Success message
showSuccess('Data saved successfully');

// Error handling
try {
  await someOperation();
} catch (error) {
  showError(error);
}
```

### 3. Loading State Hook (`src/hooks/use-loading.ts`)

Manages loading states for multiple async operations with automatic error handling.

**Functions:**

- `setLoading(key, loading)` - Set loading state for a specific operation
- `isLoading(key)` - Check if a specific operation is loading
- `isAnyLoading()` - Check if any operation is loading
- `withLoading(key, asyncOperation, options?)` - Execute async operation with loading state
- `resetLoading()` - Clear all loading states

**Usage:**

```tsx
const { isLoading, withLoading } = useLoading();

const handleSubmit = async () => {
  const result = await withLoading(
    'submit',
    async () => {
      return await api.submitData(data);
    },
    {
      showErrorToast: true,
      errorTitle: 'Submission Failed',
    }
  );

  if (result) {
    // Handle success
  }
};

return (
  <Button disabled={isLoading('submit')}>
    {isLoading('submit') ? 'Submitting...' : 'Submit'}
  </Button>
);
```

### 4. Form Validation Hook (`src/hooks/use-form-validation.ts`)

Provides comprehensive form validation with real-time feedback.

**Functions:**

- `validateField(fieldName, value, rules)` - Validate a single field
- `validateFileField(fieldName, file, rules)` - Validate file uploads
- `validateAndSetError(fieldName, value, rules)` - Validate and set error state
- `validateAllFields(fields)` - Validate multiple fields at once
- `shouldShowError(fieldName)` - Check if error should be displayed
- `hasErrors()` - Check if form has any errors

**Validation Rules:**

- `required` - Field is required
- `minLength` - Minimum character length
- `maxLength` - Maximum character length
- `custom` - Custom validation function

**File Validation Rules:**

- `required` - File is required
- `allowedTypes` - Array of allowed MIME types
- `maxSizeInMB` - Maximum file size in MB
- `custom` - Custom file validation function

**Usage:**

```tsx
const { validateAndSetError, shouldShowError, getFieldError, setFieldTouched } =
  useFormValidation();

const handleInputChange = (value: string) => {
  setValue(value);
  if (shouldShowError('fieldName')) {
    validateAndSetError('fieldName', value, {
      required: true,
      minLength: 3,
    });
  }
};

return (
  <div>
    <Input
      value={value}
      onChange={(e) => handleInputChange(e.target.value)}
      onBlur={() => {
        setFieldTouched('fieldName');
        validateAndSetError('fieldName', value, { required: true });
      }}
      className={shouldShowError('fieldName') ? 'border-destructive' : ''}
    />
    {shouldShowError('fieldName') && (
      <p className="text-destructive text-sm">{getFieldError('fieldName')}</p>
    )}
  </div>
);
```

## Utility Functions (`src/lib/utils.ts`)

### Error Message Utilities

- `getErrorMessage(error)` - Extract error message from various error types
- `getSupabaseErrorMessage(error)` - Handle Supabase-specific error formats
- `getNetworkErrorMessage(error)` - Handle network and HTTP errors

### Validation Utilities

- `validateRequired(value, fieldName)` - Required field validation
- `validateMinLength(value, minLength, fieldName)` - Minimum length validation
- `validateMaxLength(value, maxLength, fieldName)` - Maximum length validation
- `validateFileType(file, allowedTypes)` - File type validation
- `validateFileSize(file, maxSizeInMB)` - File size validation

## Implementation Examples

### Dashboard Component

The Dashboard component demonstrates comprehensive error handling:

```tsx
// Form validation with real-time feedback
const validateForm = (): boolean => {
  clearAllErrors();
  let isValid = true;

  if (!validateFileAndSetError('resume', file, {
    required: true,
    allowedTypes: ['application/pdf', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'],
    maxSizeInMB: 10,
  })) {
    isValid = false;
  }

  return isValid;
};

// Async operation with loading state and error handling
const handleAnalyze = async () => {
  if (!validateForm()) {
    showValidationError('Please fix the validation errors before submitting');
    return;
  }

  const result = await withLoading('analyze', async () => {
    // API calls with proper error handling
    const response = await fetch('/api/analyze', { ... });
    if (!response.ok) {
      throw new Error(`Analysis failed with status ${response.status}`);
    }
    return await response.json();
  }, {
    errorTitle: 'Analysis Failed'
  });

  if (result) {
    showSuccess('Analysis completed successfully!');
    navigate(`/analysis/${result.id}`);
  }
};
```

### History Component

The History component shows Supabase error handling:

```tsx
const fetchHistory = useCallback(async () => {
  const result = await withLoading(
    'fetchHistory',
    async () => {
      const { data, error } = await supabase
        .from('analyses')
        .select('*')
        .eq('user_id', user.id);

      if (error) {
        throw error; // Will be handled by getSupabaseErrorMessage
      }

      return data || [];
    },
    {
      showErrorToast: true,
      errorTitle: 'Failed to Load History',
    }
  );

  if (result) {
    setAnalyses(result);
  }
}, [user?.id, withLoading]);
```

## Error Types and Handling

### 1. Network Errors

- Connection failures
- HTTP status errors (400, 401, 403, 404, 500, etc.)
- Timeout errors

### 2. Supabase Errors

- Authentication errors (JWT expired)
- Row Level Security violations
- Database constraint violations
- Connection errors

### 3. Validation Errors

- Required field validation
- Format validation (email, phone, etc.)
- File type and size validation
- Custom business rule validation

### 4. Component Errors

- JavaScript runtime errors
- React rendering errors
- Async operation failures

## Best Practices

1. **Always use the enhanced toast hooks** instead of the basic toast
2. **Wrap async operations** with the `withLoading` hook
3. **Validate forms** before submission using the validation hook
4. **Show loading states** for all async operations
5. **Provide specific error messages** rather than generic ones
6. **Handle edge cases** like network failures and authentication errors
7. **Use error boundaries** around major component sections
8. **Log errors** for debugging while showing user-friendly messages
9. **Provide recovery options** (retry, refresh, navigate away)
10. **Test error scenarios** to ensure proper handling

## Testing Error Handling

To test the error handling implementation:

1. **Network Errors**: Disconnect internet or use network throttling
2. **Validation Errors**: Submit forms with invalid data
3. **Authentication Errors**: Use expired tokens or log out during operations
4. **File Upload Errors**: Upload invalid file types or oversized files
5. **Component Errors**: Introduce intentional errors in development

## Future Enhancements

1. **Error Reporting Service**: Integration with services like Sentry
2. **Offline Support**: Handle offline scenarios gracefully
3. **Retry Mechanisms**: Automatic retry for transient failures
4. **Error Analytics**: Track error patterns and frequencies
5. **User Feedback**: Allow users to report errors or provide feedback
