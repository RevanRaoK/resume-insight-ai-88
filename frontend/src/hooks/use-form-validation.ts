import { useState, useCallback } from 'react';
import {
  validateRequired,
  validateMinLength,
  validateMaxLength,
  validateFileType,
  validateFileSize,
} from '@/lib/utils';
import { ValidationErrors, TouchedFields } from '@/types';

export interface ValidationRule {
  required?: boolean;
  minLength?: number;
  maxLength?: number;
  custom?: (value: string) => string | null;
}

export interface FileValidationRule {
  required?: boolean;
  allowedTypes?: readonly string[] | string[];
  maxSizeInMB?: number;
  custom?: (file: File) => string | null;
}

export const useFormValidation = () => {
  const [errors, setErrors] = useState<ValidationErrors>({});
  const [touched, setTouched] = useState<TouchedFields>({
    resume: false,
    jobDescription: false,
    jobRole: false,
  });

  const validateField = useCallback(
    (
      fieldName: string,
      value: string,
      rules: ValidationRule
    ): string | null => {
      // Required validation
      if (rules.required) {
        const requiredError = validateRequired(value, fieldName);
        if (requiredError) return requiredError;
      }

      // Skip other validations if field is empty and not required
      if (!value || !value.trim()) {
        return null;
      }

      // Min length validation
      if (rules.minLength !== undefined) {
        const minLengthError = validateMinLength(
          value,
          rules.minLength,
          fieldName
        );
        if (minLengthError) return minLengthError;
      }

      // Max length validation
      if (rules.maxLength !== undefined) {
        const maxLengthError = validateMaxLength(
          value,
          rules.maxLength,
          fieldName
        );
        if (maxLengthError) return maxLengthError;
      }

      // Custom validation
      if (rules.custom) {
        const customError = rules.custom(value);
        if (customError) return customError;
      }

      return null;
    },
    []
  );

  const validateFileField = useCallback(
    (
      fieldName: string,
      file: File | null,
      rules: FileValidationRule
    ): string | null => {
      // Required validation
      if (rules.required && !file) {
        return `${fieldName} is required`;
      }

      // Skip other validations if file is not provided and not required
      if (!file) {
        return null;
      }

      // File type validation
      if (rules.allowedTypes) {
        const typeError = validateFileType(file, rules.allowedTypes);
        if (typeError) return typeError;
      }

      // File size validation
      if (rules.maxSizeInMB !== undefined) {
        const sizeError = validateFileSize(file, rules.maxSizeInMB);
        if (sizeError) return sizeError;
      }

      // Custom validation
      if (rules.custom) {
        const customError = rules.custom(file);
        if (customError) return customError;
      }

      return null;
    },
    []
  );

  const setFieldError = useCallback(
    (fieldName: string, error: string | null) => {
      setErrors((prev) => ({
        ...prev,
        [fieldName]: error,
      }));
    },
    []
  );

  const clearFieldError = useCallback((fieldName: string) => {
    setErrors((prev) => {
      const newErrors = { ...prev };
      delete newErrors[fieldName];
      return newErrors;
    });
  }, []);

  const setFieldTouched = useCallback(
    (fieldName: string, isTouched: boolean = true) => {
      setTouched((prev) => ({
        ...prev,
        [fieldName]: isTouched,
      }));
    },
    []
  );

  const validateAndSetError = useCallback(
    (fieldName: string, value: string, rules: ValidationRule) => {
      const error = validateField(fieldName, value, rules);
      setFieldError(fieldName, error);
      return error === null;
    },
    [validateField, setFieldError]
  );

  const validateFileAndSetError = useCallback(
    (fieldName: string, file: File | null, rules: FileValidationRule) => {
      const error = validateFileField(fieldName, file, rules);
      setFieldError(fieldName, error);
      return error === null;
    },
    [validateFileField, setFieldError]
  );

  const validateAllFields = useCallback(
    (fields: {
      [fieldName: string]: { value: string; rules: ValidationRule };
    }): boolean => {
      let isValid = true;
      const newErrors: ValidationErrors = {};

      Object.entries(fields).forEach(([fieldName, { value, rules }]) => {
        const error = validateField(fieldName, value, rules);
        if (error) {
          newErrors[fieldName] = error;
          isValid = false;
        }
      });

      setErrors(newErrors);
      return isValid;
    },
    [validateField]
  );

  const clearAllErrors = useCallback(() => {
    setErrors({});
  }, []);

  const clearAllTouched = useCallback(() => {
    setTouched({
      resume: false,
      jobDescription: false,
      jobRole: false,
    });
  }, []);

  const reset = useCallback(() => {
    setErrors({});
    setTouched({
      resume: false,
      jobDescription: false,
      jobRole: false,
    });
  }, []);

  const hasErrors = useCallback(() => {
    return Object.values(errors).some((error) => error !== null);
  }, [errors]);

  const getFieldError = useCallback(
    (fieldName: string): string | null => {
      return errors[fieldName] || null;
    },
    [errors]
  );

  const isFieldTouched = useCallback(
    (fieldName: string): boolean => {
      return touched[fieldName] || false;
    },
    [touched]
  );

  const shouldShowError = useCallback(
    (fieldName: string): boolean => {
      return isFieldTouched(fieldName) && !!getFieldError(fieldName);
    },
    [isFieldTouched, getFieldError]
  );

  return {
    errors,
    touched,
    validateField,
    validateFileField,
    setFieldError,
    clearFieldError,
    setFieldTouched,
    validateAndSetError,
    validateFileAndSetError,
    validateAllFields,
    clearAllErrors,
    clearAllTouched,
    reset,
    hasErrors,
    getFieldError,
    isFieldTouched,
    shouldShowError,
  };
};
