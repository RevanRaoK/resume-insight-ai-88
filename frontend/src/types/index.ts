/**
 * Centralized TypeScript type definitions for the job role user management feature
 * This file consolidates all interfaces and types used across the application
 */

import { Json } from '@/integrations/supabase/types';

// =============================================================================
// DATABASE TYPES (Supabase Schema Aligned)
// =============================================================================

/**
 * Analysis interface matching the Supabase analyses table schema
 * Used for type-safe database operations and UI components
 */
export interface Analysis {
  id: string;
  user_id: string;
  job_title: string; // Serves as job_role in the UI
  job_description: string;
  match_score: number;
  ai_feedback: Json; // Stored as JSON in Supabase
  matched_keywords: Json; // Array of strings stored as JSON
  missing_keywords: Json; // Array of strings stored as JSON
  resume_id: string;
  created_at: string;
}

/**
 * Typed version of Analysis with parsed JSON fields for UI consumption
 */
export interface AnalysisWithParsedData
  extends Omit<
    Analysis,
    'ai_feedback' | 'matched_keywords' | 'missing_keywords'
  > {
  ai_feedback: AIFeedback;
  matched_keywords: string[];
  missing_keywords: string[];
}

/**
 * AI Feedback structure for analysis results
 */
export interface AIFeedback {
  overall_assessment?: string;
  strengths?: string[];
  priority_improvements?: Array<
    | {
        category?: string;
        priority?: string;
        recommendation?: string;
        impact?: string;
        area?: string;
        suggestion?: string;
      }
    | string
  >;
  ats_optimization_tips?: string[];
  match_score_interpretation?: string;
  missing_keywords_analysis?:
    | string
    | {
        critical_missing?: string[];
        suggestions?: string;
      };
}

/**
 * Analysis insert type for creating new analyses
 */
export interface AnalysisInsert {
  user_id: string;
  job_title: string;
  job_description: string;
  match_score: number;
  ai_feedback?: Json;
  matched_keywords?: Json;
  missing_keywords?: Json;
  resume_id: string;
}

/**
 * Analysis update type for modifying existing analyses
 */
export interface AnalysisUpdate {
  job_title?: string;
  job_description?: string;
  match_score?: number;
  ai_feedback?: Json;
  matched_keywords?: Json;
  missing_keywords?: Json;
}

// =============================================================================
// FORM STATE TYPES
// =============================================================================

/**
 * Dashboard form state interface
 */
export interface DashboardFormState {
  file: File | null;
  jobDescription: string;
  jobRole: string;
  loading: boolean;
}

/**
 * History page state interface
 */
export interface HistoryState {
  analyses: Analysis[];
  loading: boolean;
  deleteModalOpen: boolean;
  selectedAnalysisId: string | null;
}

/**
 * Settings page state interface
 */
export interface SettingsState {
  deleteAccountModalOpen: boolean;
  isDeleting: boolean;
}

// =============================================================================
// MODAL AND CONFIRMATION TYPES
// =============================================================================

/**
 * Confirmation modal step configuration
 */
export interface ConfirmationStep {
  title: string;
  description: string;
  warning?: string;
}

/**
 * Confirmation modal props interface
 */
export interface ConfirmationModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  description: string;
  confirmText?: string;
  cancelText?: string;
  variant?: 'default' | 'destructive';
  loading?: boolean;
  onConfirm: () => void;
  onCancel?: () => void;
  requiresTextConfirmation?: boolean;
  confirmationText?: string;
  multiStep?: boolean;
  steps?: ConfirmationStep[];
}

/**
 * Confirmation modal state interface
 */
export interface ConfirmationModalState {
  currentStep: number;
  textInput: string;
  isTextConfirmed: boolean;
}

// =============================================================================
// API AND OPERATION TYPES
// =============================================================================

/**
 * Analysis API request payload
 */
export interface AnalysisRequest {
  resume_id: string;
  job_description: string;
  job_title: string;
}

/**
 * Analysis API response
 */
export interface AnalysisResponse {
  analysis_id: string;
  match_score: number;
  ai_feedback: AIFeedback;
  matched_keywords: string[];
  missing_keywords: string[];
}

/**
 * File upload response
 */
export interface FileUploadResponse {
  resume_id: string;
  file_name: string;
  message: string;
}

// =============================================================================
// ERROR HANDLING TYPES
// =============================================================================

/**
 * Application error interface
 */
export interface AppError {
  message: string;
  code?: string;
  details?: Record<string, unknown>;
}

/**
 * Supabase operation error
 */
export interface SupabaseError {
  message: string;
  details?: string;
  hint?: string;
  code?: string;
}

/**
 * API error response
 */
export interface APIError {
  detail?: {
    message?: string;
  };
  message?: string;
  status?: number;
}

/**
 * Error handling result type
 */
export type ErrorResult<T> =
  | {
      success: true;
      data: T;
    }
  | {
      success: false;
      error: AppError;
    };

// =============================================================================
// FUNCTION TYPES
// =============================================================================

/**
 * Analysis deletion function type
 */
export type DeleteAnalysisFunction = (analysisId: string) => Promise<void>;

/**
 * Account deletion function type
 */
export type DeleteAccountFunction = () => Promise<void>;

/**
 * Analysis fetch function type
 */
export type FetchAnalysesFunction = () => Promise<Analysis[]>;

/**
 * Analysis creation function type
 */
export type CreateAnalysisFunction = (
  data: AnalysisInsert
) => Promise<Analysis>;

// =============================================================================
// UTILITY TYPES
// =============================================================================

/**
 * Loading states for different operations
 */
export interface LoadingStates {
  analyze: boolean;
  fetchHistory: boolean;
  deleteAnalysis: boolean;
  deleteAccount: boolean;
  fetchAnalysis: boolean;
  [key: string]: boolean;
}

/**
 * Form validation errors
 */
export interface ValidationErrors {
  resume?: string;
  jobDescription?: string;
  jobRole?: string;
  [key: string]: string | undefined;
}

/**
 * Form field touched state
 */
export interface TouchedFields {
  resume: boolean;
  jobDescription: boolean;
  jobRole: boolean;
  [key: string]: boolean;
}

/**
 * Score color mapping type
 */
export type ScoreColorType =
  | 'text-success'
  | 'text-warning'
  | 'text-destructive';

/**
 * Score background color mapping type
 */
export type ScoreBgColorType =
  | 'bg-success-light text-success'
  | 'bg-warning-light text-warning'
  | 'bg-destructive/10 text-destructive';

// =============================================================================
// COMPONENT PROP TYPES
// =============================================================================

/**
 * Analysis card props
 */
export interface AnalysisCardProps {
  analysis: Analysis;
  onDelete: (analysisId: string) => void;
  onNavigate: (analysisId: string) => void;
  isDeleting?: boolean;
}

/**
 * Score display props
 */
export interface ScoreDisplayProps {
  score: number;
  size?: 'small' | 'medium' | 'large';
  showMessage?: boolean;
}

/**
 * Keyword badge props
 */
export interface KeywordBadgeProps {
  keywords: string[];
  type: 'matched' | 'missing';
  maxDisplay?: number;
}

// =============================================================================
// SUPABASE OPERATION TYPES
// =============================================================================

/**
 * Supabase query result type for analyses
 */
export type AnalysisQueryResult = {
  data: Analysis[] | null;
  error: Error | null;
  count?: number;
};

/**
 * Supabase insert result type for analyses
 */
export type AnalysisInsertResult = {
  data: Analysis | null;
  error: Error | null;
};

/**
 * Supabase delete result type
 */
export type AnalysisDeleteResult = {
  data: null;
  error: Error | null;
  count?: number;
};

// =============================================================================
// TYPE GUARDS AND UTILITIES
// =============================================================================

/**
 * Type guard to check if an object is an Analysis
 */
export function isAnalysis(obj: unknown): obj is Analysis {
  return (
    typeof obj === 'object' &&
    obj !== null &&
    'id' in obj &&
    'user_id' in obj &&
    'job_title' in obj &&
    'match_score' in obj
  );
}

/**
 * Type guard to check if an object is an AIFeedback
 */
export function isAIFeedback(obj: unknown): obj is AIFeedback {
  return typeof obj === 'object' && obj !== null;
}

/**
 * Type guard to check if an error is a Supabase error
 */
export function isSupabaseError(error: unknown): error is SupabaseError {
  return (
    typeof error === 'object' &&
    error !== null &&
    'message' in error &&
    typeof (error as any).message === 'string'
  );
}

/**
 * Type guard to check if an error is an API error
 */
export function isAPIError(error: unknown): error is APIError {
  return (
    typeof error === 'object' &&
    error !== null &&
    ('detail' in error || 'message' in error || 'status' in error)
  );
}

// =============================================================================
// CONSTANTS AND ENUMS
// =============================================================================

/**
 * Analysis score thresholds
 */
export const SCORE_THRESHOLDS = {
  EXCELLENT: 80,
  GOOD: 60,
} as const;

/**
 * File validation constants
 */
export const FILE_VALIDATION = {
  MAX_SIZE_MB: 10,
  ALLOWED_TYPES: [
    'application/pdf',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'text/plain',
  ] as readonly string[],
} as const;

/**
 * Form validation constants
 */
export const FORM_VALIDATION = {
  JOB_DESCRIPTION: {
    MIN_LENGTH: 10,
    MAX_LENGTH: 5000,
  },
  JOB_ROLE: {
    MIN_LENGTH: 2,
    MAX_LENGTH: 100,
  },
} as const;

/**
 * Modal confirmation text
 */
export const CONFIRMATION_TEXT = {
  DELETE_ACCOUNT: 'DELETE',
} as const;
