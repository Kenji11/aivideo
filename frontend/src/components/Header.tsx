import { Film, Moon, Sun } from 'lucide-react'
import { useDarkMode } from '@/hooks/useDarkMode'

export function Header() {
  const { darkMode, toggle } = useDarkMode()

  return (
    <header className="sticky top-0 z-50 border-b border-gray-200 dark:border-slate-700 bg-white dark:bg-slate-900 shadow-sm">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo with hover animation */}
          <a 
            href="/" 
            className="flex items-center gap-2 group cursor-pointer"
          >
            <div className="bg-blue-500 rounded-lg p-1.5">
              <Film className="h-5 w-5 text-white transition-all duration-300 
                             group-hover:scale-110 group-hover:rotate-12" />
            </div>
            <div className="flex flex-col">
              <span className="text-base font-bold text-blue-600 dark:text-blue-400 
                             transition-all duration-300 group-hover:text-blue-700 
                             dark:group-hover:text-blue-300 leading-tight">
                VideoAI
              </span>
              <span className="text-xs text-gray-500 dark:text-gray-400 leading-tight">
                Studio
              </span>
            </div>
          </a>

          {/* Right side */}
          <div className="flex items-center gap-4">
            {/* Dark mode toggle */}
            <button
              onClick={toggle}
              className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-slate-800 transition-colors"
              aria-label="Toggle dark mode"
            >
              {darkMode ? (
                <Sun className="h-5 w-5 text-yellow-500" />
              ) : (
                <Moon className="h-5 w-5 text-gray-600" />
              )}
            </button>

            {/* My Projects link */}
            <a
              href="/projects"
              className="text-gray-700 dark:text-gray-300 hover:text-blue-500 dark:hover:text-blue-400 
                       font-medium transition-colors text-sm"
            >
              My Projects
            </a>
          </div>
        </div>
      </div>
    </header>
  )
}

