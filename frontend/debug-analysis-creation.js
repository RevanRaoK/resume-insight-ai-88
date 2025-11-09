// URGENT: Debug why analyses aren't being saved to database
// Paste this into console to check what's happening during analysis creation

(async function debugAnalysisCreation() {
     console.log('🚨 URGENT: Debugging Analysis Creation Issue');
     console.log('User ID:', '3d44314c-45b6-4abf-9623-f1e6baac10b4');

     const supabase = window.debugSupabase;
     if (!supabase) {
          console.error('❌ Run the previous debug script first!');
          return;
     }

     // Check all tables for this user
     console.log('\n🔍 Checking all user data...');

     // 1. Check profiles table
     console.log('1️⃣ Checking profiles...');
     const { data: profiles, error: profileError } = await supabase
          .from('profiles')
          .select('*')
          .eq('id', '3d44314c-45b6-4abf-9623-f1e6baac10b4');

     if (profileError) {
          console.error('❌ Profile error:', profileError);
     } else {
          console.log('✅ Profile found:', profiles);
     }

     // 2. Check resumes table
     console.log('\n2️⃣ Checking resumes...');
     const { data: resumes, error: resumeError } = await supabase
          .from('resumes')
          .select('*')
          .eq('user_id', '3d44314c-45b6-4abf-9623-f1e6baac10b4');

     if (resumeError) {
          console.error('❌ Resume error:', resumeError);
     } else {
          console.log('✅ Resumes found:', resumes?.length || 0);
          if (resumes && resumes.length > 0) {
               console.log('📄 Resume details:', resumes);
          }
     }

     // 3. Check ALL analyses (bypass RLS temporarily for debugging)
     console.log('\n3️⃣ Checking ALL analyses in database...');
     const { data: allAnalyses, error: allError } = await supabase
          .from('analyses')
          .select('id, user_id, job_title, created_at')
          .order('created_at', { ascending: false })
          .limit(10);

     if (allError) {
          console.error('❌ All analyses error:', allError);
     } else {
          console.log('📊 Total analyses in DB:', allAnalyses?.length || 0);
          if (allAnalyses && allAnalyses.length > 0) {
               console.log('📋 Recent analyses:', allAnalyses);

               // Check if any belong to our user
               const userAnalyses = allAnalyses.filter(a => a.user_id === '3d44314c-45b6-4abf-9623-f1e6baac10b4');
               console.log('👤 User analyses found:', userAnalyses.length);

               if (userAnalyses.length === 0) {
                    console.log('🔍 Other user IDs in database:');
                    const otherUsers = [...new Set(allAnalyses.map(a => a.user_id))];
                    otherUsers.forEach(uid => {
                         const count = allAnalyses.filter(a => a.user_id === uid).length;
                         console.log(`   ${uid}: ${count} analyses`);
                    });
               }
          }
     }

     // 4. Test creating a new analysis
     console.log('\n4️⃣ Testing analysis creation...');

     if (!resumes || resumes.length === 0) {
          console.warn('⚠️ No resumes found - cannot test analysis creation');
          console.log('💡 You need to upload a resume first before creating analyses');
     } else {
          console.log('🧪 Attempting to create test analysis...');

          const testAnalysis = {
               user_id: '3d44314c-45b6-4abf-9623-f1e6baac10b4',
               resume_id: resumes[0].id,
               job_title: 'DEBUG TEST JOB',
               job_description: 'This is a test job description for debugging',
               match_score: 85,
               ai_feedback: [{ type: 'test', message: 'Debug test feedback' }],
               matched_keywords: ['test', 'debug'],
               missing_keywords: ['production']
          };

          const { data: newAnalysis, error: createError } = await supabase
               .from('analyses')
               .insert([testAnalysis])
               .select();

          if (createError) {
               console.error('❌ Failed to create test analysis:', createError);
               console.log('🔧 Error details:', {
                    code: createError.code,
                    message: createError.message,
                    details: createError.details,
                    hint: createError.hint
               });
          } else {
               console.log('✅ Test analysis created successfully!', newAnalysis);

               // Now try to fetch it back
               const { data: fetchedAnalysis, error: fetchError } = await supabase
                    .from('analyses')
                    .select('*')
                    .eq('id', newAnalysis[0].id);

               if (fetchError) {
                    console.error('❌ Cannot fetch back the analysis:', fetchError);
               } else {
                    console.log('✅ Can fetch back the analysis:', fetchedAnalysis);
               }
          }
     }

     console.log('\n🎯 DIAGNOSIS:');
     if (resumes && resumes.length === 0) {
          console.log('❌ ROOT CAUSE: No resumes uploaded!');
          console.log('🔧 SOLUTION: Upload a resume first, then create analyses');
     } else if (allAnalyses && allAnalyses.length === 0) {
          console.log('❌ ROOT CAUSE: No analyses exist in the entire database!');
          console.log('🔧 SOLUTION: Check the analysis creation process in your app');
     } else {
          console.log('❌ ROOT CAUSE: Analyses exist but not for your user ID');
          console.log('🔧 SOLUTION: Check user ID consistency in analysis creation');
     }

})();

// Helper function to check the analysis creation endpoint
window.checkAnalysisEndpoint = async function () {
     console.log('🔍 Checking analysis creation endpoint...');

     // Check if there's a function or API endpoint being used
     const { data: functions, error } = await window.debugSupabase.functions.invoke('analyze-resume', {
          body: { test: true }
     });

     console.log('Function test result:', { functions, error });
};

console.log('🚨 Analysis creation debug loaded!');
console.log('💡 Run checkAnalysisEndpoint() to test the analysis function');