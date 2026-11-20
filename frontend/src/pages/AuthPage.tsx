import { useEffect, useState, type FormEvent, type ReactNode } from 'react';
import { Link, Navigate, useLocation, useNavigate, useParams } from 'react-router-dom';
import { ArrowLeft, ArrowRight, LockKeyhole, ShieldCheck } from 'lucide-react';
import { useAuth } from '../auth/AuthContext';

type Mode = 'login' | 'signup' | 'forgot-password' | 'reset-password' | 'callback';

function authErrorMessage(reason: unknown, fallback: string) {
  const message = reason instanceof Error ? reason.message : '';
  return /failed to fetch|networkerror|load failed/i.test(message)
    ? 'Could not reach Supabase Auth. Check your connection and project URL, then retry.'
    : message || fallback;
}

export default function AuthPage() {
  const location = useLocation();
  const { mode: routeMode } = useParams();
  const mode = (routeMode || location.pathname.split('/').pop() || 'login') as Mode;
  const auth = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [token, setToken] = useState('');
  const [codeRequested, setCodeRequested] = useState(false);
  const [passwordMode, setPasswordMode] = useState(false);
  const [password, setPassword] = useState('');
  const [notice, setNotice] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (mode === 'callback' && !auth.loading) {
      if (auth.user) navigate('/command-center', { replace: true });
      else { setError('The sign-in link could not be verified. Request a new code and try again.'); navigate('/auth/login', { replace: true }); }
    }
  }, [auth.loading, auth.user, mode, navigate]);

  if (!['login', 'signup', 'forgot-password', 'reset-password', 'callback'].includes(mode)) return <Navigate to="/auth/login" replace />;
  if (auth.loading || mode === 'callback') return <main id="main-content" className="auth-loading" role="status">Verifying secure session...</main>;
  if (mode === 'reset-password' && !auth.session) {
    return <AuthFrame><p className="auth-eyebrow">Password recovery</p><h1>Open your recovery link</h1><p className="auth-copy">This page needs a valid Supabase recovery session. Request a fresh link if this one has expired.</p>{error && <p className="auth-error" role="alert">{error}</p>}<Link className="auth-primary" to="/auth/login">Return to sign in <ArrowRight size={16}/></Link></AuthFrame>;
  }
  if (mode === 'login' && auth.user) return <Navigate to="/command-center" replace />;

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true); setError(''); setNotice('');
    try {
      if (mode === 'login' && passwordMode) {
        await auth.signIn(email, password);
        const from = (location.state as { from?: string } | null)?.from;
        navigate(from?.startsWith('/') ? from : '/command-center', { replace: true });
      } else if ((mode === 'login' || mode === 'signup') && !codeRequested) {
        const hasSession = await auth.requestEmailCode(email, mode === 'signup');
        if (hasSession) {
          const from = (location.state as { from?: string } | null)?.from;
          navigate(from?.startsWith('/') ? from : '/command-center', { replace: true });
        } else {
          setCodeRequested(true);
          setNotice(`If this address can ${mode === 'signup' ? 'create an account' : 'sign in'}, Supabase sent a one-time code. Check your inbox and spam folder.`);
        }
      } else if ((mode === 'login' || mode === 'signup') && codeRequested) {
        await auth.verifyEmailCode(email, token);
        const from = (location.state as { from?: string } | null)?.from;
        navigate(from?.startsWith('/') ? from : '/command-center', { replace: true });
      } else if (mode === 'forgot-password') {
        await auth.sendPasswordReset(email);
        setNotice('If the account exists, Supabase sent a password recovery email to this address.');
      } else {
        await auth.updatePassword(password);
        setNotice('Password updated. Your account is ready to use.');
        window.setTimeout(() => navigate('/command-center', { replace: true }), 900);
      }
    } catch (reason) {
      setError(authErrorMessage(reason, 'Authentication could not be completed. Try again.'));
    } finally { setBusy(false); }
  }

  const title = mode === 'signup' ? 'Create your analyst account'
    : mode === 'forgot-password' ? 'Reset your password'
      : mode === 'reset-password' ? 'Choose a new password' : 'Sign in to NetLens AI';
  const submitLabel = mode === 'signup' ? 'Create account'
    : mode === 'forgot-password' ? 'Send recovery email'
      : mode === 'reset-password' ? 'Update password' : 'Sign in';
  const emailMode = mode === 'signup' || (mode === 'login' && !passwordMode);

  return <AuthFrame>
    <p className="auth-eyebrow"><ShieldCheck size={15}/> Secure analyst access</p>
    <h1>{title}</h1>
    <p className="auth-copy">Your analyses and investigation history stay private to your account.</p>
    {!auth.configured && <div className="auth-error" role="alert">Supabase Auth is unavailable. Check that <code>VITE_SUPABASE_URL</code> and <code>VITE_SUPABASE_PUBLISHABLE_KEY</code> are set correctly, then restart the frontend.</div>}
    <form className="auth-form" onSubmit={submit}>
      {(emailMode || (mode === 'login' && passwordMode) || mode === 'forgot-password') && <label>Email address<input type="email" autoComplete="email" required value={email} onChange={event => setEmail(event.target.value)} disabled={!auth.configured || busy || codeRequested}/></label>}
      {emailMode && codeRequested && <>
        <label>One-time code from your email<input type="password" inputMode="numeric" autoComplete="one-time-code" pattern="[0-9]{6}" minLength={6} maxLength={6} required value={token} onChange={event => setToken(event.target.value.replace(/\D/g, '').slice(0, 6))} disabled={busy} aria-describedby="otp-help"/></label>
        <small id="otp-help">Enter the six-digit code from your email. The code is never displayed in this app.</small>
      </>}
      {(mode === 'reset-password' || (mode === 'login' && passwordMode)) && <label>{mode === 'reset-password' ? 'New password' : 'Password'}<input type="password" autoComplete={mode === 'reset-password' ? 'new-password' : 'current-password'} minLength={8} required value={password} onChange={event => setPassword(event.target.value)} disabled={busy}/></label>}
      {notice && <p className="auth-success" role="status">{notice}</p>}
      {error && <p className="auth-error" role="alert">{error}</p>}
      <button className="auth-primary" type="submit" disabled={!auth.configured || busy || (emailMode && codeRequested && token.length !== 6)}>{busy ? 'Please wait...' : emailMode && codeRequested ? 'Verify code and sign in' : submitLabel}<ArrowRight size={16}/></button>
    </form>
    <div className="auth-links">
      {emailMode && codeRequested && <button type="button" className="auth-text-button" disabled={busy} onClick={() => { setCodeRequested(false); setToken(''); setNotice(''); setError(''); }}>Use a different email</button>}
      {mode === 'login' && !codeRequested && (passwordMode
        ? <button type="button" className="auth-text-button" onClick={() => { setPasswordMode(false); setPassword(''); setError(''); }}>Use an email code instead</button>
        : <><button type="button" className="auth-text-button" onClick={() => { setPasswordMode(true); setError(''); }}>Use password instead</button><Link to="/auth/forgot-password">Trouble signing in?</Link><span>New to NetLens? <Link to="/auth/signup">Create account</Link></span></>)}
      {emailMode && !codeRequested && mode === 'signup' && <span>Already have an account? <Link to="/auth/login">Sign in</Link></span>}
      {mode === 'forgot-password' && <span>Remembered it? <Link to="/auth/login">Return to sign in</Link></span>}
      {mode === 'reset-password' && <span><LockKeyhole size={14}/> Use at least 8 characters.</span>}
    </div>
    {emailMode && codeRequested && <button type="button" className="auth-resend" disabled={busy} onClick={() => { setBusy(true); setToken(''); setError(''); void auth.requestEmailCode(email, mode === 'signup').then(hasSession => { if (hasSession) navigate('/command-center', { replace: true }); else setNotice('A new code was requested. Check your email.'); }).catch(reason => setError(authErrorMessage(reason, 'The code could not be resent.'))).finally(() => setBusy(false)); }}>Resend code</button>}
    {emailMode && !codeRequested && <p className="auth-email-note">No code arrived? Supabase's built-in sender may restrict delivery; configure custom SMTP for this project.</p>}
    <Link className="auth-back" to="/"><ArrowLeft size={15}/> Back to NetLens AI</Link>
  </AuthFrame>;
}

function AuthFrame({ children }: { children: ReactNode }) {
  return <main id="main-content" className="auth-page"><Link to="/" className="auth-brand"><img src="/netsight-ai-logo.png" alt="NetSight AI" width="180" height="50"/><span>Network intelligence, made clear.</span></Link><section className="auth-panel">{children}</section><p className="auth-footnote">Access is verified by Supabase Auth. Network analysis records are scoped to your user ID.</p></main>;
}
