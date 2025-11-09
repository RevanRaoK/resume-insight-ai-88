import { useEffect, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Navbar } from '@/components/Navbar';
import { Button } from '@/components/ui/button';
import { useEnhancedToast } from '@/hooks/use-enhanced-toast';
import { useLoading } from '@/hooks/use-loading';
import { formatDistanceToNow } from 'date-fns';
import { RefreshCw, Clock, Target, Trash2, Loader2 } from 'lucide-react';
import { supabase } from '@/integrations/supabase/client';
import { useAuth } from '@/contexts/AuthContext';
import { ConfirmationModal } from '@/components/ConfirmationModal';
import {
  Analysis,
  HistoryState,
  DeleteAnalysisFunction,
  ScoreBgColorType,
  SCORE_THRESHOLDS,
} from '@/types';

export default function History() {
  const [historyState, setHistoryState] = useState<HistoryState>({
    analyses: [],
    loading: false,
    deleteModalOpen: false,
    selectedAnalysisId: null,
  });
  const navigate = useNavigate();
  const { user } = useAuth();

  // Enhanced hooks
  const { showOperationSuccess, showOperationError } = useEnhancedToast();

  const { isLoading, withLoading } = useLoading();

  const fetchHistory = useCallback(async () => {
    if (!user?.id) {
      console.log('No user ID available, skipping fetch');
      return;
    }

    const result = await withLoading(
      'fetchHistory',
      async () => {
        const { data, error } = await supabase
          .from('analyses')
          .select('*')
          .eq('user_id', user.id)
          .order('created_at', { ascending: false });

        if (error) {
          throw error;
        }

        return data || [];
      },
      {
        showErrorToast: true,
        errorTitle: 'Failed to Load History',
      }
    );

    if (result) {
      setHistoryState((prev) => ({ ...prev, analyses: result }));
    }
  }, [user?.id]); // Remove withLoading from dependencies

  useEffect(() => {
    fetchHistory();
  }, [fetchHistory, user.id]); // Use user?.id directly instead of fetchHistory

  const deleteAnalysis: DeleteAnalysisFunction = async (analysisId: string) => {
    if (!user?.id) {
      showOperationError('Delete analysis', 'User not authenticated');
      return;
    }

    const result = await withLoading(
      'deleteAnalysis',
      async () => {
        const { error } = await supabase
          .from('analyses')
          .delete()
          .eq('id', analysisId)
          .eq('user_id', user.id); // Additional security check

        if (error) {
          throw error;
        }

        return true;
      },
      {
        showErrorToast: true,
        errorTitle: 'Delete Failed',
      }
    );

    if (result) {
      // Update UI to remove deleted item from the list
      setHistoryState((prev) => ({
        ...prev,
        analyses: prev.analyses.filter(
          (analysis) => analysis.id !== analysisId
        ),
        deleteModalOpen: false,
        selectedAnalysisId: null,
      }));

      showOperationSuccess('Delete', 'analysis');
    }
  };

  const handleDeleteClick = (e: React.MouseEvent, analysisId: string) => {
    e.stopPropagation(); // Prevent navigation when clicking delete button
    setHistoryState((prev) => ({
      ...prev,
      selectedAnalysisId: analysisId,
      deleteModalOpen: true,
    }));
  };

  const handleConfirmDelete = () => {
    if (historyState.selectedAnalysisId) {
      deleteAnalysis(historyState.selectedAnalysisId);
    }
  };

  const handleCancelDelete = () => {
    setHistoryState((prev) => ({
      ...prev,
      deleteModalOpen: false,
      selectedAnalysisId: null,
    }));
  };

  const getScoreColor = (score: number): ScoreBgColorType => {
    if (score >= SCORE_THRESHOLDS.EXCELLENT)
      return 'bg-success-light text-success';
    if (score >= SCORE_THRESHOLDS.GOOD) return 'bg-warning-light text-warning';
    return 'bg-destructive/10 text-destructive';
  };

  if (isLoading('fetchHistory')) {
    return (
      <div className="min-h-screen bg-background">
        <Navbar />
        <div className="flex items-center justify-center h-[calc(100vh-4rem)]">
          <div className="flex flex-col items-center gap-4">
            <Loader2 className="h-12 w-12 animate-spin text-primary" />
            <p className="text-muted-foreground">
              Loading your analysis history...
            </p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background">
      <Navbar />
      <main className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-12">
        <div className="flex items-center justify-between mb-8">
          <h1 className="text-3xl font-bold">Your Analysis History</h1>
          <Button
            onClick={fetchHistory}
            variant="outline"
            size="sm"
            disabled={isLoading('fetchHistory')}
          >
            <RefreshCw
              className={`h-4 w-4 mr-2 ${
                isLoading('fetchHistory') ? 'animate-spin' : ''
              }`}
            />
            Refresh
          </Button>
        </div>

        {historyState.analyses.length === 0 ? (
          <div className="text-center py-12">
            <p className="text-muted-foreground mb-4">
              No analyses yet. Start by analyzing your first resume!
            </p>
            <button
              onClick={() => navigate('/dashboard')}
              className="text-primary hover:underline font-medium"
            >
              Go to Dashboard
            </button>
          </div>
        ) : (
          <div className="space-y-4">
            {historyState.analyses.map((analysis) => (
              <div
                key={analysis.id}
                className="w-full bg-card rounded-xl p-6 border border-border hover:border-primary transition-all hover:shadow-md relative"
              >
                <button
                  onClick={() => navigate(`/analysis/${analysis.id}`)}
                  className="w-full text-left"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex-1 pr-4">
                      <div className="flex items-center gap-3 mb-3">
                        <Target className="h-5 w-5 text-primary" />
                        <h3 className="text-xl font-bold text-foreground">
                          {analysis.job_title}
                        </h3>
                      </div>
                      <div className="flex items-center gap-2 text-sm text-muted-foreground">
                        <Clock className="h-3 w-3" />
                        <span>
                          Analyzed{' '}
                          {formatDistanceToNow(new Date(analysis.created_at), {
                            addSuffix: true,
                          })}
                        </span>
                      </div>
                    </div>
                    <div className="flex items-center gap-4">
                      <div
                        className={`flex items-center justify-center w-20 h-20 rounded-full text-2xl font-bold ${getScoreColor(
                          analysis.match_score
                        )}`}
                      >
                        {analysis.match_score}%
                      </div>
                    </div>
                  </div>
                </button>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={(e) => handleDeleteClick(e, analysis.id)}
                  className="absolute top-4 right-4 h-8 w-8 p-0 text-muted-foreground hover:text-destructive hover:bg-destructive/10"
                >
                  <Trash2 className="h-4 w-4" />
                </Button>
              </div>
            ))}
          </div>
        )}
      </main>

      <ConfirmationModal
        open={historyState.deleteModalOpen}
        onOpenChange={(open) =>
          setHistoryState((prev) => ({ ...prev, deleteModalOpen: open }))
        }
        title="Delete Analysis"
        description="Are you sure you want to delete this analysis? This action cannot be undone."
        confirmText="Delete"
        cancelText="Cancel"
        variant="destructive"
        loading={isLoading('deleteAnalysis')}
        onConfirm={handleConfirmDelete}
        onCancel={handleCancelDelete}
      />
    </div>
  );
}
