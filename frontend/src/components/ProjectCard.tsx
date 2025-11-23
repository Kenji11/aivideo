import { Play, Trash2, Calendar, Video as VideoIcon, Loader2, Download, Scissors } from 'lucide-react';
import { Link } from 'react-router-dom';
import { VideoListItem } from '../lib/api';
import { formatDistanceToNow } from 'date-fns';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { useRef, useEffect } from 'react';

interface ProjectCardProps {
  project: VideoListItem;
  onSelect?: (project: VideoListItem) => void;
  onDelete?: (projectId: string) => void;
  onDownload?: (project: VideoListItem) => void;
  onEdit?: (project: VideoListItem) => void;
}

const statusConfig: Record<string, { variant: 'default' | 'secondary' | 'destructive' | 'outline'; label: string }> = {
  queued: { variant: 'secondary', label: 'Queued' },
  validating: { variant: 'default', label: 'Validating' },
  generating_animatic: { variant: 'default', label: 'Generating' },
  generating_chunks: { variant: 'default', label: 'Generating' },
  refining: { variant: 'default', label: 'Refining' },
  exporting: { variant: 'default', label: 'Exporting' },
  complete: { variant: 'default', label: 'Ready' },
  failed: { variant: 'destructive', label: 'Failed' },
};

export function ProjectCard({ project, onSelect, onDelete, onDownload, onEdit }: ProjectCardProps) {
  const status = statusConfig[project.status] || statusConfig.queued;
  const isProcessing = project.status !== 'complete' && project.status !== 'failed';
  const hasVideo = project.final_video_url || project.status === 'complete';
  const videoRef = useRef<HTMLVideoElement | null>(null);

  // Cleanup video on unmount
  useEffect(() => {
    return () => {
      if (videoRef.current) {
        videoRef.current.pause();
        videoRef.current.src = '';
        videoRef.current.load();
      }
    };
  }, []);

  const handleClick = () => {
    // Clean up video before navigation to prevent abort errors
    if (videoRef.current) {
      videoRef.current.pause();
      videoRef.current.src = '';
    }
    // Small delay to allow cleanup
    setTimeout(() => {
      onSelect?.(project);
    }, 50);
  };

  // Determine navigation route based on status
  const getVideoRoute = () => {
    // If there's a final video URL, allow preview (even for failed status)
    if (project.final_video_url) {
      return `/preview/${project.video_id}`;
    } else if (project.status !== 'complete' && project.status !== 'failed') {
      return `/processing/${project.video_id}`;
    }
    return '#'; // No link if no video and not processing
  };

  const videoRoute = getVideoRoute();

  return (
    <Card className="overflow-hidden hover:shadow-lg group animate-fade-in">
      <Link
        to={videoRoute}
        className="block"
        onClick={(e) => {
          // Clean up video before navigation to prevent abort errors
          if (videoRef.current) {
            videoRef.current.pause();
            videoRef.current.src = '';
          }
          // Still call onSelect if provided (for backwards compatibility)
          if (onSelect) {
            onSelect(project);
          }
        }}
      >
        <div 
          className="aspect-video bg-gradient-to-br from-slate-200 to-slate-300 dark:from-slate-700 dark:to-slate-800 flex items-center justify-center relative overflow-hidden cursor-pointer"
        >
        {hasVideo && project.final_video_url ? (
          <>
            {/* Show thumbnail if available, otherwise show video directly */}
            {project.thumbnail_url ? (
              <>
                <img
                  src={project.thumbnail_url}
                  alt={project.title}
                  className="w-full h-full object-cover"
                  onError={(e) => {
                    // Fallback to video if thumbnail fails to load
                    const target = e.currentTarget;
                    target.style.display = 'none';
                    const video = target.nextElementSibling as HTMLVideoElement;
                    if (video) {
                      video.style.display = 'block';
                    }
                  }}
                />
                <video
                  ref={videoRef}
                  src={project.final_video_url}
                  className="w-full h-full object-cover absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-300"
                  muted
                  preload="none"
                  onMouseEnter={(e) => {
                    if (videoRef.current && !videoRef.current.paused) return;
                    e.currentTarget.play().catch(() => {
                      // Ignore play errors (e.g., if video is being cleaned up)
                    });
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.pause();
                    e.currentTarget.currentTime = 0;
                  }}
                  onError={(e) => {
                    // Silently handle video errors
                    console.debug('ProjectCard video error (expected when navigating):', e);
                  }}
                  onAbort={(e) => {
                    // Silently handle abort (expected when navigating)
                    console.debug('ProjectCard video aborted (expected when navigating)');
                  }}
                />
              </>
            ) : (
              <video
                ref={videoRef}
                src={project.final_video_url}
                className="w-full h-full object-cover"
                muted
                preload="none"
                onMouseEnter={(e) => {
                  if (videoRef.current && !videoRef.current.paused) return;
                  e.currentTarget.play().catch(() => {
                    // Ignore play errors (e.g., if video is being cleaned up)
                  });
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.pause();
                  e.currentTarget.currentTime = 0;
                }}
                onError={(e) => {
                  // Silently handle video errors
                  console.debug('ProjectCard video error (expected when navigating):', e);
                }}
                onAbort={(e) => {
                  // Silently handle abort (expected when navigating)
                  console.debug('ProjectCard video aborted (expected when navigating)');
                }}
              />
            )}
          </>
        ) : (
          <>
            <div className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-300 bg-black/30 flex items-center justify-center">
              <div className="rounded-full bg-secondary p-3 transform scale-0 group-hover:scale-100 transition-transform duration-300">
                {isProcessing ? (
                  <Loader2 className="w-6 h-6 text-primary animate-spin" />
                ) : (
                  <Play className="w-6 h-6 text-primary fill-current" />
                )}
              </div>
            </div>
            {isProcessing ? (
              <Loader2 className="w-12 h-12 text-primary animate-spin" />
            ) : (
              <VideoIcon className="w-12 h-12 text-muted-foreground" />
            )}
          </>
        )}
        {isProcessing && (
          <div className="absolute bottom-2 left-2 right-2">
            <Progress value={project.progress} className="h-1.5" />
          </div>
        )}
      </div>
      </Link>

      <CardContent className="p-4 space-y-3">
        <Link
          to={videoRoute}
          className="block hover:text-primary transition-colors"
          onClick={(e) => {
            if (onSelect) {
              onSelect(project);
            }
          }}
        >
          <h3 className="font-semibold text-foreground line-clamp-2">
            {project.title}
          </h3>
          <p className="text-xs text-muted-foreground mt-1">
            {project.current_phase ? `Phase: ${project.current_phase.replace('phase', '').replace('_', ' ')}` : ''}
          </p>
        </Link>

        <div className="flex items-center justify-between">
          <Badge variant={status.variant}>
            {status.label}
          </Badge>
          <div className="flex items-center text-xs text-muted-foreground space-x-1">
            <Calendar className="w-3 h-3" />
            <span>{formatDistanceToNow(new Date(project.created_at), { addSuffix: true })}</span>
          </div>
        </div>

        {project.cost_usd > 0 && (
          <div className="text-xs text-muted-foreground">
            Cost: ${project.cost_usd.toFixed(4)}
          </div>
        )}

        {(onDownload || onEdit || onDelete) && (
          <div className="flex gap-2">
            {onDownload && project.status === 'complete' && project.final_video_url && (
              <Button
                variant="outline"
                size="sm"
                onClick={(e) => {
                  e.stopPropagation();
                  onDownload?.(project);
                }}
                className="flex-1"
              >
                <Download className="w-4 h-4 mr-2" />
                Download
              </Button>
            )}
            {onEdit && project.status === 'complete' && project.final_video_url && (
              <Button
                variant="default"
                size="sm"
                onClick={(e) => {
                  e.stopPropagation();
                  onEdit?.(project);
                }}
                className="flex-1 bg-primary hover:bg-primary/90"
              >
                <Scissors className="w-4 h-4 mr-2" />
                Edit
              </Button>
            )}
            {onDelete && (
              <Button
                variant="destructive"
                size="sm"
                onClick={(e) => {
                  e.stopPropagation();
                  onDelete?.(project.video_id);
                }}
                className="flex-1"
              >
                <Trash2 className="w-4 h-4 mr-2" />
                Delete
              </Button>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
