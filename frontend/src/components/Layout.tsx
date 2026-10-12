import { NavLink, useLocation } from 'react-router-dom'
import { Menu, X, ChevronLeft, ChevronRight } from 'lucide-react'
import { useState } from 'react'
import { clsx } from 'clsx'

export function Layout({ children }: { children: React.ReactNode }) {
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)
  const location = useLocation()

  const navItems = [
    { path: '/dashboard', label: 'Dashboard', icon: 'LayoutDashboard' },
    { path: '/sessions', label: 'Sessions', icon: 'Database' },
    { path: '/health', label: 'Health', icon: 'Activity' },
  ]

  return (
    <div className="min-h-screen bg-background flex">
      {/* Mobile menu button */}
      <button
        className="fixed top-4 left-4 z-50 lg:hidden p-2 rounded-md bg-card border border-border"
        onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
        aria-label="Toggle menu"
      >
        {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
      </button>

      {/* Sidebar */}
      <aside
        className={clsx(
          'fixed lg:static inset-y-0 left-0 z-40 bg-card border-r border-border transition-all duration-300 flex flex-col',
          sidebarOpen ? 'w-64' : 'w-20',
          mobileMenuOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'
        )}
        aria-label="Main navigation"
      >
        <div className="flex h-16 items-center justify-between px-4 border-b border-border">
          {sidebarOpen && (
            <span className="font-semibold text-lg text-primary">Vector Forge</span>
          )}
          <button
            className="lg:hidden p-1 rounded"
            onClick={() => setMobileMenuOpen(false)}
            aria-label="Close menu"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <nav className="flex-1 p-4 space-y-1 overflow-y-auto" role="navigation" aria-label="Main">
          {navItems.map((item) => {
            const isActive = location.pathname.startsWith(item.path)
            const IconComponent = getIcon(item.icon)
            return (
              <NavLink
                key={item.path}
                to={item.path}
                className={clsx(
                  'flex items-center gap-3 rounded-lg px-3 py-2 transition-colors',
                  'text-sm font-medium',
                  isActive
                    ? 'bg-primary text-primary-foreground'
                    : 'text-muted-foreground hover:text-foreground hover:bg-accent',
                  !sidebarOpen && 'justify-center'
                )}
                aria-current={isActive ? 'page' : undefined}
                title={sidebarOpen ? undefined : item.label}
                onClick={() => setMobileMenuOpen(false)}
              >
                <IconComponent className="w-5 h-5 flex-shrink-0" aria-hidden="true" />
                {sidebarOpen && <span>{item.label}</span>}
              </NavLink>
            )
          })}
        </nav>

        <div className="p-4 border-t border-border">
          <button
            className={clsx(
              'w-full flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium',
              'text-muted-foreground hover:text-foreground hover:bg-accent transition-colors',
              !sidebarOpen && 'justify-center'
            )}
            title={sidebarOpen ? undefined : 'Toggle sidebar'}
            onClick={() => setSidebarOpen(!sidebarOpen)}
          >
            {sidebarOpen ? (
              <>
                <ChevronLeft className="w-5 h-5 flex-shrink-0" aria-hidden="true" />
                <span>Collapse</span>
              </>
            ) : (
              <ChevronRight className="w-5 h-5" aria-hidden="true" />
            )}
          </button>
        </div>
      </aside>

      {/* Mobile overlay */}
      {mobileMenuOpen && (
        <div
          className="fixed inset-0 z-30 bg-black/50 lg:hidden"
          onClick={() => setMobileMenuOpen(false)}
          aria-hidden="true"
        />
      )}

      {/* Main content */}
      <main
        className={clsx(
          'flex-1 min-w-0 lg:ml-0',
          sidebarOpen ? 'lg:ml-64' : 'lg:ml-20'
        )}
      >
        <div className="p-4 lg:p-6">
          {children}
        </div>
      </main>
    </div>
  )
}

function getIcon(name: string) {
  const icons: Record<string, React.ComponentType<{ className?: string }>> = {
    LayoutDashboard: () => <Menu className="w-5 h-5" />,
    Database: () => <Database className="w-5 h-5" />,
    Activity: () => <Activity className="w-5 h-5" />,
  }
  return icons[name] || (() => <Menu className="w-5 h-5" />)
}

// Simple icon components
function Database({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <ellipse cx="12" cy="5" rx="9" ry="3" />
      <path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3" />
      <path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5" />
    </svg>
  )
}

function Activity({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
    </svg>
  )
}