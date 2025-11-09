import React, { useState, useEffect } from 'react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { AlertTriangle, Loader2 } from 'lucide-react';
import { ConfirmationModalProps, ConfirmationModalState } from '@/types';

export const ConfirmationModal: React.FC<ConfirmationModalProps> = ({
  open,
  onOpenChange,
  title,
  description,
  confirmText = 'Confirm',
  cancelText = 'Cancel',
  variant = 'default',
  loading = false,
  onConfirm,
  onCancel,
  requiresTextConfirmation = false,
  confirmationText = '',
  multiStep = false,
  steps = [],
}) => {
  const [modalState, setModalState] = useState<ConfirmationModalState>({
    currentStep: 0,
    textInput: '',
    isTextConfirmed: false,
  });

  // Reset state when modal opens/closes
  useEffect(() => {
    if (open) {
      setModalState({
        currentStep: 0,
        textInput: '',
        isTextConfirmed: false,
      });
    }
  }, [open]);

  // Check text confirmation
  useEffect(() => {
    if (requiresTextConfirmation && confirmationText) {
      setModalState((prev) => ({
        ...prev,
        isTextConfirmed:
          prev.textInput.toLowerCase() === confirmationText.toLowerCase(),
      }));
    }
  }, [modalState.textInput, confirmationText, requiresTextConfirmation]);

  const handleCancel = () => {
    if (onCancel) {
      onCancel();
    } else {
      onOpenChange(false);
    }
  };

  const handleNext = () => {
    if (multiStep && modalState.currentStep < steps.length - 1) {
      setModalState((prev) => ({ ...prev, currentStep: prev.currentStep + 1 }));
    } else {
      handleConfirm();
    }
  };

  const handleBack = () => {
    if (modalState.currentStep > 0) {
      setModalState((prev) => ({ ...prev, currentStep: prev.currentStep - 1 }));
    }
  };

  const handleConfirm = () => {
    if (requiresTextConfirmation && !modalState.isTextConfirmed) {
      return;
    }

    try {
      onConfirm();
    } catch (error) {
      console.error('Error in confirmation modal:', error);
      // The parent component should handle the error
    }
  };

  const canProceed = (): boolean => {
    if (loading) return false;
    if (requiresTextConfirmation && !modalState.isTextConfirmed) return false;
    return true;
  };

  const getCurrentContent = () => {
    if (multiStep && steps.length > 0) {
      const step = steps[modalState.currentStep];
      return {
        title: step.title,
        description: step.description,
        warning: step.warning,
      };
    }
    return { title, description };
  };

  const content = getCurrentContent();
  const isLastStep = !multiStep || modalState.currentStep === steps.length - 1;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            {variant === 'destructive' && (
              <AlertTriangle className="h-5 w-5 text-destructive" />
            )}
            {content.title}
          </DialogTitle>
          <DialogDescription
            className={variant === 'destructive' ? 'text-destructive/80' : ''}
          >
            {content.description}
          </DialogDescription>
          {content.warning && (
            <div className="mt-4 p-4 bg-destructive/10 border border-destructive/20 rounded-md">
              <div className="flex items-start gap-2">
                <AlertTriangle className="h-4 w-4 text-destructive mt-0.5 flex-shrink-0" />
                <p className="text-sm text-destructive font-medium">
                  {content.warning}
                </p>
              </div>
            </div>
          )}
        </DialogHeader>

        {requiresTextConfirmation && isLastStep && (
          <div className="space-y-2">
            <Label htmlFor="confirmation-input" className="text-sm font-medium">
              Type "{confirmationText}" to confirm:
            </Label>
            <Input
              id="confirmation-input"
              value={modalState.textInput}
              onChange={(e) =>
                setModalState((prev) => ({
                  ...prev,
                  textInput: e.target.value,
                }))
              }
              placeholder={confirmationText}
              className={
                modalState.textInput && !modalState.isTextConfirmed
                  ? 'border-destructive focus:ring-destructive'
                  : ''
              }
              disabled={loading}
            />
            {modalState.textInput && !modalState.isTextConfirmed && (
              <p className="text-sm text-destructive">
                Please type "{confirmationText}" exactly as shown.
              </p>
            )}
          </div>
        )}

        {multiStep && (
          <div className="flex justify-center space-x-1">
            {steps.map((_, index) => (
              <div
                key={index}
                className={`h-2 w-2 rounded-full ${
                  index === modalState.currentStep
                    ? 'bg-primary'
                    : index < modalState.currentStep
                    ? 'bg-primary/50'
                    : 'bg-muted'
                }`}
              />
            ))}
          </div>
        )}

        <DialogFooter className="gap-2 sm:gap-0">
          {multiStep && modalState.currentStep > 0 && (
            <Button
              type="button"
              variant="outline"
              onClick={handleBack}
              disabled={loading}
            >
              Back
            </Button>
          )}
          <Button
            type="button"
            variant="outline"
            onClick={handleCancel}
            disabled={loading}
          >
            {cancelText}
          </Button>
          <Button
            type="button"
            variant={variant === 'destructive' ? 'destructive' : 'default'}
            onClick={handleNext}
            disabled={!canProceed()}
          >
            {loading && <Loader2 className="h-4 w-4 animate-spin mr-2" />}
            {isLastStep ? confirmText : 'Next'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};
