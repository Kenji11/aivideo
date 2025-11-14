import { Zap, Plus, FolderOpen, RotateCcw } from 'lucide-react';

interface QuickActionsProps {
  onNewProject: () => void;
  onViewProjects: () => void;
  recentProjects?: { id: string; title: string }[];
}

export function QuickActions({ onNewProject, onViewProjects, recentProjects = [] }: QuickActionsProps) {
  return (
    <div className="card p-6 mb-8">
      <div className="flex items-center space-x-2 mb-4">
        <Zap className="w-5 h-5 text-orange-600" />
        <h3 className="font-semibold text-slate-900">Quick Actions</h3>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <button
          onClick={onNewProject}
          className="flex items-center space-x-3 p-4 bg-blue-50 hover:bg-blue-100 rounded-lg border border-blue-200 transition-colors text-left group"
        >
          <div className="w-10 h-10 bg-blue-600 rounded-lg flex items-center justify-center group-hover:scale-110 transition-transform">
            <Plus className="w-5 h-5 text-white" />
          </div>
          <div>
            <p className="font-medium text-slate-900">Create New Video</p>
            <p className="text-xs text-slate-600">Start from scratch</p>
          </div>
        </button>

        <button
          onClick={onViewProjects}
          className="flex items-center space-x-3 p-4 bg-purple-50 hover:bg-purple-100 rounded-lg border border-purple-200 transition-colors text-left group"
        >
          <div className="w-10 h-10 bg-purple-600 rounded-lg flex items-center justify-center group-hover:scale-110 transition-transform">
            <FolderOpen className="w-5 h-5 text-white" />
          </div>
          <div>
            <p className="font-medium text-slate-900">My Projects</p>
            <p className="text-xs text-slate-600">View all videos</p>
          </div>
        </button>
      </div>

      {recentProjects.length > 0 && (
        <div className="mt-6 pt-6 border-t border-slate-200">
          <p className="text-sm font-medium text-slate-700 mb-3 flex items-center space-x-2">
            <RotateCcw className="w-4 h-4" />
            <span>Recent</span>
          </p>
          <div className="space-y-2">
            {recentProjects.slice(0, 3).map((project) => (
              <button
                key={project.id}
                className="w-full text-left p-2 rounded-lg hover:bg-slate-100 transition-colors group"
              >
                <p className="text-sm text-slate-900 group-hover:text-blue-600 truncate">{project.title}</p>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
