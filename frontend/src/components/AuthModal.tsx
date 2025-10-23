import { AnimatePresence, motion } from 'framer-motion';
import { useEffect, useMemo, useState } from 'react';

import type {
  ConfirmPasswordResetPayload,
  SignInPayload,
  SignUpPayload,
} from '../services/chatApi';

type AuthView = 'signin' | 'signup' | 'reset-request' | 'reset-confirm';

interface AuthModalProps {
  isOpen: boolean;
  mode: 'signin' | 'signup';
  onClose: () => void;
  onModeChange: (mode: 'signin' | 'signup') => void;
  onSignIn: (payload: SignInPayload) => Promise<void>;
  onSignUp: (payload: SignUpPayload) => Promise<void>;
  onRequestPasswordReset: (email: string) => Promise<string | null>;
  onConfirmPasswordReset: (payload: ConfirmPasswordResetPayload) => Promise<void>;
  isSubmitting: boolean;
  errorMessage?: string | null;
  successMessage?: string | null;
}

interface FormState {
  name: string;
  email: string;
  password: string;
  confirmPassword: string;
  resetToken: string;
}

interface FormErrors {
  email?: string;
  password?: string;
  confirmPassword?: string;
  name?: string;
  resetToken?: string;
}

const PASSWORD_MIN_LENGTH = 8;

const emptyForm: FormState = {
  name: '',
  email: '',
  password: '',
  confirmPassword: '',
  resetToken: '',
};

const AuthModal = ({
  isOpen,
  mode,
  onClose,
  onModeChange,
  onSignIn,
  onSignUp,
  onRequestPasswordReset,
  onConfirmPasswordReset,
  isSubmitting,
  errorMessage,
  successMessage,
}: AuthModalProps) => {
  const [view, setView] = useState<AuthView>(mode);
  const [form, setForm] = useState<FormState>(emptyForm);
  const [formErrors, setFormErrors] = useState<FormErrors>({});
  const [resetEmail, setResetEmail] = useState<string>('');

  useEffect(() => {
    if (isOpen) {
      setView(mode);
      setForm(emptyForm);
      setFormErrors({});
      setResetEmail('');
    }
  }, [isOpen, mode]);

  const heading = useMemo(() => {
    switch (view) {
      case 'signup':
        return 'Create your account';
      case 'reset-request':
        return 'Reset your password';
      case 'reset-confirm':
        return 'Choose a new password';
      case 'signin':
      default:
        return 'Welcome back';
    }
  }, [view]);

  const subheading = useMemo(() => {
    switch (view) {
      case 'signup':
        return 'Sign up with your email to get started.';
      case 'reset-request':
        return 'Enter your email and we will send a reset code.';
      case 'reset-confirm':
        return resetEmail
          ? `Enter the reset code for ${resetEmail} and set a new password.`
          : 'Enter your reset code and pick a new password.';
      case 'signin':
      default:
        return 'Sign in with your email to continue.';
    }
  }, [view, resetEmail]);

  const primaryButtonLabel = useMemo(() => {
    switch (view) {
      case 'signup':
        return 'Create account';
      case 'reset-request':
        return 'Send reset code';
      case 'reset-confirm':
        return 'Update password';
      case 'signin':
      default:
        return 'Sign in';
    }
  }, [view]);

  const validate = () => {
    const errors: FormErrors = {};

    const shouldValidateEmail = view === 'signin' || view === 'signup' || view === 'reset-request';
    if (shouldValidateEmail) {
      if (!form.email.trim()) {
        errors.email = 'Email is required.';
      } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email.trim())) {
        errors.email = 'Enter a valid email address.';
      }
    }

    if (view === 'signin' || view === 'signup') {
      if (!form.password) {
        errors.password = 'Password is required.';
      } else if (form.password.length < PASSWORD_MIN_LENGTH) {
        errors.password = `Password must be at least ${PASSWORD_MIN_LENGTH} characters.`;
      }
    }

    if (view === 'signup' && !form.name.trim()) {
      errors.name = 'Name is required.';
    }

    if (view === 'reset-confirm') {
      if (!form.resetToken.trim()) {
        errors.resetToken = 'Reset code is required.';
      }

      if (!form.password) {
        errors.password = 'New password is required.';
      } else if (form.password.length < PASSWORD_MIN_LENGTH) {
        errors.password = `Password must be at least ${PASSWORD_MIN_LENGTH} characters.`;
      }

      if (!form.confirmPassword) {
        errors.confirmPassword = 'Please confirm your new password.';
      } else if (form.confirmPassword !== form.password) {
        errors.confirmPassword = 'Passwords do not match.';
      }
    }

    setFormErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    if (!validate()) {
      return;
    }

    try {
      if (view === 'signup') {
        await onSignUp({
          name: form.name.trim(),
          email: form.email.trim(),
          password: form.password,
        });
      } else if (view === 'signin') {
        await onSignIn({
          email: form.email.trim(),
          password: form.password,
        });
      } else if (view === 'reset-request') {
        const token = await onRequestPasswordReset(form.email.trim());
        setResetEmail(form.email.trim());
        setForm({
          ...emptyForm,
          email: form.email.trim(),
          resetToken: token ?? '',
        });
        setFormErrors({});
        setView('reset-confirm');
      } else if (view === 'reset-confirm') {
        await onConfirmPasswordReset({
          token: form.resetToken.trim(),
          password: form.password,
        });
        setForm(emptyForm);
        setFormErrors({});
        setView('signin');
      }
    } catch (error) {
      console.error('Authentication error', error);
    }
  };

  const switchToResetRequest = () => {
    setView('reset-request');
    setForm((prev) => ({ ...emptyForm, email: prev.email }));
    setFormErrors({});
    setResetEmail('');
  };

  const switchToSignIn = () => {
    onModeChange('signin');
    setView('signin');
    setForm(emptyForm);
    setFormErrors({});
  };

  const switchToSignUp = () => {
    onModeChange('signup');
    setView('signup');
    setForm(emptyForm);
    setFormErrors({});
  };

  if (!isOpen) {
    return null;
  }

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/60"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          role="dialog"
          aria-modal="true"
        >
          <motion.div
            className="w-full max-w-md rounded-2xl bg-slate-900/95 p-8 shadow-xl backdrop-blur"
            initial={{ scale: 0.95, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            exit={{ scale: 0.95, opacity: 0 }}
          >
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-xl font-semibold text-white">{heading}</h2>
                <p className="mt-1 text-sm text-slate-300">{subheading}</p>
                {successMessage && (
                  <p className="mt-2 text-xs text-emerald-300">{successMessage}</p>
                )}
              </div>
              <button
                type="button"
                className="rounded-full p-2 text-slate-300 transition hover:bg-slate-800 hover:text-white"
                onClick={onClose}
                aria-label="Close authentication"
              >
                ×
              </button>
            </div>

            <form className="mt-6 space-y-4" onSubmit={handleSubmit}>
              {view === 'signup' && (
                <div>
                  <label className="text-sm font-medium text-slate-200" htmlFor="auth-name">
                    Name
                  </label>
                  <input
                    id="auth-name"
                    type="text"
                    autoComplete="name"
                    className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-white focus:border-indigo-400 focus:outline-none"
                    value={form.name}
                    onChange={(event) => setForm((prev) => ({ ...prev, name: event.target.value }))}
                    disabled={isSubmitting}
                  />
                  {formErrors.name && <p className="mt-1 text-xs text-rose-400">{formErrors.name}</p>}
                </div>
              )}

              {view !== 'reset-confirm' && (
                <div>
                  <label className="text-sm font-medium text-slate-200" htmlFor="auth-email">
                    Email
                  </label>
                  <input
                    id="auth-email"
                    type="email"
                    autoComplete="email"
                    className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-white focus:border-indigo-400 focus:outline-none"
                    value={form.email}
                    onChange={(event) => setForm((prev) => ({ ...prev, email: event.target.value }))}
                    disabled={isSubmitting}
                  />
                  {formErrors.email && <p className="mt-1 text-xs text-rose-400">{formErrors.email}</p>}
                </div>
              )}

              {(view === 'signin' || view === 'signup') && (
                <div>
                  <label className="text-sm font-medium text-slate-200" htmlFor="auth-password">
                    Password
                  </label>
                  <input
                    id="auth-password"
                    type="password"
                    autoComplete={view === 'signup' ? 'new-password' : 'current-password'}
                    className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-white focus:border-indigo-400 focus:outline-none"
                    value={form.password}
                    onChange={(event) => setForm((prev) => ({ ...prev, password: event.target.value }))}
                    disabled={isSubmitting}
                  />
                  {formErrors.password && <p className="mt-1 text-xs text-rose-400">{formErrors.password}</p>}
                </div>
              )}

              {view === 'reset-request' && (
                <p className="text-xs text-slate-400">
                  We will generate a reset code for your account. In production this would be emailed to you.
                </p>
              )}

              {view === 'reset-confirm' && (
                <>
                  <div>
                    <label className="text-sm font-medium text-slate-200" htmlFor="auth-reset-token">
                      Reset code
                    </label>
                    <input
                      id="auth-reset-token"
                      type="text"
                      className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-white focus:border-indigo-400 focus:outline-none"
                      value={form.resetToken}
                      onChange={(event) => setForm((prev) => ({ ...prev, resetToken: event.target.value }))}
                      disabled={isSubmitting}
                    />
                    {formErrors.resetToken && <p className="mt-1 text-xs text-rose-400">{formErrors.resetToken}</p>}
                  </div>

                  <div>
                    <label className="text-sm font-medium text-slate-200" htmlFor="auth-new-password">
                      New password
                    </label>
                    <input
                      id="auth-new-password"
                      type="password"
                      autoComplete="new-password"
                      className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-white focus:border-indigo-400 focus:outline-none"
                      value={form.password}
                      onChange={(event) => setForm((prev) => ({ ...prev, password: event.target.value }))}
                      disabled={isSubmitting}
                    />
                    {formErrors.password && <p className="mt-1 text-xs text-rose-400">{formErrors.password}</p>}
                  </div>

                  <div>
                    <label className="text-sm font-medium text-slate-200" htmlFor="auth-confirm-password">
                      Confirm password
                    </label>
                    <input
                      id="auth-confirm-password"
                      type="password"
                      autoComplete="new-password"
                      className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-white focus:border-indigo-400 focus:outline-none"
                      value={form.confirmPassword}
                      onChange={(event) => setForm((prev) => ({ ...prev, confirmPassword: event.target.value }))}
                      disabled={isSubmitting}
                    />
                    {formErrors.confirmPassword && (
                      <p className="mt-1 text-xs text-rose-400">{formErrors.confirmPassword}</p>
                    )}
                  </div>
                </>
              )}

              {view === 'signin' && (
                <button
                  type="button"
                  className="text-xs font-medium text-indigo-300 transition hover:text-indigo-200"
                  onClick={switchToResetRequest}
                  disabled={isSubmitting}
                >
                  Forgot password?
                </button>
              )}

              {errorMessage && <p className="text-sm text-rose-300">{errorMessage}</p>}

              <button
                type="submit"
                className="flex w-full items-center justify-center rounded-lg bg-indigo-500 px-4 py-2 text-sm font-medium text-white transition hover:bg-indigo-400 disabled:cursor-not-allowed disabled:opacity-60"
                disabled={isSubmitting}
              >
                {isSubmitting ? 'Processing…' : primaryButtonLabel}
              </button>
            </form>

            <div className="mt-6 text-center text-sm text-slate-300">
              {view === 'signup' ? (
                <button
                  type="button"
                  className="font-medium text-indigo-300 transition hover:text-indigo-200"
                  onClick={switchToSignIn}
                  disabled={isSubmitting}
                >
                  Already have an account? Sign in instead
                </button>
              ) : view === 'signin' ? (
                <button
                  type="button"
                  className="font-medium text-indigo-300 transition hover:text-indigo-200"
                  onClick={switchToSignUp}
                  disabled={isSubmitting}
                >
                  Need an account? Create one
                </button>
              ) : (
                <button
                  type="button"
                  className="font-medium text-indigo-300 transition hover:text-indigo-200"
                  onClick={switchToSignIn}
                  disabled={isSubmitting}
                >
                  Back to sign in
                </button>
              )}
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
};

export default AuthModal;
