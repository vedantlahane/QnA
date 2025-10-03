import { useCallback, useState } from 'react'
import { api, type LoginPayload, type RegisterPayload } from '../api'
import type { User } from '../types'

const TOKEN_STORAGE_KEY = 'qna_auth_token'

export function useAuth() {
  const [token, setToken] = useState<string | null>(() => localStorage.getItem(TOKEN_STORAGE_KEY))
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const persistToken = useCallback((value: string | null) => {
    if (value) {
      localStorage.setItem(TOKEN_STORAGE_KEY, value)
    } else {
      localStorage.removeItem(TOKEN_STORAGE_KEY)
    }
    setToken(value)
  }, [])

  const resetSession = useCallback(() => {
    setUser(null)
    setToken(null)
    localStorage.removeItem(TOKEN_STORAGE_KEY)
  }, [])

  const login = useCallback(async (payload: LoginPayload) => {
    setLoading(true)
    setError(null)
    try {
      const response = await api.login(payload)
      persistToken(response.token)
      setUser(response.user)
    } catch (err) {
      if (err instanceof Error) {
        setError(err.message)
      } else {
        setError('Login failed. Please try again.')
      }
      throw err
    } finally {
      setLoading(false)
    }
  }, [persistToken])

  const register = useCallback(async (payload: RegisterPayload) => {
    setLoading(true)
    setError(null)
    try {
      const response = await api.register(payload)
      persistToken(response.token)
      setUser(response.user)
    } catch (err) {
      if (err instanceof Error) {
        setError(err.message)
      } else {
        setError('Registration failed. Please try again.')
      }
      throw err
    } finally {
      setLoading(false)
    }
  }, [persistToken])

  const logout = useCallback(async () => {
    if (!token) {
      resetSession()
      return
    }
    try {
      await api.logout(token)
    } catch (err) {
      console.warn('Logout error', err)
    } finally {
      resetSession()
    }
  }, [token, resetSession])

  const loadProfile = useCallback(async (authToken: string) => {
    const profile = await api.profile(authToken)
    setUser(profile)
    return profile
  }, [])

  return {
    token,
    user,
    loading,
    error,
    login,
    register,
    logout,
    loadProfile,
    resetSession,
  }
}