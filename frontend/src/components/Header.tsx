import { Film, Moon, Sun } from 'lucide-react'
import { useDarkMode } from '@/hooks/useDarkMode'

export function Header() {
  const { darkMode, toggle } = useDarkMode()

  return (
    <header className="sticky top-0 z-50 border-b border-gray-200 dark:border-slate-700 bg-white dark:bg-slate-900">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo with hover animation */}
          <a 
            href="/" 
            className="flex items-center gap-2 group cursor-pointer"
          >
            <Film className="h-8 w-8 text-blue-500 transition-all duration-300 
                           group-hover:scale-110 group-hover:rotate-12 
                           group-hover:text-blue-600 dark:group-hover:text-blue-400" />
            <span className="text-xl font-bold text-gray-900 dark:text-gray-100 
                           transition-all duration-300 group-hover:text-blue-600 
                           dark:group-hover:text-blue-400">
              VideoAI
            </span>
            <span className="text-xl font-normal text-gray-600 dark:text-gray-400 
                           transition-all duration-300 group-hover:text-blue-500">
              Studio
            </span>
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
              className="text-gray-700 dark:text-gray-300 hover:text-blue-500 dark:hover:text-blue-400 font-medium transition-colors"
            >
              My Projects
            </a>
          </div>
        </div>
      </div>
    </header>
  )
}

