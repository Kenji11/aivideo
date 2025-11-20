import { Play, Trash2, Calendar, Video as VideoIcon, Loader2 } from 'lucide-react';
import { VideoListItem } from '../lib/api';
import { formatDistanceToNow } from 'date-fns';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';

interface ProjectCardProps {
  project: VideoListItem;
  onSelect?: (project: VideoListItem) => void;
  onDelete?: (projectId: string) => void;
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

export function ProjectCard({ project, onSelect, onDelete }: ProjectCardProps) {
  const status = statusConfig[project.status] || statusConfig.queued;
  const isProcessing = project.status !== 'complete' && project.status !== 'failed';
  const hasVideo = project.final_video_url || project.status === 'complete';

  return (
    <Card className="overflow-hidden hover:shadow-lg group cursor-pointer animate-fade-in">
      <div 
        className="aspect-video bg-gradient-to-br from-slate-200 to-slate-300 dark:from-slate-700 dark:to-slate-800 flex items-center justify-center relative overflow-hidden"
        onClick={() => onSelect?.(project)}
      >
        {hasVideo && project.final_video_url ? (
          <video
            src={project.final_video_url}
            className="w-full h-full object-cover"
            muted
            preload="none"
            onMouseEnter={(e) => e.currentTarget.play()}
            onMouseLeave={(e) => {
              e.currentTarget.pause();
              e.currentTarget.currentTime = 0;
            }}
          />
        ) : (
          <>
            <div className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-300 bg-black/30 flex items-center justify-center">
              <Button
                variant="secondary"
                size="icon"
                onClick={(e) => {
                  e.stopPropagation();
                  onSelect?.(project);
                }}
                className="rounded-full transform scale-0 group-hover:scale-100 transition-transform duration-300"
              >
                {isProcessing ? (
                  <Loader2 className="w-6 h-6 text-primary animate-spin" />
                ) : (
                  <Play className="w-6 h-6 text-primary fill-current" />
                )}
              </Button>
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

      <CardContent className="p-4 space-y-3">
        <div>
          <h3 className="font-semibold text-foreground line-clamp-2 group-hover:text-primary transition-colors">
            {project.title}
          </h3>
          <p className="text-xs text-muted-foreground mt-1">
            {project.current_phase ? `Phase: ${project.current_phase.replace('phase', '').replace('_', ' ')}` : ''}
          </p>
        </div>

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

        {onDelete && (
          <Button
            variant="destructive"
            size="sm"
            onClick={(e) => {
              e.stopPropagation();
              onDelete?.(project.video_id);
            }}
            className="w-full"
          >
            <Trash2 className="w-4 h-4 mr-2" />
            Delete
          </Button>
        )}
      </CardContent>
    </Card>
  );
}
