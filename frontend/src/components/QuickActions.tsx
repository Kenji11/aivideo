import { Zap, Plus, FolderOpen, RotateCcw } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';

interface QuickActionsProps {
  onNewProject: () => void;
  onViewProjects: () => void;
  recentProjects?: { id: string; title: string }[];
}

export function QuickActions({ onNewProject, onViewProjects, recentProjects = [] }: QuickActionsProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center space-x-2">
          <Zap className="w-5 h-5 text-orange-600" />
          <span>Quick Actions</span>
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <Button
            onClick={onNewProject}
            variant="outline"
            className="flex items-center space-x-3 p-4 h-auto justify-start group"
          >
            <div className="w-10 h-10 bg-blue-600 rounded-lg flex items-center justify-center group-hover:scale-110 transition-transform">
              <Plus className="w-5 h-5 text-white" />
            </div>
            <div className="text-left">
              <p className="font-medium">Create New Video</p>
              <p className="text-xs text-muted-foreground">Start from scratch</p>
            </div>
          </Button>

          <Button
            onClick={onViewProjects}
            variant="outline"
            className="flex items-center space-x-3 p-4 h-auto justify-start group"
          >
            <div className="w-10 h-10 bg-purple-600 rounded-lg flex items-center justify-center group-hover:scale-110 transition-transform">
              <FolderOpen className="w-5 h-5 text-white" />
            </div>
            <div className="text-left">
              <p className="font-medium">My Projects</p>
              <p className="text-xs text-muted-foreground">View all videos</p>
            </div>
          </Button>
        </div>

        {recentProjects.length > 0 && (
          <div className="mt-6 pt-6 border-t">
            <p className="text-sm font-medium text-slate-700 dark:text-slate-300 mb-3 flex items-center space-x-2">
              <RotateCcw className="w-4 h-4" />
              <span>Recent</span>
            </p>
            <div className="space-y-2">
              {recentProjects.slice(0, 3).map((project) => (
                <Button
                  key={project.id}
                  variant="ghost"
                  className="w-full justify-start"
                >
                  <p className="text-sm truncate">{project.title}</p>
                </Button>
              ))}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
