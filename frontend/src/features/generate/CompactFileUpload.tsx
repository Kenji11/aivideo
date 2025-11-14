import { useState } from 'react'
import { AlertCircle } from 'lucide-react'
import { DropZone } from './DropZone'
import { FilePreviewGrid } from './FilePreviewGrid'

interface CompactFileUploadProps {
  files: File[]
  onChange: (files: File[]) => void
}

export function CompactFileUpload({ files, onChange }: CompactFileUploadProps) {
  const [isDragging, setIsDragging] = useState(false)

  const handleFilesAdded = (newFiles: File[]) => {
    onChange([...files, ...newFiles])
  }

  const handleRemove = (index: number) => {
    onChange(files.filter((_, i) => i !== index))
  }

  return (
    <div className="space-y-3">
      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
        Reference Materials
      </label>

      {files.length === 0 ? (
        <DropZone
          onFilesAdded={handleFilesAdded}
          isDragging={isDragging}
          setIsDragging={setIsDragging}
        />
      ) : (
        <FilePreviewGrid
          files={files}
          onRemove={handleRemove}
          onAddMore={handleFilesAdded}
        />
      )}

      {/* Warning message */}
      <div className="flex items-start gap-2 text-sm text-amber-700 dark:text-amber-400 
                      bg-amber-50 dark:bg-amber-900/20 p-3 rounded-lg">
        <AlertCircle className="h-4 w-4 mt-0.5 flex-shrink-0" />
        <span>For best results, upload clear, high-quality reference materials</span>
      </div>
    </div>
  )
}

