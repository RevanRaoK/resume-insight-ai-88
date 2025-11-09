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

-- Verify the policy is working by testing with a sample query
-- This comment serves as documentation for manual testing:
-- SELECT * FROM public.analyses WHERE user_id = auth.uid();