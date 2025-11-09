// Debug script to identify why History page isn't loading data
// This will help us understand if the issue is with authentication, data, or the RLS policy

import { createClient } from '@supabase/supabase-js';

const SUPABASE_URL = 'https://deeomgotpmynipwwbkuf.supabase.co';
const SUPABASE_ANON_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImRlZW9tZ290cG15bmlwd3dia3VmIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjIyNzU4MzgsImV4cCI6MjA3Nzg1MTgzOH0.F7t0gW5_z6Eit1Gt_6hEm6yadRAskhaiO6tFVzJvjes';

const supabase = createClient(SUPABASE_URL, SUPABASE_ANON_KEY);

async function debugHistoryIssue() {
     console.log('🔍 Debugging History Page Issue...\n');

     try {
          // Step 1: Check if we can connect to Supabase
          console.log('1. Testing Supabase connection...');
          const { data: connectionTest, error: connectionError } = await supabase
               .from('profiles')
               .select('count')
               .limit(1);

          if (connectionError) {
               console.log('❌ Supabase connection failed:', connectionError.message);
               return;
          } else {
               console.log('✅ Supabase connection successful');
          }

          // Step 2: Check current authentication
          console.log('\n2. Checking authentication status...');
          const { data: { user }, error: userError } = await supabase.auth.getUser();

          if (userError) {
               console.log('❌ Error getting user:', userError.message);
          } else if (!user) {
               console.log('⚠️  No authenticated user found');
               console.log('   This script needs to be run with authentication');
               console.log('   Try logging into your app first, then run this script');
          } else {
               console.log('✅ Authenticated user found:', user.id);
               console.log('   Email:', user.email);
          }

          // Step 3: Test analyses table access (unauthenticated)
          console.log('\n3. Testing unauthenticated access to analyses table...');
          const { data: unauthData, error: unauthError } = await supabase
               .from('analyses')
               .select('*')
               .limit(1);

          if (unauthError) {
               console.log('✅ Unauthenticated access blocked:', unauthError.message);
               console.log('   This is expected with RLS enabled');
          } else {
               console.log('⚠️  Unauthenticated access succeeded - potential security issue');
               console.log('   Returned:', unauthData?.length || 0, 'records');
          }

          // Step 4: If authenticated, test authenticated access
          if (user) {
               console.log('\n4. Testing authenticated access to analyses table...');
               const { data: authData, error: authError } = await supabase
                    .from('analyses')
                    .select('*')
                    .eq('user_id', user.id)
                    .order('created_at', { ascending: false });

               if (authError) {
                    console.log('❌ Authenticated access failed:', authError.message);
                    console.log('   Error code:', authError.code);
                    console.log('   This might be the issue preventing History page from working');
               } else {
                    console.log('✅ Authenticated access successful');
                    console.log('   Found', authData?.length || 0, 'analyses for user');

                    if (authData && authData.length > 0) {
                         console.log('   Sample analysis:', {
                              id: authData[0].id,
                              job_title: authData[0].job_title,
                              created_at: authData[0].created_at,
                              user_id: authData[0].user_id
                         });
                    }
               }

               // Step 5: Check if there are any analyses in the database at all
               console.log('\n5. Checking total analyses in database (admin query)...');
               // Note: This might fail due to RLS, which is expected
               const { data: totalData, error: totalError } = await supabase
                    .from('analyses')
                    .select('id, user_id, job_title')
                    .limit(10);

               if (totalError) {
                    console.log('⚠️  Cannot query all analyses (expected with RLS):', totalError.message);
               } else {
                    console.log('   Total analyses visible:', totalData?.length || 0);
               }
          }

          // Step 6: Recommendations
          console.log('\n📋 Debugging Summary:');
          if (!user) {
               console.log('❗ Main Issue: No authenticated user');
               console.log('   Solution: Make sure you\'re logged into the app');
          } else {
               console.log('✅ User is authenticated');
               console.log('   If History page still shows "No analyses yet", possible causes:');
               console.log('   1. User genuinely has no analyses');
               console.log('   2. RLS policy is too restrictive');
               console.log('   3. Frontend authentication state is not synced');
          }

     } catch (error) {
          console.error('❌ Debug script failed:', error);
     }
}

// Instructions for running this script
console.log('🚀 History Page Debug Script');
console.log('To run this script:');
console.log('1. Make sure you\'re logged into your app in the browser');
console.log('2. Run: node debug-history-issue.js');
console.log('3. Check the output for issues\n');

debugHistoryIssue();