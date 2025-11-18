import { useState, useEffect } from 'react';
import { BrowserRouter, Routes, Route, useNavigate, useLocation } from 'react-router-dom';
import { Sparkles, Video, Film, Download, Settings, BarChart3, Zap, Library, CreditCard, Code2 } from 'lucide-react';
import { Header } from './components/Header';
import { StepIndicator } from './components/StepIndicator';
import { UploadZone } from './components/UploadZone';
import { ProjectCard } from './components/ProjectCard';
import { ProcessingSteps } from './components/ProcessingSteps';
import { NotificationCenter, Notification } from './components/NotificationCenter';
import type { Template } from './components/TemplateGallery';
import { ExportPanel } from './components/ExportPanel';
import { Auth } from './pages/Auth';
import { Settings as SettingsPage } from './pages/Settings';
import { Analytics } from './pages/Analytics';
import { Templates } from './pages/Templates';
import { Dashboard } from './pages/Dashboard';
import { VideoLibrary } from './pages/VideoLibrary';
import { Billing } from './pages/Billing';
import { API } from './pages/API';
import { generateVideo, getVideoStatus, StatusResponse, listVideos, VideoListItem } from './lib/api';
import { useAuth } from './contexts/AuthContext';

// Main App Content (inside router)
function AppContent() {
  const navigate = useNavigate();
  const location = useLocation();
  const { user, loading: authLoading, signOut } = useAuth();
  const [prompt, setPrompt] = useState('');
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);
  const [elapsedTime, setElapsedTime] = useState(0);
  const [projects, setProjects] = useState<VideoListItem[]>([]);
  const [, setSelectedProject] = useState<VideoListItem | null>(null);
  const [isLoadingProjects, setIsLoadingProjects] = useState(false);
  const [processingProgress, setProcessingProgress] = useState(0);
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [videoId, setVideoId] = useState<string | null>(null);
  const [animaticUrls, setAnimaticUrls] = useState<string[] | null>(null);
  const [referenceAssets, setReferenceAssets] = useState<StatusResponse['reference_assets'] | null>(null);
  const [stitchedVideoUrl, setStitchedVideoUrl] = useState<string | null>(null);
  const [uploadedAssetIds, setUploadedAssetIds] = useState<string[]>([]);
  const [selectedModel, setSelectedModel] = useState<string>('veo_fast');
  const [currentChunkIndex, setCurrentChunkIndex] = useState<number | null>(null);
  const [totalChunks, setTotalChunks] = useState<number | null>(null);
  const [currentPhase, setCurrentPhase] = useState<string | undefined>(undefined);

  const steps = [
    { id: 1, name: 'Create', icon: Sparkles },
    { id: 2, name: 'Generate', icon: Video },
    { id: 3, name: 'Preview', icon: Film },
    { id: 4, name: 'Download', icon: Download },
  ];

  // Map current_phase to processing step index
  // Phase 3 (References) is disabled - skipped in pipeline
  const getProcessingStepFromPhase = (phase: string | undefined, progress: number): number => {
    if (!phase) return 0;
    if (phase === 'phase1_validate') return 0;
    if (phase === 'phase2_storyboard' || phase === 'phase2_animatic') return 1; // Support both new and legacy phase names
    // Phase 3 (references) is disabled - skip to Phase 4
    if (phase === 'phase3_references') return 2; // Should not occur, but handle gracefully
    if (phase === 'phase4_chunks') return 2; // Moved from 3 to 2 (Phase 3 removed)
    if (phase === 'phase5_refine') return 2; // Phase 5 is part of chunk generation/refinement, keep at step 2
    return Math.min(Math.floor(progress / 25), 2); // Cap at 2 (max step index)
  };

  const getStepStatus = (stepIndex: number): 'completed' | 'processing' | 'pending' => {
    if (processingProgress > stepIndex) return 'completed';
    if (processingProgress === stepIndex) return 'processing';
    return 'pending';
  };

  const processingSteps = [
    { name: 'Content planning with AI', status: getStepStatus(0) },
    { name: 'Generating storyboard images', status: getStepStatus(1) },
    // Phase 3 (Creating reference images) is disabled - commented out
    // { name: 'Creating reference images', status: getStepStatus(2) },
    { name: 'Generating & stitching video chunks', status: getStepStatus(2) }, // Moved from 3 to 2
  ];

  const addNotification = (type: Notification['type'], title: string, message: string) => {
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
    setTimeout(() => setNotifications((prev) => prev.filter((n) => n.id !== id)), 5000);
  };

  // Poll for video status
  useEffect(() => {
    if (!videoId || !isProcessing) return;

    let hasShownAnimaticNotification = false;
    let hasShownStitchedNotification = false;

    const pollStatus = async () => {
      try {
        const status = await getVideoStatus(videoId);
        
        const currentStep = getProcessingStepFromPhase(status.current_phase, status.progress);
        setProcessingProgress(currentStep);
        setCurrentPhase(status.current_phase);
        
        // Update animatic URLs (allow updates if they change)
        if (status.animatic_urls && status.animatic_urls.length > 0) {
          // Only show notification on first set, but allow updates
          setAnimaticUrls(prev => {
            const isFirstTime = !prev;
            if (isFirstTime && !hasShownAnimaticNotification) {
              hasShownAnimaticNotification = true;
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
              if (!hasShownStitchedNotification) {
                hasShownStitchedNotification = true;
                if (isFinalVideo) {
                  addNotification('success', 'Video Complete', 'Your video with audio is ready!');
                } else {
                  addNotification('success', 'Video Chunks Generated', 'Video chunks are being stitched together!');
                }
              }
            } else if (urlChanged && isFinalVideo) {
              // URL changed from stitched to final (Phase 5 completed for non-Veo models)
              if (!hasShownStitchedNotification) {
                hasShownStitchedNotification = true;
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
      } catch (error) {
        console.error('Failed to poll status:', error);
      }
    };

    const interval = setInterval(pollStatus, 2000);
    pollStatus();

    return () => clearInterval(interval);
  }, [videoId, isProcessing, navigate]); // Removed unnecessary dependencies to prevent re-renders

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
      navigate('/processing');
      
      const response = await generateVideo({
        title: title || 'Untitled Video',
        description: description || undefined,
        prompt: prompt,
        reference_assets: uploadedAssetIds,
        model: selectedModel
      });
      
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
      setVideoId(project.video_id);
      setIsProcessing(true);
      navigate('/processing');
    }
  };

  useEffect(() => {
    const fetchProjects = async () => {
      if (location.pathname === '/projects' || location.pathname === '/') {
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
  }, [location.pathname]);

  const getCurrentStep = () => {
    if (location.pathname === '/processing') return 2;
    if (location.pathname === '/preview') return 3;
    if (location.pathname === '/download') return 4;
    return 1;
  };

  const handleSelectTemplate = (template: Template) => {
    setTitle(template.name);
    setDescription(template.description);
    navigate('/');
    addNotification('success', 'Template Selected', `Started with ${template.name} template`);
  };

  const handleAuthSuccess = () => {
    navigate('/');
  };

  const handleLogout = async () => {
    try {
      await signOut();
      navigate('/login');
    } catch (error) {
      console.error('Logout error:', error);
      addNotification('error', 'Logout Failed', 'Failed to sign out. Please try again.');
    }
  };

  // Show loading state while checking auth
  if (authLoading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 dark:from-slate-900 dark:to-slate-800 flex items-center justify-center">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-12 w-12 border-4 border-blue-600 border-t-transparent mb-4"></div>
          <p className="text-slate-600 dark:text-slate-400">Loading...</p>
        </div>
      </div>
    );
  }

  // Show auth page if user is not logged in
  if (!user) {
    return <Auth onAuthSuccess={handleAuthSuccess} />;
  }

  const showStepIndicator = ['/processing', '/preview', '/download'].includes(location.pathname);

  // Get user display name or email
  const userName = user.displayName || user.email?.split('@')[0] || 'User';

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 dark:from-slate-900 dark:to-slate-800">
      <Header onLogout={handleLogout} userName={userName} />

      <NotificationCenter
        notifications={notifications}
        onDismiss={(id) => setNotifications((prev) => prev.filter((n) => n.id !== id))}
      />

      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        {/* Navigation buttons - always visible on all pages */}
        <div className="flex items-center justify-between mb-8 overflow-x-auto pb-2">
          <div className="space-x-2 flex flex-shrink-0">
            <button
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
            </button>
          </div>
        </div>

        {/* Step indicator - only shown on processing/preview/download pages */}
        {showStepIndicator && (
          <StepIndicator steps={steps} currentStep={getCurrentStep()} />
        )}

        <Routes>
          <Route path="/" element={
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
                  <UploadZone 
                    disabled={isProcessing} 
                    onAssetsUploaded={(assetIds) => {
                      setUploadedAssetIds(assetIds);
                      addNotification('success', 'Files Uploaded', `${assetIds.length} file(s) uploaded successfully!`);
                    }}
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-2">
                    Video Model
                  </label>
                  <select
                    value={selectedModel}
                    onChange={(e) => setSelectedModel(e.target.value)}
                    className="input-field"
                    disabled={isProcessing}
                  >
                    <option value="veo_fast">Google Veo 3.1 Fast (Recommended)</option>
                    <option value="veo">Google Veo 3.1</option>
                    <option value="hailuo">Hailuo 2.3 Fast</option>
                    <option value="seedance">Seedance 1.0 Pro Fast</option>
                    <option value="kling">Kling v2.5 Turbo Pro</option>
                    <option value="pixverse">Pixverse v5</option>
                    <option value="wan_25_t2v">Wan 2.5 T2V</option>
                    <option value="wan_25_i2v">Wan 2.5 I2V Fast</option>
                    <option value="runway_gen4_turbo">Runway Gen-4 Turbo (Test)</option>
                    <option value="hailuo_23">Minimax Hailuo 2.3</option>
                    <option value="sora">OpenAI Sora 2</option>
                    <option value="wan">Wan 2.1 (Legacy)</option>
                    <option value="zeroscope">Zeroscope v2 XL</option>
                    <option value="animatediff">AnimateDiff</option>
                    <option value="runway">Runway Gen-2</option>
                  </select>
                  <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                    Choose the AI model for video generation. Different models have different quality, speed, and cost characteristics.
                  </p>
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
          } />

          <Route path="/projects" element={
            <div className="animate-fade-in">
              <div className="mb-8">
                <h2 className="text-3xl font-bold text-slate-900 dark:text-slate-100 mb-2">
                  My Projects
                </h2>
                <p className="text-slate-600 dark:text-slate-400">
                  Create and manage your AI-generated videos
                </p>
              </div>

              {isLoadingProjects ? (
                <div className="card p-16 text-center">
                  <div className="inline-block animate-spin rounded-full h-12 w-12 border-4 border-blue-600 border-t-transparent mb-4"></div>
                  <p className="text-slate-500 dark:text-slate-400">Loading projects...</p>
                </div>
              ) : projects.length === 0 ? (
                <div className="card p-16 text-center">
                  <Film className="w-16 h-16 mx-auto text-slate-300 mb-4" />
                  <p className="text-slate-500 dark:text-slate-400 mb-6">No projects yet</p>
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

          <Route path="/processing" element={
            <div className="card p-8 text-center animate-fade-in">
              <div className="inline-flex items-center justify-center w-20 h-20 bg-blue-100 dark:bg-blue-900 rounded-full mb-6 animate-pulse-subtle">
                <Video className="w-10 h-10 text-blue-600 dark:text-blue-400" />
              </div>
              <h2 className="text-2xl font-bold text-slate-900 dark:text-slate-100 mb-2">
                AI is Creating Your Video
              </h2>
              <p className="text-slate-600 dark:text-slate-400 mb-8">
                Sit back and relax while our AI works its magic...
              </p>

              <div className="max-w-md mx-auto text-left mb-8">
                <ProcessingSteps steps={processingSteps} elapsedTime={elapsedTime} />
              </div>

              {animaticUrls && animaticUrls.length > 0 && (
                <div className="mt-8 pt-8 border-t border-slate-200 dark:border-slate-700">
                  <div className="flex items-center justify-between mb-6">
                    <div>
                      <h3 className="text-xl font-bold text-slate-900 dark:text-slate-100 mb-1">
                        🎬 Storyboard Images Generated
                      </h3>
                      <p className="text-sm text-slate-600 dark:text-slate-400">
                        {animaticUrls.length} storyboard image{animaticUrls.length !== 1 ? 's' : ''} ready for video generation
                        {currentChunkIndex !== null && totalChunks !== null && (
                          <span className="ml-2 text-blue-600 dark:text-blue-400 font-semibold">
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

              {/* Phase 3 (Reference Assets) is disabled - commented out */}
              {/* {referenceAssets && (
                <div className="mt-8 pt-8 border-t border-slate-200 dark:border-slate-700">
                  <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100 mb-4">
                    Reference Assets Generated
                  </h3>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4 max-w-2xl mx-auto">
                    {referenceAssets.style_guide_url && (
                      <div className="bg-slate-50 dark:bg-slate-800 rounded-lg p-4">
                        <p className="text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">Style Guide</p>
                        <img 
                          src={referenceAssets.style_guide_url} 
                          alt="Style Guide"
                          className="w-full h-48 object-cover rounded-lg border border-slate-200 dark:border-slate-700"
                          onError={(e) => {
                            e.currentTarget.src = 'https://via.placeholder.com/400x400?text=Style+Guide';
                          }}
                        />
                      </div>
                    )}
                    {referenceAssets.product_reference_url && (
                      <div className="bg-slate-50 dark:bg-slate-800 rounded-lg p-4">
                        <p className="text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">Product Reference</p>
                        <img 
                          src={referenceAssets.product_reference_url} 
                          alt="Product Reference"
                          className="w-full h-48 object-cover rounded-lg border border-slate-200 dark:border-slate-700"
                          onError={(e) => {
                            e.currentTarget.src = 'https://via.placeholder.com/400x400?text=Product+Reference';
                          }}
                        />
                      </div>
                    )}
                  </div>
                  {referenceAssets.uploaded_assets && referenceAssets.uploaded_assets.length > 0 && (
                    <div className="mt-4">
                      <p className="text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
                        Uploaded Assets ({referenceAssets.uploaded_assets.length})
                      </p>
                      <div className="grid grid-cols-3 gap-2">
                        {referenceAssets.uploaded_assets.map((asset, idx) => (
                          <img
                            key={idx}
                            src={asset.s3_url}
                            alt={`Uploaded asset ${idx + 1}`}
                            className="w-full h-24 object-cover rounded border border-slate-200 dark:border-slate-700"
                            onError={(e) => {
                              e.currentTarget.src = 'https://via.placeholder.com/200x200?text=Asset';
                            }}
                          />
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )} */}
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
                <div className="inline-flex items-center justify-center w-20 h-20 bg-green-100 dark:bg-green-900 rounded-full mb-6">
                  <Download className="w-10 h-10 text-green-600 dark:text-green-400" />
                </div>
                <h2 className="text-2xl font-bold text-slate-900 dark:text-slate-100 mb-2">
                  Your Video is Ready!
                </h2>
                <p className="text-slate-600 dark:text-slate-400 mb-8">
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

          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/templates" element={<Templates onSelectTemplate={handleSelectTemplate} />} />
          <Route path="/library" element={<VideoLibrary />} />
          <Route path="/analytics" element={<Analytics />} />
          <Route path="/billing" element={<Billing />} />
          <Route path="/api" element={<API />} />
          <Route path="/settings" element={<SettingsPage />} />
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
