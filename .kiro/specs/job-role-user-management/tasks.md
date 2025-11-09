# Implementation Plan

- [x] 1. Create reusable confirmation modal component

  - Implement a custom ConfirmationModal component using shadcn/ui Dialog
  - Include props for title, description, confirm text, cancel text, and variant (default/destructive)
  - Add loading state support for async operations
  - Style with appropriate warning colors for destructive actions
  - _Requirements: 3.2, 5.2, 5.7_

- [x] 2. Enhance Dashboard page with job role input

  - Add jobRole state variable to Dashboard component
  - Create job role input field using existing Input component and Label
  - Position job role field prominently in the form layout
  - Update form validation to require job role input
  - Modify validation error messages to include job role requirement
  - _Requirements: 1.1, 1.2_

- [x] 3. Update Dashboard submission logic for job role

  - Modify handleAnalyze function to include job role validation
  - Update the analysis API request to include job_title field with jobRole value
  - Ensure user_id is properly included in the analysis workflow
  - Add proper error handling for job role validation
  - _Requirements: 1.3, 1.4_

- [x] 4. Enhance History page data fetching with Supabase

  - Replace existing FastAPI history fetching with direct Supabase queries
  - Implement fetchAnalyses function using supabase.from('analyses').select()
  - Add proper user_id filtering using currentUserId from auth context
  - Update Analysis interface to include all necessary fields from Supabase schema
  - Add error handling for Supabase operations
  - _Requirements: 2.1, 2.4_

- [x] 5. Update History page UI to display job roles prominently

  - Modify analysis card layout to prominently display job_title as job role
  - Update the existing Target icon and job title display
  - Ensure job role is visually prominent for quick identification
  - Maintain existing card styling and hover effects
  - _Requirements: 2.2, 2.3_

- [x] 6. Implement analysis deletion functionality in History page

  - Add delete button/icon to each analysis card using Trash icon from Lucide React
  - Create state management for delete modal (deleteModalOpen, selectedAnalysisId)
  - Implement deleteAnalysis function using Supabase delete operation
  - Add proper user_id filtering in delete operation for security
  - Update UI to remove deleted items from the list
  - _Requirements: 3.1, 3.3, 3.4, 3.5_

- [x] 7. Integrate confirmation modal with History page deletion

  - Import and use the ConfirmationModal component in History page
  - Configure modal with appropriate warning text for analysis deletion
  - Handle modal open/close state management
  - Connect modal confirmation to deleteAnalysis function
  - Add loading state during deletion process
  - _Requirements: 3.2, 3.3_

- [x] 8. Create password management section in Settings page

  - Add new section titled "Change Password" to Settings page
  - Create disabled input fields for "Current Password" and "New Password"
  - Add explanatory text: "Password changes are handled by the external authentication provider logic"
  - Style section consistently with existing settings page design
  - Use existing Input and Label components
  - _Requirements: 4.1, 4.2, 4.3, 4.4_

- [x] 9. Implement account deletion functionality in Settings page

  - Add "Permanently Delete Account" section to Settings page
  - Create state management for account deletion modal and loading state
  - Implement deleteAccount function with two-step process (data deletion, then auth deletion)
  - Add Supabase operation to delete all user analyses
  - Integrate with existing signOut function for auth account deletion
  - _Requirements: 5.1, 5.3, 5.4, 5.5_

- [x] 10. Create high-warning confirmation modal for account deletion

  - Configure ConfirmationModal with destructive variant for account deletion
  - Add multiple confirmation steps and clear warning about permanent data loss
  - Include loading state during account deletion process
  - Handle error scenarios with appropriate user feedback
  - Ensure modal prevents accidental deletion through clear messaging
  - _Requirements: 5.2, 5.6, 5.7_

- [x] 11. Add comprehensive error handling and user feedback

  - Implement toast notifications for all Supabase operations (success/error)
  - Add proper error boundaries for component error handling
  - Create loading states for all async operations
  - Add validation feedback for form inputs
  - Ensure consistent error messaging across all components
  - _Requirements: 3.5, 5.6_

- [x] 12. Update TypeScript interfaces and types

  - Update Analysis interface to match Supabase schema
  - Add proper typing for new state variables and functions
  - Create type definitions for modal props and confirmation states
  - Ensure type safety for all Supabase operations
  - Add proper error type handling
  - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5_
