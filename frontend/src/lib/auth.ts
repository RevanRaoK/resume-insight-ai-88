/**
 * Dynamic JWT Authentication for SmartResume using Supabase Auth
 */
import { supabase } from '@/integrations/supabase/client';

export async function getAuthHeaders(): Promise<Record<string, string>> {
  const {
    data: { session },
  } = await supabase.auth.getSession();

  if (!session?.access_token) {
    throw new Error('No active session - user must be authenticated');
  }

  return {
    Authorization: `Bearer ${session.access_token}`,
    'Content-Type': 'application/json',
  };
}

export async function getAuthToken(): Promise<string> {
  const {
    data: { session },
  } = await supabase.auth.getSession();

  if (!session?.access_token) {
    throw new Error('No active session - user must be authenticated');
  }

  return session.access_token;
}

export async function getBearerToken(): Promise<string> {
  const {
    data: { session },
  } = await supabase.auth.getSession();

  if (!session?.access_token) {
    throw new Error('No active session - user must be authenticated');
  }

  return `Bearer ${session.access_token}`;
}
