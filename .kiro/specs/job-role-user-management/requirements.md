# Requirements Document

## Introduction

This feature enhances the existing resume analysis application by adding job role tracking capabilities and comprehensive user management features. The implementation will add a mandatory job role field to the analysis workflow, enhance the history page with job role display and deletion capabilities, and expand the settings page with password management and account deletion features. All database interactions will utilize the existing Supabase client setup with proper user authentication and row-level security.

## Requirements

### Requirement 1: Job Role Input on Dashboard

**User Story:** As a user analyzing my resume, I want to specify the job role I'm applying for, so that my analysis results are properly categorized and easily identifiable in my history.

#### Acceptance Criteria

1. WHEN a user visits the Dashboard page THEN the system SHALL display a mandatory "Job Role" text input field alongside the existing resume upload and job description fields
2. WHEN a user attempts to submit an analysis without entering a job role THEN the system SHALL prevent submission and display an appropriate validation message
3. WHEN a user submits a valid analysis with all required fields (resume, job description, and job role) THEN the system SHALL include the job_role value in the Supabase analyses table insert operation
4. WHEN inserting analysis data into Supabase THEN the system SHALL include the currentUserId in the user_id column to ensure proper data ownership and row-level security

### Requirement 2: Enhanced History Page with Job Role Display

**User Story:** As a user reviewing my analysis history, I want to see the job role for each analysis prominently displayed, so that I can quickly identify and navigate to specific analyses.

#### Acceptance Criteria

1. WHEN a user visits the History page THEN the system SHALL fetch all analyses from the Supabase analyses table WHERE user_id matches the currentUserId
2. WHEN displaying analysis items in the history list THEN the system SHALL prominently show the associated job role for each analysis item
3. WHEN the history data is loaded THEN the system SHALL display job roles in a visually prominent manner to enable quick identification of analysis purpose
4. IF no analyses exist for the current user THEN the system SHALL display an appropriate empty state message

### Requirement 3: Analysis Deletion from History Page

**User Story:** As a user managing my analysis history, I want to delete specific analysis records, so that I can remove outdated or unwanted analyses from my account.

#### Acceptance Criteria

1. WHEN viewing the history page THEN the system SHALL display a Delete button or icon next to each analysis item
2. WHEN a user clicks the Delete button THEN the system SHALL display a custom confirmation modal (not window.confirm()) asking for deletion confirmation
3. WHEN a user confirms deletion in the modal THEN the system SHALL execute a Supabase delete() operation targeting the specific analysis ID/primary key
4. WHEN the deletion is successful THEN the system SHALL update the UI to remove the deleted item from the history list
5. WHEN the deletion fails THEN the system SHALL display an appropriate error message to the user

### Requirement 4: Password Management Section in Settings

**User Story:** As a user managing my account settings, I want to see a password change section, so that I understand this functionality exists even though it's handled externally.

#### Acceptance Criteria

1. WHEN a user visits the Settings page THEN the system SHALL display a "Change Password" section with visual fields for "Current Password" and "New Password"
2. WHEN the password section is displayed THEN the system SHALL show a disabled note stating "Password changes are handled by the external authentication provider logic"
3. WHEN displaying the password fields THEN the system SHALL NOT implement actual authentication logic as this is handled externally
4. WHEN the password section is rendered THEN the system SHALL maintain visual consistency with the existing settings page design

### Requirement 5: Permanent Account Deletion

**User Story:** As a user who no longer wants to use the service, I want to permanently delete my account and all associated data, so that my information is completely removed from the system.

#### Acceptance Criteria

1. WHEN a user visits the Settings page THEN the system SHALL display a clearly labeled "Permanently Delete Account" feature available to all users
2. WHEN a user clicks the account deletion option THEN the system SHALL display a custom high-warning confirmation modal explaining the permanent nature of the action
3. WHEN a user confirms account deletion THEN the system SHALL first delete all rows from the analyses table WHERE user_id equals currentUserId
4. WHEN the data deletion is successful THEN the system SHALL trigger the existing external function or mechanism that handles Supabase User/Auth account deletion
5. WHEN the account deletion process completes THEN the system SHALL automatically log out the user and redirect them appropriately
6. IF the data deletion fails THEN the system SHALL display an error message and NOT proceed with account deletion
7. WHEN displaying the deletion confirmation modal THEN the system SHALL use custom modal components (not browser alerts)

### Requirement 6: Database Schema Compliance

**User Story:** As a system administrator, I want all analysis records to include proper job role tracking and user association, so that data integrity and security are maintained.

#### Acceptance Criteria

1. WHEN inserting new analysis records THEN the system SHALL ensure the analyses table includes a user_id column for row-level security
2. WHEN storing analysis results THEN the system SHALL include an analysis_result column as per existing schema
3. WHEN creating new analyses THEN the system SHALL include a mandatory job_role column (string type) in all insert operations
4. WHEN querying analyses THEN the system SHALL filter results by user_id to ensure users only see their own data
5. WHEN performing delete operations THEN the system SHALL target specific analysis IDs while respecting user ownership through user_id filtering
