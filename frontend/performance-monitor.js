// Performance monitoring script for analysis requests
// Paste this to monitor analysis performance in real-time

(async function monitorPerformance() {
     console.log('🚀 PERFORMANCE MONITOR ACTIVE');

     // Initialize Supabase
     const { createClient } = await import('https://cdn.skypack.dev/@supabase/supabase-js');
     const supabase = createClient(
          'https://deeomgotpmynipwwbkuf.supabase.co',
          'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImRlZW9tZ290cG15bmlwd3dia3VmIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjIyNzU4MzgsImV4cCI6MjA3Nzg1MTgzOH0.F7t0gW5_z6Eit1Gt_6hEm6yadRAskhaiO6tFVzJvjes',
          { auth: { storage: localStorage, persistSession: true, autoRefreshToken: true } }
     );

     const { data: { user } } = await supabase.auth.getUser();
     const { data: { session } } = await supabase.auth.getSession();

     if (!user || !session) {
          console.error('❌ Not authenticated');
          return;
     }

     console.log('👤 User:', user.id);

     // Test with a shorter job description for performance
     const shortJobDescription = `
Data Analyst Position

Requirements:
- Bachelor's degree in Data Science, Statistics, or related field
- 2+ years experience with Python, R, or SQL
- Experience with data visualization tools (Tableau, Power BI)
- Strong analytical and problem-solving skills
- Knowledge of statistical analysis and machine learning
- Excellent communication skills

Responsibilities:
- Analyze large datasets to identify trends and insights
- Create reports and dashboards for stakeholders
- Collaborate with cross-functional teams
- Develop predictive models and algorithms
- Present findings to management

We offer competitive salary, benefits, and growth opportunities.
    `.trim();

     console.log('📊 Job description length:', shortJobDescription.length, 'characters');

     // Create test resume
     const testContent = `
JOHN DOE
Data Analyst
Email: john@example.com

EXPERIENCE:
- 3+ years in data analysis and visualization
- Expert in Python, SQL, and Tableau
- Machine learning and statistical modeling
- Cross-functional team collaboration

SKILLS:
- Programming: Python, R, SQL
- Visualization: Tableau, Power BI, matplotlib
- Statistics: regression, hypothesis testing
- Machine Learning: scikit-learn, pandas
- Communication: presentations, reporting

EDUCATION:
- Bachelor's in Statistics
- Data Science Certification
    `;

     const testFile = new Blob([testContent], { type: 'text/plain' });
     const formData = new FormData();
     formData.append('file', testFile, 'performance-test-resume.txt');

     console.log('\n⏱️ Starting performance test...');
     const startTime = Date.now();

     try {
          // Upload resume
          console.log('📤 Uploading resume...');
          const uploadStart = Date.now();

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
          const uploadTime = Date.now() - uploadStart;
          console.log(`✅ Upload completed in ${uploadTime}ms`);

          // Analyze with optimized job description
          console.log('🧠 Starting analysis...');
          const analysisStart = Date.now();

          const analysisRequest = {
               resume_id: uploadData.resume_id,
               job_description: shortJobDescription,
               job_title: 'Data Analyst - Performance Test'
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
          const analysisTime = Date.now() - analysisStart;
          const totalTime = Date.now() - startTime;

          console.log(`✅ Analysis completed in ${analysisTime}ms`);
          console.log(`🎯 Total time: ${totalTime}ms`);
          console.log(`📊 Match score: ${analysisData.match_score}%`);
          console.log(`🆔 Analysis ID: ${analysisData.analysis_id}`);

          // Performance benchmarks
          console.log('\n📈 PERFORMANCE RESULTS:');
          console.log(`Upload: ${uploadTime}ms ${uploadTime < 3000 ? '✅' : '⚠️'}`);
          console.log(`Analysis: ${analysisTime}ms ${analysisTime < 30000 ? '✅' : '⚠️'}`);
          console.log(`Total: ${totalTime}ms ${totalTime < 35000 ? '✅' : '⚠️'}`);

          if (totalTime < 35000) {
               console.log('🎉 EXCELLENT PERFORMANCE!');
          } else if (totalTime < 60000) {
               console.log('⚠️ ACCEPTABLE PERFORMANCE');
          } else {
               console.log('❌ PERFORMANCE NEEDS IMPROVEMENT');
          }

     } catch (error) {
          const totalTime = Date.now() - startTime;
          console.error(`❌ Performance test failed after ${totalTime}ms:`, error);
     }

})();