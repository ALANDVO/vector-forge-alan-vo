import { useEffect } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useAuth } from './AuthProvider'
import { Loader2 } from 'lucide-react'

export function LoginCallback() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const { refreshUser } = useAuth()

  const error = searchParams.get('error')
  const errorDescription = searchParams.get('error_description')

  useEffect(() => {
    const handleCallback = async () => {
      if (error) {
        console.error('OIDC callback error:', error, errorDescription)
        navigate('/login?error=' + encodeURIComponent(errorDescription || error))
        return
      }

      try {
        await refreshUser()
        navigate('/dashboard')
      } catch {
        navigate('/login?error=Authentication failed')
      }
    }

    handleCallback()
  }, [error, errorDescription, navigate, refreshUser])

  return (
    <div className="min-h-screen flex items-center justify-center bg-background">
      <div className="text-center">
        <Loader2 className="w-8 h-8 animate-spin mx-auto text-primary" />
        <p className="mt-4 text-muted-foreground">Completing sign in...</p>
      </div>
    </div>
  )
}