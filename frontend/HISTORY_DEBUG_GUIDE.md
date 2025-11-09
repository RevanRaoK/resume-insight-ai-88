# History Page Debug Guide

## 🔍 Understanding the "No Endpoint" Issue

The History page **does** have an endpoint - it uses Supabase's auto-generated REST API. Here's what's happening:

### How the History Page Works

1. **Frontend**: `src/pages/History.tsx` calls `supabase.from('analyses').select('*')`
2. **Supabase**: Automatically creates REST endpoint at `https://deeomgotpmynipwwbkuf.supabase.co/rest/v1/analyses`
3. **Authentication**: Uses JWT token from user session
4. **RLS Policy**: Filters results to only show user's own analyses

## 🚨 Debugging Steps

### Step 1: Check Browser Console

1. Open your app at `http://localhost:5174/`
2. Log in with a user account
3. Navigate to History page (`/history`)
4. Open Developer Tools (F12) → Console tab
5. Look for any errors, especially:
   - Authentication errors
   - Network request failures
   - RLS policy errors

### Step 2: Check Network Requests

1. In Developer Tools → Network tab
2. Refresh the History page
3. Look for requests to `/rest/v1/analyses`
4. Check the response:
   - **200 OK + empty array**: RLS working, but no data for user
   - **401/403 Error**: Authentication or RLS issue
   - **No request**: Frontend issue

### Step 3: Verify Database Data

Run this in Supabase SQL Editor to check if analyses exist:

```sql
-- Check if there are any analyses in the database
SELECT COUNT(*) as total_analyses FROM analyses;

-- Check analyses by user (replace with actual user ID)
SELECT user_id, COUNT(*) as user_analyses
FROM analyses
GROUP BY user_id;

-- Check a sample of analyses
SELECT id, user_id, job_title, created_at
FROM analyses
ORDER BY created_at DESC
LIMIT 5;
```

### Step 4: Test RLS Policy

Run this in Supabase SQL Editor:

```sql
-- Check if RLS is enabled
SELECT schemaname, tablename, rowsecurity
FROM pg_tables
WHERE tablename = 'analyses';

-- List RLS policies
SELECT policyname, permissive, roles, cmd, qual
FROM pg_policies
WHERE tablename = 'analyses';
```

### Step 5: Test Authentication

In your browser console (while logged in), run:

```javascript
// Check if user is authenticated
const {
  data: { user },
} = await supabase.auth.getUser();
console.log('Current user:', user);

// Test direct query
const { data, error } = await supabase.from('analyses').select('*').limit(1);
console.log('Query result:', { data, error });
```

## 🔧 Common Issues & Solutions

### Issue 1: "No analyses yet" but user has data

**Cause**: RLS policy blocking access
**Solution**:

```sql
-- Verify the policy exists and is correct
SELECT * FROM pg_policies WHERE tablename = 'analyses';

-- If policy is missing, recreate it:
CREATE POLICY "authenticated_users_select_own_analyses"
  ON public.analyses
  FOR SELECT
  TO authenticated
  USING (auth.uid() = user_id);
```

### Issue 2: Authentication errors

**Cause**: User session expired or invalid
**Solution**:

1. Log out and log back in
2. Check if JWT token is valid
3. Verify Supabase client configuration

### Issue 3: Network request fails

**Cause**: Supabase URL/key incorrect
**Solution**:

1. Verify `.env` file has correct values
2. Check Supabase project settings
3. Ensure project is not paused

### Issue 4: User has no analyses

**Cause**: User genuinely has no analysis data
**Solution**:

1. Create a test analysis through the app
2. Or insert test data via SQL:

```sql
INSERT INTO analyses (user_id, resume_id, job_title, job_description, match_score, ai_feedback, matched_keywords, missing_keywords)
VALUES (
  'your-user-id-here',
  'some-resume-id',
  'Test Job Title',
  'Test job description',
  85,
  '[]'::jsonb,
  '[]'::jsonb,
  '[]'::jsonb
);
```

## 🎯 Quick Test

Run this in your browser console while on the History page:

```javascript
// Quick test to see what's happening
async function quickTest() {
  console.log('=== History Page Debug ===');

  // Check user
  const {
    data: { user },
  } = await supabase.auth.getUser();
  console.log('1. User:', user?.id || 'Not authenticated');

  // Check analyses
  const { data, error } = await supabase
    .from('analyses')
    .select('*')
    .eq('user_id', user?.id);

  console.log('2. Analyses query:', {
    success: !error,
    count: data?.length || 0,
    error: error?.message,
  });

  if (data && data.length > 0) {
    console.log('3. Sample analysis:', data[0]);
  }
}

quickTest();
```

## 📞 Next Steps

After running these tests, you should know:

1. ✅ Is the user authenticated?
2. ✅ Are there analyses in the database?
3. ✅ Is the RLS policy working correctly?
4. ✅ Are network requests succeeding?

Share the results and I can help pinpoint the exact issue!
