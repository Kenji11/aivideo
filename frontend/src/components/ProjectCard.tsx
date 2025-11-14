import { Play, Trash2, FileText, Calendar } from 'lucide-react';
import { Project } from '../lib/supabase';
import { formatDistanceToNow } from 'date-fns';

interface ProjectCardProps {
  project: Project;
  onSelect?: (project: Project) => void;
  onDelete?: (projectId: string) => void;
}

const statusConfig = {
  pending: { bg: 'bg-slate-100 dark:bg-slate-700', text: 'text-slate-700 dark:text-slate-300', label: 'Pending' },
  processing: { bg: 'bg-blue-100', text: 'text-blue-700', label: 'Processing' },
  completed: { bg: 'bg-green-100', text: 'text-green-700', label: 'Ready' },
  failed: { bg: 'bg-red-100', text: 'text-red-700', label: 'Failed' },
};

export function ProjectCard({ project, onSelect, onDelete }: ProjectCardProps) {
  const status = statusConfig[project.status];

  return (
    <div className="card overflow-hidden hover:shadow-lg group cursor-pointer animate-fade-in">
      <div className="aspect-video bg-gradient-to-br from-slate-200 to-slate-300 flex items-center justify-center relative overflow-hidden">
        <div className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-300 bg-black/30 flex items-center justify-center">
          <button
            onClick={() => onSelect?.(project)}
            className="bg-white rounded-full p-3 transform scale-0 group-hover:scale-100 transition-transform duration-300"
          >
            <Play className="w-6 h-6 text-blue-600 fill-current" />
          </button>
        </div>
        <FileText className="w-12 h-12 text-slate-400" />
      </div>

      <div className="p-4 space-y-3">
        <div>
          <h3 className="font-semibold text-slate-900 dark:text-slate-100 line-clamp-2 group-hover:text-blue-600 transition-colors">
            {project.title}
          </h3>
          {project.description && (
            <p className="text-sm text-slate-500 dark:text-slate-400 line-clamp-2 mt-1">
              {project.description}
            </p>
          )}
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

        <button
          onClick={() => onDelete?.(project.id)}
          className="w-full text-sm text-slate-500 dark:text-slate-400 hover:text-red-600 hover:bg-red-50 py-2 rounded-lg transition-colors flex items-center justify-center space-x-1"
        >
          <Trash2 className="w-4 h-4" />
          <span>Delete</span>
        </button>
      </div>
    </div>
  );
}
