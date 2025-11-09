# RLS Policy Fix Instructions

## Problem

Users cannot access their analysis history due to a faulty Row Level Security (RLS) policy on the `analyses` table in Supabase.

## Solution

The migration file `supabase/migrations/20241109000000_fix_analyses_rls_policy.sql` has been created to fix this issue.

## How to Apply the Fix

### Option 1: Using Supabase Dashboard (Recommended)

1. Go to your Supabase project dashboard
2. Navigate to the SQL Editor
3. Copy and paste the following SQL commands:

```sql
-- Fix Supabase Row Level Security policy for analyses table
-- This migration addresses the issue where users cannot access their analysis history

-- Drop existing SELECT policy if it exists
DROP POLICY IF EXISTS "Users can view their own analyses" ON public.analyses;

-- Create new explicit SELECT policy with proper authentication
CREATE POLICY "authenticated_users_select_own_analyses"
  ON public.analyses
  FOR SELECT
  TO authenticated
  USING (auth.uid() = user_id);

-- Ensure RLS is enabled on the analyses table
ALTER TABLE public.analyses ENABLE ROW LEVEL SECURITY;
```

4. Execute the SQL commands
5. Verify the policy is active by checking the "Authentication" > "Policies" section

### Option 2: Using Supabase CLI (If Available)

1. Install Supabase CLI: `npm install -g supabase`
2. Login to Supabase: `supabase login`
3. Link your project: `supabase link --project-ref deeomgotpmynipwwbkuf`
4. Push the migration: `supabase db push`

## Verification Steps

### 1. Check Policy in Supabase Dashboard

- Go to Authentication > Policies
- Verify that the `analyses` table has the policy "authenticated_users_select_own_analyses"
- Ensure the policy is enabled

### 2. Test in Application

- Log in to the application
- Navigate to the History page
- Verify that your analysis history loads correctly
- Check browser console for any errors

### 3. Security Test

- Ensure users can only see their own analyses
- Verify that unauthenticated users cannot access any analyses

## Expected Behavior After Fix

- Authenticated users should be able to view their own analyses in the History page
- Users should not be able to access other users' analyses
- The History page should load without errors
- Analysis data should be properly filtered by user_id

## Troubleshooting

If the fix doesn't work:

1. Check that RLS is enabled on the analyses table
2. Verify the policy name and conditions are correct
3. Ensure the user is properly authenticated
4. Check browser console for authentication errors
5. Verify the user_id column exists and is properly populated

## Files Modified

- `supabase/migrations/20241109000000_fix_analyses_rls_policy.sql` (created)
- `RLS_POLICY_FIX_INSTRUCTIONS.md` (created)
