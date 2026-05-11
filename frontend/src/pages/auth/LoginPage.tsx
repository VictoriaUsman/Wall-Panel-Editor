import React, { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { authApi } from '../../api'
import { useAuthStore } from '../../stores/authStore'
import toast from 'react-hot-toast'

export function LoginPage() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const { setAuth } = useAuthStore()
  const navigate = useNavigate()

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    try {
      await authApi.login(email, password)
      const { data: user } = await authApi.me()
      setAuth(user, '')
      navigate(user.is_operator ? '/operator' : '/dashboard')
    } catch (err: any) {
      const status = err.response?.status
      if (status === 401 || status === 404) {
        toast.error('Invalid email or password')
      } else {
        toast.error('Something went wrong. Please try again.')
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-wood-50">
      <div className="card p-8 w-full max-w-sm">
        <h1 className="text-2xl font-bold text-wood-700 mb-2">Wood Panel Designer</h1>
        <p className="text-sm text-gray-500 mb-6">Sign in to your account</p>
        <form onSubmit={submit} className="flex flex-col gap-4">
          <div>
            <label className="label">Email</label>
            <input className="input" type="email" value={email} onChange={e => setEmail(e.target.value)} required />
          </div>
          <div>
            <label className="label">Password</label>
            <input className="input" type="password" value={password} onChange={e => setPassword(e.target.value)} required />
          </div>
          <button className="btn-primary justify-center" disabled={loading}>
            {loading ? 'Signing in…' : 'Sign in'}
          </button>
        </form>
        <p className="text-sm text-center text-gray-500 mt-4">
          No account? <Link to="/register" className="text-wood-600 hover:underline">Register</Link>
        </p>
      </div>
    </div>
  )
}
