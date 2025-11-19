import { useState, useEffect } from 'react';
import { BrowserRouter, Routes, Route, useNavigate, useLocation } from 'react-router-dom';
import { Sparkles, Video, Film, Download, BarChart3 } from 'lucide-react';
// Commented out - may use later
// import { Settings, Zap, Library, CreditCard, Code2 } from 'lucide-react';
import { Header } from './components/Header';
import { StepIndicator } from './components/StepIndicator';
import { ProjectCard } from './components/ProjectCard';
import { ProcessingSteps } from './components/ProcessingSteps';
import { Notification } from './components/NotificationCenter';
import { toast } from '@/hooks/use-toast';
import { Toaster } from '@/components/ui/toaster';
import type { Template } from './components/TemplateGallery';
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
import { listVideos, VideoListItem } from './lib/api';
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
  const [processingProgress, setProcessingProgress] = useState(0);
  const [videoId, setVideoId] = useState<string | null>(null);
  const [animaticUrls, setAnimaticUrls] = useState<string[] | null>(null);
  const [referenceAssets, setReferenceAssets] = useState<StatusResponse['reference_assets'] | null>(null);
  const [stitchedVideoUrl, setStitchedVideoUrl] = useState<string | null>(null);
  const [uploadedAssetIds, setUploadedAssetIds] = useState<string[]>([]);
  const [selectedModel, setSelectedModel] = useState<string>('veo_fast');

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

  // Get videoId from route params if on processing page, otherwise use state
  const routeParams = useParams<{ videoId?: string }>();
  const activeVideoId = location.pathname.startsWith('/processing/') 
    ? routeParams.videoId || null 
    : videoId || null;

  // Use SSE stream for real-time status updates (with automatic fallback to polling)
  const { status: streamStatus, error: streamError, isConnected } = useVideoStatusStream(
    activeVideoId,
    isProcessing
  );

  // Use refs to track notification state across renders
  const hasShownAnimaticNotificationRef = useRef(false);
  const hasShownStitchedNotificationRef = useRef(false);

  // Reset notification flags and state when activeVideoId changes
  useEffect(() => {
    if (activeVideoId) {
      hasShownAnimaticNotificationRef.current = false;
      hasShownStitchedNotificationRef.current = false;
      // Reset state when navigating to a new video
      setAnimaticUrls(null);
      setStitchedVideoUrl(null);
      setCurrentChunkIndex(null);
      setTotalChunks(null);
      setCurrentPhase(undefined);
      setProcessingProgress(0);
      setElapsedTime(0);
      setIsProcessing(true);
    }
  }, [activeVideoId]);

  // Handle status updates from SSE stream
  useEffect(() => {
    if (!streamStatus || !isProcessing) return;

    const status = streamStatus;
    
    console.log('[App] Processing status update:', {
      video_id: status.video_id,
      status: status.status,
      progress: status.progress,
      current_phase: status.current_phase,
      has_animatic_urls: !!status.animatic_urls?.length,
      has_video_url: !!(status.final_video_url || status.stitched_video_url),
      chunk_progress: status.current_chunk_index !== undefined 
        ? `${status.current_chunk_index + 1}/${status.total_chunks}` 
        : null,
      timestamp: new Date().toISOString()
    });
    
    const currentStep = getProcessingStepFromPhase(status.current_phase, status.progress);
    setProcessingProgress(currentStep);
    setCurrentPhase(status.current_phase);
    
    // Update animatic URLs (allow updates if they change)
    if (status.animatic_urls && status.animatic_urls.length > 0) {
      // Only show notification on first set, but allow updates
      setAnimaticUrls(prev => {
        const isFirstTime = !prev;
        if (isFirstTime && !hasShownAnimaticNotificationRef.current) {
          hasShownAnimaticNotificationRef.current = true;
          addNotification('success', 'Storyboard Images Generated', `${status.animatic_urls!.length} storyboard image${status.animatic_urls!.length !== 1 ? 's' : ''} ready!`);
        }
        return status.animatic_urls!;
      });
    }
    
    // Phase 3 (Reference Assets) is disabled - commented out
    // if (status.reference_assets && !referenceAssets) {
    //   setReferenceAssets(status.reference_assets);
    //   addNotification('success', 'Reference Assets Generated', 'Style guide and product references are ready!');
    // }
    
    // Update current chunk progress for Phase 4
    if (status.current_phase === 'phase4_chunks') {
      if (status.current_chunk_index !== undefined) {
        setCurrentChunkIndex(status.current_chunk_index);
      }
      if (status.total_chunks !== undefined) {
        setTotalChunks(status.total_chunks);
      }
    } else {
      // Clear chunk progress when Phase 4 is done
      setCurrentChunkIndex(null);
      setTotalChunks(null);
    }
    
    // Update video URLs - prefer final_video_url, fallback to stitched_video_url
    // For Veo models, Phase 5 is skipped, so final_video_url might not be set
    const videoUrl = status.final_video_url || status.stitched_video_url;
    if (videoUrl) {
      setStitchedVideoUrl(prev => {
        const isFirstTime = !prev;
        const urlChanged = prev && prev !== videoUrl;
        const isFinalVideo = !!status.final_video_url;
        
        if (isFirstTime) {
          // First time we get a video URL
          if (!hasShownStitchedNotificationRef.current) {
            hasShownStitchedNotificationRef.current = true;
            if (isFinalVideo) {
              addNotification('success', 'Video Complete', 'Your video with audio is ready!');
            } else {
              addNotification('success', 'Video Chunks Generated', 'Video chunks are being stitched together!');
            }
          }
        } else if (urlChanged && isFinalVideo) {
          // URL changed from stitched to final (Phase 5 completed for non-Veo models)
          if (!hasShownStitchedNotificationRef.current) {
            hasShownStitchedNotificationRef.current = true;
            addNotification('success', 'Video Complete', 'Your video with audio is ready!');
          }
        }
        
        return videoUrl;
      });
    }
    
    if (status.status === 'complete') {
      setIsProcessing(false);
      navigate('/preview');
    } else if (status.status === 'failed') {
      setIsProcessing(false);
      addNotification('error', 'Generation Failed', status.error || 'Unknown error');
    }
  }, [streamStatus, isProcessing, navigate]);

  // Handle SSE errors (fallback to polling is automatic, but log errors)
  useEffect(() => {
    if (streamError) {
      console.error('SSE stream error:', streamError);
      // Fallback to polling happens automatically in the hook
    }
  }, [streamError]);

  useEffect(() => {
    let interval: NodeJS.Timeout;
    if (isProcessing) {
      interval = setInterval(() => {
        setElapsedTime(t => t + 1);
      }, 1000);
    }
    return () => clearInterval(interval);
  }, [isProcessing]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    try {
      setIsProcessing(true);
      setElapsedTime(0);
      setProcessingProgress(0);
      // Reset all state for new video generation
      setAnimaticUrls(null);
      setStitchedVideoUrl(null);
      setCurrentChunkIndex(null);
      setTotalChunks(null);
      setCurrentPhase(undefined);
      // Phase 3 disabled - reference assets not used
      // setReferenceAssets(null);
      
      const response = await generateVideo({
        title: title || 'Untitled Video',
        description: description || undefined,
        prompt: prompt,
        reference_assets: uploadedAssetIds,
        model: selectedModel
      });
      
      // Navigate to processing page with videoId in route
      navigate(`/processing/${response.video_id}`);
      setVideoId(response.video_id);
      addNotification('success', 'Generation Started', 'Your video is being created...');
    } catch (error) {
      addNotification('error', 'Generation Failed', error instanceof Error ? error.message : 'Unknown error');
      setIsProcessing(false);
      navigate('/');
    }
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
  }, [location.pathname, projects.length]);

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
                  ? 'bg-blue-600 text-white' 
                  : 'text-slate-700 dark:text-slate-300 hover:bg-white dark:hover:bg-slate-700'
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
                  ? 'bg-blue-600 text-white' 
                  : 'text-slate-700 dark:text-slate-300 hover:bg-white dark:hover:bg-slate-700'
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
                  ? 'bg-blue-600 text-white' 
                  : 'text-slate-700 dark:text-slate-300 hover:bg-white dark:hover:bg-slate-700'
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
                  ? 'bg-blue-600 text-white' 
                  : 'text-slate-700 dark:text-slate-300 hover:bg-white dark:hover:bg-slate-700'
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
                  ? 'bg-blue-600 text-white' 
                  : 'text-slate-700 dark:text-slate-300 hover:bg-white dark:hover:bg-slate-700'
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
                  ? 'bg-blue-600 text-white' 
                  : 'text-slate-700 dark:text-slate-300 hover:bg-white dark:hover:bg-slate-700'
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
                  ? 'bg-blue-600 text-white' 
                  : 'text-slate-700 dark:text-slate-300 hover:bg-white dark:hover:bg-slate-700'
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
                  <div className="inline-block animate-spin rounded-full h-12 w-12 border-4 border-blue-600 border-t-transparent mb-4"></div>
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
                    />
                  ))}
                </div>
              )}
            </div>
          } />

          <Route path="/processing/:videoId" element={
            <div className="card p-8 text-center animate-fade-in">
              <div className="inline-flex items-center justify-center w-20 h-20 bg-primary/20 rounded-full mb-6 animate-pulse-subtle">
                <Video className="w-10 h-10 text-primary" />
              </div>
              <h2 className="text-2xl font-bold text-foreground mb-2">
                AI is Creating Your Video
              </h2>
              <p className="text-muted-foreground mb-8">
                Sit back and relax while our AI works its magic...
              </p>

              <div className="max-w-md mx-auto text-left mb-8">
                <ProcessingSteps steps={processingSteps} elapsedTime={elapsedTime} />
              </div>

              {animaticUrls && animaticUrls.length > 0 && (
                <div className="mt-8 pt-8 border-t border-border">
                  <div className="flex items-center justify-between mb-6">
                    <div>
                      <h3 className="text-xl font-bold text-foreground mb-1">
                        🎬 Storyboard Images Generated
                      </h3>
                      <p className="text-sm text-muted-foreground">
                        {animaticUrls.length} storyboard image{animaticUrls.length !== 1 ? 's' : ''} ready for video generation
                        {currentChunkIndex !== null && totalChunks !== null && (
                          <span className="ml-2 text-primary font-semibold">
                            • Processing chunk {currentChunkIndex + 1} of {totalChunks}
                          </span>
                        )}
                      </p>
                    </div>
                  </div>
                  
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4 max-w-4xl mx-auto">
                    {animaticUrls.map((url, idx) => {
                      const isProcessing = currentChunkIndex === idx && currentPhase === 'phase4_chunks';
                      // Chunk is completed if currentChunkIndex is past this chunk's index
                      // Or if Phase 4 is complete (currentPhase is not phase4_chunks and we have a final video)
                      const isCompleted = (currentChunkIndex !== null && idx < currentChunkIndex) ||
                                         (currentPhase !== 'phase4_chunks' && currentChunkIndex !== null && idx <= currentChunkIndex) ||
                                         (stitchedVideoUrl && currentPhase !== 'phase4_chunks');
                      
                      return (
                        <div key={idx} className="relative group">
                          <div className={`relative ${isProcessing ? 'animate-pulse' : ''}`}>
                            <img
                              src={url}
                              alt={`Storyboard image ${idx + 1}`}
                              className={`w-full h-32 object-cover rounded-lg border-2 shadow-md group-hover:scale-105 transition-transform cursor-pointer ${
                                isProcessing
                                  ? 'border-blue-500 dark:border-blue-400 ring-4 ring-blue-300 dark:ring-blue-600'
                                  : isCompleted
                                  ? 'border-green-500 dark:border-green-400'
                                  : 'border-slate-200 dark:border-slate-700'
                              }`}
                              onClick={() => window.open(url, '_blank')}
                              onError={(e) => {
                                e.currentTarget.src = 'https://via.placeholder.com/200x200?text=Image+Not+Available';
                              }}
                            />
                            {isProcessing && (
                              <div className="absolute inset-0 bg-blue-500 bg-opacity-20 rounded-lg flex items-center justify-center">
                                <div className="animate-spin rounded-full h-8 w-8 border-4 border-blue-600 border-t-transparent"></div>
                              </div>
                            )}
                            {isCompleted && (
                              <div className="absolute top-2 right-2 bg-green-500 rounded-full p-1">
                                <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                                </svg>
                              </div>
                            )}
                          </div>
                          <div className="absolute bottom-2 right-2 bg-black bg-opacity-50 text-white text-xs px-2 py-1 rounded opacity-0 group-hover:opacity-100 transition-opacity">
                            Beat {idx + 1}
                            {isProcessing && ' • Processing...'}
                            {isCompleted && ' • Complete'}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              {/* Phase 3 (Reference Assets) */}
              {referenceAssets && (
                <div className="mt-8 pt-8 border-t border-border">
                  <h3 className="text-lg font-semibold text-foreground mb-4">
                    Reference Assets Generated
                  </h3>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4 max-w-2xl mx-auto">
                    {referenceAssets.style_guide_url && (
                      <div className="bg-card rounded-lg p-4">
                        <p className="text-sm font-medium text-card-foreground mb-2">Style Guide</p>
                        <img 
                          src={referenceAssets.style_guide_url} 
                          alt="Style Guide"
                          className="w-full h-48 object-cover rounded-lg border border-border"
                          onError={(e) => {
                            e.currentTarget.src = 'https://via.placeholder.com/400x400?text=Style+Guide';
                          }}
                        />
                      </div>
                    )}
                    {referenceAssets.product_reference_url && (
                      <div className="bg-card rounded-lg p-4">
                        <p className="text-sm font-medium text-card-foreground mb-2">Product Reference</p>
                        <img 
                          src={referenceAssets.product_reference_url} 
                          alt="Product Reference"
                          className="w-full h-48 object-cover rounded-lg border border-border"
                          onError={(e) => {
                            e.currentTarget.src = 'https://via.placeholder.com/400x400?text=Product+Reference';
                          }}
                        />
                      </div>
                    )}
                  </div>
                  {referenceAssets.uploaded_assets && referenceAssets.uploaded_assets.length > 0 && (
                    <div className="mt-4">
                      <p className="text-sm font-medium text-card-foreground mb-2">
                        Uploaded Assets ({referenceAssets.uploaded_assets.length})
                      </p>
                      <div className="grid grid-cols-3 gap-2">
                        {referenceAssets.uploaded_assets.map((asset, idx) => (
                          <img
                            key={idx}
                            src={asset.s3_url}
                            alt={`Uploaded asset ${idx + 1}`}
                            className="w-full h-24 object-cover rounded border border-border"
                            onError={(e) => {
                              e.currentTarget.src = 'https://via.placeholder.com/200x200?text=Asset';
                            }}
                          />
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          } />

          <Route path="/preview" element={
            <div className="card overflow-hidden animate-fade-in">
              <div className="aspect-video bg-gradient-to-br from-slate-800 to-slate-900 flex items-center justify-center">
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
                      className="w-full max-w-2xl mx-auto rounded-lg border border-slate-200 dark:border-slate-700"
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
