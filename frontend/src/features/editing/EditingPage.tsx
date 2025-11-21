import { useState, useEffect, useRef } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { ArrowLeft, Loader2 } from 'lucide-react';
import { api, ChunksListResponse, ChunkMetadata } from '../../lib/api';
import { toast } from '@/hooks/use-toast';
import { ChunkTimeline } from './ChunkTimeline';
import { ChunkPreview } from './ChunkPreview';
import { EditActions } from './EditActions';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';

export function EditingPage() {
  const navigate = useNavigate();
  const { videoId } = useParams<{ videoId: string }>();
  
  const [chunks, setChunks] = useState<ChunkMetadata[]>([]);
  const [selectedChunks, setSelectedChunks] = useState<number[]>([]);
  const [selectedChunkIndex, setSelectedChunkIndex] = useState<number | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isProcessing, setIsProcessing] = useState(false);
  const [stitchedVideoUrl, setStitchedVideoUrl] = useState<string | null>(null);
  const loadingAbortControllerRef = useRef<AbortController | null>(null);
  const isLoadingRef = useRef(false);

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
    
    // Cleanup on unmount
    return () => {
      if (loadingAbortControllerRef.current) {
        loadingAbortControllerRef.current.abort();
      }
    };
  }, [videoId]);

  const loadChunks = async () => {
    if (!videoId) return;
    
    // Prevent multiple simultaneous loads
    if (isLoadingRef.current) {
      return;
    }
    
    // Abort any previous request
    if (loadingAbortControllerRef.current) {
      loadingAbortControllerRef.current.abort();
    }
    
    // Create new abort controller
    const abortController = new AbortController();
    loadingAbortControllerRef.current = abortController;
    
    isLoadingRef.current = true;
    setIsLoading(true);
    
    try {
      console.log('[EditingPage] Loading chunks for video:', videoId);
      const startTime = Date.now();
      
      const response: ChunksListResponse = await api.getChunks(videoId);
      
      const loadTime = Date.now() - startTime;
      console.log(`[EditingPage] Chunks loaded in ${loadTime}ms, got ${response.chunks.length} chunks`);
      console.log('[EditingPage] Chunks data:', response.chunks);
      
      // Check if this is still the current request (not aborted or replaced)
      const isCurrentRequest = loadingAbortControllerRef.current === abortController;
      const wasAborted = abortController.signal.aborted;
      
      if (wasAborted && !isCurrentRequest) {
        console.log('[EditingPage] Request was replaced by a new one, skipping state update');
        isLoadingRef.current = false;
        setIsLoading(false);
        return;
      }
      
      // Validate chunks data
      if (!response.chunks || response.chunks.length === 0) {
        console.warn('[EditingPage] No chunks in response');
        toast({
          variant: 'destructive',
          title: 'No Chunks',
          description: 'No chunks found for this video',
        });
        isLoadingRef.current = false;
        setIsLoading(false);
        return;
      }
      
      // Update state with chunks data (even if aborted, as long as it's still the current request)
      // The abort might have been from cleanup, but if fetch completed, we should update
      setChunks(response.chunks);
      setStitchedVideoUrl(response.stitched_video_url || null);
      console.log('[EditingPage] Chunks state updated, chunks.length:', response.chunks.length);
      
      // Set loading to false after successful load
      isLoadingRef.current = false;
      setIsLoading(false);
      console.log('[EditingPage] Loading state set to false');
    } catch (error: any) {
      // Ignore abort errors
      if (error.name === 'AbortError' || abortController.signal.aborted) {
        console.log('[EditingPage] Request was aborted in catch, skipping state update');
        isLoadingRef.current = false;
        setIsLoading(false);
        return;
      }
      console.error('[EditingPage] Error loading chunks:', error);
      toast({
        variant: 'destructive',
        title: 'Error',
        description: error.message || 'Failed to load chunks',
      });
      isLoadingRef.current = false;
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
    // Use a small delay to allow any ongoing video loads to complete
    setTimeout(() => {
      loadChunks();
      setSelectedChunks([]);
      setSelectedChunkIndex(null);
    }, 100);
  };

  const handleProceedToRefinement = () => {
    if (!videoId) return;
    // Navigate to processing page to continue with Phase 4
    navigate(`/processing/${videoId}`);
  };

  // Debug: Log current state
  console.log('[EditingPage] Render - isLoading:', isLoading, 'chunks.length:', chunks.length);

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
            <Card className="p-6">
              <h2 className="text-xl font-semibold mb-4">Chunk Timeline</h2>
              {chunks.length === 0 ? (
                <div className="text-center py-8 text-muted-foreground">
                  No chunks available. Please wait for chunks to load.
                </div>
              ) : (
                <ChunkTimeline
                  chunks={chunks}
                  selectedChunks={selectedChunks}
                  onChunkSelect={handleChunkSelect}
                  onReorder={(newOrder) => {
                    // Handle reorder
                    console.log('Reorder:', newOrder);
                  }}
                />
              )}
            </Card>

            {/* Chunk Preview */}
            {selectedChunkIndex !== null && selectedChunkIndex < chunks.length && (
              <Card className="p-6">
                <h2 className="text-xl font-semibold mb-4">
                  Chunk {selectedChunkIndex + 1} Preview
                </h2>
                <ChunkPreview
                  videoId={videoId!}
                  chunk={chunks[selectedChunkIndex]}
                  onVersionChange={handleEditComplete}
                />
              </Card>
            )}
          </div>

          {/* Right Column: Edit Actions */}
          <div className="lg:col-span-1">
            <Card className="p-6 sticky top-4">
              <h2 className="text-xl font-semibold mb-4">Edit Actions</h2>
              <EditActions
                videoId={videoId!}
                selectedChunks={selectedChunks}
                chunks={chunks}
                onEditComplete={handleEditComplete}
                onProcessingChange={setIsProcessing}
              />
            </Card>
          </div>
        </div>
      </div>
    </div>
  );
}

