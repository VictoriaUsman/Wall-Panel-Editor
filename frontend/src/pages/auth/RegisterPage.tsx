import React, { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { authApi } from '../../api'
import { useAuthStore } from '../../stores/authStore'
import toast from 'react-hot-toast'

export function RegisterPage() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const { setAuth } = useAuthStore()
  const navigate = useNavigate()

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (password.length < 8) { toast.error('Password must be at least 8 characters'); return }
    setLoading(true)
    try {
      await authApi.register(email, password)
      const { data: user } = await authApi.me()
      setAuth(user, '')
      navigate('/dashboard')
    } catch (err: any) {
      const status = err.response?.status
      if (status === 400) {
        toast.error('An account with that email already exists')
      } else {
        toast.error('Registration failed. Please try again.')
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-wood-50">
      <div className="card p-8 w-full max-w-sm">
        <h1 className="text-2xl font-bold text-wood-700 mb-2">Create account</h1>
        <p className="text-sm text-gray-500 mb-6">Design your wall panel layout</p>
        <form onSubmit={submit} className="flex flex-col gap-4">
          <div>
            <label className="label">Email</label>
            <input className="input" type="email" value={email} onChange={e => setEmail(e.target.value)} required />
          </div>
          <div>
            <label className="label">Password</label>
            <input className="input" type="password" value={password} onChange={e => setPassword(e.target.value)} required minLength={8} />
          </div>
          <button className="btn-primary justify-center" disabled={loading}>
            {loading ? 'Creating account…' : 'Create account'}
          </button>
        </form>
        <p className="text-sm text-center text-gray-500 mt-4">
          Already have an account? <Link to="/login" className="text-wood-600 hover:underline">Sign in</Link>
        </p>
      </div>
    </div>
  )
}
