import { Header } from '@/components/Header'
import { Film, Sparkles } from 'lucide-react'

export default function ProjectsPage() {
  return (
    <div className="min-h-screen bg-gray-50 dark:bg-slate-950">
      <Header />
      
      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-6 py-12">
        {/* Page Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 dark:text-gray-100 mb-2">
            My Projects
          </h1>
          <p className="text-gray-600 dark:text-gray-400">
            Create and manage your AI-generated videos
          </p>
        </div>

        {/* Empty State */}
        <div className="bg-white dark:bg-slate-900 rounded-xl border border-gray-200 dark:border-slate-800 shadow-sm">
          <div className="flex flex-col items-center justify-center py-20 px-6">
            {/* Film Icon */}
            <div className="mb-6 text-gray-300 dark:text-gray-600">
              <Film className="h-24 w-24" strokeWidth={1.5} />
            </div>
            
            {/* Empty State Text */}
            <p className="text-gray-500 dark:text-gray-400 text-lg mb-8">
              No projects yet
            </p>
            
            {/* CTA Button */}
            <a
              href="#"
              className="inline-flex items-center gap-2 px-6 py-3 
                       bg-blue-600 hover:bg-blue-700 
                       text-white font-semibold rounded-lg 
                       transition-all duration-200 
                       hover:shadow-lg hover:scale-105
                       active:scale-95"
            >
              <Sparkles className="h-5 w-5" />
              <span>Create Your First Video</span>
            </a>
          </div>
        </div>
      </main>
    </div>
  )
}

