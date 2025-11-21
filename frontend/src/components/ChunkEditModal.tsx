import { useState, useRef, useEffect } from 'react';
import { Play, Pause } from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from './ui/dialog';
import { Button } from './ui/button';

interface ChunkEditModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  chunkIndex: number;
  chunkUrl: string;
  beatImageUrl?: string;
}

export function ChunkEditModal({
  open,
  onOpenChange,
  chunkIndex,
  chunkUrl,
}: ChunkEditModalProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const timelineRef = useRef<HTMLDivElement>(null);
  const isDraggingRef = useRef(false);
  const [duration, setDuration] = useState(0);
  const [currentTime, setCurrentTime] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [isHovered, setIsHovered] = useState(false);
  const [isDragging, setIsDragging] = useState(false);

  useEffect(() => {
    if (!open) {
      setIsPlaying(false);
      return;
    }

    let animationFrameId: number | null = null;
    let retryFrameId: number | null = null;
    let isCleanedUp = false;
    let videoElement: HTMLVideoElement | null = null;
    
    // Store handler references for cleanup
    const handlers: {
      loadedmetadata?: () => void;
      loadeddata?: () => void;
      durationchange?: () => void;
      timeupdate?: () => void;
      seeked?: () => void;
      play?: () => void;
      pause?: () => void;
    } = {};

    const setupVideoListeners = () => {
      // Check if effect was cleaned up
      if (isCleanedUp) return;

      const video = videoRef.current;
      if (!video) {
        // Video element not yet mounted, try again on next frame
        retryFrameId = requestAnimationFrame(setupVideoListeners);
        return;
      }

      // Video element is now available
      videoElement = video;

      const updateDuration = () => {
        if (isCleanedUp || !videoElement) return;
        console.log("duration: ", videoElement.duration)
        console.log("seekable: ", videoElement.seekable, videoElement.seekable.length)
        if (videoElement.duration && isFinite(videoElement.duration)) {
          setDuration(videoElement.duration);
        }
      };

      const updateCurrentTime = () => {
        if (isCleanedUp || !videoElement) return;
        // Don't update from video if user is dragging
        if (isDraggingRef.current) return;
        if (videoElement.currentTime !== undefined && isFinite(videoElement.currentTime)) {
          setCurrentTime(videoElement.currentTime);
        }
      };

      handlers.loadedmetadata = () => {
        updateDuration();
        updateCurrentTime();
      };

      handlers.loadeddata = () => {
        updateDuration();
        updateCurrentTime();
      };

      handlers.durationchange = () => {
        updateDuration();
      };

      handlers.timeupdate = () => {
        updateCurrentTime();
      };

      handlers.seeked = () => {
        updateCurrentTime();
      };

      // Use requestAnimationFrame for smoother updates when playing
      const updateLoop = () => {
        if (isCleanedUp || !videoElement) return;
        if (!videoElement.paused) {
          updateCurrentTime();
          animationFrameId = requestAnimationFrame(updateLoop);
        }
      };

      handlers.play = () => {
        setIsPlaying(true);
        updateCurrentTime();
        updateLoop();
      };

      handlers.pause = () => {
        setIsPlaying(false);
        if (animationFrameId !== null) {
          cancelAnimationFrame(animationFrameId);
          animationFrameId = null;
        }
        updateCurrentTime();
      };

      // Check if duration and currentTime are already available
      updateDuration();
      updateCurrentTime();

      // Add event listeners
      video.addEventListener('loadedmetadata', handlers.loadedmetadata);
      video.addEventListener('loadeddata', handlers.loadeddata);
      video.addEventListener('durationchange', handlers.durationchange);
      video.addEventListener('timeupdate', handlers.timeupdate);
      video.addEventListener('seeked', handlers.seeked);
      video.addEventListener('play', handlers.play);
      video.addEventListener('pause', handlers.pause);
    };

    // Start setup, which will retry if video element is not available
    setupVideoListeners();

    return () => {
      isCleanedUp = true;
      
      // Cancel any pending retry
      if (retryFrameId !== null) {
        cancelAnimationFrame(retryFrameId);
      }
      
      // Cancel animation frame loop
      if (animationFrameId !== null) {
        cancelAnimationFrame(animationFrameId);
      }
      
      // Remove event listeners if video element was set up
      if (videoElement && handlers.loadedmetadata) {
        videoElement.removeEventListener('loadedmetadata', handlers.loadedmetadata);
        videoElement.removeEventListener('loadeddata', handlers.loadeddata!);
        videoElement.removeEventListener('durationchange', handlers.durationchange!);
        videoElement.removeEventListener('timeupdate', handlers.timeupdate!);
        videoElement.removeEventListener('seeked', handlers.seeked!);
        videoElement.removeEventListener('play', handlers.play!);
        videoElement.removeEventListener('pause', handlers.pause!);
      }
    };
  }, [chunkUrl, open]);

  const handlePlayPause = () => {
    const video = videoRef.current;
    if (!video) return;

    if (video.paused) {
      video.play();
    } else {
      video.pause();
    }
  };

  const getTimeFromPosition = (clientX: number): number => {
    const timeline = timelineRef.current;
    if (!timeline || duration === 0) return 0;

    const maxDuration = Math.ceil(duration);
    // Get the flex-1 div (the actual track area)
    const trackArea = timeline.querySelector('.flex-1') as HTMLElement;
    if (!trackArea) return 0;
    
    const trackRect = trackArea.getBoundingClientRect();
    const x = clientX - trackRect.left;
    const percentage = Math.max(0, Math.min(1, x / trackRect.width));
    const time = percentage * maxDuration;
    
    // Clamp to actual video duration
    return Math.max(0, Math.min(time, duration));
  };

  const handleTimelineMouseDown = (e: React.MouseEvent) => {
    const video = videoRef.current;
    if (!video || duration === 0) return;

    isDraggingRef.current = true;
    setIsDragging(true);
    const time = getTimeFromPosition(e.clientX);
    video.currentTime = time;
    setCurrentTime(time);
  };

  const handleMouseMove = (e: MouseEvent) => {
    if (!isDraggingRef.current) return;
    const video = videoRef.current;
    if (!video || duration === 0) return;

    const time = getTimeFromPosition(e.clientX);
    video.currentTime = time;
    setCurrentTime(time);
  };

  const handleMouseUp = () => {
    if (isDraggingRef.current) {
      isDraggingRef.current = false;
      setIsDragging(false);
    }
  };

  useEffect(() => {
    if (isDragging) {
      document.addEventListener('mousemove', handleMouseMove);
      document.addEventListener('mouseup', handleMouseUp);
      return () => {
        document.removeEventListener('mousemove', handleMouseMove);
        document.removeEventListener('mouseup', handleMouseUp);
      };
    }
  }, [isDragging, duration]);


  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Chunk {chunkIndex + 1}</DialogTitle>
        </DialogHeader>

        <div className="space-y-4">
          {/* Video Player */}
          <div 
            className="relative aspect-video bg-black rounded-lg overflow-hidden"
            onMouseEnter={() => setIsHovered(true)}
            onMouseLeave={() => setIsHovered(false)}
          >
            <video
              ref={videoRef}
              src={chunkUrl}
              preload="metadata"
              className="w-full h-full"
              onError={(e) => {
                console.error(`Failed to load chunk ${chunkIndex + 1}:`, e);
              }}
            >
              Your browser does not support the video tag.
            </video>
            {/* Custom Play/Pause Button */}
            {(isPlaying ? isHovered : true) && (
              <div className="absolute inset-0 flex items-center justify-center">
                <Button
                  variant="secondary"
                  size="icon"
                  onClick={handlePlayPause}
                  className="rounded-full w-16 h-16 bg-black/50 hover:bg-black/70 border-2 border-white/50"
                >
                  {isPlaying ? (
                    <Pause className="w-8 h-8 text-white fill-current" />
                  ) : (
                    <Play className="w-8 h-8 text-white fill-current" />
                  )}
                </Button>
              </div>
            )}
          </div>

          {/* Timeline */}
          <div className="border border-border rounded-lg overflow-hidden bg-background">
            <div className="w-full">
                {/* Timeline ruler with time markers */}
                <div 
                  ref={timelineRef}
                  className="relative h-8 bg-muted/30 border-b border-border flex w-full cursor-pointer"
                  onMouseDown={handleTimelineMouseDown}
                >
                  <div className="w-4 flex-shrink-0 border-r border-border/50" />
                  {duration > 0 && (() => {
                    const maxDuration = Math.ceil(duration);
                    const markers = Array.from({ length: maxDuration + 1 }, (_, i) => i);
                    return (
                      <div className="flex-1 relative h-full">
                        {/* Time markers */}
                        {markers.map((marker) => {
                          const position = (marker / maxDuration) * 100;
                          return (
                            <div
                              key={marker}
                              className="absolute top-0 h-full flex flex-col items-center justify-center pb-0.5 pointer-events-none"
                              style={{ left: `${position}%` }}
                            >
                              <div className="w-px h-2 bg-border/60" />
                              <span className="text-[10px] text-muted-foreground mt-0.5 leading-none">
                                {marker}s
                              </span>
                            </div>
                          );
                        })}
                        {/* Playhead */}
                        <div
                          className="absolute top-0 h-full w-0.5 bg-white z-30 cursor-pointer group transition-none"
                          style={{
                            left: maxDuration > 0 ? `${(currentTime / maxDuration) * 100}%` : '0%',
                            transition: 'none',
                          }}
                        >
                          <div className="absolute -top-0.5 left-1/2 -translate-x-1/2 w-3 h-3 bg-white border border-gray-300 rounded-full group-hover:scale-125 transition-transform" />
                        </div>
                      </div>
                    );
                  })()}
                </div>

                {/* Tracks */}
                <div className="relative">
                  {/* Text Track */}
                  <div className="flex items-center h-10 border-b border-border/50">
                    <div className="w-4 flex-shrink-0flex items-center justify-center border-r border-border/50" />
                    <div className="flex-1 relative h-full">
                      {duration > 0 && (() => {
                        const maxDuration = Math.ceil(duration);
                        const violetTrackWidth = (duration / maxDuration) * 100;
                        return (
                          <>
                            {/* Text bar spanning actual duration */}
                            <div
                              className="absolute top-1 bottom-1 bg-primary opacity-60 rounded"
                              style={{
                                left: '0%',
                                width: `${violetTrackWidth}%`,
                              }}
                            />
                            {/* Playhead line through tracks */}
                            <div
                              className="absolute top-0 bottom-0 w-0.5 bg-white z-20 pointer-events-none transition-none"
                              style={{
                                left: maxDuration > 0 ? `${(currentTime / maxDuration) * 100}%` : '0%',
                                transition: 'none',
                              }}
                            />
                          </>
                        );
                      })()}
                    </div>
                  </div>

                </div>
            </div>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}

