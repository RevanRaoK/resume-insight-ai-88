// Test script to verify backend database fix
// Run this after restarting your backend server

(async function testBackendFix() {
     console.log('🔧 TESTING BACKEND DATABASE FIX');

     // Initialize Supabase
     let supabase;
     try {
          const { createClient } = await import('https://cdn.skypack.dev/@supabase/supabase-js');
          supabase = createClient(
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
          console.log('✅ Supabase initialized');
     } catch (e) {
          console.error('❌ Failed to initialize Supabase:', e);
          return;
     }

     const { data: { user } } = await supabase.auth.getUser();
     if (!user) {
          console.error('❌ No authenticated user');
          return;
     }

     console.log('👤 User ID:', user.id);

     // Check current analyses count
     const { data: beforeAnalyses } = await supabase
          .from('analyses')
          .select('id')
          .eq('user_id', user.id);

     console.log('📊 Analyses before test:', beforeAnalyses?.length || 0);

     // Create test analysis through backend
     console.log('\n🧪 Creating test analysis through backend...');

     const { data: { session } } = await supabase.auth.getSession();

     // Upload test resume
     const testContent = `
TEST RESUME FOR DATABASE FIX
Software Engineer
Email: test@example.com

EXPERIENCE:
- 3+ years in web development
- Expert in JavaScript, React, Node.js
- Database design experience

SKILLS:
- Frontend: React, TypeScript, CSS
- Backend: Node.js, Express, FastAPI
- Database: PostgreSQL, MongoDB
- Testing: Jest, Cypress
    `;

     const testFile = new Blob([testContent], { type: 'text/plain' });
     const formData = new FormData();
     formData.append('file', testFile, 'test-resume-fix.txt');

     try {
          // Upload
          const uploadResponse = await fetch('http://localhost:8000/api/v1/upload', {
               method: 'POST',
               headers: {
                    'Authorization': `Bearer ${session.access_token}`
               },
               body: formData
          });

          if (!uploadResponse.ok) {
               throw new Error(`Upload failed: ${uploadResponse.status}`);
          }

          const uploadData = await uploadResponse.json();
          console.log('✅ Resume uploaded:', uploadData.resume_id);

          // Analyze
          const analysisRequest = {
               resume_id: uploadData.resume_id,
               job_description: 'We need a Full Stack Developer with React and Node.js experience. Must have database knowledge and testing skills.',
               job_title: 'Full Stack Developer - Database Fix Test'
          };

          const analysisResponse = await fetch('http://localhost:8000/api/v1/analyze', {
               method: 'POST',
               headers: {
                    'Authorization': `Bearer ${session.access_token}`,
                    'Content-Type': 'application/json'
               },
               body: JSON.stringify(analysisRequest)
          });

          if (!analysisResponse.ok) {
               const errorText = await analysisResponse.text();
               throw new Error(`Analysis failed: ${analysisResponse.status} - ${errorText}`);
          }

          const analysisData = await analysisResponse.json();
          console.log('✅ Analysis created:', analysisData.analysis_id);
          console.log('📊 Match score:', analysisData.match_score);

          // Wait and check Supabase
          console.log('\n⏳ Waiting 3 seconds then checking Supabase...');
          await new Promise(resolve => setTimeout(resolve, 3000));

          const { data: afterAnalyses } = await supabase
               .from('analyses')
               .select('*')
               .eq('user_id', user.id)
               .order('created_at', { ascending: false });

          console.log('📊 Analyses after test:', afterAnalyses?.length || 0);

          if (afterAnalyses && afterAnalyses.length > (beforeAnalyses?.length || 0)) {
               const newAnalysis = afterAnalyses[0];
               console.log('🎉 SUCCESS! Analysis saved to Supabase:');
               console.log(`   - Job Title: ${newAnalysis.job_title}`);
               console.log(`   - Match Score: ${newAnalysis.match_score}%`);
               console.log(`   - ID: ${newAnalysis.id}`);
               console.log(`   - Created: ${newAnalysis.created_at}`);

               if (newAnalysis.id === analysisData.analysis_id) {
                    console.log('✅ PERFECT! Analysis IDs match - fix is working!');
               } else {
                    console.log('⚠️ Analysis IDs don\'t match but analysis was saved');
               }
          } else {
               console.log('❌ STILL BROKEN: Analysis not saved to Supabase');
               console.log('🔧 Check backend logs for errors');
          }

     } catch (error) {
          console.error('❌ Test failed:', error);
     }

     console.log('\n🎯 NEXT STEPS:');
     console.log('1. If test passes: Try creating a real analysis in your app');
     console.log('2. If test fails: Check backend console logs for errors');
     console.log('3. Restart backend server if needed');

})();