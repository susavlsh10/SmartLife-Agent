import { useState, useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
import { settingsApi, GoogleCalendarStatus, UserPreferences, TimePreference } from '../services/api'

export default function Settings() {
  const [searchParams, setSearchParams] = useSearchParams()
  const [activeTab, setActiveTab] = useState<'calendar' | 'preferences' | 'password'>('calendar')
  const [calendarStatus, setCalendarStatus] = useState<GoogleCalendarStatus | null>(null)
  const [preferences, setPreferences] = useState<UserPreferences | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')

  // Password form state
  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')

  useEffect(() => {
    loadCalendarStatus()
    loadPreferences()
    
    // Check for OAuth callback success
    if (searchParams.get('connected') === 'true') {
      setSuccess('Google Calendar connected successfully!')
      setSearchParams({}, { replace: true })
      loadCalendarStatus()
    }
  }, [searchParams, setSearchParams])

  const loadCalendarStatus = async () => {
    try {
      const status = await settingsApi.getGoogleCalendarStatus()
      setCalendarStatus(status)
    } catch (err) {
      console.error('Failed to load calendar status:', err)
    }
  }

  const loadPreferences = async () => {
    try {
      const prefs = await settingsApi.getPreferences()
      setPreferences(prefs)
    } catch (err) {
      console.error('Failed to load preferences:', err)
    }
  }

  const handleConnectGoogleCalendar = async () => {
    setLoading(true)
    setError('')
    setSuccess('')

    try {
      // Get redirect URI (current origin + callback path)
      const redirectUri = `${window.location.origin}/settings/oauth/callback`
      const { authorization_url } = await settingsApi.getGoogleCalendarAuthUrl(redirectUri)
      
      // Redirect to Google OAuth
      window.location.href = authorization_url
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to initiate Google Calendar connection')
      setLoading(false)
    }
  }

  const handleDisconnect = async () => {
    if (!confirm('Are you sure you want to disconnect Google Calendar?')) return

    setLoading(true)
    setError('')
    setSuccess('')

    try {
      await settingsApi.disconnectGoogleCalendar()
      setSuccess('Google Calendar disconnected successfully')
      await loadCalendarStatus()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to disconnect')
    } finally {
      setLoading(false)
    }
  }

  const handlePreferencesUpdate = async () => {
    if (!preferences) return

    setLoading(true)
    setError('')
    setSuccess('')

    try {
      await settingsApi.updatePreferences(preferences)
      setSuccess('Preferences updated successfully!')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update preferences')
    } finally {
      setLoading(false)
    }
  }

  const handlePasswordUpdate = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setSuccess('')

    if (newPassword !== confirmPassword) {
      setError('New passwords do not match')
      return
    }

    if (newPassword.length < 6) {
      setError('New password must be at least 6 characters long')
      return
    }

    setLoading(true)
    try {
      await settingsApi.updatePassword(currentPassword, newPassword)
      setSuccess('Password updated successfully!')
      setCurrentPassword('')
      setNewPassword('')
      setConfirmPassword('')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update password')
    } finally {
      setLoading(false)
    }
  }

  const updatePreference = (
    category: 'work_study' | 'gym_activity' | 'personal_goals',
    field: keyof TimePreference,
    value: string | boolean
  ) => {
    if (!preferences) return
    setPreferences({
      ...preferences,
      [category]: {
        ...preferences[category],
        [field]: value,
      },
    })
  }

  return (
    <div className="max-w-4xl mx-auto p-6 overflow-y-auto h-full">
      <h1 className="text-3xl font-bold text-gray-900 mb-6">Settings</h1>

      {/* Tabs */}
      <div className="border-b border-gray-200 mb-6">
        <nav className="-mb-px flex space-x-8">
          {(['calendar', 'preferences', 'password'] as const).map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`py-4 px-1 border-b-2 font-medium text-sm ${
                activeTab === tab
                  ? 'border-indigo-500 text-indigo-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              {tab === 'calendar' && 'Google Calendar'}
              {tab === 'preferences' && 'Time Preferences'}
              {tab === 'password' && 'Password'}
            </button>
          ))}
        </nav>
      </div>

      {/* Messages */}
      {error && (
        <div className="mb-4 rounded-md bg-red-50 p-4">
          <p className="text-sm text-red-800">{error}</p>
        </div>
      )}
      {success && (
        <div className="mb-4 rounded-md bg-green-50 p-4">
          <p className="text-sm text-green-800">{success}</p>
        </div>
      )}

      {/* Google Calendar Tab */}
      {activeTab === 'calendar' && (
        <div className="bg-white shadow rounded-lg p-6">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">Google Calendar Integration</h2>
          
          {calendarStatus?.connected ? (
            <div className="space-y-4">
              <div className="flex items-center justify-between p-4 bg-green-50 rounded-lg">
                <div>
                  <p className="text-sm font-medium text-green-800">Connected</p>
                  {calendarStatus.email && (
                    <p className="text-sm text-green-600">{calendarStatus.email}</p>
                  )}
                </div>
                <button
                  onClick={handleDisconnect}
                  disabled={loading}
                  className="px-4 py-2 text-sm font-medium text-red-700 bg-red-100 rounded-md hover:bg-red-200 disabled:opacity-50"
                >
                  Disconnect
                </button>
              </div>
            </div>
          ) : (
            <div className="space-y-4">
              <p className="text-sm text-gray-600 mb-4">
                Connect your Google Calendar to enable calendar management features. Click the button below to authenticate with Google.
              </p>
              <button
                onClick={handleConnectGoogleCalendar}
                disabled={loading}
                className="w-full px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center"
              >
                {loading ? (
                  'Connecting...'
                ) : (
                  <>
                    <svg className="w-5 h-5 mr-2" viewBox="0 0 24 24" fill="currentColor">
                      <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4"/>
                      <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
                      <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05"/>
                      <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/>
                    </svg>
                    Connect Google Calendar
                  </>
                )}
              </button>
            </div>
          )}
        </div>
      )}

      {/* Preferences Tab */}
      {activeTab === 'preferences' && preferences && (
        <div className="bg-white shadow rounded-lg p-6 space-y-6">
          <h2 className="text-xl font-semibold text-gray-900">Time Preferences</h2>
          <p className="text-sm text-gray-600">
            Set your preferred times for different activities. Use format "HH-HH" (24-hour) or "any" for flexible times.
          </p>

          {(['work_study', 'gym_activity', 'personal_goals'] as const).map((category) => (
            <div key={category} className="border border-gray-200 rounded-lg p-4">
              <h3 className="text-lg font-medium text-gray-900 mb-4 capitalize">
                {category.replace('_', ' / ')}
              </h3>
              <div className="space-y-4">
                <div className="flex items-center">
                  <input
                    type="checkbox"
                    id={`${category}-all-time`}
                    checked={preferences[category].all_time}
                    onChange={(e) => updatePreference(category, 'all_time', e.target.checked)}
                    className="h-4 w-4 text-indigo-600 focus:ring-indigo-500 border-gray-300 rounded"
                  />
                  <label htmlFor={`${category}-all-time`} className="ml-2 text-sm text-gray-700">
                    Available all time
                  </label>
                </div>
                {!preferences[category].all_time && (
                  <>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Weekdays (e.g., "9-17" for 9am-5pm or "any")
                      </label>
                      <input
                        type="text"
                        value={preferences[category].weekdays || ''}
                        onChange={(e) => updatePreference(category, 'weekdays', e.target.value)}
                        placeholder="9-17"
                        className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Weekends (e.g., "10-14" or "any")
                      </label>
                      <input
                        type="text"
                        value={preferences[category].weekends || ''}
                        onChange={(e) => updatePreference(category, 'weekends', e.target.value)}
                        placeholder="any"
                        className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm"
                      />
                    </div>
                  </>
                )}
              </div>
            </div>
          ))}

          <button
            onClick={handlePreferencesUpdate}
            disabled={loading}
            className="w-full px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 disabled:opacity-50"
          >
            {loading ? 'Saving...' : 'Save Preferences'}
          </button>
        </div>
      )}

      {/* Password Tab */}
      {activeTab === 'password' && (
        <div className="bg-white shadow rounded-lg p-6">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">Update Password</h2>
          <form onSubmit={handlePasswordUpdate} className="space-y-4">
            <div>
              <label htmlFor="current-password" className="block text-sm font-medium text-gray-700">
                Current Password
              </label>
              <input
                id="current-password"
                type="password"
                value={currentPassword}
                onChange={(e) => setCurrentPassword(e.target.value)}
                required
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm"
              />
            </div>
            <div>
              <label htmlFor="new-password" className="block text-sm font-medium text-gray-700">
                New Password
              </label>
              <input
                id="new-password"
                type="password"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                required
                minLength={6}
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm"
              />
            </div>
            <div>
              <label htmlFor="confirm-password" className="block text-sm font-medium text-gray-700">
                Confirm New Password
              </label>
              <input
                id="confirm-password"
                type="password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                required
                minLength={6}
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm"
              />
            </div>
            <button
              type="submit"
              disabled={loading}
              className="w-full px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 disabled:opacity-50"
            >
              {loading ? 'Updating...' : 'Update Password'}
            </button>
          </form>
        </div>
      )}
    </div>
  )
}

