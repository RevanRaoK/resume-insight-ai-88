# Testing the History Page RLS Fix

## Manual Testing Steps

### Before Applying the Fix

1. Open the application in your browser
2. Log in with a valid user account
3. Navigate to the History page (`/history`)
4. Open browser Developer Tools (F12)
5. Check the Console tab for errors
6. Check the Network tab for failed requests to `/rest/v1/analyses`

**Expected Issues Before Fix:**

- History page shows "No analyses yet" even if user has analyses
- Console may show authentication or permission errors
- Network requests to analyses endpoint may return 401/403 errors

### After Applying the Fix

#### Step 1: Apply the Migration

1. Go to your Supabase project dashboard
2. Navigate to SQL Editor
3. Execute the SQL from `supabase/migrations/20241109000000_fix_analyses_rls_policy.sql`

#### Step 2: Verify in Supabase Dashboard

1. Go to Authentication > Policies
2. Check that the `analyses` table has the policy "authenticated_users_select_own_analyses"
3. Verify the policy is enabled and has the correct condition: `auth.uid() = user_id`

#### Step 3: Test the Application

1. Refresh the History page in your browser
2. Verify that your analyses now load correctly
3. Check that the analysis cards display with proper data
4. Click on an analysis to ensure the detail view works

#### Step 4: Security Verification

1. Open browser Developer Tools
2. Go to Application/Storage tab
3. Find the Supabase session token
4. Verify in Network tab that requests include proper authentication headers
5. Confirm that only analyses belonging to the authenticated user are returned

### Expected Behavior After Fix

- ✅ History page loads user's analyses correctly
- ✅ Analysis cards show job titles, match scores, and dates
- ✅ No authentication errors in console
- ✅ Network requests to analyses endpoint return 200 status
- ✅ Only user's own analyses are visible
- ✅ Clicking on analyses navigates to detail view

### Troubleshooting

#### If History Page Still Shows "No analyses yet"

1. Check if the user actually has analyses in the database
2. Verify the user_id in analyses table matches the authenticated user's ID
3. Ensure the RLS policy was applied correctly
4. Check browser console for JavaScript errors

#### If Getting Permission Errors

1. Verify RLS is enabled on the analyses table
2. Check that the policy condition uses `auth.uid() = user_id`
3. Ensure the user is properly authenticated
4. Verify the session token is valid

#### If Seeing Other Users' Analyses

1. This indicates a security issue with the RLS policy
2. Re-check the policy condition
3. Ensure the policy is applied to the correct table
4. Verify user_id column contains correct values

### Database Queries for Manual Verification

You can run these in Supabase SQL Editor to verify the fix:

```sql
-- Check if RLS is enabled
SELECT schemaname, tablename, rowsecurity
FROM pg_tables
WHERE tablename = 'analyses';

-- List all policies on analyses table
SELECT schemaname, tablename, policyname, permissive, roles, cmd, qual
FROM pg_policies
WHERE tablename = 'analyses';

-- Test the policy (replace 'your-user-id' with actual user ID)
SELECT id, user_id, job_title, created_at
FROM analyses
WHERE user_id = 'your-user-id';
```

## Files Created for This Fix

- `supabase/migrations/20241109000000_fix_analyses_rls_policy.sql` - Migration to fix RLS policy
- `RLS_POLICY_FIX_INSTRUCTIONS.md` - Detailed instructions for applying the fix
- `verify-rls-fix.js` - Automated verification script
- `test-history-page.md` - Manual testing guide (this file)
