import { useEffect, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { settingsApi } from '../services/api'

export default function OAuthCallback() {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const [status, setStatus] = useState<'processing' | 'success' | 'error'>('processing')
  const [message, setMessage] = useState('')

  useEffect(() => {
    const code = searchParams.get('code')
    const state = searchParams.get('state')
    const error = searchParams.get('error')

    if (error) {
      setStatus('error')
      setMessage('Authentication failed. Please try again.')
      setTimeout(() => navigate('/settings'), 3000)
      return
    }

    if (!code || !state) {
      setStatus('error')
      setMessage('Missing authorization code. Please try again.')
      setTimeout(() => navigate('/settings'), 3000)
      return
    }

    const completeOAuth = async () => {
      try {
        const redirectUri = `${window.location.origin}/settings/oauth/callback`
        await settingsApi.completeGoogleCalendarOAuth(code, state, redirectUri)
        setStatus('success')
        setMessage('Google Calendar connected successfully!')
        setTimeout(() => navigate('/settings?connected=true'), 2000)
      } catch (err) {
        setStatus('error')
        setMessage(err instanceof Error ? err.message : 'Failed to connect Google Calendar. Please try again.')
        setTimeout(() => navigate('/settings'), 3000)
      }
    }

    completeOAuth()
  }, [searchParams, navigate])

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="max-w-md w-full space-y-4 text-center">
        {status === 'processing' && (
          <>
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600 mx-auto"></div>
            <p className="text-gray-600">Completing Google Calendar connection...</p>
          </>
        )}
        {status === 'success' && (
          <>
            <div className="rounded-full h-12 w-12 bg-green-100 mx-auto flex items-center justify-center">
              <svg className="h-6 w-6 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
            </div>
            <p className="text-gray-900 font-medium">Connection successful!</p>
            <p className="text-gray-600">{message}</p>
          </>
        )}
        {status === 'error' && (
          <>
            <div className="rounded-full h-12 w-12 bg-red-100 mx-auto flex items-center justify-center">
              <svg className="h-6 w-6 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </div>
            <p className="text-gray-900 font-medium">Connection failed</p>
            <p className="text-gray-600">{message}</p>
          </>
        )}
      </div>
    </div>
  )
}

