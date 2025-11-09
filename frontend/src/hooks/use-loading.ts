import { useState, useCallback } from 'react';
import { useEnhancedToast } from './use-enhanced-toast';
import { LoadingStates } from '@/types';

export const useLoading = (
  initialState: LoadingStates = {
    analyze: false,
    fetchHistory: false,
    deleteAnalysis: false,
    deleteAccount: false,
    fetchAnalysis: false,
  }
) => {
  const [loadingStates, setLoadingStates] =
    useState<LoadingStates>(initialState);
  const { showError } = useEnhancedToast();

  const setLoading = useCallback((key: string, loading: boolean) => {
    setLoadingStates((prev) => ({
      ...prev,
      [key]: loading,
    }));
  }, []);

  const isLoading = useCallback(
    (key: string): boolean => {
      return loadingStates[key] || false;
    },
    [loadingStates]
  );

  const isAnyLoading = useCallback((): boolean => {
    return Object.values(loadingStates).some((loading) => loading);
  }, [loadingStates]);

  const withLoading = useCallback(
    async <T>(
      key: string,
      asyncOperation: () => Promise<T>,
      options?: {
        showErrorToast?: boolean;
        errorTitle?: string;
      }
    ): Promise<T | null> => {
      try {
        setLoading(key, true);
        const result = await asyncOperation();
        return result;
      } catch (error) {
        console.error(`Error in ${key}:`, error);

        if (options?.showErrorToast !== false) {
          showError(error, { title: options?.errorTitle });
        }

        return null;
      } finally {
        setLoading(key, false);
      }
    },
    [setLoading, showError]
  );

  const resetLoading = useCallback(() => {
    setLoadingStates({
      analyze: false,
      fetchHistory: false,
      deleteAnalysis: false,
      deleteAccount: false,
      fetchAnalysis: false,
    });
  }, []);

  return {
    loadingStates,
    setLoading,
    isLoading,
    isAnyLoading,
    withLoading,
    resetLoading,
  };
};
