import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Navbar } from '@/components/Navbar';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Upload, FileText, AlertCircle, Loader2 } from 'lucide-react';
import { useEnhancedToast } from '@/hooks/use-enhanced-toast';
import { useFormValidation } from '@/hooks/use-form-validation';
import { useLoading } from '@/hooks/use-loading';
import { supabase } from '@/integrations/supabase/client';
import { getAuthHeaders, getBearerToken } from '@/lib/auth';
import {
  DashboardFormState,
  AnalysisRequest,
  AnalysisResponse,
  FileUploadResponse,
  FILE_VALIDATION,
  FORM_VALIDATION,
} from '@/types';

export default function Dashboard() {
  const [formState, setFormState] = useState<DashboardFormState>({
    file: null,
    jobDescription: '',
    jobRole: '',
    loading: false,
  });
  const navigate = useNavigate();

  // Enhanced hooks
  const { showSuccess, showError, showValidationError, showNetworkError } =
    useEnhancedToast();

  const {
    errors,
    validateFileAndSetError,
    validateAndSetError,
    setFieldTouched,
    shouldShowError,
    clearAllErrors,
    hasErrors,
  } = useFormValidation();

  const { isLoading, withLoading } = useLoading();

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0];

    if (selectedFile) {
      const isValid = validateFileAndSetError('resume', selectedFile, {
        required: true,
        allowedTypes: FILE_VALIDATION.ALLOWED_TYPES,
        maxSizeInMB: FILE_VALIDATION.MAX_SIZE_MB,
      });

      if (isValid) {
        setFormState((prev) => ({ ...prev, file: selectedFile }));
        showSuccess('Resume uploaded successfully');
      } else {
        setFormState((prev) => ({ ...prev, file: null }));
      }
    }

    setFieldTouched('resume');
  };

  const validateForm = (): boolean => {
    // Clear previous errors
    clearAllErrors();

    let isValid = true;

    // Validate file
    if (
      !validateFileAndSetError('resume', formState.file, {
        required: true,
        allowedTypes: FILE_VALIDATION.ALLOWED_TYPES,
        maxSizeInMB: FILE_VALIDATION.MAX_SIZE_MB,
      })
    ) {
      isValid = false;
    }

    // Validate job description
    if (
      !validateAndSetError('jobDescription', formState.jobDescription, {
        required: true,
        minLength: FORM_VALIDATION.JOB_DESCRIPTION.MIN_LENGTH,
        maxLength: FORM_VALIDATION.JOB_DESCRIPTION.MAX_LENGTH,
      })
    ) {
      isValid = false;
    }

    // Validate job role
    if (
      !validateAndSetError('jobRole', formState.jobRole, {
        required: true,
        minLength: FORM_VALIDATION.JOB_ROLE.MIN_LENGTH,
        maxLength: FORM_VALIDATION.JOB_ROLE.MAX_LENGTH,
      })
    ) {
      isValid = false;
    }

    // Mark all fields as touched to show errors
    setFieldTouched('resume');
    setFieldTouched('jobDescription');
    setFieldTouched('jobRole');

    return isValid;
  };

  const handleAnalyze = async () => {
    if (!validateForm()) {
      showValidationError('Please fix the validation errors before submitting');
      return;
    }

    const result = await withLoading(
      'analyze',
      async () => {
        // Get auth token
        const {
          data: { session },
        } = await supabase.auth.getSession();

        if (!session?.access_token) {
          throw new Error('Authentication required - please log in');
        }

        // Step 1: Upload resume to FastAPI backend
        const formData = new FormData();
        formData.append('file', formState.file!);

        const uploadResponse = await fetch(
          `${import.meta.env.VITE_API_BASE_URL}/api/v1/upload`,
          {
            method: 'POST',
            headers: {
              Authorization: await getBearerToken(),
            },
            body: formData,
          }
        );

        if (!uploadResponse.ok) {
          const errorData = await uploadResponse.json().catch(() => ({}));
          throw new Error(
            errorData.detail?.message ||
              `Upload failed with status ${uploadResponse.status}`
          );
        }

        const uploadData: FileUploadResponse = await uploadResponse.json();

        // Step 2: Analyze resume with job description
        const analysisRequest: AnalysisRequest = {
          resume_id: uploadData.resume_id,
          job_description: formState.jobDescription,
          job_title: formState.jobRole,
        };

        const analysisResponse = await fetch(
          `${import.meta.env.VITE_API_BASE_URL}/api/v1/analyze`,
          {
            method: 'POST',
            headers: await getAuthHeaders(),
            body: JSON.stringify(analysisRequest),
          }
        );

        if (!analysisResponse.ok) {
          const errorData = await analysisResponse.json().catch(() => ({}));
          throw new Error(
            errorData.detail?.message ||
              `Analysis failed with status ${analysisResponse.status}`
          );
        }

        const analysisData: AnalysisResponse = await analysisResponse.json();
        return analysisData;
      },
      {
        errorTitle: 'Analysis Failed',
      }
    );

    if (result) {
      showSuccess('Your resume has been analyzed successfully!');
      navigate(`/analysis/${result.analysis_id}`);
    }
  };

  return (
    <div className="min-h-screen bg-background">
      <Navbar />
      <main className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-12">
        {/* Job Role Input - Prominently positioned */}
        <div className="mb-8">
          <div className="max-w-md mx-auto space-y-4">
            <Label htmlFor="job-role" className="text-lg font-semibold">
              Job Role *
            </Label>
            <div className="space-y-2">
              <p className="text-sm text-muted-foreground">
                What position are you applying for?
              </p>
              <Input
                id="job-role"
                placeholder="e.g., Senior Software Engineer, Product Manager, Data Scientist..."
                className={`bg-card ${
                  shouldShowError('jobRole')
                    ? 'border-destructive focus:ring-destructive'
                    : ''
                }`}
                value={formState.jobRole}
                onChange={(e) => {
                  const newValue = e.target.value;
                  setFormState((prev) => ({ ...prev, jobRole: newValue }));
                  if (shouldShowError('jobRole')) {
                    validateAndSetError('jobRole', newValue, {
                      required: true,
                      minLength: FORM_VALIDATION.JOB_ROLE.MIN_LENGTH,
                      maxLength: FORM_VALIDATION.JOB_ROLE.MAX_LENGTH,
                    });
                  }
                }}
                onBlur={() => {
                  setFieldTouched('jobRole');
                  validateAndSetError('jobRole', formState.jobRole, {
                    required: true,
                    minLength: FORM_VALIDATION.JOB_ROLE.MIN_LENGTH,
                    maxLength: FORM_VALIDATION.JOB_ROLE.MAX_LENGTH,
                  });
                }}
              />
              {shouldShowError('jobRole') && (
                <div className="flex items-center gap-2 text-sm text-destructive">
                  <AlertCircle className="h-4 w-4" />
                  <span>{errors.jobRole}</span>
                </div>
              )}
            </div>
          </div>
        </div>

        <div className="grid md:grid-cols-2 gap-8">
          {/* Resume Upload */}
          <div className="space-y-4">
            <Label className="text-lg font-semibold">Your Resume *</Label>
            <div
              className={`border-2 border-dashed rounded-xl p-12 text-center space-y-4 bg-card transition-colors ${
                shouldShowError('resume')
                  ? 'border-destructive'
                  : 'border-border hover:border-primary'
              }`}
            >
              {formState.file ? (
                <div className="space-y-4">
                  <FileText className="h-16 w-16 text-primary mx-auto" />
                  <p className="text-sm font-medium">{formState.file.name}</p>
                  <Button
                    variant="outline"
                    onClick={() => {
                      setFormState((prev) => ({ ...prev, file: null }));
                      setFieldTouched('resume');
                    }}
                    className="mt-2"
                  >
                    Remove File
                  </Button>
                </div>
              ) : (
                <>
                  <Upload
                    className={`h-16 w-16 mx-auto ${
                      shouldShowError('resume')
                        ? 'text-destructive'
                        : 'text-muted-foreground'
                    }`}
                  />
                  <div className="space-y-2">
                    <p className="text-lg font-medium">
                      Drag & Drop your Resume
                    </p>
                    <p className="text-sm text-muted-foreground">
                      PDF, DOCX, or TXT only. Max 10MB.
                    </p>
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
            {shouldShowError('resume') && (
              <div className="flex items-center gap-2 text-sm text-destructive">
                <AlertCircle className="h-4 w-4" />
                <span>{errors.resume}</span>
              </div>
            )}
          </div>

          {/* Job Description */}
          <div className="space-y-4">
            <Label htmlFor="job-description" className="text-lg font-semibold">
              Job Description *
            </Label>
            <div className="space-y-2">
              <p className="text-sm text-muted-foreground">
                Paste Job Description Here (10-5000 characters)
              </p>
              <Textarea
                id="job-description"
                placeholder="e.g., Paste the full job description for the Senior Software Engineer role at Google..."
                className={`min-h-[400px] resize-none bg-card ${
                  shouldShowError('jobDescription')
                    ? 'border-destructive focus:ring-destructive'
                    : ''
                }`}
                value={formState.jobDescription}
                onChange={(e) => {
                  const newValue = e.target.value;
                  setFormState((prev) => ({
                    ...prev,
                    jobDescription: newValue,
                  }));
                  if (shouldShowError('jobDescription')) {
                    validateAndSetError('jobDescription', newValue, {
                      required: true,
                      minLength: FORM_VALIDATION.JOB_DESCRIPTION.MIN_LENGTH,
                      maxLength: FORM_VALIDATION.JOB_DESCRIPTION.MAX_LENGTH,
                    });
                  }
                }}
                onBlur={() => {
                  setFieldTouched('jobDescription');
                  validateAndSetError(
                    'jobDescription',
                    formState.jobDescription,
                    {
                      required: true,
                      minLength: FORM_VALIDATION.JOB_DESCRIPTION.MIN_LENGTH,
                      maxLength: FORM_VALIDATION.JOB_DESCRIPTION.MAX_LENGTH,
                    }
                  );
                }}
              />
              <div className="flex justify-between items-center">
                <div>
                  {shouldShowError('jobDescription') && (
                    <div className="flex items-center gap-2 text-sm text-destructive">
                      <AlertCircle className="h-4 w-4" />
                      <span>{errors.jobDescription}</span>
                    </div>
                  )}
                </div>
                <div className="text-xs text-muted-foreground">
                  {formState.jobDescription.length}/
                  {FORM_VALIDATION.JOB_DESCRIPTION.MAX_LENGTH} characters
                </div>
              </div>
            </div>
          </div>
        </div>

        <div className="mt-8">
          <Button
            onClick={handleAnalyze}
            disabled={
              isLoading('analyze') ||
              !formState.file ||
              !formState.jobDescription.trim() ||
              !formState.jobRole.trim() ||
              hasErrors()
            }
            className="w-full h-14 text-lg bg-primary hover:bg-primary-hover"
          >
            {isLoading('analyze') ? (
              <>
                <Loader2 className="h-5 w-5 animate-spin mr-2" />
                Analyzing...
              </>
            ) : (
              'Analyze My Resume'
            )}
          </Button>
          {hasErrors() && (
            <p className="text-sm text-destructive text-center mt-2">
              Please fix the validation errors above before submitting
            </p>
          )}
        </div>
      </main>
    </div>
  );
}
