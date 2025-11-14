import { BarChart3, Zap, FolderOpen, LineChart, CreditCard, Code, Settings as SettingsIcon } from 'lucide-react'

interface NavigationProps {
  activeTab?: string
}

export function Navigation({ activeTab = 'dashboard' }: NavigationProps) {
  const navItems = [
    { id: 'dashboard', label: 'Dashboard', icon: BarChart3 },
    { id: 'templates', label: 'Templates', icon: Zap },
    { id: 'library', label: 'Library', icon: FolderOpen },
    { id: 'analytics', label: 'Analytics', icon: LineChart },
    { id: 'billing', label: 'Billing', icon: CreditCard },
    { id: 'api', label: 'API', icon: Code },
    { id: 'settings', label: 'Settings', icon: SettingsIcon },
  ]

  return (
    <nav className="bg-white dark:bg-slate-900 border-b border-gray-200 dark:border-slate-700">
      <div className="max-w-7xl mx-auto px-6 lg:px-8">
        <div className="flex items-center gap-2 h-14 overflow-x-auto scrollbar-hide">
          {navItems.map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              className={`
                flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium
                whitespace-nowrap transition-all duration-200
                ${
                  activeTab === id
                    ? 'text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-900/20 shadow-sm'
                    : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200 hover:bg-gray-50 dark:hover:bg-slate-800'
                }
              `}
            >
              <Icon className="h-4 w-4" />
              <span>{label}</span>
            </button>
          ))}
        </div>
      </div>
    </nav>
  )
}

