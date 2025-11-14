import { Header } from '@/components/Header'
import { Navigation } from '@/components/Navigation'
import { GenerateForm } from './GenerateForm'

export default function GeneratePage() {
  return (
    <div className="min-h-screen bg-gray-50 dark:bg-slate-950">
      <Header />
      <Navigation activeTab="dashboard" />
      <main className="max-w-5xl mx-auto px-6 py-12">
        <GenerateForm />
      </main>
    </div>
  )
}
