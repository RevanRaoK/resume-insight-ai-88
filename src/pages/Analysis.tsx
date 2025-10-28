import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { Navbar } from '@/components/Navbar';
import { Badge } from '@/components/ui/badge';
import { CheckCircle2, Lightbulb, AlertCircle } from 'lucide-react';
import { supabase } from '@/integrations/supabase/client';
import { useToast } from '@/hooks/use-toast';

interface AnalysisData {
  id: string;
  job_title: string;
  match_score: number;
  ai_feedback: any;
  matched_keywords: any;
  missing_keywords: any;
  created_at: string;
}

export default function Analysis() {
  const { id } = useParams();
  const [analysis, setAnalysis] = useState<AnalysisData | null>(null);
  const [loading, setLoading] = useState(true);
  const { toast } = useToast();

  useEffect(() => {
    const fetchAnalysis = async () => {
      if (!id) return;
      
      try {
        const { data, error } = await supabase
          .from('analyses')
          .select('*')
          .eq('id', id)
          .single();

        if (error) throw error;
        setAnalysis(data);
      } catch (error: any) {
        toast({
          title: 'Error',
          description: 'Failed to load analysis results.',
          variant: 'destructive'
        });
      } finally {
        setLoading(false);
      }
    };

    fetchAnalysis();
  }, [id]);

  if (loading) {
    return (
      <div className="min-h-screen bg-background">
        <Navbar />
        <div className="flex items-center justify-center h-[calc(100vh-4rem)]">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
        </div>
      </div>
    );
  }

  if (!analysis) {
    return (
      <div className="min-h-screen bg-background">
        <Navbar />
        <div className="flex items-center justify-center h-[calc(100vh-4rem)]">
          <p className="text-muted-foreground">Analysis not found.</p>
        </div>
      </div>
    );
  }

  const getScoreColor = (score: number) => {
    if (score >= 80) return 'text-success';
    if (score >= 60) return 'text-warning';
    return 'text-destructive';
  };

  const getScoreMessage = (score: number) => {
    if (score >= 80) return 'Excellent Match Score!';
    if (score >= 60) return 'Good Match Score!';
    return 'Room for Improvement';
  };

  return (
    <div className="min-h-screen bg-background">
      <Navbar />
      <main className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-12">
        <h1 className="text-3xl font-bold mb-8">Analysis for: {analysis.job_title}</h1>

        {/* Match Score Card */}
        <div className="bg-card rounded-xl p-8 mb-8 border border-border">
          <div className="flex items-center gap-8">
            <div className="relative">
              <svg className="w-48 h-48 transform -rotate-90">
                <circle
                  cx="96"
                  cy="96"
                  r="80"
                  stroke="hsl(var(--secondary))"
                  strokeWidth="12"
                  fill="none"
                />
                <circle
                  cx="96"
                  cy="96"
                  r="80"
                  stroke="hsl(var(--success))"
                  strokeWidth="12"
                  fill="none"
                  strokeDasharray={`${(analysis.match_score / 100) * 502.4} 502.4`}
                  className="transition-all duration-1000"
                />
              </svg>
              <div className="absolute inset-0 flex items-center justify-center">
                <span className={`text-5xl font-bold ${getScoreColor(analysis.match_score)}`}>
                  {analysis.match_score}%
                </span>
              </div>
            </div>
            <div className="flex-1">
              <h2 className="text-2xl font-bold mb-2">{getScoreMessage(analysis.match_score)}</h2>
              <p className="text-muted-foreground">
                Your resume is a {analysis.match_score >= 80 ? 'strong' : 'good'} match for this role. 
                Review the AI feedback and keyword breakdown below to get even closer to 100%.
              </p>
            </div>
          </div>
        </div>

        <div className="grid md:grid-cols-2 gap-8">
          {/* AI Feedback */}
          <div className="bg-card rounded-xl p-6 border border-border">
            <h3 className="text-xl font-bold mb-6">AI-Powered Feedback</h3>
            <div className="space-y-4">
              {analysis.ai_feedback.map((feedback, index) => (
                <div key={index} className="flex gap-3">
                  <div className="flex-shrink-0 mt-1">
                    {index === 0 ? (
                      <CheckCircle2 className="h-5 w-5 text-success" />
                    ) : index === 1 ? (
                      <Lightbulb className="h-5 w-5 text-warning" />
                    ) : (
                      <AlertCircle className="h-5 w-5 text-primary" />
                    )}
                  </div>
                  <div className="flex-1">
                    <p className="text-sm leading-relaxed">{feedback}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Keyword Breakdown */}
          <div className="bg-card rounded-xl p-6 border border-border">
            <h3 className="text-xl font-bold mb-6">Keyword Breakdown</h3>
            <div className="space-y-6">
              <div>
                <h4 className="text-sm font-semibold mb-3">Matching Keywords</h4>
                <div className="flex flex-wrap gap-2">
                  {analysis.matched_keywords.map((keyword, index) => (
                    <Badge key={index} className="bg-success-light text-success border-none">
                      {keyword}
                    </Badge>
                  ))}
                </div>
              </div>
              <div>
                <h4 className="text-sm font-semibold mb-3">Missing Keywords</h4>
                <div className="flex flex-wrap gap-2">
                  {analysis.missing_keywords.map((keyword, index) => (
                    <Badge key={index} className="bg-warning-light text-warning border-none">
                      {keyword}
                    </Badge>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
