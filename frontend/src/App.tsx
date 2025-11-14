import { useState, useEffect } from 'react'
import GeneratePage from '@/features/generate/GeneratePage'
import ProjectsPage from '@/features/projects/ProjectsPage'
import '@/styles/globals.css'

function App() {
  const [currentPage, setCurrentPage] = useState<'generate' | 'projects'>('generate')

  // Simple routing using URL hash
  useEffect(() => {
    const handleHashChange = () => {
      const hash = window.location.hash.slice(1) // Remove the '#'
      if (hash === 'projects') {
        setCurrentPage('projects')
      } else {
        setCurrentPage('generate')
      }
    }

    // Check initial hash
    handleHashChange()

    // Listen for hash changes
    window.addEventListener('hashchange', handleHashChange)
    return () => window.removeEventListener('hashchange', handleHashChange)
  }, [])

  return (
    <div>
      {currentPage === 'generate' ? <GeneratePage /> : <ProjectsPage />}
    </div>
  )
}

export default App
