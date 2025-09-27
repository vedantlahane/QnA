import { type ChangeEvent, type FormEvent, useMemo, useState } from 'react'
import { motion } from 'framer-motion'

import type { LoginPayload, RegisterPayload } from '../api'

const loginVariants = {
  hidden: { opacity: 0, y: 20 },
  visible: { opacity: 1, y: 0 },
}

const buttonVariants = {
  tap: { scale: 0.97 },
  hover: { scale: 1.03 },
}

type AuthPanelProps = {
  mode: 'login' | 'register'
  loading: boolean
  error: string | null
  onToggleMode: () => void
  onLogin: (payload: LoginPayload) => Promise<void>
  onRegister: (payload: RegisterPayload) => Promise<void>
}

export function AuthPanel({ mode, loading, error, onToggleMode, onLogin, onRegister }: AuthPanelProps) {
  const [formState, setFormState] = useState({
    username: '',
    email: '',
    password: '',
    first_name: '',
    last_name: '',
  })

  const isLogin = mode === 'login'

  const title = useMemo(() => (isLogin ? 'Welcome back' : 'Create an account'), [isLogin])
  const subtitle = useMemo(
    () => (isLogin ? 'Log in to continue exploring your documents.' : 'Sign up to build knowledge threads from your files.'),
    [isLogin],
  )

  const handleChange = (key: keyof typeof formState) => (event: ChangeEvent<HTMLInputElement>) => {
    const { value } = event.target
    setFormState((prev) => ({ ...prev, [key]: value }))
  }

  const inputClassName =
    'w-full rounded-xl border border-slate-500/30 bg-slate-900/70 px-4 py-3 text-base text-slate-100 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-sky-400/60 focus:border-sky-300/40 disabled:cursor-not-allowed disabled:opacity-60'
  const labelClassName = 'flex flex-col gap-2 text-sm font-medium text-slate-200/90'
  const cardClassName =
    'w-full max-w-md rounded-2xl border border-slate-400/20 bg-slate-900/70 p-10 backdrop-blur-xl shadow-lg shadow-sky-900/20 flex flex-col gap-7'

  const resetSensitiveFields = () => {
    setFormState((prev) => ({
      ...prev,
      password: '',
    }))
  }

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    const payload = { ...formState }
    try {
      if (isLogin) {
        const loginPayload: LoginPayload = {
          username: payload.username.trim(),
          password: payload.password,
        }
        await onLogin(loginPayload)
      } else {
        const registerPayload: RegisterPayload = {
          username: payload.username.trim(),
          email: payload.email.trim(),
          password: payload.password,
          first_name: payload.first_name.trim(),
          last_name: payload.last_name.trim(),
        }
        await onRegister(registerPayload)
      }
    } finally {
      resetSensitiveFields()
    }
  }

  return (
    <motion.section
      className={cardClassName}
      initial="hidden"
      animate="visible"
      variants={loginVariants}
      transition={{ duration: 0.6, ease: 'easeOut' }}
    >
      <h2 className="text-3xl font-semibold text-slate-50">{title}</h2>
      <p className="text-base text-slate-300/90">{subtitle}</p>
      <form onSubmit={handleSubmit} className="flex flex-col gap-5">
        <label className={labelClassName}>
          <span>Username</span>
          <input
            type="text"
            required
            autoComplete="username"
            value={formState.username}
            onChange={handleChange('username')}
            disabled={loading}
            className={inputClassName}
          />
        </label>

        {!isLogin && (
          <>
            <label className={labelClassName}>
              <span>Email</span>
              <input
                type="email"
                required
                autoComplete="email"
                value={formState.email}
                onChange={handleChange('email')}
                disabled={loading}
                className={inputClassName}
              />
            </label>
            <div className="grid gap-4 sm:grid-cols-2">
              <label className={labelClassName}>
                <span>First name</span>
                <input
                  type="text"
                  required
                  value={formState.first_name}
                  onChange={handleChange('first_name')}
                  disabled={loading}
                  className={inputClassName}
                />
              </label>
              <label className={labelClassName}>
                <span>Last name</span>
                <input
                  type="text"
                  required
                  value={formState.last_name}
                  onChange={handleChange('last_name')}
                  disabled={loading}
                  className={inputClassName}
                />
              </label>
            </div>
          </>
        )}

        <label className={labelClassName}>
          <span>Password</span>
          <input
            type="password"
            required
            autoComplete={isLogin ? 'current-password' : 'new-password'}
            value={formState.password}
            onChange={handleChange('password')}
            disabled={loading}
            className={inputClassName}
          />
        </label>

        {error && (
          <p className="rounded-lg border border-rose-400/40 bg-rose-500/15 px-4 py-2 text-sm text-rose-200">
            {error}
          </p>
        )}

        <motion.button
          type="submit"
          className="inline-flex items-center justify-center rounded-xl bg-gradient-to-br from-sky-400 to-indigo-500 px-5 py-3 text-sm font-semibold text-slate-950 shadow-lg shadow-sky-500/25 transition hover:from-sky-300 hover:to-indigo-400 focus:outline-none focus-visible:ring-2 focus-visible:ring-sky-400 disabled:cursor-wait disabled:opacity-60"
          whileHover="hover"
          whileTap="tap"
          variants={buttonVariants}
          disabled={loading}
        >
          {loading ? 'Please wait…' : isLogin ? 'Log in' : 'Create account'}
        </motion.button>
      </form>
      <button
        type="button"
        className="mt-2 inline-flex items-center gap-1 text-sm font-medium text-sky-200/90 transition hover:text-sky-100 disabled:cursor-not-allowed disabled:opacity-60"
        onClick={onToggleMode}
        disabled={loading}
      >
        {isLogin ? "Don't have an account?" : 'Already have an account?'}{' '}
        <span className="underline decoration-sky-200/70 underline-offset-4">{isLogin ? 'Sign up' : 'Log in'}</span>
      </button>
    </motion.section>
  )
}
