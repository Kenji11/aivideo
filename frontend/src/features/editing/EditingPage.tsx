import { useState, useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { ArrowLeft, Loader2 } from 'lucide-react';
import { api, ChunksListResponse, ChunkMetadata } from '../../lib/api';
import { toast } from '@/hooks/use-toast';
import { ChunkTimeline } from './ChunkTimeline';
import { ChunkPreview } from './ChunkPreview';
import { EditActions } from './EditActions';
import { Button } from '@/components/ui/button';

export function EditingPage() {
  const navigate = useNavigate();
  const { videoId } = useParams<{ videoId: string }>();
  
  const [chunks, setChunks] = useState<ChunkMetadata[]>([]);
  const [selectedChunks, setSelectedChunks] = useState<number[]>([]);
  const [selectedChunkIndex, setSelectedChunkIndex] = useState<number | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isProcessing, setIsProcessing] = useState(false);
  const [stitchedVideoUrl, setStitchedVideoUrl] = useState<string | null>(null);

  useEffect(() => {
    if (!videoId) {
      toast({
        variant: 'destructive',
        title: 'Error',
        description: 'No video ID provided',
      });
      navigate('/projects');
      return;
    }

    loadChunks();
  }, [videoId]);

  const loadChunks = async () => {
    if (!videoId) return;
    
    setIsLoading(true);
    try {
      const response: ChunksListResponse = await api.getChunks(videoId);
      setChunks(response.chunks);
      setStitchedVideoUrl(response.stitched_video_url || null);
    } catch (error: any) {
      toast({
        variant: 'destructive',
        title: 'Error',
        description: error.message || 'Failed to load chunks',
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleChunkSelect = (chunkIndex: number, multiSelect: boolean = false) => {
    if (multiSelect) {
      setSelectedChunks((prev) =>
        prev.includes(chunkIndex)
          ? prev.filter((idx) => idx !== chunkIndex)
          : [...prev, chunkIndex]
      );
    } else {
      setSelectedChunks([chunkIndex]);
      setSelectedChunkIndex(chunkIndex);
    }
  };

  const handleEditComplete = () => {
    // Reload chunks after editing
    loadChunks();
    setSelectedChunks([]);
    setSelectedChunkIndex(null);
  };

  const handleProceedToRefinement = () => {
    if (!videoId) return;
    // Navigate to processing page to continue with Phase 4
    navigate(`/processing/${videoId}`);
  };

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="w-12 h-12 animate-spin mx-auto mb-4 text-primary" />
          <p className="text-muted-foreground">Loading chunks...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background">
      <div className="container mx-auto px-4 py-8">
        {/* Header */}
        <div className="mb-6 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Button
              variant="ghost"
              onClick={() => navigate(-1)}
              className="flex items-center gap-2"
            >
              <ArrowLeft className="w-4 h-4" />
              Back
            </Button>
            <div>
              <h1 className="text-3xl font-bold text-foreground">Edit Video Chunks</h1>
              <p className="text-muted-foreground mt-1">
                Select chunks to replace, reorder, delete, or split
              </p>
            </div>
          </div>
          {stitchedVideoUrl && (
            <Button
              onClick={handleProceedToRefinement}
              disabled={isProcessing}
              className="flex items-center gap-2"
            >
              Proceed to Refinement
            </Button>
          )}
        </div>

        {/* Main Content */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left Column: Timeline */}
          <div className="lg:col-span-2 space-y-6">
            {/* Chunk Timeline */}
            <div className="card p-6">
              <h2 className="text-xl font-semibold mb-4">Chunk Timeline</h2>
              <ChunkTimeline
                chunks={chunks}
                selectedChunks={selectedChunks}
                onChunkSelect={handleChunkSelect}
                onReorder={(newOrder) => {
                  // Handle reorder
                  console.log('Reorder:', newOrder);
                }}
              />
            </div>

            {/* Chunk Preview */}
            {selectedChunkIndex !== null && selectedChunkIndex < chunks.length && (
              <div className="card p-6">
                <h2 className="text-xl font-semibold mb-4">
                  Chunk {selectedChunkIndex + 1} Preview
                </h2>
                <ChunkPreview
                  videoId={videoId!}
                  chunk={chunks[selectedChunkIndex]}
                  onVersionChange={handleEditComplete}
                />
              </div>
            )}
          </div>

          {/* Right Column: Edit Actions */}
          <div className="lg:col-span-1">
            <div className="card p-6 sticky top-4">
              <h2 className="text-xl font-semibold mb-4">Edit Actions</h2>
              <EditActions
                videoId={videoId!}
                selectedChunks={selectedChunks}
                chunks={chunks}
                onEditComplete={handleEditComplete}
                onProcessingChange={setIsProcessing}
              />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

