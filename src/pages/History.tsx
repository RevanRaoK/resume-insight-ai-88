import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Navbar } from '@/components/Navbar';
import { supabase } from '@/integrations/supabase/client';
import { useToast } from '@/hooks/use-toast';
import { formatDistanceToNow } from 'date-fns';

interface Analysis {
  id: string;
  job_title: string;
  match_score: number;
  created_at: string;
}

export default function History() {
  const [analyses, setAnalyses] = useState<Analysis[]>([]);
  const [loading, setLoading] = useState(true);
  const { toast } = useToast();
  const navigate = useNavigate();

  useEffect(() => {
    const fetchHistory = async () => {
      try {
        const { data, error } = await supabase
          .from('analyses')
          .select('id, job_title, match_score, created_at')
          .order('created_at', { ascending: false });

        if (error) throw error;
        setAnalyses(data || []);
      } catch (error: any) {
        toast({
          title: 'Error',
          description: 'Failed to load analysis history.',
          variant: 'destructive'
        });
      } finally {
        setLoading(false);
      }
    };

    fetchHistory();
  }, []);

  const getScoreColor = (score: number) => {
    if (score >= 80) return 'bg-success-light text-success';
    if (score >= 60) return 'bg-warning-light text-warning';
    return 'bg-destructive/10 text-destructive';
  };

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

  return (
    <div className="min-h-screen bg-background">
      <Navbar />
      <main className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-12">
        <h1 className="text-3xl font-bold mb-8">Your Analysis History</h1>

        {analyses.length === 0 ? (
          <div className="text-center py-12">
            <p className="text-muted-foreground mb-4">No analyses yet. Start by analyzing your first resume!</p>
            <button
              onClick={() => navigate('/dashboard')}
              className="text-primary hover:underline font-medium"
            >
              Go to Dashboard
            </button>
          </div>
        ) : (
          <div className="space-y-4">
            {analyses.map((analysis) => (
              <button
                key={analysis.id}
                onClick={() => navigate(`/analysis/${analysis.id}`)}
                className="w-full bg-card rounded-xl p-6 border border-border hover:border-primary transition-all text-left"
              >
                <div className="flex items-center justify-between">
                  <div className="flex-1">
                    <h3 className="text-lg font-semibold mb-1">{analysis.job_title}</h3>
                    <p className="text-sm text-muted-foreground">
                      Analyzed {formatDistanceToNow(new Date(analysis.created_at), { addSuffix: true })}
                    </p>
                  </div>
                  <div className={`flex items-center justify-center w-20 h-20 rounded-full text-2xl font-bold ${getScoreColor(analysis.match_score)}`}>
                    {analysis.match_score}%
                  </div>
                </div>
              </button>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
