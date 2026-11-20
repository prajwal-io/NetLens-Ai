import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from 'react';
import type { Session, User } from '@supabase/supabase-js';
import { supabase, supabaseConfigured } from './client';

interface AuthValue {
  configured: boolean;
  loading: boolean;
  session: Session | null;
  user: User | null;
  signIn(email: string, password: string): Promise<void>;
  requestEmailCode(email: string, createUser?: boolean): Promise<boolean>;
  verifyEmailCode(email: string, token: string): Promise<void>;
  signOut(): Promise<void>;
  sendPasswordReset(email: string): Promise<void>;
  updatePassword(password: string): Promise<void>;
}

const AuthContext = createContext<AuthValue | null>(null);

function configuredClient() {
  if (!supabase) throw new Error('Supabase Auth is not configured. Add the public project URL and publishable key to the frontend environment.');
  return supabase;
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<Session | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!supabase) { setLoading(false); return; }
    let active = true;
    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, nextSession) => {
      if (active) {
        setSession(nextSession);
        setLoading(false);
      }
    });
    return () => { active = false; subscription.unsubscribe(); };
  }, []);

  const value = useMemo<AuthValue>(() => ({
    configured: supabaseConfigured,
    loading,
    session,
    user: session?.user ?? null,
    async signIn(email, password) {
      const { error } = await configuredClient().auth.signInWithPassword({ email: email.trim(), password });
      if (error) throw error;
    },
    async requestEmailCode(email, createUser = false) {
      const { data, error } = await configuredClient().auth.signInWithOtp({
        email: email.trim(),
        options: { shouldCreateUser: createUser },
      });
      if (error) throw error;
      return Boolean(data.session);
    },
    async verifyEmailCode(email, token) {
      const { error } = await configuredClient().auth.verifyOtp({ email: email.trim(), token, type: 'email' });
      if (error) throw error;
    },
    async signOut() {
      const { error } = await configuredClient().auth.signOut();
      if (error) throw error;
    },
    async sendPasswordReset(email) {
      const { error } = await configuredClient().auth.resetPasswordForEmail(email.trim(), {
        redirectTo: `${window.location.origin}/auth/reset-password`,
      });
      if (error) throw error;
    },
    async updatePassword(password) {
      const { error } = await configuredClient().auth.updateUser({ password });
      if (error) throw error;
    },
  }), [loading, session]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const value = useContext(AuthContext);
  if (!value) throw new Error('useAuth must be used inside AuthProvider.');
  return value;
}

export async function getAccessToken() {
  if (!supabase) return null;
  const { data, error } = await supabase.auth.getSession();
  if (error) throw error;
  return data.session?.access_token ?? null;
}
