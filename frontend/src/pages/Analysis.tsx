import { useEffect, useState, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Navbar } from '@/components/Navbar';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  CheckCircle2,
  Lightbulb,
  AlertCircle,
  Loader2,
  ArrowLeft,
} from 'lucide-react';
// import { useEnhancedToast } from '@/hooks/use-enhanced-toast';
import { useLoading } from '@/hooks/use-loading';
import { getAuthHeaders } from '@/lib/auth';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeHighlight from 'rehype-highlight';
import 'highlight.js/styles/github.css';
import '../styles/markdown.css';
import {
  AnalysisWithParsedData,
  ScoreColorType,
  SCORE_THRESHOLDS,
} from '@/types';

// Type definitions for ReactMarkdown components
interface MarkdownComponentProps {
  children?: React.ReactNode;
}

const MarkdownComponents = {
  h1: ({ children }: MarkdownComponentProps) => (
    <h1 className="text-2xl font-bold mb-4 text-foreground border-b border-border pb-2">
      {children}
    </h1>
  ),
  h2: ({ children }: MarkdownComponentProps) => (
    <h2 className="text-xl font-semibold mb-3 text-foreground mt-6">
      {children}
    </h2>
  ),
  h3: ({ children }: MarkdownComponentProps) => (
    <h3 className="text-lg font-medium mb-2 text-foreground mt-4">
      {children}
    </h3>
  ),
  p: ({ children }: MarkdownComponentProps) => (
    <p className="text-sm leading-relaxed text-muted-foreground mb-3">
      {children}
    </p>
  ),
  ul: ({ children }: MarkdownComponentProps) => (
    <ul className="list-disc list-inside space-y-1 mb-3 ml-4">{children}</ul>
  ),
  ol: ({ children }: MarkdownComponentProps) => (
    <ol className="list-decimal list-inside space-y-1 mb-3 ml-4">{children}</ol>
  ),
  li: ({ children }: MarkdownComponentProps) => (
    <li className="text-sm text-muted-foreground">{children}</li>
  ),
  strong: ({ children }: MarkdownComponentProps) => (
    <strong className="font-semibold text-foreground">{children}</strong>
  ),
  em: ({ children }: MarkdownComponentProps) => (
    <em className="italic text-muted-foreground">{children}</em>
  ),
  code: ({ children }: MarkdownComponentProps) => (
    <code className="bg-muted px-1.5 py-0.5 rounded text-sm font-mono text-foreground">
      {children}
    </code>
  ),
  pre: ({ children }: MarkdownComponentProps) => (
    <pre className="bg-muted p-4 rounded-lg overflow-x-auto mb-4">
      {children}
    </pre>
  ),
  blockquote: ({ children }: MarkdownComponentProps) => (
    <blockquote className="border-l-4 border-primary pl-4 italic text-muted-foreground mb-4">
      {children}
    </blockquote>
  ),
};

export default function Analysis() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [analysis, setAnalysis] = useState<AnalysisWithParsedData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const fetchingRef = useRef(false);

  // Enhanced hooks
  const { isLoading, withLoading } = useLoading();

  useEffect(() => {
    let isCancelled = false;

    const fetchAnalysis = async () => {
      if (!id || isCancelled || fetchingRef.current) {
        if (!id) setError('No analysis ID provided');
        return;
      }

      fetchingRef.current = true;

      try {
        const result = await withLoading(
          'fetchAnalysis',
          async () => {
            if (isCancelled) return null;

            const response = await fetch(
              `${import.meta.env.VITE_API_BASE_URL}/api/v1/analysis/${id}`,
              {
                method: 'GET',
                headers: await getAuthHeaders(),
              }
            );

            if (isCancelled) return null;

            if (!response.ok) {
              if (response.status === 404) {
                throw new Error(
                  'Analysis not found. It may have been deleted or the link is invalid.'
                );
              }
              throw new Error(`Failed to fetch analysis: ${response.status}`);
            }

            const data = await response.json();
            return data;
          },
          {
            showErrorToast: true,
            errorTitle: 'Failed to Load Analysis',
          }
        );

        if (!isCancelled && result) {
          setAnalysis(result);
          setError(null);
        } else if (!isCancelled && !result) {
          setError('Failed to load analysis');
        }
      } catch (error) {
        if (!isCancelled) {
          console.error('Error fetching analysis:', error);
          setError('Failed to load analysis');
        }
      } finally {
        if (!isCancelled) {
          fetchingRef.current = false;
        }
      }
    };

    fetchAnalysis();

    return () => {
      isCancelled = true;
      fetchingRef.current = false;
    };
  }, [id]); // eslint-disable-line react-hooks/exhaustive-deps
  // Note: withLoading is intentionally excluded to prevent infinite loop

  if (isLoading('fetchAnalysis')) {
    return (
      <div className="min-h-screen bg-background">
        <Navbar />
        <div className="flex items-center justify-center h-[calc(100vh-4rem)]">
          <div className="flex flex-col items-center gap-4">
            <Loader2 className="h-12 w-12 animate-spin text-primary" />
            <p className="text-muted-foreground">Loading analysis results...</p>
          </div>
        </div>
      </div>
    );
  }

  if (error || !analysis) {
    return (
      <div className="min-h-screen bg-background">
        <Navbar />
        <div className="flex items-center justify-center h-[calc(100vh-4rem)]">
          <div className="text-center space-y-4 max-w-md">
            <AlertCircle className="h-16 w-16 text-destructive mx-auto" />
            <h2 className="text-2xl font-bold text-foreground">
              Analysis Not Found
            </h2>
            <p className="text-muted-foreground">
              {error ||
                'The requested analysis could not be found. It may have been deleted or the link is invalid.'}
            </p>
            <div className="flex gap-3 justify-center">
              <Button
                onClick={() => navigate('/history')}
                variant="outline"
                className="flex items-center gap-2"
              >
                <ArrowLeft className="h-4 w-4" />
                Back to History
              </Button>
              <Button
                onClick={() => navigate('/dashboard')}
                className="flex items-center gap-2"
              >
                New Analysis
              </Button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  const getScoreColor = (score: number): ScoreColorType => {
    if (score >= SCORE_THRESHOLDS.EXCELLENT) return 'text-success';
    if (score >= SCORE_THRESHOLDS.GOOD) return 'text-warning';
    return 'text-destructive';
  };

  const getScoreMessage = (score: number): string => {
    if (score >= SCORE_THRESHOLDS.EXCELLENT) return 'Excellent Match Score!';
    if (score >= SCORE_THRESHOLDS.GOOD) return 'Good Match Score!';
    return 'Room for Improvement';
  };

  return (
    <div className="min-h-screen bg-background">
      <Navbar />
      <main className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-12">
        <h1 className="text-3xl font-bold mb-8">
          Analysis for: {analysis.job_title}
        </h1>

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
                  strokeDasharray={`${
                    (analysis.match_score / 100) * 502.4
                  } 502.4`}
                  className="transition-all duration-1000"
                />
              </svg>
              <div className="absolute inset-0 flex items-center justify-center">
                <span
                  className={`text-5xl font-bold ${getScoreColor(
                    analysis.match_score
                  )}`}
                >
                  {analysis.match_score}%
                </span>
              </div>
            </div>
            <div className="flex-1">
              <h2 className="text-2xl font-bold mb-2">
                {getScoreMessage(analysis.match_score)}
              </h2>
              <p className="text-muted-foreground">
                Your resume is a{' '}
                {analysis.match_score >= 80 ? 'strong' : 'good'} match for this
                role. Review the AI feedback and keyword breakdown below to get
                even closer to 100%.
              </p>
            </div>
          </div>
        </div>

        <div className="grid md:grid-cols-2 gap-8">
          {/* AI Feedback */}
          <div className="bg-card rounded-xl p-6 border border-border">
            <h3 className="text-xl font-bold mb-6">AI-Powered Feedback</h3>
            <div className="space-y-4">
              {/* Overall Assessment */}
              {analysis.ai_feedback.overall_assessment && (
                <div className="mb-6">
                  <div className="flex items-center gap-2 mb-3">
                    <CheckCircle2 className="h-5 w-5 text-primary" />
                    <h4 className="font-semibold text-foreground">
                      Overall Assessment
                    </h4>
                  </div>
                  <div className="prose prose-sm max-w-none">
                    <ReactMarkdown
                      components={MarkdownComponents}
                      remarkPlugins={[remarkGfm]}
                      rehypePlugins={[rehypeHighlight]}
                    >
                      {analysis.ai_feedback.overall_assessment}
                    </ReactMarkdown>
                  </div>
                </div>
              )}

              {/* Strengths */}
              {analysis.ai_feedback.strengths &&
                analysis.ai_feedback.strengths.length > 0 && (
                  <div className="mb-6">
                    <div className="flex items-center gap-2 mb-3">
                      <CheckCircle2 className="h-5 w-5 text-success" />
                      <h4 className="font-semibold text-foreground">
                        Strengths
                      </h4>
                    </div>
                    {analysis.ai_feedback.strengths.map(
                      (strength: string, index: number) => (
                        <div key={index} className="mb-3 strength-item">
                          <div className="prose prose-sm max-w-none">
                            <ReactMarkdown
                              components={MarkdownComponents}
                              remarkPlugins={[remarkGfm]}
                              rehypePlugins={[rehypeHighlight]}
                            >
                              {strength}
                            </ReactMarkdown>
                          </div>
                        </div>
                      )
                    )}
                  </div>
                )}

              {/* Priority Improvements */}
              {analysis.ai_feedback.priority_improvements &&
                analysis.ai_feedback.priority_improvements.length > 0 && (
                  <div className="mb-6">
                    <div className="flex items-center gap-2 mb-3">
                      <Lightbulb className="h-5 w-5 text-warning" />
                      <h4 className="font-semibold text-foreground">
                        Priority Improvements
                      </h4>
                    </div>
                    {analysis.ai_feedback.priority_improvements.map(
                      (improvement, index: number) => {
                        // Handle both object and string formats
                        if (typeof improvement === 'string') {
                          return (
                            <div
                              key={index}
                              className="mb-4 p-3 bg-muted/50 rounded-lg improvement-card"
                            >
                              <div className="font-medium text-foreground mb-2 improvement-title">
                                Improvement {index + 1}
                              </div>
                              <div className="prose prose-sm max-w-none">
                                <ReactMarkdown
                                  components={MarkdownComponents}
                                  remarkPlugins={[remarkGfm]}
                                  rehypePlugins={[rehypeHighlight]}
                                >
                                  {improvement}
                                </ReactMarkdown>
                              </div>
                            </div>
                          );
                        }

                        // Handle object format (new structure)
                        const category =
                          improvement.category ||
                          improvement.area ||
                          `Improvement ${index + 1}`;
                        const recommendation =
                          improvement.recommendation ||
                          improvement.suggestion ||
                          'No recommendation available';
                        const priority = improvement.priority;
                        const impact = improvement.impact;

                        return (
                          <div
                            key={index}
                            className="mb-4 p-4 bg-muted/50 rounded-lg improvement-card border-l-4 border-primary"
                          >
                            <div className="flex items-center justify-between mb-2">
                              <div className="font-semibold text-foreground improvement-title">
                                {category}
                              </div>
                              {priority && (
                                <span
                                  className={`px-2 py-1 rounded text-xs font-medium ${
                                    priority.toLowerCase() === 'critical'
                                      ? 'bg-destructive/10 text-destructive'
                                      : priority.toLowerCase() === 'high'
                                      ? 'bg-warning/10 text-warning'
                                      : 'bg-muted text-muted-foreground'
                                  }`}
                                >
                                  {priority}
                                </span>
                              )}
                            </div>

                            <div className="prose prose-sm max-w-none mb-3">
                              <ReactMarkdown
                                components={MarkdownComponents}
                                remarkPlugins={[remarkGfm]}
                                rehypePlugins={[rehypeHighlight]}
                              >
                                {recommendation}
                              </ReactMarkdown>
                            </div>

                            {impact && (
                              <div className="mt-3 p-2 bg-primary/5 rounded text-sm">
                                <div className="font-medium text-primary mb-1">
                                  Impact:
                                </div>
                                <div className="text-muted-foreground">
                                  <ReactMarkdown
                                    components={MarkdownComponents}
                                    remarkPlugins={[remarkGfm]}
                                    rehypePlugins={[rehypeHighlight]}
                                  >
                                    {impact}
                                  </ReactMarkdown>
                                </div>
                              </div>
                            )}
                          </div>
                        );
                      }
                    )}
                  </div>
                )}

              {/* ATS Optimization Tips */}
              {analysis.ai_feedback.ats_optimization_tips &&
                analysis.ai_feedback.ats_optimization_tips.length > 0 && (
                  <div className="mb-6">
                    <div className="flex items-center gap-2 mb-3">
                      <AlertCircle className="h-5 w-5 text-primary" />
                      <h4 className="font-semibold text-foreground">
                        ATS Optimization Tips
                      </h4>
                    </div>
                    {analysis.ai_feedback.ats_optimization_tips.map(
                      (tip: string, index: number) => (
                        <div key={index} className="mb-3 tip-item">
                          <div className="prose prose-sm max-w-none">
                            <ReactMarkdown
                              components={MarkdownComponents}
                              remarkPlugins={[remarkGfm]}
                              rehypePlugins={[rehypeHighlight]}
                            >
                              {tip}
                            </ReactMarkdown>
                          </div>
                        </div>
                      )
                    )}
                  </div>
                )}

              {/* Match Score Interpretation */}
              {analysis.ai_feedback.match_score_interpretation && (
                <div className="mb-6">
                  <div className="flex items-center gap-2 mb-3">
                    <AlertCircle className="h-5 w-5 text-primary" />
                    <h4 className="font-semibold text-foreground">
                      Match Score Analysis
                    </h4>
                  </div>
                  <div className="prose prose-sm max-w-none">
                    <ReactMarkdown
                      components={MarkdownComponents}
                      remarkPlugins={[remarkGfm]}
                      rehypePlugins={[rehypeHighlight]}
                    >
                      {analysis.ai_feedback.match_score_interpretation}
                    </ReactMarkdown>
                  </div>
                </div>
              )}

              {/* Missing Keywords Analysis */}
              {analysis.ai_feedback.missing_keywords_analysis && (
                <div className="mb-6">
                  <div className="flex items-center gap-2 mb-3">
                    <AlertCircle className="h-5 w-5 text-warning" />
                    <h4 className="font-semibold text-foreground">
                      Missing Keywords Analysis
                    </h4>
                  </div>
                  <div className="prose prose-sm max-w-none">
                    {typeof analysis.ai_feedback.missing_keywords_analysis ===
                    'string' ? (
                      <ReactMarkdown
                        components={MarkdownComponents}
                        remarkPlugins={[remarkGfm]}
                        rehypePlugins={[rehypeHighlight]}
                      >
                        {analysis.ai_feedback.missing_keywords_analysis}
                      </ReactMarkdown>
                    ) : (
                      <div className="space-y-4">
                        {analysis.ai_feedback.missing_keywords_analysis
                          ?.suggestions && (
                          <div>
                            <ReactMarkdown
                              components={MarkdownComponents}
                              remarkPlugins={[remarkGfm]}
                              rehypePlugins={[rehypeHighlight]}
                            >
                              {
                                analysis.ai_feedback.missing_keywords_analysis
                                  .suggestions
                              }
                            </ReactMarkdown>
                          </div>
                        )}
                        {analysis.ai_feedback.missing_keywords_analysis
                          ?.critical_missing &&
                          Array.isArray(
                            analysis.ai_feedback.missing_keywords_analysis
                              .critical_missing
                          ) &&
                          analysis.ai_feedback.missing_keywords_analysis
                            .critical_missing.length > 0 && (
                            <div className="mt-4">
                              <h5 className="font-medium text-foreground mb-3">
                                Critical Missing Keywords:
                              </h5>
                              <div className="flex flex-wrap gap-2">
                                {analysis.ai_feedback.missing_keywords_analysis.critical_missing.map(
                                  (keyword: string, index: number) => (
                                    <span
                                      key={index}
                                      className="bg-destructive/10 text-destructive px-2 py-1 rounded text-sm font-medium"
                                    >
                                      {keyword}
                                    </span>
                                  )
                                )}
                              </div>
                            </div>
                          )}
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Keyword Breakdown */}
          <div className="bg-card rounded-xl p-6 border border-border">
            <h3 className="text-xl font-bold mb-6">Keyword Breakdown</h3>
            <div className="space-y-6">
              <div>
                <h4 className="text-sm font-semibold mb-3">
                  Matching Keywords
                </h4>
                <div className="flex flex-wrap gap-2">
                  {analysis.matched_keywords.map(
                    (keyword: string, index: number) => (
                      <Badge
                        key={index}
                        className="bg-success-light text-success border-none"
                      >
                        {keyword}
                      </Badge>
                    )
                  )}
                </div>
              </div>
              <div>
                <h4 className="text-sm font-semibold mb-3">Missing Keywords</h4>
                <div className="flex flex-wrap gap-2">
                  {analysis.missing_keywords.map(
                    (keyword: string, index: number) => (
                      <Badge
                        key={index}
                        className="bg-warning-light text-warning border-none"
                      >
                        {keyword}
                      </Badge>
                    )
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
