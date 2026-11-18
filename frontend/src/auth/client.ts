import { createClient } from '@supabase/supabase-js';

const env = (import.meta as ImportMeta & { env: Record<string, string | undefined> }).env;
export const supabaseUrl = env.VITE_SUPABASE_URL?.trim() ?? '';
export const supabasePublishableKey = env.VITE_SUPABASE_PUBLISHABLE_KEY?.trim() ?? '';
export const supabase = (() => {
  if (!supabaseUrl || !supabasePublishableKey) return null;
  try {
    return createClient(supabaseUrl, supabasePublishableKey, {
      auth: { autoRefreshToken: true, detectSessionInUrl: true, persistSession: true, flowType: 'pkce' },
    });
  } catch {
    return null;
  }
})();
export const supabaseConfigured = Boolean(supabase);
