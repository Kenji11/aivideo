import { useState, useEffect, useCallback } from 'react';
import { Sparkles, Video, Film, Download, ArrowLeft, Settings, BarChart3, Zap, Library, CreditCard, Code2 } from 'lucide-react';
import { Header } from './components/Header';
import { StepIndicator } from './components/StepIndicator';
import { UploadZone } from './components/UploadZone';
import { AssetList } from './components/AssetList';
import { ProjectCard } from './components/ProjectCard';
import { ProcessingSteps } from './components/ProcessingSteps';
import { NotificationCenter, Notification } from './components/NotificationCenter';
import { TemplateGallery, Template } from './components/TemplateGallery';
import { ExportPanel } from './components/ExportPanel';
import { Auth } from './pages/Auth';
import { Settings as SettingsPage } from './pages/Settings';
import { Analytics } from './pages/Analytics';
import { Templates } from './pages/Templates';
import { Dashboard } from './pages/Dashboard';
import { VideoLibrary } from './pages/VideoLibrary';
import { Billing } from './pages/Billing';
import { API } from './pages/API';
import { supabase, Project } from './lib/supabase';
import { api } from './lib/api';

type AppStep = 'projects' | 'create' | 'processing' | 'preview' | 'download' | 'templates' | 'settings' | 'analytics' | 'dashboard' | 'library' | 'billing' | 'api' | 'export';

function App() {
  const [appStep, setAppStep] = useState<AppStep>('create');
  const [prompt, setPrompt] = useState('');
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);
  const [elapsedTime, setElapsedTime] = useState(0);
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedProject, setSelectedProject] = useState<Project | null>(null);
  const [processingProgress, setProcessingProgress] = useState(0);
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [referenceAssets, setReferenceAssets] = useState<string[]>([]);
  const [currentVideoId, setCurrentVideoId] = useState<string | null>(null);
  const [assetRefreshTrigger, setAssetRefreshTrigger] = useState(0);
  const [isLoadingProjects, setIsLoadingProjects] = useState(false);
  const [projectsError, setProjectsError] = useState<string | null>(null);

  const steps = [
    { id: 1, name: 'Create', icon: Sparkles },
    { id: 2, name: 'Generate', icon: Video },
    { id: 3, name: 'Preview', icon: Film },
    { id: 4, name: 'Download', icon: Download },
  ];

  const processingSteps = [
    { name: 'Content planning with AI', status: processingProgress > 0 ? 'completed' : 'pending' },
    { name: 'Generating video scenes', status: processingProgress > 1 ? (processingProgress === 1 ? 'completed' : 'processing') : 'pending' },
    { name: 'Creating images with AI', status: processingProgress > 2 ? (processingProgress === 2 ? 'completed' : 'processing') : 'pending' },
    { name: 'Composing final video', status: processingProgress > 3 ? 'completed' : processingProgress === 3 ? 'processing' : 'pending' },
  ];

  useEffect(() => {
    let interval: NodeJS.Timeout;
    if (isProcessing) {
      interval = setInterval(() => {
        setElapsedTime(t => t + 1);
        if (elapsedTime > 5 && processingProgress < 4) {
          setProcessingProgress(p => p + 1);
        }
        if (elapsedTime > 15) {
          setIsProcessing(false);
          setAppStep('preview');
        }
      }, 1000);
    }
    return () => clearInterval(interval);
  }, [isProcessing, elapsedTime, processingProgress]);

  const addNotification = useCallback((type: Notification['type'], title: string, message: string) => {
    const id = Math.random().toString();
    const notification: Notification = {
      id,
      type,
      title,
      message,
      timestamp: new Date(),
      read: false,
    };
    setNotifications((prev) => [notification, ...prev]);
    
    // Auto-dismiss success notifications after 2 seconds
    if (type === 'success') {
      setTimeout(() => {
        setNotifications((prev) => prev.filter((n) => n.id !== id));
      }, 2000);
    }
  }, []);

  const fetchVideos = useCallback(async () => {
    setIsLoadingProjects(true);
    setProjectsError(null);
    
    try {
      const response = await api.getVideos();
      
      // Map backend video data to Project format
      const mappedProjects: Project[] = response.videos.map((video) => {
        // Map backend status to Project status
        let projectStatus: Project['status'] = 'pending';
        if (video.status === 'complete' || video.status === 'completed') {
          projectStatus = 'completed';
        } else if (video.status === 'failed') {
          projectStatus = 'failed';
        } else if (
          video.status === 'validating' ||
          video.status === 'generating_animatic' ||
          video.status === 'generating_references' ||
          video.status === 'generating_chunks' ||
          video.status === 'refining' ||
          video.status === 'exporting' ||
          video.status === 'queued'
        ) {
          projectStatus = video.status === 'queued' || video.status === 'validating' ? 'pending' : 'processing';
        }
        
        return {
          id: video.video_id,
          user_id: 'mock-user-id', // Using mock user ID for now
          title: video.title,
          description: undefined, // Backend doesn't return description in list
          prompt: '', // Backend doesn't return prompt in list
          status: projectStatus,
          created_at: video.created_at,
          updated_at: video.completed_at || video.created_at,
        };
      });
      
      setProjects(mappedProjects);
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to fetch videos. Please try again.';
      setProjectsError(errorMessage);
      addNotification('error', 'Failed to Load Projects', errorMessage);
    } finally {
      setIsLoadingProjects(false);
    }
  }, [addNotification]);

  // Fetch videos when "My Projects" page loads
  useEffect(() => {
    if (appStep === 'projects') {
      fetchVideos();
    }
  }, [appStep, fetchVideos]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    // Validate required fields
    if (!prompt.trim() || !title.trim()) {
      addNotification('error', 'Validation Error', 'Please fill in all required fields.');
      return;
    }

    // Validate prompt length (backend requires min 10 chars)
    if (prompt.trim().length < 10) {
      addNotification('error', 'Validation Error', 'Prompt must be at least 10 characters long.');
      return;
    }

    setIsProcessing(true);
    setElapsedTime(0);
    setProcessingProgress(0);

    try {
      // Call API to generate video
      const response = await api.generateVideo({
        title: title.trim(),
        description: description.trim() || undefined,
        prompt: prompt.trim(),
        reference_assets: referenceAssets,
      });

      // Store video ID for tracking
      setCurrentVideoId(response.video_id);
      
      // Show success notification
      addNotification('success', 'Video Generation Started', response.message || 'Your video is being generated.');
      
      // Switch to processing view
      setAppStep('processing');
    } catch (error) {
      // Handle errors
      const errorMessage = error instanceof Error ? error.message : 'Failed to start video generation. Please try again.';
      addNotification('error', 'Generation Failed', errorMessage);
      
      // Reset processing state
      setIsProcessing(false);
    }
  };

  const handleProjectSelect = (project: Project) => {
    setSelectedProject(project);
  };

  const getCurrentStep = () => {
    switch (appStep) {
      case 'processing':
        return 2;
      case 'preview':
        return 3;
      case 'download':
        return 4;
      default:
        return 1;
    }
  };


  const handleSelectTemplate = (template: Template) => {
    setTitle(template.name);
    setDescription(template.description);
    setAppStep('create');
    addNotification('success', 'Template Selected', `Started with ${template.name} template`);
  };

  if (!isLoggedIn) {
    return <Auth onAuthSuccess={() => setIsLoggedIn(true)} />;
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 dark:from-slate-900 dark:to-slate-800">
      <Header
        onProjectsClick={() => setAppStep(appStep === 'projects' ? 'create' : 'projects')}
      />

      <NotificationCenter
        notifications={notifications}
        onDismiss={(id) => setNotifications((prev) => prev.filter((n) => n.id !== id))}
      />

      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        {appStep === 'dashboard' && (
          <Dashboard onBack={() => setAppStep('create')} />
        )}

        {appStep === 'settings' && (
          <SettingsPage onBack={() => setAppStep('create')} />
        )}

        {appStep === 'analytics' && (
          <Analytics onBack={() => setAppStep('create')} />
        )}

        {appStep === 'templates' && (
          <Templates onBack={() => setAppStep('create')} onSelectTemplate={handleSelectTemplate} />
        )}

        {appStep === 'library' && (
          <VideoLibrary onBack={() => setAppStep('create')} />
        )}

        {appStep === 'billing' && (
          <Billing onBack={() => setAppStep('create')} />
        )}

        {appStep === 'api' && (
          <API onBack={() => setAppStep('create')} />
        )}

        {appStep === 'export' && (
          <ExportPanel onExport={() => {
            addNotification('success', 'Export Started', 'Your video is being exported');
            setAppStep('preview');
          }} onCancel={() => setAppStep('preview')} />
        )}

        {(appStep === 'create' || appStep === 'processing' || appStep === 'preview' || appStep === 'download') && (
          <>
            <div className="flex items-center justify-between mb-8 overflow-x-auto pb-2">
              <div className="space-x-2 flex flex-shrink-0">
                <button
                  onClick={() => setAppStep('dashboard')}
                  className="flex items-center space-x-2 px-3 py-2 text-slate-700 dark:text-slate-300 hover:bg-white dark:hover:bg-slate-700 rounded-lg transition-colors whitespace-nowrap text-sm"
                  title="Dashboard"
                >
                  <BarChart3 className="w-5 h-5" />
                  <span className="hidden sm:inline">Dashboard</span>
                </button>
                <button
                  onClick={() => setAppStep('templates')}
                  className="flex items-center space-x-2 px-3 py-2 text-slate-700 dark:text-slate-300 hover:bg-white dark:hover:bg-slate-700 rounded-lg transition-colors whitespace-nowrap text-sm"
                  title="Templates"
                >
                  <Zap className="w-5 h-5" />
                  <span className="hidden sm:inline">Templates</span>
                </button>
                <button
                  onClick={() => setAppStep('library')}
                  className="flex items-center space-x-2 px-3 py-2 text-slate-700 dark:text-slate-300 hover:bg-white dark:hover:bg-slate-700 rounded-lg transition-colors whitespace-nowrap text-sm"
                  title="Video Library"
                >
                  <Library className="w-5 h-5" />
                  <span className="hidden sm:inline">Library</span>
                </button>
                <button
                  onClick={() => setAppStep('analytics')}
                  className="flex items-center space-x-2 px-3 py-2 text-slate-700 dark:text-slate-300 hover:bg-white dark:hover:bg-slate-700 rounded-lg transition-colors whitespace-nowrap text-sm"
                  title="Analytics"
                >
                  <BarChart3 className="w-5 h-5" />
                  <span className="hidden sm:inline">Analytics</span>
                </button>
                <button
                  onClick={() => setAppStep('billing')}
                  className="flex items-center space-x-2 px-3 py-2 text-slate-700 dark:text-slate-300 hover:bg-white dark:hover:bg-slate-700 rounded-lg transition-colors whitespace-nowrap text-sm"
                  title="Billing"
                >
                  <CreditCard className="w-5 h-5" />
                  <span className="hidden sm:inline">Billing</span>
                </button>
                <button
                  onClick={() => setAppStep('api')}
                  className="flex items-center space-x-2 px-3 py-2 text-slate-700 dark:text-slate-300 hover:bg-white dark:hover:bg-slate-700 rounded-lg transition-colors whitespace-nowrap text-sm"
                  title="API"
                >
                  <Code2 className="w-5 h-5" />
                  <span className="hidden sm:inline">API</span>
                </button>
                <button
                  onClick={() => setAppStep('settings')}
                  className="flex items-center space-x-2 px-3 py-2 text-slate-700 dark:text-slate-300 hover:bg-white dark:hover:bg-slate-700 rounded-lg transition-colors whitespace-nowrap text-sm"
                  title="Settings"
                >
                  <Settings className="w-5 h-5" />
                  <span className="hidden sm:inline">Settings</span>
                </button>
              </div>
            </div>

            {(appStep !== 'create') && (
              <StepIndicator steps={steps} currentStep={getCurrentStep()} />
            )}
          </>
        )}

        {appStep === 'projects' && (
          <div className="animate-fade-in">
            <div className="mb-8 flex items-center justify-between">
              <div>
                <h2 className="text-3xl font-bold text-slate-900 dark:text-slate-100 mb-2">
                  My Projects
                </h2>
                <p className="text-slate-600 dark:text-slate-400">
                  Create and manage your AI-generated videos
                </p>
              </div>
              <button
                onClick={fetchVideos}
                disabled={isLoadingProjects}
                className="btn-secondary flex items-center space-x-2"
              >
                <span>{isLoadingProjects ? 'Loading...' : 'Refresh'}</span>
              </button>
            </div>

            {isLoadingProjects ? (
              <div className="card p-16 text-center">
                <div className="inline-flex items-center justify-center w-12 h-12 bg-blue-100 rounded-full mb-4 animate-pulse">
                  <Video className="w-6 h-6 text-blue-600" />
                </div>
                <p className="text-slate-500 dark:text-slate-400">Loading projects...</p>
              </div>
            ) : projectsError ? (
              <div className="card p-16 text-center">
                <p className="text-red-600 dark:text-red-400 mb-4">{projectsError}</p>
                <button
                  onClick={fetchVideos}
                  className="btn-primary"
                >
                  Try Again
                </button>
              </div>
            ) : projects.length === 0 ? (
              <div className="card p-16 text-center">
                <Film className="w-16 h-16 mx-auto text-slate-300 mb-4" />
                <p className="text-slate-500 dark:text-slate-400 mb-6">No projects yet</p>
                <button
                  onClick={() => setAppStep('create')}
                  className="btn-primary"
                >
                  Create Your First Video
                </button>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {projects.map((project) => (
                  <ProjectCard
                    key={project.id}
                    project={project}
                    onSelect={handleProjectSelect}
                  />
                ))}
              </div>
            )}
          </div>
        )}

        {appStep === 'create' && (
          <div className="card p-8 animate-fade-in">
            <div className="mb-8">
              <h2 className="text-2xl font-bold text-slate-900 dark:text-slate-100 mb-2">
                Create Your Video
              </h2>
              <p className="text-slate-600 dark:text-slate-400">
                Describe your vision and let AI bring it to life, or choose a template to get started
              </p>
            </div>

            <form onSubmit={handleSubmit} className="space-y-6">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-2">
                  Project Title
                </label>
                <input
                  type="text"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  placeholder="E.g., Summer Travel Vlog"
                  className="input-field"
                  required
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-2">
                  Description (optional)
                </label>
                <textarea
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="Add more context about your project..."
                  className="input-field resize-none h-20"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-2">
                  What would you like to create?
                </label>
                <textarea
                  value={prompt}
                  onChange={(e) => setPrompt(e.target.value)}
                  placeholder="Describe your video in detail. E.g., Create a promotional video about sustainable living with nature scenes, uplifting music, and inspirational quotes..."
                  className="input-field resize-none h-32"
                  required
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-2">
                  Reference Materials
                </label>
                <div className="space-y-4">
                  <UploadZone
                    disabled={isProcessing}
                    onAssetsUploaded={(assetIds) => {
                      setReferenceAssets(prev => {
                        const newIds = [...prev, ...assetIds];
                        // Remove duplicates
                        return Array.from(new Set(newIds));
                      });
                      // Trigger asset list refresh
                      setAssetRefreshTrigger(prev => prev + 1);
                      addNotification('success', 'Files Uploaded', `${assetIds.length} file(s) uploaded successfully.`);
                    }}
                  />
                  <AssetList
                    selectedAssetIds={referenceAssets}
                    onSelectionChange={(assetIds) => {
                      setReferenceAssets(assetIds);
                    }}
                    disabled={isProcessing}
                    refreshTrigger={assetRefreshTrigger}
                  />
                </div>
              </div>

              <button
                type="submit"
                disabled={!prompt || !title || isProcessing}
                className="w-full btn-primary flex items-center justify-center space-x-2"
              >
                <Sparkles className="w-5 h-5" />
                <span>{isProcessing ? 'Processing...' : 'Start Creating'}</span>
              </button>
            </form>
          </div>
        )}

        {appStep === 'processing' && (
          <div className="card p-8 text-center animate-fade-in">
            <div className="inline-flex items-center justify-center w-20 h-20 bg-blue-100 rounded-full mb-6 animate-pulse-subtle">
              <Video className="w-10 h-10 text-blue-600" />
            </div>
            <h2 className="text-2xl font-bold text-slate-900 dark:text-slate-100 mb-2">
              AI is Creating Your Video
            </h2>
            <p className="text-slate-600 dark:text-slate-400 mb-8">
              Sit back and relax while our AI works its magic...
            </p>

            <div className="max-w-md mx-auto text-left">
              <ProcessingSteps steps={processingSteps} elapsedTime={elapsedTime} />
            </div>
          </div>
        )}

        {appStep === 'preview' && (
          <div className="card overflow-hidden animate-fade-in">
            <div className="aspect-video bg-gradient-to-br from-slate-800 to-slate-900 flex items-center justify-center">
              <div className="text-center text-white">
                <Film className="w-20 h-20 mx-auto mb-4 opacity-50 animate-float" />
                <p className="text-lg font-medium opacity-75">Your Video is Ready</p>
              </div>
            </div>
            <div className="p-8 space-y-6">
              <div>
                <h2 className="text-2xl font-bold text-slate-900 dark:text-slate-100 mb-2">
                  {title}
                </h2>
                {description && (
                  <p className="text-slate-600 dark:text-slate-400">
                    {description}
                  </p>
                )}
              </div>

              <div className="grid grid-cols-2 gap-4 p-4 bg-slate-50 rounded-lg">
                <div>
                  <p className="text-xs text-slate-500 dark:text-slate-400">Duration</p>
                  <p className="text-lg font-semibold text-slate-900 dark:text-slate-100">2:45</p>
                </div>
                <div>
                  <p className="text-xs text-slate-500 dark:text-slate-400">Resolution</p>
                  <p className="text-lg font-semibold text-slate-900 dark:text-slate-100">1080p</p>
                </div>
              </div>

              <div className="flex flex-col space-y-3">
                <div className="grid grid-cols-2 gap-4">
                  <button
                    onClick={() => {
                      setAppStep('create');
                      setPrompt('');
                      setTitle('');
                      setDescription('');
                    }}
                    className="btn-secondary"
                  >
                    Create Another
                  </button>
                  <button
                    onClick={() => setAppStep('export')}
                    className="btn-primary flex items-center justify-center space-x-2"
                  >
                    <BarChart3 className="w-5 h-5" />
                    <span>Export</span>
                  </button>
                </div>
                <button
                  onClick={() => setAppStep('download')}
                  className="w-full btn-primary flex items-center justify-center space-x-2"
                >
                  <Download className="w-5 h-5" />
                  <span>Download Video</span>
                </button>
              </div>
            </div>
          </div>
        )}

        {appStep === 'download' && (
          <div className="card p-8 text-center animate-fade-in">
            <div className="inline-flex items-center justify-center w-20 h-20 bg-green-100 rounded-full mb-6">
              <Download className="w-10 h-10 text-green-600" />
            </div>
            <h2 className="text-2xl font-bold text-slate-900 dark:text-slate-100 mb-2">
              Download Complete!
            </h2>
            <p className="text-slate-600 dark:text-slate-400 mb-8">
              Your video is ready to share with the world
            </p>
            <div className="flex flex-col space-y-3">
              <button
                onClick={() => {
                  setAppStep('create');
                  setPrompt('');
                  setTitle('');
                  setDescription('');
                }}
                className="btn-primary"
              >
                Create New Video
              </button>
              <button
                onClick={() => setAppStep('projects')}
                className="btn-secondary flex items-center justify-center space-x-2"
              >
                <ArrowLeft className="w-5 h-5" />
                <span>My Projects</span>
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default App;
