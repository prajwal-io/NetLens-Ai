import { useEffect, useState, type FormEvent, type ReactNode } from 'react';
import { Link, Navigate, useLocation, useNavigate, useParams } from 'react-router-dom';
import { ArrowLeft, ArrowRight, LockKeyhole, ShieldCheck } from 'lucide-react';
import { useAuth } from '../auth/AuthContext';

type Mode = 'login' | 'signup' | 'forgot-password' | 'reset-password' | 'callback';

export default function AuthPage() {
  const location = useLocation();
  const { mode: routeMode } = useParams();
  const mode = (routeMode || location.pathname.split('/').pop() || 'login') as Mode;
  const auth = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [notice, setNotice] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (mode === 'callback' && !auth.loading) {
      if (auth.user) navigate('/command-center', { replace: true });
      else { setError('The sign-in link could not be verified. Request a new link and try again.'); navigate('/auth/login', { replace: true }); }
    }
  }, [auth.loading, auth.user, mode, navigate]);

  if (!['login', 'signup', 'forgot-password', 'reset-password', 'callback'].includes(mode)) {
    return <Navigate to="/auth/login" replace />;
  }
  if (auth.loading || mode === 'callback') return <main id="main-content" className="auth-loading" role="status">Verifying secure session…</main>;
  if (mode === 'reset-password' && !auth.session) {
    return <AuthFrame>
      <p className="auth-eyebrow">Password recovery</p><h1>Open your recovery link</h1>
      <p className="auth-copy">This page needs a valid Supabase recovery session. Request a fresh link if this one has expired.</p>
      {error && <p className="auth-error" role="alert">{error}</p>}
      <Link className="auth-primary" to="/auth/forgot-password">Request a new link <ArrowRight size={16}/></Link>
    </AuthFrame>;
  }

  if (mode === 'login' && auth.user) return <Navigate to="/command-center" replace />;

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true); setError(''); setNotice('');
    try {
      if (mode === 'login') {
        await auth.signIn(email, password);
        const from = (location.state as { from?: string } | null)?.from;
        navigate(from?.startsWith('/') ? from : '/command-center', { replace: true });
      } else if (mode === 'signup') {
        const hasSession = await auth.signUp(email, password);
        if (hasSession) navigate('/command-center', { replace: true });
        else setNotice('Check your email for the confirmation link, then return here to sign in.');
      } else if (mode === 'forgot-password') {
        await auth.sendPasswordReset(email);
        setNotice('If the account exists, Supabase sent a password reset link to this address.');
      } else {
        await auth.updatePassword(password);
        setNotice('Password updated. Your account is ready to use.');
        window.setTimeout(() => navigate('/command-center', { replace: true }), 900);
      }
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Authentication could not be completed. Try again.');
    } finally { setBusy(false); }
  }

  const title = mode === 'signup' ? 'Create your analyst account'
    : mode === 'forgot-password' ? 'Reset your password'
      : mode === 'reset-password' ? 'Choose a new password' : 'Sign in to NetLens AI';
  const submitLabel = mode === 'signup' ? 'Create account'
    : mode === 'forgot-password' ? 'Send reset link'
      : mode === 'reset-password' ? 'Update password' : 'Sign in';

  return <AuthFrame>
    <p className="auth-eyebrow"><ShieldCheck size={15}/> Secure analyst access</p>
    <h1>{title}</h1>
    <p className="auth-copy">Your analyses and investigation history stay private to your account.</p>
    {!auth.configured && <div className="auth-error" role="alert">Supabase Auth is unavailable. Check that <code>VITE_SUPABASE_URL</code> and <code>VITE_SUPABASE_PUBLISHABLE_KEY</code> are set correctly, then restart the frontend.</div>}
    <form className="auth-form" onSubmit={submit}>
      {mode !== 'reset-password' && <label>Email address<input type="email" autoComplete="email" required value={email} onChange={event => setEmail(event.target.value)} disabled={!auth.configured || busy}/></label>}
      {(mode === 'login' || mode === 'signup' || mode === 'reset-password') && <label>{mode === 'reset-password' ? 'New password' : 'Password'}<input type="password" autoComplete={mode === 'login' ? 'current-password' : 'new-password'} minLength={8} required value={password} onChange={event => setPassword(event.target.value)} disabled={!auth.configured || busy}/></label>}
      {notice && <p className="auth-success" role="status">{notice}</p>}
      {error && <p className="auth-error" role="alert">{error}</p>}
      <button className="auth-primary" type="submit" disabled={!auth.configured || busy}>{busy ? 'Please wait…' : submitLabel}<ArrowRight size={16}/></button>
    </form>
    <div className="auth-links">
      {mode === 'login' && <><Link to="/auth/forgot-password">Forgot password?</Link><span>New to NetLens? <Link to="/auth/signup">Create account</Link></span></>}
      {mode === 'signup' && <span>Already have an account? <Link to="/auth/login">Sign in</Link></span>}
      {mode === 'forgot-password' && <span>Remembered it? <Link to="/auth/login">Return to sign in</Link></span>}
      {mode === 'reset-password' && <span><LockKeyhole size={14}/> Use at least 8 characters.</span>}
    </div>
    <Link className="auth-back" to="/"><ArrowLeft size={15}/> Back to NetLens AI</Link>
  </AuthFrame>;
}

function AuthFrame({ children }: { children: ReactNode }) {
  return <main id="main-content" className="auth-page"><Link to="/" className="auth-brand"><img src="/netsight-ai-logo.png" alt="NetSight AI" width="180" height="50"/><span>Network intelligence, made clear.</span></Link><section className="auth-panel">{children}</section><p className="auth-footnote">Access is verified by Supabase Auth. Network analysis records are scoped to your user ID.</p></main>;
}
