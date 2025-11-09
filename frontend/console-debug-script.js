// Paste this script into your browser console while on the History page
// This will help debug the RLS policy issue

(async function debugHistoryPage() {
     console.log('🔍 Starting History Page Debug...');

     try {
          // Try to access the Supabase client from the React app
          let supabaseClient = null;

          // Method 1: Check if it's available on window
          if (window.supabase) {
               supabaseClient = window.supabase;
               console.log('✅ Found supabase on window object');
          }

          // Method 2: Try to import it dynamically
          if (!supabaseClient) {
               try {
                    const { createClient } = await import('https://cdn.skypack.dev/@supabase/supabase-js');
                    supabaseClient = createClient(
                         'https://deeomgotpmynipwwbkuf.supabase.co',
                         'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImRlZW9tZ290cG15bmlwd3dia3VmIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjIyNzU4MzgsImV4cCI6MjA3Nzg1MTgzOH0.F7t0gW5_z6Eit1Gt_6hEm6yadRAskhaiO6tFVzJvjes',
                         {
                              auth: {
                                   storage: localStorage,
                                   persistSession: true,
                                   autoRefreshToken: true,
                              }
                         }
                    );
                    console.log('✅ Created new supabase client');
               } catch (importError) {
                    console.error('❌ Failed to import Supabase:', importError);
                    return;
               }
          }

          // Make it available globally
          window.debugSupabase = supabaseClient;

          console.log('\n📋 Running diagnostic tests...\n');

          // Test 1: Check authentication
          console.log('1️⃣ Testing authentication...');
          const { data: { user }, error: userError } = await supabaseClient.auth.getUser();

          if (userError) {
               console.error('❌ Auth error:', userError);
               return;
          }

          if (!user) {
               console.warn('⚠️ No authenticated user found. Please log in first.');
               return;
          }

          console.log('✅ User authenticated:', {
               id: user.id,
               email: user.email,
               created_at: user.created_at
          });

          // Test 2: Test the exact query from History page
          console.log('\n2️⃣ Testing History page query...');
          const { data: analyses, error: analysesError } = await supabaseClient
               .from('analyses')
               .select('*')
               .eq('user_id', user.id)
               .order('created_at', { ascending: false });

          if (analysesError) {
               console.error('❌ Analyses query failed:', analysesError);
               console.log('🔧 This is likely the RLS policy issue!');
               console.log('📝 Error details:', {
                    code: analysesError.code,
                    message: analysesError.message,
                    details: analysesError.details,
                    hint: analysesError.hint
               });
          } else {
               console.log('✅ Analyses query successful!');
               console.log('📊 Found analyses:', analyses?.length || 0);
               if (analyses && analyses.length > 0) {
                    console.log('📄 Sample analysis:', analyses[0]);
               }
          }

          // Test 3: Test RLS policy directly
          console.log('\n3️⃣ Testing RLS policy...');
          const { data: allAnalyses, error: rlsError } = await supabaseClient
               .from('analyses')
               .select('id, user_id')
               .limit(5);

          if (rlsError) {
               if (rlsError.code === 'PGRST116' || rlsError.message.includes('row-level security')) {
                    console.log('✅ RLS is working (blocking access as expected)');
               } else {
                    console.error('❌ Unexpected RLS error:', rlsError);
               }
          } else {
               console.log('📊 RLS test returned:', allAnalyses?.length || 0, 'records');
               const userRecords = allAnalyses?.filter(a => a.user_id === user.id) || [];
               const otherRecords = allAnalyses?.filter(a => a.user_id !== user.id) || [];

               console.log('👤 User records:', userRecords.length);
               console.log('👥 Other user records:', otherRecords.length);

               if (otherRecords.length > 0) {
                    console.warn('⚠️ SECURITY ISSUE: Can see other users\' records!');
               }
          }

          // Test 4: Check localStorage for session
          console.log('\n4️⃣ Checking session storage...');
          const sessionKey = `sb-deeomgotpmynipwwbkuf-auth-token`;
          const session = localStorage.getItem(sessionKey);
          if (session) {
               try {
                    const sessionData = JSON.parse(session);
                    console.log('✅ Session found in localStorage');
                    console.log('🔑 Access token present:', !!sessionData.access_token);
                    console.log('⏰ Expires at:', new Date(sessionData.expires_at * 1000).toLocaleString());
               } catch (e) {
                    console.warn('⚠️ Session data corrupted');
               }
          } else {
               console.warn('⚠️ No session found in localStorage');
          }

          console.log('\n🎯 Summary:');
          if (analysesError) {
               console.log('❌ The History page issue is confirmed');
               console.log('🔧 Apply the RLS policy migration to fix it');
               console.log('📋 Migration SQL:');
               console.log(`
DROP POLICY IF EXISTS "Users can view their own analyses" ON public.analyses;

CREATE POLICY "authenticated_users_select_own_analyses"
  ON public.analyses
  FOR SELECT
  TO authenticated
  USING (auth.uid() = user_id);

ALTER TABLE public.analyses ENABLE ROW LEVEL SECURITY;
            `);
          } else {
               console.log('✅ History page query is working correctly');
               console.log('🤔 The issue might be elsewhere in the React app');
          }

          console.log('\n💡 You can now use window.debugSupabase to run more tests');

     } catch (error) {
          console.error('❌ Debug script failed:', error);
     }
})();

// Helper functions for manual testing
window.testAnalysesQuery = async function () {
     if (!window.debugSupabase) {
          console.error('❌ Run the main debug script first');
          return;
     }

     const { data: { user } } = await window.debugSupabase.auth.getUser();
     if (!user) {
          console.error('❌ No authenticated user');
          return;
     }

     const { data, error } = await window.debugSupabase
          .from('analyses')
          .select('*')
          .eq('user_id', user.id);

     console.log('Query result:', { data, error });
     return { data, error };
};

window.testRawQuery = async function () {
     if (!window.debugSupabase) {
          console.error('❌ Run the main debug script first');
          return;
     }

     const { data, error } = await window.debugSupabase
          .from('analyses')
          .select('*')
          .limit(1);

     console.log('Raw query result:', { data, error });
     return { data, error };
};

console.log('🚀 Debug script loaded! Functions available:');
console.log('- testAnalysesQuery() - Test the History page query');
console.log('- testRawQuery() - Test raw access to analyses table');