# Design Document

## Overview

This design document outlines the implementation of job role tracking and enhanced user management features for the resume analysis application. The solution leverages the existing Supabase infrastructure, React/TypeScript frontend, and shadcn/ui component library to provide a seamless user experience while maintaining data integrity and security.

The implementation focuses on three main areas: enhancing the Dashboard with job role input, upgrading the History page with job role display and deletion capabilities, and expanding the Settings page with password management UI and account deletion functionality.

## Architecture

### Database Layer

The existing Supabase `analyses` table will be utilized with a schema clarification. The current table includes:

- `user_id`: string (for row-level security)
- `job_title`: string (existing field that will serve as job_role)
- `analysis_result`: stored in `ai_feedback` field as JSON
- Other existing fields: `id`, `created_at`, `job_description`, `match_score`, etc.

**Schema Mapping Decision**: The existing `job_title` field in the analyses table will be used to store the job role information, maintaining backward compatibility while fulfilling the requirement for job role tracking.

### Frontend Architecture

The solution follows the existing React/TypeScript architecture with:

- Component-based UI using shadcn/ui library
- Supabase client for database operations
- AuthContext for user authentication state
- React Router for navigation
- Custom hooks for data fetching and state management

### Security Model

- Row-level security through user_id filtering
- Authentication state management via existing AuthContext
- Proper error handling and user feedback
- Confirmation modals for destructive actions

## Components and Interfaces

### 1. Enhanced Dashboard Component

**New State Variables:**

```typescript
const [jobRole, setJobRole] = useState<string>('');
```

**Modified Form Validation:**

```typescript
const validateForm = () => {
  return file && jobDescription.trim() && jobRole.trim();
};
```

**Updated Supabase Integration:**
The existing backend API integration will be maintained, but we need to ensure the job role is passed through the analysis workflow. The current flow goes through FastAPI backend, so the job role will be included in the analysis request.

**UI Components:**

- New Input field for job role using existing `Input` component
- Enhanced form validation messaging
- Consistent styling with existing form elements

### 2. Enhanced History Component

**Updated Data Interface:**

```typescript
interface Analysis {
  id: string;
  job_title: string; // This serves as job_role
  match_score: number;
  created_at: string;
  job_description: string;
  user_id: string;
}
```

**New State Management:**

```typescript
const [deleteModalOpen, setDeleteModalOpen] = useState(false);
const [selectedAnalysisId, setSelectedAnalysisId] = useState<string | null>(
  null
);
```

**Supabase Operations:**

```typescript
// Fetch user's analyses
const fetchAnalyses = async () => {
  const { data, error } = await supabase
    .from('analyses')
    .select('*')
    .eq('user_id', user?.id)
    .order('created_at', { ascending: false });
};

// Delete analysis
const deleteAnalysis = async (analysisId: string) => {
  const { error } = await supabase
    .from('analyses')
    .delete()
    .eq('id', analysisId)
    .eq('user_id', user?.id); // Additional security check
};
```

**UI Components:**

- Enhanced analysis cards with prominent job role display
- Delete button with trash icon using Lucide React
- Custom confirmation modal using shadcn/ui Dialog component
- Loading states and error handling

### 3. Enhanced Settings Component

**New State Variables:**

```typescript
const [deleteAccountModalOpen, setDeleteAccountModalOpen] = useState(false);
const [isDeleting, setIsDeleting] = useState(false);
```

**Account Deletion Flow:**

```typescript
const deleteAccount = async () => {
  try {
    setIsDeleting(true);

    // Step 1: Delete all user analyses
    const { error: analysesError } = await supabase
      .from('analyses')
      .delete()
      .eq('user_id', user?.id);

    if (analysesError) throw analysesError;

    // Step 2: Trigger auth account deletion (existing mechanism)
    // This will be handled by the existing signOut function
    // which should include account deletion logic
    await signOut();
  } catch (error) {
    // Handle error appropriately
  } finally {
    setIsDeleting(false);
  }
};
```

**UI Components:**

- Password management section with disabled inputs and explanatory text
- Account deletion section with high-warning styling
- Custom confirmation modal with multiple confirmation steps
- Loading states during deletion process

## Data Models

### Analysis Data Model

```typescript
interface AnalysisData {
  id: string;
  user_id: string;
  job_title: string; // Serves as job_role
  job_description: string;
  match_score: number;
  ai_feedback: Json;
  matched_keywords: Json;
  missing_keywords: Json;
  resume_id: string;
  created_at: string;
}
```

### Form State Models

```typescript
interface DashboardFormState {
  file: File | null;
  jobDescription: string;
  jobRole: string;
  loading: boolean;
}

interface HistoryState {
  analyses: AnalysisData[];
  loading: boolean;
  deleteModalOpen: boolean;
  selectedAnalysisId: string | null;
}

interface SettingsState {
  deleteAccountModalOpen: boolean;
  isDeleting: boolean;
}
```

## Error Handling

### Database Operation Errors

- Supabase errors will be caught and displayed using the existing toast system
- Network errors will show appropriate retry mechanisms
- Authentication errors will redirect to login

### Form Validation Errors

- Real-time validation feedback for required fields
- Clear error messages for file upload constraints
- Consistent error styling using existing design system

### Deletion Confirmation Flow

- Multi-step confirmation for account deletion
- Clear warning messages about data permanence
- Graceful error recovery with user feedback

## Testing Strategy

### Unit Testing

- Component rendering tests for new UI elements
- Form validation logic testing
- State management testing for new features
- Mock Supabase operations for isolated testing

### Integration Testing

- End-to-end form submission flow
- Database operation testing with test data
- Authentication flow testing
- Modal interaction testing

### User Acceptance Testing

- Job role input and display workflow
- Analysis deletion workflow
- Account deletion workflow
- Error handling scenarios

## Implementation Considerations

### Database Schema Compatibility

The existing `job_title` field in the analyses table will be repurposed to store job role information. This maintains backward compatibility while fulfilling the new requirements.

### API Integration

The current FastAPI backend integration will need to be updated to handle the job role parameter in analysis requests. The frontend will pass the job role through the existing API endpoints.

### Modal Component Strategy

Custom confirmation modals will be implemented using the shadcn/ui Dialog component to provide consistent styling and behavior across the application.

### State Management

Local component state will be used for form management and modal states, while Supabase operations will handle data persistence and retrieval.

### Security Considerations

- All database operations will include user_id filtering
- Deletion operations will include additional security checks
- Error messages will not expose sensitive information
- Account deletion will follow a secure two-step process

### Performance Optimization

- Efficient data fetching with proper loading states
- Optimistic UI updates for better user experience
- Proper cleanup of event listeners and subscriptions
- Minimal re-renders through proper state management

## Migration Strategy

### Phase 1: Dashboard Enhancement

- Add job role input field
- Update form validation
- Modify submission logic to include job role

### Phase 2: History Page Enhancement

- Update data fetching to include job role display
- Implement deletion functionality with confirmation modal
- Enhance UI to prominently display job roles

### Phase 3: Settings Page Enhancement

- Add password management UI section
- Implement account deletion functionality
- Add comprehensive confirmation flow

### Phase 4: Testing and Refinement

- Comprehensive testing of all new features
- User feedback integration
- Performance optimization
- Documentation updates
