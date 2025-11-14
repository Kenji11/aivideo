import { useState, useEffect } from 'react'
import { X, FileText, Video } from 'lucide-react'

interface FileThumbnailProps {
  file: File
  onRemove: () => void
}

export function FileThumbnail({ file, onRemove }: FileThumbnailProps) {
  const [preview, setPreview] = useState<string>('')

  useEffect(() => {
    if (file.type.startsWith('image/')) {
      const reader = new FileReader()
      reader.onloadend = () => {
        setPreview(reader.result as string)
      }
      reader.readAsDataURL(file)
    }
  }, [file])

  const isImage = file.type.startsWith('image/')
  const isVideo = file.type.startsWith('video/')
  const isPDF = file.type === 'application/pdf'

  return (
    <div className="relative group w-20">
      {/* Thumbnail */}
      <div className="w-20 h-20 border border-gray-200 dark:border-slate-700 rounded-lg overflow-hidden bg-gray-100 dark:bg-slate-800">
        {isImage && preview ? (
          <img src={preview} alt={file.name} className="w-full h-full object-cover" />
        ) : isVideo ? (
          <div className="w-full h-full flex items-center justify-center">
            <Video className="h-8 w-8 text-gray-400 dark:text-gray-500" />
          </div>
        ) : isPDF ? (
          <div className="w-full h-full flex items-center justify-center">
            <FileText className="h-8 w-8 text-gray-400 dark:text-gray-500" />
          </div>
        ) : (
          <div className="w-full h-full flex items-center justify-center">
            <FileText className="h-8 w-8 text-gray-400 dark:text-gray-500" />
          </div>
        )}
      </div>

      {/* Remove button on hover */}
      <button
        onClick={onRemove}
        className="absolute -top-2 -right-2 bg-red-500 text-white rounded-full p-1 
                   opacity-0 group-hover:opacity-100 transition-opacity
                   hover:bg-red-600"
        aria-label="Remove file"
      >
        <X className="h-3 w-3" />
      </button>

      {/* Filename below */}
      <p className="text-xs text-gray-600 dark:text-gray-400 mt-1 truncate" title={file.name}>
        {file.name}
      </p>
    </div>
  )
}

