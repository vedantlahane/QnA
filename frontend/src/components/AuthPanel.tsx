import { type ChangeEvent, type FormEvent, useMemo, useState } from 'react'

import { Button } from './ui/Button'
import { Input } from './ui/Input'
import { Card } from './ui/Card'
import type { LoginPayload, RegisterPayload } from '../api'

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
    <Card className="w-full max-w-md p-10 flex flex-col gap-7">
      <h2 className="text-3xl font-semibold text-slate-50">{title}</h2>
      <p className="text-base text-slate-300/90">{subtitle}</p>
      <form onSubmit={handleSubmit} className="flex flex-col gap-5">
        <Input
          label="Username"
          type="text"
          required
          autoComplete="username"
          value={formState.username}
          onChange={handleChange('username')}
          disabled={loading}
        />

        {!isLogin && (
          <>
            <Input
              label="Email"
              type="email"
              required
              autoComplete="email"
              value={formState.email}
              onChange={handleChange('email')}
              disabled={loading}
            />
            <div className="grid gap-4 sm:grid-cols-2">
              <Input
                label="First name"
                type="text"
                required
                value={formState.first_name}
                onChange={handleChange('first_name')}
                disabled={loading}
              />
              <Input
                label="Last name"
                type="text"
                required
                value={formState.last_name}
                onChange={handleChange('last_name')}
                disabled={loading}
              />
            </div>
          </>
        )}

        <Input
          label="Password"
          type="password"
          required
          autoComplete={isLogin ? 'current-password' : 'new-password'}
          value={formState.password}
          onChange={handleChange('password')}
          disabled={loading}
        />

        {error && (
          <p className="rounded-lg border border-rose-400/40 bg-rose-500/15 px-4 py-2 text-sm text-rose-200">
            {error}
          </p>
        )}

        <Button
          type="submit"
          disabled={loading}
          loading={loading}
          className="w-full"
        >
          {loading ? 'Please wait…' : isLogin ? 'Log in' : 'Create account'}
        </Button>
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
    </Card>
  )
}
