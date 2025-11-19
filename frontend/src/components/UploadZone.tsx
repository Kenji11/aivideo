import { Upload, AlertCircle, Loader2, CheckCircle2, XCircle } from 'lucide-react';
import { useRef, useState } from 'react';
import { api } from '../lib/api';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { Alert, AlertDescription } from '@/components/ui/alert';

interface UploadZoneProps {
  onAssetsUploaded?: (assetIds: string[]) => void;
  disabled?: boolean;
}

interface FileUploadState {
  file: File;
  status: 'pending' | 'uploading' | 'success' | 'error';
  progress: number;
  error?: string;
  assetId?: string;
}

export function UploadZone({ onAssetsUploaded, disabled = false }: UploadZoneProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [isDragActive, setIsDragActive] = useState(false);
  const [uploadStates, setUploadStates] = useState<FileUploadState[]>([]);
  const [isUploading, setIsUploading] = useState(false);

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

  const handleFiles = async (files: File[]) => {
    const validFiles = files.filter(f => {
      const isValid = ['image/', 'video/', 'application/pdf'].some(type =>
        f.type.startsWith(type.replace('/', '')) || f.type === 'application/pdf'
      );
      return isValid;
    });

    if (validFiles.length === 0) return;

    // Initialize upload states
    const initialStates: FileUploadState[] = validFiles.map(file => ({
      file,
      status: 'pending',
      progress: 0,
    }));
    setUploadStates(initialStates);
    setIsUploading(true);

    try {
      // Upload files with progress tracking
      const response = await api.uploadAssets(validFiles, (progress) => {
        // Update progress for all files (simplified - could be per-file if needed)
        setUploadStates(prev => prev.map(state => ({
          ...state,
          status: 'uploading' as const,
          progress,
        })));
      });

      // Update states with results
      const assetIds: string[] = [];
      setUploadStates(prev => {
        return prev.map((state, idx) => {
          const uploadedAsset = response.assets[idx];
          if (uploadedAsset) {
            assetIds.push(uploadedAsset.asset_id);
            return {
              ...state,
              status: 'success' as const,
              progress: 100,
              assetId: uploadedAsset.asset_id,
            };
          } else {
            return {
              ...state,
              status: 'error' as const,
              error: response.errors?.[idx] || 'Upload failed',
            };
          }
        });
      });

      // Notify parent of uploaded asset IDs
      if (assetIds.length > 0) {
        onAssetsUploaded?.(assetIds);
      }

      // Show errors if any
      if (response.errors && response.errors.length > 0) {
        console.error('Upload errors:', response.errors);
      }
    } catch (error) {
      // Handle upload errors
      const errorMessage = error instanceof Error ? error.message : 'Failed to upload files';
      setUploadStates(prev => prev.map(state => ({
        ...state,
        status: 'error' as const,
        error: errorMessage,
      })));
      console.error('Upload error:', error);
    } finally {
      setIsUploading(false);
    }
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
            ? 'opacity-50 cursor-not-allowed border-slate-300 dark:border-slate-600'
            : isDragActive
              ? 'border-blue-500 bg-blue-50'
              : 'border-slate-300 dark:border-slate-600 hover:border-blue-400 hover:bg-blue-50'
        }`}
      >
        {isUploading ? (
          <Loader2 className="w-12 h-12 mx-auto mb-3 text-blue-600 animate-spin" />
        ) : (
          <Upload className={`w-12 h-12 mx-auto mb-3 ${isDragActive ? 'text-blue-600' : 'text-slate-400'}`} />
        )}
        <p className="text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
          {isUploading
            ? 'Uploading files...'
            : uploadStates.length > 0
            ? `${uploadStates.filter(s => s.status === 'success').length} file(s) uploaded`
            : 'Drag & drop or click to upload'}
        </p>
        <p className="text-xs text-slate-500 dark:text-slate-400">
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

      {uploadStates.length > 0 && (
        <div className="space-y-2">
          {uploadStates.map((state, idx) => (
            <div
              key={idx}
              className={`p-3 rounded-lg border ${
                state.status === 'success'
                  ? 'bg-green-50 border-green-200 dark:bg-green-900/20 dark:border-green-800'
                  : state.status === 'error'
                  ? 'bg-red-50 border-red-200 dark:bg-red-900/20 dark:border-red-800'
                  : state.status === 'uploading'
                  ? 'bg-blue-50 border-blue-200 dark:bg-blue-900/20 dark:border-blue-800'
                  : 'bg-slate-50 border-slate-200 dark:bg-slate-800 dark:border-slate-700'
              }`}
            >
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center space-x-2 flex-1 min-w-0">
                  {state.status === 'uploading' && (
                    <Loader2 className="w-4 h-4 text-blue-600 animate-spin flex-shrink-0" />
                  )}
                  {state.status === 'success' && (
                    <CheckCircle2 className="w-4 h-4 text-green-600 flex-shrink-0" />
                  )}
                  {state.status === 'error' && (
                    <XCircle className="w-4 h-4 text-red-600 flex-shrink-0" />
                  )}
                  <p className="text-sm font-medium text-slate-900 dark:text-slate-100 truncate">
                    {state.file.name}
                  </p>
                </div>
                {state.status !== 'uploading' && (
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => setUploadStates(uploadStates.filter((_, i) => i !== idx))}
                    className="ml-3 h-6 w-6"
                  >
                    ×
                  </Button>
                )}
              </div>
              {state.status === 'uploading' && (
                <Progress value={state.progress} className="mb-1" />
              )}
              <div className="flex items-center justify-between">
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  {(state.file.size / 1024 / 1024).toFixed(2)} MB
                </p>
                {state.status === 'error' && state.error && (
                  <p className="text-xs text-red-600 truncate ml-2">{state.error}</p>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      <Alert>
        <AlertCircle className="h-4 w-4" />
        <AlertDescription>
          For best results, upload clear, high-quality reference materials
        </AlertDescription>
      </Alert>
    </div>
  );
}
