import { Header } from '@/components/Header'
import { GenerateForm } from './GenerateForm'

export default function GeneratePage() {
  return (
    <div className="min-h-screen bg-gray-50 dark:bg-slate-950">
      <Header />
      <main className="max-w-4xl mx-auto px-4 py-8">
        <GenerateForm />
      </main>
    </div>
  )
}
