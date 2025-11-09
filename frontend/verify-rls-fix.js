// Verification script for RLS policy fix
// Run this after applying the migration to verify the fix works

import { createClient } from '@supabase/supabase-js';

// You'll need to set these environment variables or replace with actual values
const SUPABASE_URL = 'https://deeomgotpmynipwwbkuf.supabase.co';
const SUPABASE_ANON_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImRlZW9tZ290cG15bmlwd3dia3VmIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjIyNzU4MzgsImV4cCI6MjA3Nzg1MTgzOH0.F7t0gW5_z6Eit1Gt_6hEm6yadRAskhaiO6tFVzJvjes';

const supabase = createClient(SUPABASE_URL, SUPABASE_ANON_KEY);

async function verifyRLSFix() {
     console.log('🔍 Verifying RLS Policy Fix for analyses table...\n');

     try {
          // Test 1: Check if RLS is enabled and policies exist
          console.log('1. Testing unauthenticated access (should be blocked)...');
          const { data: unauthData, error: unauthError } = await supabase
               .from('analyses')
               .select('id, user_id, job_title')
               .limit(1);

          if (unauthError) {
               if (unauthError.code === 'PGRST116' || unauthError.message.includes('row-level security')) {
                    console.log('✅ Unauthenticated access properly blocked by RLS');
               } else {
                    console.log('⚠️  Unexpected error:', unauthError.message);
               }
          } else if (!unauthData || unauthData.length === 0) {
               console.log('✅ Unauthenticated access returns no data (RLS working)');
          } else {
               console.log('❌ Unauthenticated access returned data - RLS may not be working properly');
          }

          // Test 2: Check current authentication state
          console.log('\n2. Checking authentication state...');
          const { data: { user }, error: userError } = await supabase.auth.getUser();

          if (userError) {
               console.log('⚠️  Error getting user:', userError.message);
          } else if (!user) {
               console.log('ℹ️  No authenticated user (this is expected for this test script)');
               console.log('   To fully test, you would need to authenticate first');
          } else {
               console.log('✅ Authenticated user found:', user.id);

               // Test 3: Try authenticated access
               console.log('\n3. Testing authenticated access...');
               const { data: authData, error: authError } = await supabase
                    .from('analyses')
                    .select('id, user_id, job_title, created_at')
                    .order('created_at', { ascending: false });

               if (authError) {
                    console.log('❌ Authenticated access failed:', authError.message);
               } else {
                    console.log('✅ Authenticated access successful');
                    console.log(`   Found ${authData?.length || 0} analyses for user ${user.id}`);

                    // Verify all returned analyses belong to the authenticated user
                    const invalidAnalyses = authData?.filter(analysis => analysis.user_id !== user.id) || [];
                    if (invalidAnalyses.length > 0) {
                         console.log('❌ Security issue: Found analyses that don\'t belong to the authenticated user');
                         console.log('   Invalid analyses:', invalidAnalyses.map(a => a.id));
                    } else {
                         console.log('✅ Security verified: All analyses belong to the authenticated user');
                    }
               }
          }

          console.log('\n📋 Summary:');
          console.log('- RLS Policy should block unauthenticated access');
          console.log('- Authenticated users should only see their own analyses');
          console.log('- The History page should now work correctly');

          console.log('\n🔧 Next Steps:');
          console.log('1. Test the History page in your application');
          console.log('2. Verify that analysis data loads correctly');
          console.log('3. Check that users can only see their own data');

     } catch (error) {
          console.error('❌ Verification failed with error:', error);
     }
}

// Run the verification
verifyRLSFix();