import { useState, useEffect, useRef } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { Video } from 'lucide-react';
import { ProcessingSteps } from '../components/ProcessingSteps';
import { NotificationCenter, Notification } from '../components/NotificationCenter';
import { StatusResponse } from '../lib/api';
import { useVideoStatusStream } from '../lib/useVideoStatusStream';

export function VideoStatus() {
  const navigate = useNavigate();
  const { videoId } = useParams<{ videoId: string }>();
  
  // State
  const [isProcessing, setIsProcessing] = useState(false);
  const [elapsedTime, setElapsedTime] = useState(0);
  const [processingProgress, setProcessingProgress] = useState(0);
  const [animaticUrls, setAnimaticUrls] = useState<string[] | null>(null);
  const [referenceAssets, setReferenceAssets] = useState<StatusResponse['reference_assets'] | null>(null);
  const [stitchedVideoUrl, setStitchedVideoUrl] = useState<string | null>(null);
  const [currentChunkIndex, setCurrentChunkIndex] = useState<number | null>(null);
  const [totalChunks, setTotalChunks] = useState<number | null>(null);
  const [currentPhase, setCurrentPhase] = useState<string | undefined>(undefined);
  const [notifications, setNotifications] = useState<Notification[]>([]);

  // Use refs to track notification state across renders
  const hasShownAnimaticNotificationRef = useRef(false);
  const hasShownStitchedNotificationRef = useRef(false);

  // Map current_phase to processing step index
  // Phase 3 (References) is disabled - skipped in pipeline
  const getProcessingStepFromPhase = (phase: string | undefined, progress: number): number => {
    if (!phase) return 0;
    if (phase === 'phase1_validate') return 0;
    if (phase === 'phase2_storyboard' || phase === 'phase2_animatic') return 1; // Support both new and legacy phase names
    // Phase 3 (references) is disabled - skip to Phase 4
    if (phase === 'phase3_references') return 2; // Should not occur, but handle gracefully
    if (phase === 'phase3_chunks') return 2; // Moved from 3 to 2 (Phase 3 removed)
    if (phase === 'phase4_refine') return 2; // Phase 4 is part of chunk generation/refinement, keep at step 2
    return Math.min(Math.floor(progress / 25), 2); // Cap at 2 (max step index)
  };

  const getStepStatus = (stepIndex: number): 'completed' | 'processing' | 'pending' => {
    if (processingProgress > stepIndex) return 'completed';
    if (processingProgress === stepIndex) return 'processing';
    return 'pending';
  };

  const processingSteps = [
    { name: 'Content planning with AI', status: getStepStatus(0) },
    { name: 'Generating storyboard images', status: getStepStatus(1) },
    // Phase 3 (Creating reference images) is disabled - commented out
    // { name: 'Creating reference images', status: getStepStatus(2) },
    { name: 'Generating & stitching video chunks', status: getStepStatus(2) }, // Moved from 3 to 2
  ];

  const addNotification = (type: Notification['type'], title: string, message: string) => {
    const id = Math.random().toString();
    const notification: Notification = {
      id,
      type,
      title,
      message,
      timestamp: new Date(),
      read: false,
    };
    setNotifications((prev) => [notification, ...prev]);
    setTimeout(() => setNotifications((prev) => prev.filter((n) => n.id !== id)), 5000);
  };

  // Use SSE stream for real-time status updates (with automatic fallback to polling)
  const { status: streamStatus, error: streamError, isConnected } = useVideoStatusStream(
    videoId || null,
    isProcessing
  );


  // Reset notification flags and state when videoId changes
  useEffect(() => {
    if (videoId) {
      console.log('[VideoStatus] Video ID set:', videoId);
      hasShownAnimaticNotificationRef.current = false;
      hasShownStitchedNotificationRef.current = false;
      // Reset state when starting a new video
      setAnimaticUrls(null);
      setStitchedVideoUrl(null);
      setCurrentChunkIndex(null);
      setTotalChunks(null);
      setCurrentPhase(undefined);
      setProcessingProgress(0);
      setElapsedTime(0);
      setIsProcessing(true);
    }
  }, [videoId]);

  // Handle status updates from SSE stream
  useEffect(() => {
    console.log('[VideoStatus] Status update effect triggered:', {
      has_streamStatus: !!streamStatus,
      isProcessing,
      streamStatus_video_id: streamStatus?.video_id,
      videoId
    });

    if (!streamStatus) {
      console.log('[VideoStatus] No streamStatus, skipping update');
      return;
    }

    if (!isProcessing) {
      console.log('[VideoStatus] isProcessing is false, skipping update');
      return;
    }

    const status = streamStatus;
    
    console.log('[VideoStatus] Processing status update:', {
      video_id: status.video_id,
      status: status.status,
      progress: status.progress,
      current_phase: status.current_phase,
      has_animatic_urls: !!status.animatic_urls?.length,
      has_video_url: !!(status.final_video_url || status.stitched_video_url),
      chunk_progress: status.current_chunk_index !== undefined 
        ? `${status.current_chunk_index + 1}/${status.total_chunks}` 
        : null,
      timestamp: new Date().toISOString()
    });
    
    const currentStep = getProcessingStepFromPhase(status.current_phase, status.progress);
    setProcessingProgress(currentStep);
    setCurrentPhase(status.current_phase);
    
    // Update animatic URLs (allow updates if they change)
    if (status.animatic_urls && status.animatic_urls.length > 0) {
      // Only show notification on first set, but allow updates
      setAnimaticUrls(prev => {
        const isFirstTime = !prev;
        if (isFirstTime && !hasShownAnimaticNotificationRef.current) {
          hasShownAnimaticNotificationRef.current = true;
          addNotification('success', 'Storyboard Images Generated', `${status.animatic_urls!.length} storyboard image${status.animatic_urls!.length !== 1 ? 's' : ''} ready!`);
        }
        return status.animatic_urls!;
      });
    }
    
    
    // Update current chunk progress for Phase 4
    if (status.current_phase === 'phase4_chunks') {
      if (status.current_chunk_index !== undefined) {
        setCurrentChunkIndex(status.current_chunk_index);
      }
      if (status.total_chunks !== undefined) {
        setTotalChunks(status.total_chunks);
      }
    } else {
      // Clear chunk progress when Phase 4 is done
      setCurrentChunkIndex(null);
      setTotalChunks(null);
    }
    
    // Update video URLs - prefer final_video_url, fallback to stitched_video_url
    // For Veo models, Phase 5 is skipped, so final_video_url might not be set
    const videoUrl = status.final_video_url || status.stitched_video_url;
    if (videoUrl) {
      setStitchedVideoUrl(prev => {
        const isFirstTime = !prev;
        const urlChanged = prev && prev !== videoUrl;
        const isFinalVideo = !!status.final_video_url;
        
        if (isFirstTime) {
          // First time we get a video URL
          if (!hasShownStitchedNotificationRef.current) {
            hasShownStitchedNotificationRef.current = true;
            if (isFinalVideo) {
              addNotification('success', 'Video Complete', 'Your video with audio is ready!');
            } else {
              addNotification('success', 'Video Chunks Generated', 'Video chunks are being stitched together!');
            }
          }
        } else if (urlChanged && isFinalVideo) {
          // URL changed from stitched to final (Phase 5 completed for non-Veo models)
          if (!hasShownStitchedNotificationRef.current) {
            hasShownStitchedNotificationRef.current = true;
            addNotification('success', 'Video Complete', 'Your video with audio is ready!');
          }
        }
        
        return videoUrl;
      });
    }
    
    if (status.status === 'complete') {
      console.log('[VideoStatus] Video generation complete, navigating to preview');
      setIsProcessing(false);
      navigate('/preview');
    } else if (status.status === 'failed') {
      console.error('[VideoStatus] Video generation failed:', status.error);
      setIsProcessing(false);
      addNotification('error', 'Generation Failed', status.error || 'Unknown error');
    }
  }, [streamStatus, isProcessing, navigate, videoId]);

  // Handle SSE errors (fallback to polling is automatic, but log errors)
  useEffect(() => {
    if (streamError) {
      console.error('[VideoStatus] SSE stream error:', streamError);
      // Fallback to polling happens automatically in the hook
    }
  }, [streamError]);

  // Elapsed time counter
  useEffect(() => {
    let interval: NodeJS.Timeout;
    if (isProcessing) {
      interval = setInterval(() => {
        setElapsedTime(t => t + 1);
      }, 1000);
    }
    return () => clearInterval(interval);
  }, [isProcessing]);


  return (
    <>
      <NotificationCenter
        notifications={notifications}
        onDismiss={(id) => setNotifications((prev) => prev.filter((n) => n.id !== id))}
      />

      <div className="card p-8 text-center animate-fade-in">
        <div className="inline-flex items-center justify-center w-20 h-20 bg-primary/20 rounded-full mb-6 animate-pulse-subtle">
          <Video className="w-10 h-10 text-primary" />
        </div>
        <h2 className="text-2xl font-bold text-foreground mb-2">
          AI is Creating Your Video
        </h2>
        <p className="text-muted-foreground mb-8">
          Sit back and relax while our AI works its magic...
        </p>

        <div className="max-w-md mx-auto text-left mb-8">
          <ProcessingSteps steps={processingSteps} elapsedTime={elapsedTime} />
        </div>

        {animaticUrls && animaticUrls.length > 0 && (
          <div className="mt-8 pt-8 border-t border-border">
            <div className="flex items-center justify-between mb-6">
              <div>
                <h3 className="text-xl font-bold text-foreground mb-1">
                  🎬 Storyboard Images Generated
                </h3>
                <p className="text-sm text-muted-foreground">
                  {animaticUrls.length} storyboard image{animaticUrls.length !== 1 ? 's' : ''} ready for video generation
                  {currentChunkIndex !== null && totalChunks !== null && (
                    <span className="ml-2 text-primary font-semibold">
                      • Processing chunk {currentChunkIndex + 1} of {totalChunks}
                    </span>
                  )}
                </p>
              </div>
            </div>
            
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 max-w-4xl mx-auto">
              {animaticUrls.map((url, idx) => {
                const isProcessingChunk = currentChunkIndex === idx && currentPhase === 'phase4_chunks';
                // Chunk is completed if currentChunkIndex is past this chunk's index
                // Or if Phase 4 is complete (currentPhase is not phase4_chunks and we have a final video)
                const isCompleted = (currentChunkIndex !== null && idx < currentChunkIndex) ||
                                   (currentPhase !== 'phase4_chunks' && currentChunkIndex !== null && idx <= currentChunkIndex) ||
                                   (stitchedVideoUrl && currentPhase !== 'phase4_chunks');
                
                return (
                  <div key={idx} className="relative group">
                    <div className={`relative ${isProcessingChunk ? 'animate-pulse' : ''}`}>
                      <img
                        src={url}
                        alt={`Storyboard image ${idx + 1}`}
                        className={`w-full h-32 object-cover rounded-lg border-2 shadow-md group-hover:scale-105 transition-transform cursor-pointer ${
                          isProcessingChunk
                            ? 'border-primary ring-4 ring-primary/30'
                            : isCompleted
                            ? 'border-primary'
                            : 'border-border'
                        }`}
                        onClick={() => window.open(url, '_blank')}
                        onError={(e) => {
                          e.currentTarget.src = 'https://via.placeholder.com/200x200?text=Image+Not+Available';
                        }}
                      />
                      {isProcessingChunk && (
                        <div className="absolute inset-0 bg-primary/20 rounded-lg flex items-center justify-center">
                          <div className="animate-spin rounded-full h-8 w-8 border-4 border-primary border-t-transparent"></div>
                        </div>
                      )}
                      {isCompleted && (
                        <div className="absolute top-2 right-2 bg-primary rounded-full p-1">
                          <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                          </svg>
                        </div>
                      )}
                    </div>
                    <div className="absolute bottom-2 right-2 bg-black bg-opacity-50 text-white text-xs px-2 py-1 rounded opacity-0 group-hover:opacity-100 transition-opacity">
                      Beat {idx + 1}
                      {isProcessingChunk && ' • Processing...'}
                      {isCompleted && ' • Complete'}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Phase 3 (Reference Assets) */}
        {referenceAssets && (
          <div className="mt-8 pt-8 border-t border-border">
            <h3 className="text-lg font-semibold text-foreground mb-4">
              Reference Assets Generated
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 max-w-2xl mx-auto">
              {referenceAssets.style_guide_url && (
                <div className="bg-card rounded-lg p-4">
                  <p className="text-sm font-medium text-card-foreground mb-2">Style Guide</p>
                  <img 
                    src={referenceAssets.style_guide_url} 
                    alt="Style Guide"
                    className="w-full h-48 object-cover rounded-lg border border-border"
                    onError={(e) => {
                      e.currentTarget.src = 'https://via.placeholder.com/400x400?text=Style+Guide';
                    }}
                  />
                </div>
              )}
              {referenceAssets.product_reference_url && (
                <div className="bg-card rounded-lg p-4">
                  <p className="text-sm font-medium text-card-foreground mb-2">Product Reference</p>
                  <img 
                    src={referenceAssets.product_reference_url} 
                    alt="Product Reference"
                    className="w-full h-48 object-cover rounded-lg border border-border"
                    onError={(e) => {
                      e.currentTarget.src = 'https://via.placeholder.com/400x400?text=Product+Reference';
                    }}
                  />
                </div>
              )}
            </div>
            {referenceAssets.uploaded_assets && referenceAssets.uploaded_assets.length > 0 && (
              <div className="mt-4">
                <p className="text-sm font-medium text-card-foreground mb-2">
                  Uploaded Assets ({referenceAssets.uploaded_assets.length})
                </p>
                <div className="grid grid-cols-3 gap-2">
                  {referenceAssets.uploaded_assets.map((asset, idx) => (
                    <img
                      key={idx}
                      src={asset.s3_url}
                      alt={`Uploaded asset ${idx + 1}`}
                      className="w-full h-24 object-cover rounded border border-border"
                      onError={(e) => {
                        e.currentTarget.src = 'https://via.placeholder.com/200x200?text=Asset';
                      }}
                    />
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </>
  );
}

