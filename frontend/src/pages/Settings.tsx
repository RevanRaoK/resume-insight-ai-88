import { useState } from 'react';
import { Navbar } from '@/components/Navbar';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { ConfirmationModal } from '@/components/ConfirmationModal';
import { useAuth } from '@/contexts/AuthContext';
import { supabase } from '@/integrations/supabase/client';
import { useEnhancedToast } from '@/hooks/use-enhanced-toast';
import { useLoading } from '@/hooks/use-loading';
import { AlertTriangle, Loader2 } from 'lucide-react';
import {
  SettingsState,
  DeleteAccountFunction,
  ConfirmationStep,
  CONFIRMATION_TEXT,
} from '@/types';

export default function Settings() {
  const { user, signOut } = useAuth();
  const [settingsState, setSettingsState] = useState<SettingsState>({
    deleteAccountModalOpen: false,
    isDeleting: false,
  });

  // Enhanced hooks
  const {
    showSuccess,
    showSupabaseError,
    showOperationSuccess,
    showOperationError,
  } = useEnhancedToast();

  const { isLoading, withLoading } = useLoading();

  const deleteAccount: DeleteAccountFunction = async () => {
    if (!user?.id) {
      showOperationError(
        'Delete account',
        'User session not found. Please log in again.'
      );
      setSettingsState((prev) => ({ ...prev, deleteAccountModalOpen: false }));
      return;
    }

    const result = await withLoading(
      'deleteAccount',
      async () => {
        // Step 1: Delete all user analyses from Supabase
        const { error: analysesError, count } = await supabase
          .from('analyses')
          .delete({ count: 'exact' })
          .eq('user_id', user.id);

        if (analysesError) {
          throw new Error(
            `Failed to delete your analysis data: ${analysesError.message}. Please contact support if this issue persists.`
          );
        }

        console.log(
          `Successfully deleted ${count || 0} analysis records for user ${
            user.id
          }`
        );

        // Step 2: Sign out (which handles auth account deletion)
        try {
          await signOut();

          showSuccess(
            'Your account and all associated data have been permanently deleted. Thank you for using our service.',
            { title: 'Account Successfully Deleted', duration: 5000 }
          );
        } catch (signOutError) {
          console.error(
            'Sign out error during account deletion:',
            signOutError
          );
          // Even if sign out fails, data was deleted, so inform user
          showOperationError(
            'Sign out',
            'Your data was deleted but there was an issue signing you out. Please close your browser and clear cookies.'
          );
        }

        return true;
      },
      {
        showErrorToast: true,
        errorTitle: 'Account Deletion Failed',
      }
    );

    // Always close modal regardless of result
    setSettingsState((prev) => ({ ...prev, deleteAccountModalOpen: false }));
  };

  // Define confirmation steps for account deletion
  const accountDeletionSteps: ConfirmationStep[] = [
    {
      title: 'Account Deletion Warning',
      description:
        'You are about to permanently delete your account. This action cannot be undone.',
      warning:
        '⚠️ This will permanently delete ALL of your data including: analysis history, job roles, saved resumes, and account information.',
    },
    {
      title: 'Data Loss Confirmation',
      description:
        'Once deleted, your data cannot be recovered. All analysis results, job role tracking, and personal information will be permanently removed from our systems.',
      warning:
        '🚨 FINAL WARNING: This action is irreversible. Your account and all associated data will be permanently deleted.',
    },
    {
      title: 'Final Confirmation',
      description: `To proceed with permanent account deletion, please type '${CONFIRMATION_TEXT.DELETE_ACCOUNT}' in the field below. This confirms you understand that all your data will be permanently lost.`,
      warning:
        "💀 POINT OF NO RETURN: After clicking 'Delete My Account Forever', your account will be immediately and permanently deleted.",
    },
  ];

  return (
    <div className="min-h-screen bg-background">
      <Navbar />
      <main className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-12">
        <h1 className="text-3xl font-bold mb-8">Settings</h1>
        <div className="bg-card rounded-xl p-6 border border-border max-w-2xl">
          <div className="space-y-6">
            <div>
              <h3 className="text-lg font-semibold mb-2">
                Account Information
              </h3>
              <p className="text-sm text-muted-foreground mb-4">
                Email: {user?.email}
              </p>
            </div>
            <div>
              <h3 className="text-lg font-semibold mb-2">Change Password</h3>
              <div className="space-y-4">
                <div>
                  <Label htmlFor="current-password">Current Password</Label>
                  <Input
                    id="current-password"
                    type="password"
                    disabled
                    placeholder="••••••••"
                    className="mt-1"
                  />
                </div>
                <div>
                  <Label htmlFor="new-password">New Password</Label>
                  <Input
                    id="new-password"
                    type="password"
                    disabled
                    placeholder="••••••••"
                    className="mt-1"
                  />
                </div>
                <p className="text-sm text-muted-foreground">
                  Password changes are handled by the external authentication
                  provider logic
                </p>
              </div>
            </div>
            <div>
              <h3 className="text-lg font-semibold mb-2">Actions</h3>
              <div className="space-y-4">
                <Button onClick={signOut} variant="destructive">
                  Log Out
                </Button>
              </div>
            </div>
            <div className="border-2 border-destructive/20 rounded-lg p-4 bg-destructive/5">
              <h3 className="text-lg font-semibold mb-2 text-destructive flex items-center gap-2">
                <AlertTriangle className="h-5 w-5" />
                Danger Zone - Permanently Delete Account
              </h3>
              <div className="space-y-3 mb-4">
                <p className="text-sm text-destructive font-medium">
                  ⚠️ WARNING: This action is permanent and irreversible!
                </p>
                <p className="text-sm text-muted-foreground">
                  Deleting your account will permanently remove:
                </p>
                <ul className="text-sm text-muted-foreground ml-4 space-y-1">
                  <li>• All your resume analysis history</li>
                  <li>• All saved job roles and descriptions</li>
                  <li>• Your account profile and settings</li>
                  <li>• Any uploaded resume files</li>
                </ul>
                <p className="text-sm text-destructive font-medium">
                  This data cannot be recovered once deleted.
                </p>
              </div>
              <Button
                onClick={() =>
                  setSettingsState((prev) => ({
                    ...prev,
                    deleteAccountModalOpen: true,
                  }))
                }
                variant="destructive"
                className="bg-red-600 hover:bg-red-700 font-semibold"
                disabled={isLoading('deleteAccount')}
              >
                {isLoading('deleteAccount') ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin mr-2" />
                    Deleting Account...
                  </>
                ) : (
                  'Delete My Account Forever'
                )}
              </Button>
            </div>
          </div>
        </div>
      </main>

      <ConfirmationModal
        open={settingsState.deleteAccountModalOpen}
        onOpenChange={(open) =>
          setSettingsState((prev) => ({
            ...prev,
            deleteAccountModalOpen: open,
          }))
        }
        title="Permanently Delete Account"
        description="This will permanently delete your account and all associated data."
        confirmText="Delete My Account Forever"
        cancelText="Cancel"
        variant="destructive"
        loading={isLoading('deleteAccount')}
        onConfirm={deleteAccount}
        multiStep={true}
        requiresTextConfirmation={true}
        confirmationText={CONFIRMATION_TEXT.DELETE_ACCOUNT}
        steps={accountDeletionSteps}
      />
    </div>
  );
}
