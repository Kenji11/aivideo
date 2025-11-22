import { useState, useRef, useCallback } from 'react';
import { api } from '../lib/api';
import { Upload, X, FileImage } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { toast } from '@/hooks/use-toast';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';

const REFERENCE_ASSET_TYPES = [
  { value: 'product', label: 'Product' },
  { value: 'logo', label: 'Logo' },
  { value: 'person', label: 'Person' },
  { value: 'environment', label: 'Environment' },
  { value: 'texture', label: 'Texture' },
  { value: 'prop', label: 'Prop' },
];

const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10MB
const ALLOWED_TYPES = ['image/png', 'image/jpeg', 'image/jpg', 'image/webp'];

interface UploadAssetModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

export function UploadAssetModal({ isOpen, onClose, onSuccess }: UploadAssetModalProps) {
  const [files, setFiles] = useState<File[]>([]);
  const [preview, setPreview] = useState<string | null>(null);
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [referenceAssetType, setReferenceAssetType] = useState('');
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const validateFile = (file: File): string | null => {
    if (!ALLOWED_TYPES.includes(file.type)) {
      return `File type not allowed. Allowed types: PNG, JPG, WEBP`;
    }
    if (file.size > MAX_FILE_SIZE) {
      return `File too large. Maximum size: ${(MAX_FILE_SIZE / (1024 * 1024)).toFixed(0)}MB`;
    }
    return null;
  };

  const handleFileSelect = useCallback((selectedFiles: FileList | null) => {
    if (!selectedFiles || selectedFiles.length === 0) return;

    const file = selectedFiles[0];
    const error = validateFile(file);
    if (error) {
      toast({
        variant: 'destructive',
        title: 'Invalid file',
        description: error,
      });
      return;
    }

    setFiles([file]);
    setName(name || file.name.replace(/\.[^/.]+$/, '')); // Set name to filename without extension if empty

    // Create preview
    const reader = new FileReader();
    reader.onload = (e) => {
      setPreview(e.target?.result as string);
    };
    reader.readAsDataURL(file);
  }, [name]);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
    handleFileSelect(e.dataTransfer.files);
  }, [handleFileSelect]);

  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    handleFileSelect(e.target.files);
  };

  const handleUpload = async () => {
    if (files.length === 0) {
      toast({
        variant: 'destructive',
        title: 'No file selected',
        description: 'Please select a file to upload',
      });
      return;
    }

    if (!name.trim()) {
      toast({
        variant: 'destructive',
        title: 'Name required',
        description: 'Please enter a name for the asset',
      });
      return;
    }

    setIsUploading(true);
    setUploadProgress(0);

    try {
      await api.uploadAssetsWithMetadata(
        files,
        {
          name: name.trim(),
          description: description.trim() || undefined,
          reference_asset_type: referenceAssetType || undefined,
        },
        (progress) => {
          setUploadProgress(progress);
        }
      );

      toast({
        title: 'Success',
        description: 'Asset uploaded successfully',
      });

      // Reset form
      setFiles([]);
      setPreview(null);
      setName('');
      setDescription('');
      setReferenceAssetType('');
      setUploadProgress(0);

      onSuccess();
    } catch (error) {
      console.error('Upload failed:', error);
      toast({
        variant: 'destructive',
        title: 'Upload failed',
        description: error instanceof Error ? error.message : 'Failed to upload asset',
      });
    } finally {
      setIsUploading(false);
      setUploadProgress(0);
    }
  };

  const handleClose = () => {
    if (!isUploading) {
      setFiles([]);
      setPreview(null);
      setName('');
      setDescription('');
      setReferenceAssetType('');
      setUploadProgress(0);
      onClose();
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={handleClose}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Upload Reference Asset</DialogTitle>
          <DialogDescription>
            Upload an image to use as a reference asset in your video generations
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-6">
          {/* Drag and drop zone */}
          <div
            className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
              isDragging
                ? 'border-primary bg-primary/10'
                : 'border-border hover:border-primary/50'
            }`}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
          >
            <input
              ref={fileInputRef}
              type="file"
              accept={ALLOWED_TYPES.join(',')}
              onChange={handleFileInputChange}
              className="hidden"
            />
            {preview ? (
              <div className="space-y-4">
                <img
                  src={preview}
                  alt="Preview"
                  className="max-h-64 mx-auto rounded-lg object-contain"
                />
                <p className="text-sm text-muted-foreground">
                  {files[0]?.name} ({(files[0]?.size / (1024 * 1024)).toFixed(2)} MB)
                </p>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={(e) => {
                    e.stopPropagation();
                    setFiles([]);
                    setPreview(null);
                    setName('');
                  }}
                >
                  Change file
                </Button>
              </div>
            ) : (
              <div className="space-y-4">
                <Upload className="w-12 h-12 mx-auto text-muted-foreground" />
                <div>
                  <p className="text-sm font-medium text-foreground">
                    Drag and drop an image here, or click to select
                  </p>
                  <p className="text-xs text-muted-foreground mt-2">
                    PNG, JPG, WEBP up to 10MB
                  </p>
                </div>
              </div>
            )}
          </div>

          {/* Metadata fields */}
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-foreground mb-2">
                Asset Name <span className="text-destructive">*</span>
              </label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Enter asset name"
                className="w-full px-3 py-2 rounded-lg border border-border bg-background text-foreground"
                required
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-foreground mb-2">
                Asset Type
              </label>
              <select
                value={referenceAssetType}
                onChange={(e) => setReferenceAssetType(e.target.value)}
                className="w-full px-3 py-2 rounded-lg border border-border bg-background text-foreground"
              >
                <option value="">Select type (optional)</option>
                {REFERENCE_ASSET_TYPES.map((type) => (
                  <option key={type.value} value={type.value}>
                    {type.label}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-foreground mb-2">
                Description (optional)
              </label>
              <textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Enter asset description"
                rows={3}
                className="w-full px-3 py-2 rounded-lg border border-border bg-background text-foreground resize-none"
              />
            </div>
          </div>

          {/* Upload progress */}
          {isUploading && (
            <div className="space-y-2">
              <div className="flex items-center justify-between text-sm">
                <span className="text-muted-foreground">Uploading...</span>
                <span className="text-foreground">{uploadProgress}%</span>
              </div>
              <div className="w-full bg-muted rounded-full h-2">
                <div
                  className="bg-primary h-2 rounded-full transition-all"
                  style={{ width: `${uploadProgress}%` }}
                />
              </div>
            </div>
          )}

          {/* Actions */}
          <div className="flex items-center justify-end gap-3">
            <Button variant="outline" onClick={handleClose} disabled={isUploading}>
              Cancel
            </Button>
            <Button
              onClick={handleUpload}
              disabled={isUploading || files.length === 0 || !name.trim()}
              className="flex items-center gap-2"
            >
              {isUploading ? (
                <>
                  <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  Uploading...
                </>
              ) : (
                <>
                  <Upload className="w-4 h-4" />
                  Upload
                </>
              )}
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}

