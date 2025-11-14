import { Upload, AlertCircle } from 'lucide-react';
import { useRef, useState } from 'react';

interface UploadZoneProps {
  onFilesSelected?: (files: File[]) => void;
  disabled?: boolean;
}

export function UploadZone({ onFilesSelected, disabled = false }: UploadZoneProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [isDragActive, setIsDragActive] = useState(false);
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);

  const handleDragEnter = (e: React.DragEvent) => {
    e.preventDefault();
    if (!disabled) setIsDragActive(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragActive(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragActive(false);
    if (disabled) return;

    const files = Array.from(e.dataTransfer.files);
    handleFiles(files);
  };

  const handleFiles = (files: File[]) => {
    const validFiles = files.filter(f => {
      const isValid = ['image/', 'video/', 'application/pdf'].some(type =>
        f.type.startsWith(type.replace('/', '')) || f.type === 'application/pdf'
      );
      return isValid;
    });

    setSelectedFiles(validFiles);
    onFilesSelected?.(validFiles);
  };

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      handleFiles(Array.from(e.target.files));
    }
  };

  return (
    <div className="space-y-3">
      <div
        onClick={() => !disabled && fileInputRef.current?.click()}
        onDragEnter={handleDragEnter}
        onDragLeave={handleDragLeave}
        onDragOver={handleDragEnter}
        onDrop={handleDrop}
        className={`border-2 border-dashed rounded-xl p-8 text-center transition-all cursor-pointer ${
          disabled
            ? 'opacity-50 cursor-not-allowed border-slate-300'
            : isDragActive
              ? 'border-blue-500 bg-blue-50'
              : 'border-slate-300 hover:border-blue-400 hover:bg-blue-50'
        }`}
      >
        <Upload className={`w-12 h-12 mx-auto mb-3 ${isDragActive ? 'text-blue-600' : 'text-slate-400'}`} />
        <p className="text-sm font-medium text-slate-700 mb-1">
          {selectedFiles.length > 0 ? 'Files selected' : 'Drag & drop or click to upload'}
        </p>
        <p className="text-xs text-slate-500">
          Images, videos, or PDFs to guide the AI
        </p>
        <input
          ref={fileInputRef}
          type="file"
          multiple
          disabled={disabled}
          onChange={handleFileInput}
          accept="image/*,video/*,.pdf"
          className="hidden"
        />
      </div>

      {selectedFiles.length > 0 && (
        <div className="space-y-2">
          {selectedFiles.map((file, idx) => (
            <div
              key={idx}
              className="flex items-center justify-between p-3 bg-blue-50 rounded-lg border border-blue-200"
            >
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-slate-900 truncate">{file.name}</p>
                <p className="text-xs text-slate-500">
                  {(file.size / 1024 / 1024).toFixed(2)} MB
                </p>
              </div>
              <button
                onClick={() => setSelectedFiles(selectedFiles.filter((_, i) => i !== idx))}
                className="ml-3 text-slate-400 hover:text-slate-600"
              >
                ×
              </button>
            </div>
          ))}
        </div>
      )}

      <div className="flex items-start space-x-2 p-3 bg-amber-50 rounded-lg border border-amber-200">
        <AlertCircle className="w-4 h-4 text-amber-600 flex-shrink-0 mt-0.5" />
        <p className="text-xs text-amber-800">
          For best results, upload clear, high-quality reference materials
        </p>
      </div>
    </div>
  );
}
