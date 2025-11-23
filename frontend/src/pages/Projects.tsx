import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Film } from 'lucide-react';
import { listVideos, deleteVideo, VideoListItem } from '../lib/api';
import { ProjectCard } from '../components/ProjectCard';
import { toast } from '@/hooks/use-toast';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';

export function Projects() {
  const navigate = useNavigate();
  const [projects, setProjects] = useState<VideoListItem[]>([]);
  const [isLoadingProjects, setIsLoadingProjects] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [videoToDelete, setVideoToDelete] = useState<{ id: string; title: string } | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);

  const addNotification = useCallback((type: 'success' | 'error', title: string, message: string) => {
    const variant = type === 'error' ? 'destructive' : 'default';
    toast({
      variant,
      title,
      description: message,
    });
  }, []);

  const handleProjectSelect = (project: VideoListItem) => {
    // If there's a final video URL, navigate to preview (even for failed status)
    if (project.final_video_url) {
      navigate(`/preview/${project.video_id}`);
    } else if (project.status !== 'complete' && project.status !== 'failed') {
      navigate(`/processing/${project.video_id}`);
    }
  };

  const handleDeleteProject = (videoId: string) => {
    const project = projects.find(p => p.video_id === videoId);
    const projectTitle = project?.title || 'this video';
    
    setVideoToDelete({ id: videoId, title: projectTitle });
    setDeleteDialogOpen(true);
  };

  const handleDownload = (project: VideoListItem) => {
    if (project.final_video_url) {
      const link = document.createElement('a');
      link.href = project.final_video_url;
      link.download = `${project.title || 'video'}.mp4`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      addNotification('success', 'Download Started', 'Your video download has started');
    } else {
      addNotification('error', 'Video Not Ready', 'Video is not available for download');
    }
  };

  const handleEdit = (project: VideoListItem) => {
    navigate(`/video/${project.video_id}/edit`);
  };

  const confirmDelete = async () => {
    if (!videoToDelete) return;
    
    setIsDeleting(true);
    try {
      await deleteVideo(videoToDelete.id);
      setProjects(projects.filter(p => p.video_id !== videoToDelete.id));
      addNotification('success', 'Video Deleted', `"${videoToDelete.title}" has been deleted successfully.`);
      setDeleteDialogOpen(false);
      setVideoToDelete(null);
    } catch (error) {
      console.error('Failed to delete video:', error);
      addNotification('error', 'Delete Failed', error instanceof Error ? error.message : 'Failed to delete video');
    } finally {
      setIsDeleting(false);
    }
  };

  const cancelDelete = () => {
    setDeleteDialogOpen(false);
    setVideoToDelete(null);
  };

  useEffect(() => {
    const fetchProjects = async () => {
      setIsLoadingProjects(true);
      try {
        const response = await listVideos();
        setProjects(response.videos);
      } catch (error) {
        console.error('Failed to fetch projects:', error);
        addNotification('error', 'Failed to Load Projects', error instanceof Error ? error.message : 'Unknown error');
      } finally {
        setIsLoadingProjects(false);
      }
    };

    fetchProjects();
  }, [addNotification]);

  return (
    <>
      <div className="animate-fade-in">
        <div className="mb-8">
          <h2 className="text-3xl font-bold text-foreground mb-2">
            My Projects
          </h2>
          <p className="text-muted-foreground">
            Create and manage your AI-generated videos
          </p>
        </div>

        {isLoadingProjects ? (
          <div className="card p-16 text-center">
            <div className="inline-block animate-spin rounded-full h-12 w-12 border-4 border-primary border-t-transparent mb-4"></div>
            <p className="text-muted-foreground">Loading projects...</p>
          </div>
        ) : projects.length === 0 ? (
          <div className="card p-16 text-center">
            <Film className="w-16 h-16 mx-auto text-muted-foreground mb-4" />
            <p className="text-muted-foreground mb-6">No projects yet</p>
            <button
              onClick={() => navigate('/')}
              className="btn-primary"
            >
              Create Your First Video
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {projects.map((project) => (
              <ProjectCard
                key={project.video_id}
                project={project}
                onSelect={handleProjectSelect}
                onDelete={handleDeleteProject}
                onDownload={handleDownload}
                onEdit={handleEdit}
              />
            ))}
          </div>
        )}
      </div>

      <Dialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete Video</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete "{videoToDelete?.title}"? This action cannot be undone and will permanently delete the video and all associated files.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={cancelDelete}
              disabled={isDeleting}
            >
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={confirmDelete}
              disabled={isDeleting}
            >
              {isDeleting ? 'Deleting...' : 'Delete'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}

