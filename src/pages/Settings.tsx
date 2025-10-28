import { Navbar } from '@/components/Navbar';
import { Button } from '@/components/ui/button';
import { useAuth } from '@/contexts/AuthContext';

export default function Settings() {
  const { user, signOut } = useAuth();

  return (
    <div className="min-h-screen bg-background">
      <Navbar />
      <main className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-12">
        <h1 className="text-3xl font-bold mb-8">Settings</h1>
        <div className="bg-card rounded-xl p-6 border border-border max-w-2xl">
          <div className="space-y-6">
            <div>
              <h3 className="text-lg font-semibold mb-2">Account Information</h3>
              <p className="text-sm text-muted-foreground mb-4">
                Email: {user?.email}
              </p>
            </div>
            <div>
              <h3 className="text-lg font-semibold mb-2">Actions</h3>
              <Button onClick={signOut} variant="destructive">
                Log Out
              </Button>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
