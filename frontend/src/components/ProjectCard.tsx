import { Play, Trash2, Calendar, Video as VideoIcon, Loader2 } from 'lucide-react';
import { VideoListItem } from '../lib/api';
import { formatDistanceToNow } from 'date-fns';

interface ProjectCardProps {
  project: VideoListItem;
  onSelect?: (project: VideoListItem) => void;
  onDelete?: (projectId: string) => void;
}

const statusConfig: Record<string, { bg: string; text: string; label: string }> = {
  queued: { bg: 'bg-slate-100 dark:bg-slate-700', text: 'text-slate-700 dark:text-slate-300', label: 'Queued' },
  validating: { bg: 'bg-blue-100 dark:bg-blue-900', text: 'text-blue-700 dark:text-blue-300', label: 'Validating' },
  generating_animatic: { bg: 'bg-blue-100 dark:bg-blue-900', text: 'text-blue-700 dark:text-blue-300', label: 'Generating' },
  // generating_references: { bg: 'bg-blue-100 dark:bg-blue-900', text: 'text-blue-700 dark:text-blue-300', label: 'Generating' }, // Phase 3 disabled
  generating_chunks: { bg: 'bg-blue-100 dark:bg-blue-900', text: 'text-blue-700 dark:text-blue-300', label: 'Generating' },
  refining: { bg: 'bg-blue-100 dark:bg-blue-900', text: 'text-blue-700 dark:text-blue-300', label: 'Refining' },
  exporting: { bg: 'bg-blue-100 dark:bg-blue-900', text: 'text-blue-700 dark:text-blue-300', label: 'Exporting' },
  complete: { bg: 'bg-green-100 dark:bg-green-900', text: 'text-green-700 dark:text-green-300', label: 'Ready' },
  failed: { bg: 'bg-red-100 dark:bg-red-900', text: 'text-red-700 dark:text-red-300', label: 'Failed' },
};

export function ProjectCard({ project, onSelect, onDelete }: ProjectCardProps) {
  const status = statusConfig[project.status] || statusConfig.queued;
  const isProcessing = project.status !== 'complete' && project.status !== 'failed';
  const hasVideo = project.final_video_url || project.status === 'complete';

  return (
    <div className="card overflow-hidden hover:shadow-lg group cursor-pointer animate-fade-in">
      <div 
        className="aspect-video bg-gradient-to-br from-slate-200 to-slate-300 dark:from-slate-700 dark:to-slate-800 flex items-center justify-center relative overflow-hidden"
        onClick={() => onSelect?.(project)}
      >
        {hasVideo && project.final_video_url ? (
          <video
            src={project.final_video_url}
            className="w-full h-full object-cover"
            muted
            onMouseEnter={(e) => e.currentTarget.play()}
            onMouseLeave={(e) => {
              e.currentTarget.pause();
              e.currentTarget.currentTime = 0;
            }}
          />
        ) : (
          <>
            <div className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-300 bg-black/30 flex items-center justify-center">
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onSelect?.(project);
                }}
                className="bg-white dark:bg-slate-700 rounded-full p-3 transform scale-0 group-hover:scale-100 transition-transform duration-300"
              >
                {isProcessing ? (
                  <Loader2 className="w-6 h-6 text-blue-600 dark:text-blue-400 animate-spin" />
                ) : (
                  <Play className="w-6 h-6 text-blue-600 dark:text-blue-400 fill-current" />
                )}
              </button>
            </div>
            {isProcessing ? (
              <Loader2 className="w-12 h-12 text-blue-600 dark:text-blue-400 animate-spin" />
            ) : (
              <VideoIcon className="w-12 h-12 text-slate-400 dark:text-slate-500" />
            )}
          </>
        )}
        {isProcessing && (
          <div className="absolute bottom-2 left-2 right-2">
            <div className="bg-black/50 rounded-full h-1.5 overflow-hidden">
              <div 
                className="bg-blue-600 h-full transition-all duration-300"
                style={{ width: `${project.progress}%` }}
              />
            </div>
          </div>
        )}
      </div>

      <div className="p-4 space-y-3">
        <div>
          <h3 className="font-semibold text-slate-900 dark:text-slate-100 line-clamp-2 group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors">
            {project.title}
          </h3>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
            {project.current_phase ? `Phase: ${project.current_phase.replace('phase', '').replace('_', ' ')}` : ''}
          </p>
        </div>

        <div className="flex items-center justify-between">
          <span
            className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium ${status.bg} ${status.text}`}
          >
            {status.label}
          </span>
          <div className="flex items-center text-xs text-slate-500 dark:text-slate-400 space-x-1">
            <Calendar className="w-3 h-3" />
            <span>{formatDistanceToNow(new Date(project.created_at), { addSuffix: true })}</span>
          </div>
        </div>

        {project.cost_usd > 0 && (
          <div className="text-xs text-slate-500 dark:text-slate-400">
            Cost: ${project.cost_usd.toFixed(4)}
          </div>
        )}

        {onDelete && (
          <button
            onClick={(e) => {
              e.stopPropagation();
              onDelete?.(project.video_id);
            }}
            className="w-full text-sm text-slate-500 dark:text-slate-400 hover:text-red-600 dark:hover:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 py-2 rounded-lg transition-colors flex items-center justify-center space-x-1"
          >
            <Trash2 className="w-4 h-4" />
            <span>Delete</span>
          </button>
        )}
      </div>
    </div>
  );
}
