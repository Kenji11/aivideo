import { useState, useEffect, useRef } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { Film, Download, BarChart3, Edit } from 'lucide-react';
import { getVideoStatus, getVideo, StatusResponse, VideoResponse } from '../lib/api';
import { toast } from '@/hooks/use-toast';

export function Preview() {
  const navigate = useNavigate();
  const { videoId } = useParams<{ videoId: string }>();
  
  const [videoUrl, setVideoUrl] = useState<string | null>(null);
  const [title, setTitle] = useState<string>('');
  const [description, setDescription] = useState<string>('');
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const loadingAbortControllerRef = useRef<AbortController | null>(null);

  useEffect(() => {
    if (!videoId) {
      setError('No video ID provided');
      setIsLoading(false);
      return;
    }

    // Abort any previous request
    if (loadingAbortControllerRef.current) {
      loadingAbortControllerRef.current.abort();
    }

    const abortController = new AbortController();
    loadingAbortControllerRef.current = abortController;

    const fetchVideoData = async () => {
      setIsLoading(true);
      setError(null);
      
      try {
        // Try to get video details first (for completed videos)
        try {
          const videoData: VideoResponse = await getVideo(videoId);
          if (abortController.signal.aborted) return;
          
          if (videoData.final_video_url) {
            setVideoUrl(videoData.final_video_url);
            setTitle(videoData.title);
            return;
          }
        } catch (err) {
          if (abortController.signal.aborted) return;
          // If getVideo fails, try status endpoint
        }

        // Fallback to status endpoint (works for both in-progress and completed videos)
        const statusData: StatusResponse = await getVideoStatus(videoId);
        if (abortController.signal.aborted) return;
        
        const url = statusData.final_video_url || statusData.stitched_video_url;
        
        if (url) {
          setVideoUrl(url);
        } else {
          setError('Video is not ready yet. Please wait for generation to complete.');
        }
        
        // Try to get title from video list if status endpoint doesn't have it
        try {
          const { listVideos } = await import('../lib/api');
          const videoList = await listVideos();
          const matchingVideo = videoList.videos.find(v => v.video_id === videoId);
          if (matchingVideo) {
            setTitle(matchingVideo.title);
          }
        } catch (err) {
          // Failed to fetch title from video list
        }
      } catch (err: any) {
        if (err.name === 'AbortError' || abortController.signal.aborted) {
          return;
        }
        console.error('[Preview] Failed to fetch video data:', err);
        setError(err instanceof Error ? err.message : 'Failed to load video');
      } finally {
        if (!abortController.signal.aborted) {
          setIsLoading(false);
        }
      }
    };

    fetchVideoData();

    // Cleanup on unmount
    return () => {
      abortController.abort();
      if (videoRef.current) {
        videoRef.current.pause();
        videoRef.current.src = '';
        videoRef.current.load();
      }
    };
  }, [videoId]);

  const handleDownload = () => {
    if (videoUrl) {
      const link = document.createElement('a');
      link.href = videoUrl;
      link.download = `${title || 'video'}.mp4`;
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
            <button
              onClick={() => navigate('/projects')}
              className="mt-4 px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90"
            >
              Back to Projects
            </button>
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
            ref={videoRef}
            src={videoUrl}
            controls
            className="w-full h-full object-contain"
            onError={(e) => {
              console.error('Video load error:', e);
              setError('Failed to load video');
            }}
            onAbort={(e) => {
              // Silently handle abort (expected when navigating away)
              console.debug('Preview video aborted (expected when navigating)');
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
            {title || 'Video Preview'}
          </h2>
          {description && (
            <p className="text-muted-foreground">
              {description}
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
            onClick={() => navigate(`/video/${videoId}/edit`)}
            className="w-full btn-secondary flex items-center justify-center space-x-2"
          >
            <Edit className="w-5 h-5" />
            <span>Edit Chunks</span>
          </button>
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

