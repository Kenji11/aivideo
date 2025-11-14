import { Plus } from 'lucide-react'
import { FileThumbnail } from './FileThumbnail'

interface FilePreviewGridProps {
  files: File[]
  onRemove: (index: number) => void
  onAddMore: (files: File[]) => void
}

export function FilePreviewGrid({ files, onRemove, onAddMore }: FilePreviewGridProps) {
  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFiles = Array.from(e.target.files || [])
    if (selectedFiles.length > 0) {
      onAddMore(selectedFiles)
    }
  }

  return (
    <div className="flex flex-wrap gap-3">
      {files.map((file, index) => (
        <FileThumbnail key={index} file={file} onRemove={() => onRemove(index)} />
      ))}

      {/* Add more button */}
      <label className="relative group cursor-pointer">
        <input
          type="file"
          multiple
          accept="image/*,video/*,application/pdf"
          onChange={handleFileInput}
          className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
        />
        <div
          className="w-20 h-20 border-2 border-dashed border-gray-300 dark:border-slate-600 
                     rounded-lg flex items-center justify-center
                     hover:border-blue-400 dark:hover:border-blue-500 hover:bg-blue-50 dark:hover:bg-blue-900/20
                     transition-colors"
        >
          <Plus className="h-6 w-6 text-gray-400 dark:text-gray-500 group-hover:text-blue-500" />
        </div>
      </label>
    </div>
  )
}

