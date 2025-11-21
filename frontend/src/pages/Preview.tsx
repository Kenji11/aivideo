import { useState, useEffect, useCallback } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { Film, Download, BarChart3, ChevronDown, ChevronUp, Image as ImageIcon, Video, FileText, Sparkles } from 'lucide-react';
import { getVideoStatus, getVideo, StatusResponse, VideoResponse } from '../lib/api';
import { toast } from '@/hooks/use-toast';

interface PhaseArtifacts {
  phase1?: {
    spec?: any;
  };
  phase2?: {
    storyboardUrls?: string[];
  };
  phase3?: {
    chunkUrls?: string[];
    stitchedVideoUrl?: string;
  };
  phase4?: {
    finalVideoUrl?: string;
  };
}

export function Preview() {
  const navigate = useNavigate();
  const { videoId } = useParams<{ videoId: string }>();
  
  const [videoUrl, setVideoUrl] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [retryCount, setRetryCount] = useState(0);
  const [phaseArtifacts, setPhaseArtifacts] = useState<PhaseArtifacts>({});
  const [expandedPhases, setExpandedPhases] = useState<Set<string>>(new Set());

  const fetchVideoData = useCallback(async (isRetry: boolean = false) => {
    if (!videoId) {
      setError('No video ID provided');
      setIsLoading(false);
      return;
    }

    setIsLoading(true);
    if (!isRetry) {
      setError(null);
    }
    
    try {
      // Fetch both video details and status to get all phase data
      let videoData: VideoResponse | null = null;
      let statusData: StatusResponse | null = null;

      try {
        videoData = await getVideo(videoId);
      } catch (err) {
        console.log('[Preview] getVideo failed, will try status endpoint:', err);
      }

      try {
        statusData = await getVideoStatus(videoId);
      } catch (err) {
        console.error('[Preview] getVideoStatus failed:', err);
      }

      // Extract video URL
      const url = statusData?.final_video_url || statusData?.stitched_video_url || videoData?.final_video_url;
      if (url) {
        setVideoUrl(url);
      } else if (!statusData && !videoData) {
        setError('Video is not ready yet. Please wait for generation to complete.');
      }

      // Extract phase artifacts
      const artifacts: PhaseArtifacts = {};

      // Phase 1: Spec (from videoData or statusData)
      if (videoData?.spec) {
        artifacts.phase1 = { spec: videoData.spec };
      }

      // Phase 2: Storyboard images (from statusData)
      if (statusData?.storyboard_urls && statusData.storyboard_urls.length > 0) {
        artifacts.phase2 = { storyboardUrls: statusData.storyboard_urls };
      }

      // Phase 3: Individual chunk videos (from statusData)
      if (statusData?.chunk_urls && statusData.chunk_urls.length > 0) {
        artifacts.phase3 = {
          chunkUrls: statusData.chunk_urls,
        };
      }

      // Phase 4/5: Final video
      if (statusData?.final_video_url || videoData?.final_video_url) {
        artifacts.phase4 = {
          finalVideoUrl: statusData?.final_video_url || videoData?.final_video_url,
        };
      }

      setPhaseArtifacts(artifacts);
    } catch (err) {
      console.error('[Preview] Failed to fetch video data:', err);
      setError(err instanceof Error ? err.message : 'Failed to load video');
    } finally {
      setIsLoading(false);
    }
  }, [videoId]);

  useEffect(() => {
    fetchVideoData();
  }, [fetchVideoData]);

  const handleDownload = () => {
    if (videoUrl) {
      const link = document.createElement('a');
      link.href = videoUrl;
      link.download = `${videoId || 'video'}.mp4`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      toast({
        variant: 'default',
        title: 'Download Started',
        description: 'Your video download has started',
      });
    } else {
      toast({
        variant: 'destructive',
        title: 'Video Not Ready',
        description: 'Video is still processing',
      });
    }
  };

  const togglePhase = (phase: string) => {
    const newExpanded = new Set(expandedPhases);
    if (newExpanded.has(phase)) {
      newExpanded.delete(phase);
    } else {
      newExpanded.add(phase);
    }
    setExpandedPhases(newExpanded);
  };

  if (isLoading) {
    return (
      <div className="card overflow-hidden animate-fade-in">
        <div className="aspect-video bg-gradient-to-br from-card to-muted flex items-center justify-center">
          <div className="text-center text-white">
            <div className="inline-block animate-spin rounded-full h-12 w-12 border-4 border-primary border-t-transparent mb-4"></div>
            <p className="text-lg font-medium opacity-75">Loading video...</p>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="card overflow-hidden animate-fade-in">
        <div className="aspect-video bg-gradient-to-br from-card to-muted flex items-center justify-center">
          <div className="text-center text-white">
            <Film className="w-20 h-20 mx-auto mb-4 opacity-50" />
            <p className="text-lg font-medium opacity-75">{error}</p>
            <div className="mt-4 flex gap-2 justify-center">
              <button
                onClick={() => {
                  setRetryCount(0);
                  fetchVideoData();
                }}
                className="px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90"
              >
                Retry
              </button>
              <button
                onClick={() => navigate('/projects')}
                className="px-4 py-2 bg-secondary text-secondary-foreground rounded-lg hover:bg-secondary/90"
              >
                Back to Projects
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="card overflow-hidden animate-fade-in">
      <div className="aspect-video bg-gradient-to-br from-card to-muted flex items-center justify-center">
        {videoUrl ? (
          <video
            key={videoUrl} // Force re-render when URL changes
            src={videoUrl}
            controls
            className="w-full h-full object-contain"
            onError={(e) => {
              const videoElement = e.currentTarget;
              const errorCode = videoElement.error?.code;
              const errorMessage = videoElement.error?.message || 'Unknown error';
              
              console.error('Video load error:', {
                errorCode,
                errorMessage,
                videoUrl,
                networkState: videoElement.networkState,
                readyState: videoElement.readyState
              });

              // Error code 4 = MEDIA_ERR_SRC_NOT_SUPPORTED
              // This usually means Content-Type is wrong or file doesn't exist
              if (errorCode === 4) {
                // Try refreshing the URL first (might be expired or Content-Type issue)
                if (retryCount < 2 && videoUrl.includes('X-Amz-Signature')) {
                  console.log('[Preview] Video format error detected, refreshing URL...');
                  setRetryCount(retryCount + 1);
                  fetchVideoData(true);
                } else {
                  setError('Video format error. The video file may be corrupted or have incorrect metadata. Please try regenerating the video.');
                }
              } else if (retryCount < 2 && videoUrl.includes('X-Amz-Signature')) {
                // Other errors - try refreshing presigned URL
                console.log('[Preview] Presigned URL may be expired, refreshing...');
                setRetryCount(retryCount + 1);
                fetchVideoData(true);
              } else {
                setError(`Failed to load video: ${errorMessage || 'The video file may not be available.'}`);
              }
            }}
            onLoadedData={() => {
              // Reset retry count on successful load
              if (retryCount > 0) {
                setRetryCount(0);
              }
            }}
          >
            Your browser does not support the video tag.
          </video>
        ) : (
          <div className="text-center text-white">
            <Film className="w-20 h-20 mx-auto mb-4 opacity-50 animate-float" />
            <p className="text-lg font-medium opacity-75">Your Video is Ready</p>
            <p className="text-sm opacity-50 mt-2">Loading video...</p>
          </div>
        )}
      </div>
      <div className="p-8 space-y-6">
        <div>
          <h2 className="text-2xl font-bold text-foreground mb-2">
            Video Preview
          </h2>
          {videoId && (
            <p className="text-sm text-muted-foreground font-mono">
              {videoId}
            </p>
          )}
        </div>

        <div className="grid grid-cols-2 gap-4 p-4 bg-card rounded-lg">
          <div>
            <p className="text-xs text-muted-foreground">Duration</p>
            <p className="text-lg font-semibold text-foreground">2:45</p>
          </div>
          <div>
            <p className="text-xs text-muted-foreground">Resolution</p>
            <p className="text-lg font-semibold text-foreground">1080p</p>
          </div>
        </div>

        {/* Phase Artifacts Section */}
        {(phaseArtifacts.phase1 || phaseArtifacts.phase2 || phaseArtifacts.phase3 || phaseArtifacts.phase4) && (
          <div className="space-y-4">
            <h3 className="text-xl font-semibold text-foreground">Generation Phases & Artifacts</h3>
            
            {/* Phase 1: Validation & Spec */}
            {phaseArtifacts.phase1 && (
              <div className="border border-border rounded-lg overflow-hidden">
                <button
                  onClick={() => togglePhase('phase1')}
                  className="w-full px-4 py-3 bg-card hover:bg-muted/50 flex items-center justify-between transition-colors"
                >
                  <div className="flex items-center space-x-3">
                    <Sparkles className="w-5 h-5 text-primary" />
                    <span className="font-medium text-foreground">Phase 1: Validation & Spec</span>
                  </div>
                  {expandedPhases.has('phase1') ? (
                    <ChevronUp className="w-5 h-5 text-muted-foreground" />
                  ) : (
                    <ChevronDown className="w-5 h-5 text-muted-foreground" />
                  )}
                </button>
                {expandedPhases.has('phase1') && (
                  <div className="p-4 border-t border-border bg-muted/30">
                    <div className="space-y-2">
                      <div className="flex items-center space-x-2 text-sm text-muted-foreground mb-2">
                        <FileText className="w-4 h-4" />
                        <span>Video Specification</span>
                      </div>
                      <pre className="text-xs bg-background p-3 rounded border border-border overflow-auto max-h-64">
                        {JSON.stringify(phaseArtifacts.phase1.spec, null, 2)}
                      </pre>
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Phase 2: Storyboard */}
            {phaseArtifacts.phase2 && phaseArtifacts.phase2.storyboardUrls && phaseArtifacts.phase2.storyboardUrls.length > 0 && (
              <div className="border border-border rounded-lg overflow-hidden">
                <button
                  onClick={() => togglePhase('phase2')}
                  className="w-full px-4 py-3 bg-card hover:bg-muted/50 flex items-center justify-between transition-colors"
                >
                  <div className="flex items-center space-x-3">
                    <ImageIcon className="w-5 h-5 text-primary" />
                    <span className="font-medium text-foreground">
                      Phase 2: Storyboard ({phaseArtifacts.phase2.storyboardUrls.length} images)
                    </span>
                  </div>
                  {expandedPhases.has('phase2') ? (
                    <ChevronUp className="w-5 h-5 text-muted-foreground" />
                  ) : (
                    <ChevronDown className="w-5 h-5 text-muted-foreground" />
                  )}
                </button>
                {expandedPhases.has('phase2') && (
                  <div className="p-4 border-t border-border bg-muted/30">
                    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
                      {phaseArtifacts.phase2.storyboardUrls.map((url, index) => (
                        <div key={index} className="relative aspect-video rounded-lg overflow-hidden border border-border bg-card">
                          <img
                            src={url}
                            alt={`Storyboard beat ${index + 1}`}
                            className="w-full h-full object-cover"
                            onError={(e) => {
                              const img = e.currentTarget;
                              img.src = 'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" width="400" height="300"%3E%3Crect fill="%23ddd" width="400" height="300"/%3E%3Ctext fill="%23999" font-family="sans-serif" font-size="18" dy="10.5" font-weight="bold" x="50%25" y="50%25" text-anchor="middle"%3EImage not available%3C/text%3E%3C/svg%3E';
                            }}
                          />
                          <div className="absolute bottom-0 left-0 right-0 bg-black/60 text-white text-xs px-2 py-1 text-center">
                            Beat {index + 1}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Phase 3: Video Chunks */}
            {phaseArtifacts.phase3 && phaseArtifacts.phase3.chunkUrls && phaseArtifacts.phase3.chunkUrls.length > 0 && (
              <div className="border border-border rounded-lg overflow-hidden">
                <button
                  onClick={() => togglePhase('phase3')}
                  className="w-full px-4 py-3 bg-card hover:bg-muted/50 flex items-center justify-between transition-colors"
                >
                  <div className="flex items-center space-x-3">
                    <Video className="w-5 h-5 text-primary" />
                    <span className="font-medium text-foreground">
                      Phase 3: Video Chunks ({phaseArtifacts.phase3.chunkUrls.length})
                    </span>
                  </div>
                  {expandedPhases.has('phase3') ? (
                    <ChevronUp className="w-5 h-5 text-muted-foreground" />
                  ) : (
                    <ChevronDown className="w-5 h-5 text-muted-foreground" />
                  )}
                </button>
                {expandedPhases.has('phase3') && (
                  <div className="p-4 border-t border-border bg-muted/30">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      {phaseArtifacts.phase3.chunkUrls.map((url, index) => (
                        <div key={index} className="space-y-1">
                          <div className="text-xs text-muted-foreground mb-1">Chunk {index + 1}</div>
                          <video
                            src={url}
                            controls
                            className="w-full rounded-lg border border-border"
                            onError={(e) => {
                              console.error(`Failed to load chunk ${index + 1}:`, e);
                            }}
                          >
                            Your browser does not support the video tag.
                          </video>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Phase 4: Final Video */}
            {phaseArtifacts.phase4 && phaseArtifacts.phase4.finalVideoUrl && (
              <div className="border border-border rounded-lg overflow-hidden">
                <button
                  onClick={() => togglePhase('phase4')}
                  className="w-full px-4 py-3 bg-card hover:bg-muted/50 flex items-center justify-between transition-colors"
                >
                  <div className="flex items-center space-x-3">
                    <Film className="w-5 h-5 text-primary" />
                    <span className="font-medium text-foreground">Phase 4: Final Video (with Audio)</span>
                  </div>
                  {expandedPhases.has('phase4') ? (
                    <ChevronUp className="w-5 h-5 text-muted-foreground" />
                  ) : (
                    <ChevronDown className="w-5 h-5 text-muted-foreground" />
                  )}
                </button>
                {expandedPhases.has('phase4') && (
                  <div className="p-4 border-t border-border bg-muted/30">
                    <video
                      src={phaseArtifacts.phase4.finalVideoUrl}
                      controls
                      className="w-full rounded-lg border border-border"
                      onError={(e) => {
                        console.error('Failed to load final video:', e);
                      }}
                    >
                      Your browser does not support the video tag.
                    </video>
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        <div className="flex flex-col space-y-3">
          <div className="grid grid-cols-2 gap-4">
            <button
              onClick={() => {
                navigate('/');
              }}
              className="btn-secondary"
            >
              Create Another
            </button>
            <button
              onClick={() => navigate(`/export/${videoId}`)}
              className="btn-primary flex items-center justify-center space-x-2"
            >
              <BarChart3 className="w-5 h-5" />
              <span>Export</span>
            </button>
          </div>
          <button
            onClick={handleDownload}
            disabled={!videoUrl}
            className="w-full btn-primary flex items-center justify-center space-x-2 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <Download className="w-5 h-5" />
            <span>Download Video</span>
          </button>
        </div>
      </div>
    </div>
  );
}

