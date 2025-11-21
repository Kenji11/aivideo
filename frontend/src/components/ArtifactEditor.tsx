import { useState, useRef } from 'react';
import { CheckpointInfo } from '../lib/api';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from './ui/dialog';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Label } from './ui/label';
import { Badge } from './ui/badge';
import { Upload, RefreshCw } from 'lucide-react';
import { uploadBeatImage, regenerateBeat, regenerateChunk } from '../lib/api';
import { useToast } from '../hooks/use-toast';

interface ArtifactEditorProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  checkpoint: CheckpointInfo | null;
  videoId: string;
  onArtifactUpdated?: (artifact: any) => void;
}

export function ArtifactEditor({
  open,
  onOpenChange,
  checkpoint,
  videoId,
  onArtifactUpdated,
}: ArtifactEditorProps) {
  const { toast } = useToast();
  const [isLoading, setIsLoading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [selectedBeatIndex, setSelectedBeatIndex] = useState<number | null>(null);
  const [promptOverride, setPromptOverride] = useState('');

  if (!checkpoint) {
    return null;
  }

  // TODO: Implement spec editing functionality
  // const handleEditSpec = async () => {
  //   if (checkpoint.phase_number !== 1) return;
  //   setIsLoading(true);
  //   try {
  //     // For now, just a placeholder - you'd need a full spec editing UI
  //     toast({
  //       title: 'Spec Editing',
  //       description: 'Full spec editing UI coming soon. Use the continue button to proceed.',
  //     });
  //     onOpenChange(false);
  //   } catch (error: any) {
  //     toast({
  //       variant: 'destructive',
  //       title: 'Failed to edit spec',
  //       description: error.message,
  //     });
  //   } finally {
  //     setIsLoading(false);
  //   }
  // };

  const handleUploadImage = async (beatIndex: number, file: File) => {
    if (checkpoint.phase_number !== 2) return;

    setIsLoading(true);
    try {
      const result = await uploadBeatImage(videoId, checkpoint.checkpoint_id, beatIndex, file);
      toast({
        title: 'Image Uploaded',
        description: `Beat ${beatIndex} updated to version ${result.version}`,
      });
      onArtifactUpdated?.(result);
      onOpenChange(false);
    } catch (error: any) {
      toast({
        variant: 'destructive',
        title: 'Upload failed',
        description: error.message,
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleRegenerateBeat = async (beatIndex: number) => {
    if (checkpoint.phase_number !== 2) return;

    setIsLoading(true);
    try {
      const result = await regenerateBeat(videoId, checkpoint.checkpoint_id, {
        beat_index: beatIndex,
        prompt_override: promptOverride || undefined,
      });
      toast({
        title: 'Beat Regenerated',
        description: `Beat ${beatIndex} regenerated as version ${result.version}`,
      });
      onArtifactUpdated?.(result);
      setPromptOverride('');
      onOpenChange(false);
    } catch (error: any) {
      toast({
        variant: 'destructive',
        title: 'Regeneration failed',
        description: error.message,
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleRegenerateChunk = async (chunkIndex: number) => {
    if (checkpoint.phase_number !== 3) return;

    setIsLoading(true);
    try {
      const result = await regenerateChunk(videoId, checkpoint.checkpoint_id, {
        chunk_index: chunkIndex,
      });
      toast({
        title: 'Chunk Regenerated',
        description: `Chunk ${chunkIndex} regenerated as version ${result.version}`,
      });
      onArtifactUpdated?.(result);
      onOpenChange(false);
    } catch (error: any) {
      toast({
        variant: 'destructive',
        title: 'Regeneration failed',
        description: error.message,
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file && selectedBeatIndex !== null) {
      handleUploadImage(selectedBeatIndex, file);
    }
  };

  const beatArtifacts = Object.values(checkpoint.artifacts || {})
    .filter((a) => a.artifact_type === 'beat_image')
    .sort((a, b) => a.artifact_key.localeCompare(b.artifact_key));

  const chunkArtifacts = Object.values(checkpoint.artifacts || {})
    .filter((a) => a.artifact_type === 'video_chunk')
    .sort((a, b) => a.artifact_key.localeCompare(b.artifact_key));

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-3xl max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Edit Artifacts - Phase {checkpoint.phase_number}</DialogTitle>
          <DialogDescription>
            Make changes to your artifacts. Editing will create a new version and branch when you continue.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-6 py-4">
          {/* Phase 1: Spec Editing */}
          {checkpoint.phase_number === 1 && (
            <div className="space-y-3">
              <h3 className="font-semibold">Video Specification</h3>
              <p className="text-sm text-muted-foreground">
                Spec editing UI is coming soon. For now, you can continue to the next phase.
              </p>
            </div>
          )}

          {/* Phase 2: Storyboard Images */}
          {checkpoint.phase_number === 2 && beatArtifacts.length > 0 && (
            <div className="space-y-3">
              <h3 className="font-semibold">Storyboard Images</h3>
              <div className="grid grid-cols-2 gap-4">
                {beatArtifacts.map((artifact, idx) => (
                  <div key={artifact.id} className="space-y-2">
                    <div className="relative">
                      <img
                        src={artifact.s3_url}
                        alt={`Beat ${idx}`}
                        className="rounded-lg border-2 border-primary w-full aspect-video object-cover"
                      />
                      <Badge variant="secondary" className="absolute top-2 right-2">
                        Beat {idx} - v{artifact.version}
                      </Badge>
                    </div>
                    <div className="space-y-2">
                      <Button
                        variant="outline"
                        size="sm"
                        className="w-full"
                        onClick={() => {
                          setSelectedBeatIndex(idx);
                          fileInputRef.current?.click();
                        }}
                        disabled={isLoading}
                      >
                        <Upload className="h-4 w-4 mr-2" />
                        Upload New Image
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        className="w-full"
                        onClick={() => handleRegenerateBeat(idx)}
                        disabled={isLoading}
                      >
                        <RefreshCw className="h-4 w-4 mr-2" />
                        Regenerate
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
              <div className="space-y-2">
                <Label>Custom Prompt (Optional)</Label>
                <Input
                  value={promptOverride}
                  onChange={(e) => setPromptOverride(e.target.value)}
                  placeholder="Override prompt for regeneration..."
                  disabled={isLoading}
                />
                <p className="text-xs text-muted-foreground">
                  Leave empty to use the original prompt
                </p>
              </div>
              <input
                ref={fileInputRef}
                type="file"
                accept="image/*"
                className="hidden"
                onChange={handleFileSelect}
              />
            </div>
          )}

          {/* Phase 3: Video Chunks */}
          {checkpoint.phase_number === 3 && chunkArtifacts.length > 0 && (
            <div className="space-y-3">
              <h3 className="font-semibold">Video Chunks</h3>
              <div className="grid grid-cols-2 gap-4">
                {chunkArtifacts.map((artifact, idx) => (
                  <div key={artifact.id} className="space-y-2">
                    <div className="relative">
                      <video
                        src={artifact.s3_url}
                        className="rounded-lg border-2 border-primary w-full aspect-video object-cover"
                        controls
                      />
                      <Badge variant="secondary" className="absolute top-2 right-2">
                        Chunk {idx} - v{artifact.version}
                      </Badge>
                    </div>
                    <Button
                      variant="outline"
                      size="sm"
                      className="w-full"
                      onClick={() => handleRegenerateChunk(idx)}
                      disabled={isLoading}
                    >
                      <RefreshCw className="h-4 w-4 mr-2" />
                      Regenerate Chunk
                    </Button>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Phase 4: Final Video (No editing) */}
          {checkpoint.phase_number === 4 && (
            <div className="space-y-3">
              <h3 className="font-semibold">Final Video</h3>
              <p className="text-sm text-muted-foreground">
                The final video is complete. No editing available at this stage.
              </p>
            </div>
          )}
        </div>

        <DialogFooter>
          <Button variant="secondary" onClick={() => onOpenChange(false)} disabled={isLoading}>
            Close
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
