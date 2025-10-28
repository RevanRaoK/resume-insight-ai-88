import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Navbar } from '@/components/Navbar';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { Upload, FileText } from 'lucide-react';
import { useToast } from '@/hooks/use-toast';
import { supabase } from '@/integrations/supabase/client';
import { useAuth } from '@/contexts/AuthContext';

export default function Dashboard() {
  const [file, setFile] = useState<File | null>(null);
  const [jobDescription, setJobDescription] = useState('');
  const [loading, setLoading] = useState(false);
  const { toast } = useToast();
  const navigate = useNavigate();
  const { user } = useAuth();

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0];
    if (selectedFile) {
      const validTypes = ['application/pdf', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'text/plain'];
      if (!validTypes.includes(selectedFile.type)) {
        toast({
          title: 'Invalid file type',
          description: 'Please upload PDF, DOCX, or TXT files only.',
          variant: 'destructive'
        });
        return;
      }
      if (selectedFile.size > 10 * 1024 * 1024) {
        toast({
          title: 'File too large',
          description: 'File size must be less than 10MB.',
          variant: 'destructive'
        });
        return;
      }
      setFile(selectedFile);
    }
  };

  const handleAnalyze = async () => {
    if (!file || !jobDescription.trim()) {
      toast({
        title: 'Missing information',
        description: 'Please upload a resume and enter a job description.',
        variant: 'destructive'
      });
      return;
    }

    setLoading(true);
    try {
      // Upload file to storage
      const filePath = `${user?.id}/${Date.now()}-${file.name}`;
      const { error: uploadError } = await supabase.storage
        .from('resumes')
        .upload(filePath, file);

      if (uploadError) throw uploadError;

      // Get public URL
      const { data: { publicUrl } } = supabase.storage
        .from('resumes')
        .getPublicUrl(filePath);

      // Call analyze function
      const { data, error } = await supabase.functions.invoke('analyze-resume', {
        body: {
          fileName: file.name,
          fileUrl: publicUrl,
          jobDescription: jobDescription
        }
      });

      if (error) throw error;

      toast({
        title: 'Analysis complete!',
        description: 'Your resume has been analyzed successfully.'
      });

      // Navigate to analysis page with the ID
      navigate(`/analysis/${data.analysisId}`);
    } catch (error: any) {
      console.error('Analysis error:', error);
      toast({
        title: 'Analysis failed',
        description: error.message || 'Failed to analyze resume. Please try again.',
        variant: 'destructive'
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-background">
      <Navbar />
      <main className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-12">
        <div className="grid md:grid-cols-2 gap-8">
          {/* Resume Upload */}
          <div className="space-y-4">
            <Label className="text-lg font-semibold">Your Resume</Label>
            <div className="border-2 border-dashed border-border rounded-xl p-12 text-center space-y-4 bg-card hover:border-primary transition-colors">
              {file ? (
                <div className="space-y-4">
                  <FileText className="h-16 w-16 text-primary mx-auto" />
                  <p className="text-sm font-medium">{file.name}</p>
                  <Button
                    variant="outline"
                    onClick={() => setFile(null)}
                    className="mt-2"
                  >
                    Remove File
                  </Button>
                </div>
              ) : (
                <>
                  <Upload className="h-16 w-16 text-muted-foreground mx-auto" />
                  <div className="space-y-2">
                    <p className="text-lg font-medium">Drag & Drop your Resume</p>
                    <p className="text-sm text-muted-foreground">PDF, DOCX, or TXT only.</p>
                  </div>
                  <Label htmlFor="file-upload" className="cursor-pointer">
                    <Button variant="secondary" asChild>
                      <span>Or Click to Upload</span>
                    </Button>
                  </Label>
                  <input
                    id="file-upload"
                    type="file"
                    className="hidden"
                    accept=".pdf,.docx,.txt"
                    onChange={handleFileChange}
                  />
                </>
              )}
            </div>
          </div>

          {/* Job Description */}
          <div className="space-y-4">
            <Label htmlFor="job-description" className="text-lg font-semibold">
              Job Description
            </Label>
            <div className="space-y-2">
              <p className="text-sm text-muted-foreground">
                Paste Job Description Here
              </p>
              <Textarea
                id="job-description"
                placeholder="e.g., Paste the full job description for the Senior Software Engineer role at Google..."
                className="min-h-[400px] resize-none bg-card"
                value={jobDescription}
                onChange={(e) => setJobDescription(e.target.value)}
              />
            </div>
          </div>
        </div>

        <div className="mt-8">
          <Button
            onClick={handleAnalyze}
            disabled={loading || !file || !jobDescription.trim()}
            className="w-full h-14 text-lg bg-primary hover:bg-primary-hover"
          >
            {loading ? 'Analyzing...' : 'Analyze My Resume'}
          </Button>
        </div>
      </main>
    </div>
  );
}
