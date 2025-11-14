import { useState } from 'react'
import { FormHeader } from './FormHeader'
import { ProjectInfoSection } from './ProjectInfoSection'
import { PromptInput } from './PromptInput'
import { CompactFileUpload } from './CompactFileUpload'
import { SubmitButton } from './SubmitButton'

export function GenerateForm() {
  const [projectTitle, setProjectTitle] = useState('')
  const [description, setDescription] = useState('')
  const [prompt, setPrompt] = useState('')
  const [files, setFiles] = useState<File[]>([])
  const [isGenerating, setIsGenerating] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (!projectTitle || !prompt) return

    setIsGenerating(true)
    
    // TODO: Call API to generate video
    console.log('Generating video with:', {
      projectTitle,
      description,
      prompt,
      files: files.map(f => f.name),
    })
    
    // Simulate API call
    setTimeout(() => {
      setIsGenerating(false)
      alert('Video generation started!')
    }, 2000)
  }

  const isValid = projectTitle.trim().length > 0 && prompt.trim().length > 0

  return (
    <form onSubmit={handleSubmit} className="bg-white dark:bg-slate-900 rounded-lg shadow-sm p-8 space-y-8">
      <FormHeader />
      
      <ProjectInfoSection
        title={projectTitle}
        description={description}
        onTitleChange={setProjectTitle}
        onDescriptionChange={setDescription}
      />
      
      <PromptInput value={prompt} onChange={setPrompt} />
      
      <CompactFileUpload files={files} onChange={setFiles} />
      
      <SubmitButton disabled={!isValid} loading={isGenerating} />
    </form>
  )
}
