import React, { useState, useEffect } from 'react';
import { Play, Pause, Loader2 } from 'lucide-react';
import { api, ChunkMetadata, ChunkVersion } from '../../lib/api';
import { Button } from '@/components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';

interface ChunkPreviewProps {
  videoId: string;
  chunk: ChunkMetadata;
  onVersionChange: () => void;
}

export function ChunkPreview({ videoId, chunk, onVersionChange }: ChunkPreviewProps) {
  const [selectedVersion, setSelectedVersion] = useState<string>(chunk.current_version);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [isLoadingPreview, setIsLoadingPreview] = useState(false);
  const [isPlaying, setIsPlaying] = useState(false);
  const videoRef = React.useRef<HTMLVideoElement | null>(null);

  useEffect(() => {
    loadPreviewUrl(selectedVersion);
  }, [selectedVersion, videoId, chunk.chunk_index]);

  const loadPreviewUrl = async (version: string) => {
    setIsLoadingPreview(true);
    setPreviewUrl(null); // Clear previous URL
    try {
      const response = await api.getChunkPreview(videoId, chunk.chunk_index, version);
      if (response.preview_url) {
        setPreviewUrl(response.preview_url);
      } else {
        console.error('No preview URL returned from API');
      }
    } catch (error: any) {
      console.error('Failed to load preview:', error);
      setPreviewUrl(null);
    } finally {
      setIsLoadingPreview(false);
    }
  };

  const handleVersionSelect = async (version: string) => {
    setSelectedVersion(version);
  };

  const handleSelectVersion = async () => {
    try {
      await api.selectChunkVersion(videoId, chunk.chunk_index, selectedVersion);
      onVersionChange();
    } catch (error: any) {
      console.error('Failed to select version:', error);
    }
  };

  const currentVersionData = chunk.versions.find((v) => v.version_id === selectedVersion);
  const isCurrentSelected = currentVersionData?.is_selected || false;

  return (
    <div className="space-y-4">
      {/* Version Selector */}
      <div className="flex items-center gap-4">
        <label className="text-sm font-medium">Version:</label>
        <Select value={selectedVersion} onValueChange={handleVersionSelect}>
          <SelectTrigger className="w-[200px]">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {chunk.versions.map((version) => (
              <SelectItem key={version.version_id} value={version.version_id}>
                <div className="flex items-center gap-2">
                  <span>{version.version_id}</span>
                  {version.is_selected && (
                    <Badge variant="default" className="text-xs">
                      Selected
                    </Badge>
                  )}
                </div>
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        {!isCurrentSelected && (
          <Button onClick={handleSelectVersion} size="sm">
            Select This Version
          </Button>
        )}
      </div>

      {/* Video Preview */}
      <div className="relative aspect-video bg-black rounded-lg overflow-hidden">
        {isLoadingPreview ? (
          <div className="absolute inset-0 flex items-center justify-center">
            <Loader2 className="w-8 h-8 animate-spin text-primary" />
          </div>
        ) : previewUrl ? (
          <>
            <video
              ref={videoRef}
              src={previewUrl}
              className="w-full h-full object-contain"
              controls
              onPlay={() => setIsPlaying(true)}
              onPause={() => setIsPlaying(false)}
            />
            {!isPlaying && (
              <div className="absolute inset-0 flex items-center justify-center bg-black/50">
                <button
                  onClick={() => {
                    videoRef.current?.play();
                  }}
                  className="p-4 rounded-full bg-primary hover:bg-primary/90 transition-colors"
                >
                  <Play className="w-8 h-8 text-white" />
                </button>
              </div>
            )}
          </>
        ) : (
          <div className="absolute inset-0 flex items-center justify-center text-muted-foreground">
            No preview available
          </div>
        )}
      </div>

      {/* Version Info */}
      {currentVersionData && (
        <div className="space-y-2 text-sm">
          <div className="flex items-center gap-4">
            <div>
              <span className="text-muted-foreground">Model: </span>
              <span className="font-medium">{currentVersionData.model || chunk.model}</span>
            </div>
            {currentVersionData.cost && (
              <div>
                <span className="text-muted-foreground">Cost: </span>
                <span className="font-medium">${currentVersionData.cost.toFixed(4)}</span>
              </div>
            )}
            {currentVersionData.created_at && (
              <div>
                <span className="text-muted-foreground">Created: </span>
                <span className="font-medium">
                  {new Date(currentVersionData.created_at).toLocaleDateString()}
                </span>
              </div>
            )}
          </div>
          {currentVersionData.prompt && (
            <div>
              <span className="text-muted-foreground">Prompt: </span>
              <span className="font-medium">{currentVersionData.prompt}</span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

