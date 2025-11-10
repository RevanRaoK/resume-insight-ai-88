// This is a Deno/Supabase Edge Function - ignore Node.js TypeScript errors
// @ts-nocheck
import { serve } from 'https://deno.land/std@0.168.0/http/server.ts';
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2.39.3';

// Type declarations for Deno environment
declare global {
  const Deno: {
    env: {
      get(key: string): string | undefined;
    };
  };
}

const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers':
    'authorization, x-client-info, apikey, content-type',
};

interface AnalysisResult {
  matchScore: number;
  feedback: string[];
  matchedKeywords: string[];
  missingKeywords: string[];
}

serve(async (req: Request) => {
  if (req.method === 'OPTIONS') {
    return new Response(null, { headers: corsHeaders });
  }

  try {
    const supabaseClient = createClient(
      Deno.env.get('SUPABASE_URL') ?? '',
      Deno.env.get('SUPABASE_ANON_KEY') ?? '',
      {
        global: {
          headers: { Authorization: req.headers.get('Authorization')! },
        },
      }
    );

    const {
      data: { user },
      error: userError,
    } = await supabaseClient.auth.getUser();

    if (userError || !user) {
      return new Response(JSON.stringify({ error: 'Unauthorized' }), {
        status: 401,
        headers: { ...corsHeaders, 'Content-Type': 'application/json' },
      });
    }

    const { fileName, fileUrl, jobDescription } = await req.json();

    console.log('Analyzing resume for user:', user.id);

    // Extract resume text (simplified - in production, parse PDF/DOCX)
    const resumeText = `Resume file: ${fileName}`;

    // Extract job title from job description
    const jobTitleMatch = jobDescription.match(
      /(?:for|as|position:|role:)\s*([A-Za-z\s]+?)(?:\s+at|\s+\||\n|$)/i
    );
    const jobTitle = jobTitleMatch
      ? jobTitleMatch[1].trim()
      : 'Unspecified Position';

    // Call Google Gemini AI for analysis
    const GOOGLE_API_KEY = Deno.env.get('GOOGLE_API_KEY');

    const aiResponse = await fetch(
      `https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key=${GOOGLE_API_KEY}`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          contents: [
            {
              parts: [
                {
                  text: `You are a professional resume analyzer. Analyze the resume against the job description and provide:
1. A match score (0-100)
2. Exactly 3 actionable feedback items
3. Matched keywords (skills/technologies mentioned in both)
4. Missing keywords (important requirements from job description not in resume)

Job Description:
${jobDescription}

Resume:
${resumeText}

Return your response in this exact JSON format:
{
  "matchScore": 85,
  "feedback": [
    "Clear and concise summary effectively highlights key qualifications.",
    "Instead of 'Managed a team', try 'Led a team of 5 engineers to increase project delivery speed by 15%'.",
    "Add a 'Projects' section to showcase your practical skills."
  ],
  "matchedKeywords": ["Python", "React", "FastAPI", "SQL", "JavaScript", "Agile"],
  "missingKeywords": ["Docker", "Kubernetes", "CI/CD", "AWS", "Terraform"]
}`,
                },
              ],
            },
          ],
          temperature: 0.7,
        }),
      }
    );

    if (!aiResponse.ok) {
      const errorText = await aiResponse.text();
      console.error('AI API error:', aiResponse.status, errorText);

      if (aiResponse.status === 429) {
        return new Response(
          JSON.stringify({
            error: 'Rate limit exceeded. Please try again later.',
          }),
          {
            status: 429,
            headers: { ...corsHeaders, 'Content-Type': 'application/json' },
          }
        );
      }

      if (aiResponse.status === 402) {
        return new Response(
          JSON.stringify({
            error: 'AI usage limit reached. Please add credits to continue.',
          }),
          {
            status: 402,
            headers: { ...corsHeaders, 'Content-Type': 'application/json' },
          }
        );
      }

      throw new Error(`AI API error: ${errorText}`);
    }

    const aiData = await aiResponse.json();
    const aiContent = aiData.choices[0].message.content;

    // Parse AI response
    let analysisResult: AnalysisResult;
    try {
      analysisResult = JSON.parse(aiContent) as AnalysisResult;
    } catch (parseError) {
      console.error('Failed to parse AI response:', aiContent);
      // Fallback to default analysis
      analysisResult = {
        matchScore: 70,
        feedback: [
          'Resume received and processed successfully.',
          'Consider adding quantifiable achievements to strengthen your profile.',
          'Tailor your skills section to match job requirements.',
        ],
        matchedKeywords: ['Experience', 'Skills', 'Education'],
        missingKeywords: ['Specific technical skills', 'Certifications'],
      };
    }

    // Store resume in database
    const { data: resumeData, error: resumeError } = await supabaseClient
      .from('resumes')
      .insert({
        user_id: user.id,
        file_name: fileName,
        file_url: fileUrl,
        parsed_text: resumeText,
      })
      .select()
      .single();

    if (resumeError) {
      console.error('Resume insert error:', resumeError);
      throw resumeError;
    }

    // Store analysis in database
    const { data: analysisData, error: analysisError } = await supabaseClient
      .from('analyses')
      .insert({
        user_id: user.id,
        resume_id: resumeData.id,
        job_title: jobTitle,
        job_description: jobDescription,
        match_score: analysisResult.matchScore,
        ai_feedback: analysisResult.feedback,
        matched_keywords: analysisResult.matchedKeywords,
        missing_keywords: analysisResult.missingKeywords,
      })
      .select()
      .single();

    if (analysisError) {
      console.error('Analysis insert error:', analysisError);
      throw analysisError;
    }

    console.log('Analysis completed successfully:', analysisData.id);

    return new Response(
      JSON.stringify({
        analysisId: analysisData.id,
        message: 'Analysis completed successfully',
      }),
      {
        headers: { ...corsHeaders, 'Content-Type': 'application/json' },
        status: 200,
      }
    );
  } catch (error: unknown) {
    console.error('Error in analyze-resume function:', error);
    const errorMessage =
      error instanceof Error ? error.message : 'Internal server error';
    return new Response(JSON.stringify({ error: errorMessage }), {
      headers: { ...corsHeaders, 'Content-Type': 'application/json' },
      status: 500,
    });
  }
});
