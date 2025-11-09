# Critical RLS Policy Fix - Migration Instructions

## 🚨 Issue

Users cannot access their analysis history because the Row Level Security (RLS) policy on the `analyses` table is not working correctly.

## 🔧 Solution

A new migration has been created to fix the RLS policy: `supabase/migrations/20241109000000_fix_analyses_rls_policy.sql`

## ⚡ Quick Fix (Apply Immediately)

### Step 1: Apply the Migration

Copy and paste this SQL into your Supabase SQL Editor:

```sql
-- Fix Supabase Row Level Security policy for analyses table
DROP POLICY IF EXISTS "Users can view their own analyses" ON public.analyses;

CREATE POLICY "authenticated_users_select_own_analyses"
  ON public.analyses
  FOR SELECT
  TO authenticated
  USING (auth.uid() = user_id);

ALTER TABLE public.analyses ENABLE ROW LEVEL SECURITY;
```

### Step 2: Test the Fix

1. Log into your application
2. Go to the History page
3. Verify your analyses load correctly

## 📁 Files Created

- `supabase/migrations/20241109000000_fix_analyses_rls_policy.sql` - The migration file
- `RLS_POLICY_FIX_INSTRUCTIONS.md` - Detailed instructions
- `verify-rls-fix.js` - Verification script
- `test-history-page.md` - Manual testing guide
- `MIGRATION_README.md` - This quick reference

## ✅ Success Criteria

- History page loads user's analyses
- No authentication errors in console
- Users can only see their own analyses
- Analysis detail pages work correctly

## 🆘 Need Help?

Check the detailed instructions in `RLS_POLICY_FIX_INSTRUCTIONS.md` or the testing guide in `test-history-page.md`.
