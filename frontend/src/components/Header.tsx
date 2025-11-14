import { Film, Moon, Sun, Folder } from 'lucide-react'
import { useDarkMode } from '@/hooks/useDarkMode'

export function Header() {
  const { darkMode, toggle } = useDarkMode()

  return (
    <header className="sticky top-0 z-50 border-b border-gray-200 dark:border-slate-700 bg-white dark:bg-slate-900 shadow-sm">
      <div className="max-w-7xl mx-auto px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo with hover animation */}
          <a 
            href="/" 
            className="flex items-center gap-2.5 group cursor-pointer"
          >
            <div className="bg-blue-500 rounded-lg p-1.5 transition-transform duration-300 group-hover:scale-105">
              <Film className="h-5 w-5 text-white transition-all duration-300 
                             group-hover:rotate-12" />
            </div>
            <div className="flex flex-col">
              <span className="text-base font-bold text-blue-600 dark:text-blue-400 
                             transition-colors duration-300 group-hover:text-blue-700 
                             dark:group-hover:text-blue-300 leading-tight">
                VideoAI
              </span>
              <span className="text-[11px] text-gray-500 dark:text-gray-400 leading-tight tracking-wide">
                Studio
              </span>
            </div>
          </a>

          {/* Right side */}
          <div className="flex items-center gap-3">
            {/* Dark mode toggle */}
            <button
              onClick={toggle}
              className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-slate-800 
                       transition-all duration-200 hover:scale-105"
              aria-label="Toggle dark mode"
            >
              {darkMode ? (
                <Sun className="h-5 w-5 text-yellow-500" />
              ) : (
                <Moon className="h-5 w-5 text-gray-600" />
              )}
            </button>

            {/* My Projects button */}
            <a
              href="/projects"
              className="flex items-center gap-2 px-4 py-2 rounded-lg
                       bg-gray-50 dark:bg-slate-800 
                       text-gray-700 dark:text-gray-300
                       hover:bg-blue-50 dark:hover:bg-blue-900/20
                       hover:text-blue-600 dark:hover:text-blue-400
                       border border-gray-200 dark:border-slate-700
                       hover:border-blue-300 dark:hover:border-blue-700
                       font-medium text-sm transition-all duration-200
                       hover:shadow-sm"
            >
              <Folder className="h-4 w-4" />
              <span>My Projects</span>
            </a>
          </div>
        </div>
      </div>
    </header>
  )
}

