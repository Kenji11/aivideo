import { useState, useEffect } from 'react';
import { BrowserRouter, Routes, Route, useNavigate, useLocation } from 'react-router-dom';
import { Sparkles, Video, Film, Download, BarChart3 } from 'lucide-react';
// Commented out - may use later
// import { Settings, Zap, Library, CreditCard, Code2 } from 'lucide-react';
import { Header } from './components/Header';
import { StepIndicator } from './components/StepIndicator';
import { ProjectCard } from './components/ProjectCard';
import { Notification } from './components/NotificationCenter';
import { toast } from '@/hooks/use-toast';
import { Toaster } from '@/components/ui/toaster';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
// import type { Template } from './components/TemplateGallery';
import { ExportPanel } from './components/ExportPanel';
import { Auth } from './pages/Auth';
import { AssetLibrary } from './pages/AssetLibrary';
import { UploadVideo } from './pages/UploadVideo';
import { VideoStatus } from './pages/VideoStatus';
// Commented out - may use later
// import { Settings as SettingsPage } from './pages/Settings';
// import { Analytics } from './pages/Analytics';
// import { Templates } from './pages/Templates';
// import { Dashboard } from './pages/Dashboard';
// import { VideoLibraryUnused } from './pages/VideoLibraryUnused ';
// import { Billing } from './pages/Billing';
// import { API } from './pages/API';
import { listVideos, deleteVideo, VideoListItem } from './lib/api';
import { useAuth } from './contexts/AuthContext';
import { useDarkMode } from './lib/useDarkMode';

// Main App Content (inside router)
function AppContent() {
  const navigate = useNavigate();
  const location = useLocation();
  const { user, loading: authLoading, signOut } = useAuth();
  useDarkMode(); // Enforce dark mode
  const [prompt, setPrompt] = useState('');
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [projects, setProjects] = useState<VideoListItem[]>([]);
  const [, setSelectedProject] = useState<VideoListItem | null>(null);
  const [isLoadingProjects, setIsLoadingProjects] = useState(false);
  const [stitchedVideoUrl, setStitchedVideoUrl] = useState<string | null>(null);
  const [uploadedAssetIds, setUploadedAssetIds] = useState<string[]>([]);
  const [selectedModel, setSelectedModel] = useState<string>('veo_fast');
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [videoToDelete, setVideoToDelete] = useState<{ id: string; title: string } | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);

  const steps = [
    { id: 1, name: 'Create', icon: Sparkles },
    { id: 2, name: 'Generate', icon: Video },
    { id: 3, name: 'Preview', icon: Film },
    { id: 4, name: 'Download', icon: Download },
  ];

  const addNotification = (type: Notification['type'], title: string, message: string) => {
    const variant = type === 'error' ? 'destructive' : 'default';
    toast({
      variant,
      title,
      description: message,
    });
  };


  const handleProjectSelect = (project: VideoListItem) => {
    setSelectedProject(project);
    if (project.status === 'complete' && project.final_video_url) {
      setStitchedVideoUrl(project.final_video_url);
      setTitle(project.title);
      navigate('/preview');
    } else if (project.status !== 'complete' && project.status !== 'failed') {
      // Navigate to processing page for videos that are still processing
      navigate(`/processing/${project.video_id}`);
    }
  };

  const handleDeleteProject = (videoId: string) => {
    // Find the project to get its title for confirmation
    const project = projects.find(p => p.video_id === videoId);
    const projectTitle = project?.title || 'this video';
    
    // Open confirmation dialog
    setVideoToDelete({ id: videoId, title: projectTitle });
    setDeleteDialogOpen(true);
  };

  const confirmDelete = async () => {
    if (!videoToDelete) return;
    
    setIsDeleting(true);
    try {
      await deleteVideo(videoToDelete.id);
      // Remove video from local state
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
      // Only fetch projects when on the projects page AND state is empty
      if (location.pathname === '/projects' && projects.length === 0) {
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
      }
    };

    fetchProjects();
  }, [location.pathname, projects]);

  const getCurrentStep = () => {
    if (location.pathname.startsWith('/processing')) return 2;
    if (location.pathname === '/preview') return 3;
    if (location.pathname === '/download') return 4;
    return 1;
  };

  // Template selection handler - commented out for now
  // const handleSelectTemplate = (template: Template) => {
  //   setTitle(template.name);
  //   setDescription(template.description);
  //   navigate('/');
  //   addNotification('success', 'Template Selected', `Started with ${template.name} template`);
  // };

  const handleAuthSuccess = () => {
    navigate('/');
  };

  const handleLogout = async () => {
    try {
      await signOut();
      // No need to navigate - Auth component will be shown automatically when user becomes null
      navigate('/');
    } catch (error) {
      console.error('Logout error:', error);
      addNotification('error', 'Logout Failed', 'Failed to sign out. Please try again.');
    }
  };

  // Show loading state while checking auth
  if (authLoading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-12 w-12 border-4 border-primary border-t-transparent mb-4"></div>
          <p className="text-muted-foreground">Loading...</p>
        </div>
      </div>
    );
  }

  // Show auth page if user is not logged in
  if (!user) {
    return <Auth onAuthSuccess={handleAuthSuccess} />;
  }

  const showStepIndicator = location.pathname.startsWith('/processing') || 
                           location.pathname === '/preview' || 
                           location.pathname === '/download';

  // Get user display name or email
  const userName = user.displayName || user.email?.split('@')[0] || 'User';

  return (
    <div className="min-h-screen bg-background">
      <Header onLogout={handleLogout} userName={userName} />

      <Toaster />

      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        {/* Navigation buttons - always visible on all pages */}
        <div className="flex items-center justify-between mb-8 overflow-x-auto pb-2">
          <div className="space-x-2 flex flex-shrink-0">
            {/* Commented out - may use later */}
            {/* <button
              onClick={() => navigate('/dashboard')}
              className={`flex items-center space-x-2 px-3 py-2 rounded-lg transition-colors whitespace-nowrap text-sm ${
                location.pathname === '/dashboard' 
                  ? 'bg-primary text-primary-foreground' 
                  : 'text-foreground hover:bg-accent hover:text-accent-foreground'
              }`}
              title="Dashboard"
            >
              <BarChart3 className="w-5 h-5" />
              <span className="hidden sm:inline">Dashboard</span>
            </button>
            <button
              onClick={() => navigate('/templates')}
              className={`flex items-center space-x-2 px-3 py-2 rounded-lg transition-colors whitespace-nowrap text-sm ${
                location.pathname === '/templates' 
                  ? 'bg-primary text-primary-foreground' 
                  : 'text-foreground hover:bg-accent hover:text-accent-foreground'
              }`}
              title="Templates"
            >
              <Zap className="w-5 h-5" />
              <span className="hidden sm:inline">Templates</span>
            </button>
            <button
              onClick={() => navigate('/library')}
              className={`flex items-center space-x-2 px-3 py-2 rounded-lg transition-colors whitespace-nowrap text-sm ${
                location.pathname === '/library' 
                  ? 'bg-primary text-primary-foreground' 
                  : 'text-foreground hover:bg-accent hover:text-accent-foreground'
              }`}
              title="Video Library"
            >
              <Library className="w-5 h-5" />
              <span className="hidden sm:inline">Library</span>
            </button>
            <button
              onClick={() => navigate('/analytics')}
              className={`flex items-center space-x-2 px-3 py-2 rounded-lg transition-colors whitespace-nowrap text-sm ${
                location.pathname === '/analytics' 
                  ? 'bg-primary text-primary-foreground' 
                  : 'text-foreground hover:bg-accent hover:text-accent-foreground'
              }`}
              title="Analytics"
            >
              <BarChart3 className="w-5 h-5" />
              <span className="hidden sm:inline">Analytics</span>
            </button>
            <button
              onClick={() => navigate('/billing')}
              className={`flex items-center space-x-2 px-3 py-2 rounded-lg transition-colors whitespace-nowrap text-sm ${
                location.pathname === '/billing' 
                  ? 'bg-primary text-primary-foreground' 
                  : 'text-foreground hover:bg-accent hover:text-accent-foreground'
              }`}
              title="Billing"
            >
              <CreditCard className="w-5 h-5" />
              <span className="hidden sm:inline">Billing</span>
            </button>
            <button
              onClick={() => navigate('/api')}
              className={`flex items-center space-x-2 px-3 py-2 rounded-lg transition-colors whitespace-nowrap text-sm ${
                location.pathname === '/api' 
                  ? 'bg-primary text-primary-foreground' 
                  : 'text-foreground hover:bg-accent hover:text-accent-foreground'
              }`}
              title="API"
            >
              <Code2 className="w-5 h-5" />
              <span className="hidden sm:inline">API</span>
            </button>
            <button
              onClick={() => navigate('/settings')}
              className={`flex items-center space-x-2 px-3 py-2 rounded-lg transition-colors whitespace-nowrap text-sm ${
                location.pathname === '/settings' 
                  ? 'bg-primary text-primary-foreground' 
                  : 'text-foreground hover:bg-accent hover:text-accent-foreground'
              }`}
              title="Settings"
            >
              <Settings className="w-5 h-5" />
              <span className="hidden sm:inline">Settings</span>
            </button> */}
          </div>
        </div>

        {/* Step indicator - only shown on processing/preview/download pages */}
        {showStepIndicator && (
          <StepIndicator steps={steps} currentStep={getCurrentStep()} />
        )}

        <Routes>
          <Route path="/" element={
            <UploadVideo
              title={title}
              description={description}
              prompt={prompt}
              selectedModel={selectedModel}
              uploadedAssetIds={uploadedAssetIds}
              onTitleChange={setTitle}
              onDescriptionChange={setDescription}
              onPromptChange={setPrompt}
              onModelChange={setSelectedModel}
              onAssetsUploaded={(assetIds) => {
                setUploadedAssetIds(assetIds);
                addNotification('success', 'Files Uploaded', `${assetIds.length} file(s) uploaded successfully!`);
              }}
              onNotification={addNotification}
            />
          } />

          <Route path="/projects" element={
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
                    />
                  ))}
                </div>
              )}
            </div>
          } />

          <Route path="/processing/:videoId" element={<VideoStatus />} />

          <Route path="/preview" element={
            <div className="card overflow-hidden animate-fade-in">
              <div className="aspect-video bg-gradient-to-br from-card to-muted flex items-center justify-center">
                {stitchedVideoUrl ? (
                  <video
                    src={stitchedVideoUrl}
                    controls
                    className="w-full h-full object-contain"
                    onError={(e) => {
                      console.error('Video load error:', e);
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
                    {title}
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
                        setPrompt('');
                        setTitle('');
                        setDescription('');
                        navigate('/');
                      }}
                      className="btn-secondary"
                    >
                      Create Another
                    </button>
                    <button
                      onClick={() => navigate('/export')}
                      className="btn-primary flex items-center justify-center space-x-2"
                    >
                      <BarChart3 className="w-5 h-5" />
                      <span>Export</span>
                    </button>
                  </div>
                  <button
                    onClick={() => {
                      if (stitchedVideoUrl) {
                        const link = document.createElement('a');
                        link.href = stitchedVideoUrl;
                        link.download = `${title || 'video'}.mp4`;
                        document.body.appendChild(link);
                        link.click();
                        document.body.removeChild(link);
                        addNotification('success', 'Download Started', 'Your video download has started');
                        navigate('/download');
                      } else {
                        addNotification('error', 'Video Not Ready', 'Video is still processing');
                      }
                    }}
                    disabled={!stitchedVideoUrl}
                    className="w-full btn-primary flex items-center justify-center space-x-2 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    <Download className="w-5 h-5" />
                    <span>Download Video</span>
                  </button>
                </div>
              </div>
            </div>
          } />

          <Route path="/download" element={
            <div className="space-y-6 animate-fade-in">
              <div className="card p-8 text-center">
                <div className="inline-flex items-center justify-center w-20 h-20 bg-primary/20 rounded-full mb-6">
                  <Download className="w-10 h-10 text-primary" />
                </div>
                <h2 className="text-2xl font-bold text-foreground mb-2">
                  Your Video is Ready!
                </h2>
                <p className="text-muted-foreground mb-8">
                  Download your video or create another one
                </p>
                
                {stitchedVideoUrl && (
                  <div className="mb-8">
                    <video
                      src={stitchedVideoUrl}
                      controls
                      className="w-full max-w-2xl mx-auto rounded-lg border border-border"
                    >
                      Your browser does not support the video tag.
                    </video>
                  </div>
                )}
                
                <div className="flex flex-col space-y-3 max-w-md mx-auto">
                  {stitchedVideoUrl && (
                    <button
                      onClick={() => {
                        const link = document.createElement('a');
                        link.href = stitchedVideoUrl;
                        link.download = `${title || 'video'}.mp4`;
                        document.body.appendChild(link);
                        link.click();
                        document.body.removeChild(link);
                        addNotification('success', 'Download Started', 'Your video download has started');
                      }}
                      className="w-full btn-primary flex items-center justify-center space-x-2"
                    >
                      <Download className="w-5 h-5" />
                      <span>Download Video</span>
                    </button>
                  )}
                  <button
                    onClick={() => {
                      setPrompt('');
                      setTitle('');
                      setDescription('');
                      setStitchedVideoUrl(null);
                      // Phase 3 disabled - reference assets not used
                      // setReferenceAssets(null);
                      navigate('/');
                    }}
                    className="w-full btn-secondary"
                  >
                    Create New Video
                  </button>
                  <button
                    onClick={() => navigate('/projects')}
                    className="w-full btn-secondary flex items-center justify-center space-x-2"
                  >
                    <Film className="w-5 h-5" />
                    <span>My Projects</span>
                  </button>
                </div>
              </div>
            </div>
          } />

          <Route path="/export" element={
            <ExportPanel 
              onExport={() => {
                addNotification('success', 'Export Started', 'Your video is being exported');
                navigate('/preview');
              }} 
              onCancel={() => navigate('/preview')} 
            />
          } />

          <Route path="/asset-library" element={<AssetLibrary />} />

          {/* Commented out - may use later */}
          {/* <Route path="/dashboard" element={<Dashboard />} /> */}
          {/* <Route path="/templates" element={<Templates onSelectTemplate={handleSelectTemplate} />} /> */}
          {/* <Route path="/library" element={<VideoLibraryUnused />} /> */}
          {/* <Route path="/analytics" element={<Analytics />} /> */}
          {/* <Route path="/billing" element={<Billing />} /> */}
          {/* <Route path="/api" element={<API />} /> */}
          {/* <Route path="/settings" element={<SettingsPage />} /> */}
        </Routes>

        {/* Delete Confirmation Dialog */}
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
      </div>
    </div>
  );
}

// Main App with Router
function App() {
  return (
    <BrowserRouter>
      <AppContent />
    </BrowserRouter>
  );
}

export default App;
