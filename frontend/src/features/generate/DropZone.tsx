import { useCallback } from 'react'
import { Upload } from 'lucide-react'

interface DropZoneProps {
  onFilesAdded: (files: File[]) => void
  isDragging: boolean
  setIsDragging: (dragging: boolean) => void
}

export function DropZone({ onFilesAdded, isDragging, setIsDragging }: DropZoneProps) {
  const handleDrop = useCallback(
    (e: React.DragEvent<HTMLDivElement>) => {
      e.preventDefault()
      setIsDragging(false)

      const droppedFiles = Array.from(e.dataTransfer.files).filter((file) =>
        file.type.startsWith('image/') || file.type === 'application/pdf' || file.type.startsWith('video/')
      )

      if (droppedFiles.length > 0) {
        onFilesAdded(droppedFiles)
      }
    },
    [onFilesAdded, setIsDragging]
  )

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFiles = Array.from(e.target.files || [])
    if (selectedFiles.length > 0) {
      onFilesAdded(selectedFiles)
    }
  }

  return (
    <div
      onDragOver={(e) => {
        e.preventDefault()
        setIsDragging(true)
      }}
      onDragLeave={() => setIsDragging(false)}
      onDrop={handleDrop}
      className={`
        relative border-2 border-dashed rounded-lg p-8 text-center
        transition-colors cursor-pointer
        ${
          isDragging
            ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20'
            : 'border-gray-300 dark:border-slate-600 hover:border-blue-400 dark:hover:border-blue-500'
        }
      `}
    >
      <input
        type="file"
        multiple
        accept="image/*,video/*,application/pdf"
        onChange={handleFileInput}
        className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
      />

      <div className="flex flex-col items-center gap-2">
        <Upload className="h-8 w-8 text-gray-400 dark:text-gray-500" />
        <p className="text-sm font-medium text-gray-700 dark:text-gray-300">
          Drag & drop or click to upload
        </p>
        <p className="text-xs text-gray-500 dark:text-gray-400">
          Images, videos, or PDFs to guide the AI
        </p>
      </div>
    </div>
  )
}

