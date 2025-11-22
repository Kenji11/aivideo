import { EditingPage } from './features/editing/EditingPage';
import { BrowserRouter, Routes, Route, useNavigate, useLocation } from 'react-router-dom';
import { Sparkles, Video, Film, Download } from 'lucide-react';
import { Header } from './components/Header';
import { StepIndicator } from './components/StepIndicator';
import { toast } from '@/hooks/use-toast';
import { Toaster } from '@/components/ui/toaster';
import { ExportPanel } from './components/ExportPanel';
import { Auth } from './pages/Auth';
import { AssetLibrary } from './pages/AssetLibrary';
import { UploadVideo } from './pages/UploadVideo';
import { VideoStatus } from './pages/VideoStatus';
import { Preview } from './pages/Preview';
import { Projects } from './pages/Projects';
import { useAuth } from './contexts/AuthContext';
import { useDarkMode } from './lib/useDarkMode';
import { useParams } from 'react-router-dom';

// Export Route Wrapper Component
function ExportRouteWrapper() {
  const navigate = useNavigate();
  const { videoId } = useParams<{ videoId: string }>();
  
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const handleExport = (_settings: any) => {
    toast({
      variant: 'default',
      title: 'Export Started',
      description: 'Your video is being exported',
    });
    if (videoId) {
      navigate(`/preview/${videoId}`);
    } else {
      navigate('/projects');
    }
  };
  
  const handleCancel = () => {
    if (videoId) {
      navigate(`/preview/${videoId}`);
    } else {
      navigate('/projects');
    }
  };
  
  return <ExportPanel onExport={handleExport} onCancel={handleCancel} />;
}

// Main App Content (inside router)
function AppContent() {
  const navigate = useNavigate();
  const location = useLocation();
  const { user, loading: authLoading, signOut } = useAuth();
  useDarkMode();

  const steps = [
    { id: 1, name: 'Create', icon: Sparkles },
    { id: 2, name: 'Generate', icon: Video },
    { id: 3, name: 'Preview', icon: Film },
    { id: 4, name: 'Download', icon: Download },
  ];

  const getCurrentStep = () => {
    if (location.pathname.startsWith('/processing')) return 2;
    if (location.pathname.startsWith('/preview')) return 3;
    if (location.pathname === '/download') return 4;
    return 1;
  };

  const handleAuthSuccess = () => {
    navigate('/');
  };

  const handleLogout = async () => {
    try {
      await signOut();
      navigate('/');
    } catch (error) {
      console.error('Logout error:', error);
      toast({
        variant: 'destructive',
        title: 'Logout Failed',
        description: 'Failed to sign out. Please try again.',
      });
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
                           location.pathname.startsWith('/preview') || 
                           location.pathname === '/download';

  // Get user display name or email
  const userName = user.displayName || user.email?.split('@')[0] || 'User';

  return (
    <div className="min-h-screen bg-background">
      <Header onLogout={handleLogout} userName={userName} />

      <Toaster />

      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-12">

        {/* Step indicator - only shown on processing/preview/download pages */}
        {showStepIndicator && (
          <StepIndicator steps={steps} currentStep={getCurrentStep()} />
        )}

        <Routes>
          <Route path="/" element={<UploadVideo />} />
          <Route path="/projects" element={<Projects />} />

          <Route path="/processing/:videoId" element={<VideoStatus />} />

          <Route path="/preview/:videoId" element={<Preview />} />

          <Route path="/video/:videoId/edit" element={<EditingPage />} />

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
                
                <div className="flex flex-col space-y-3 max-w-md mx-auto">
                  <button
                    onClick={() => navigate('/')}
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

          <Route path="/export/:videoId" element={<ExportRouteWrapper />} />
          <Route path="/asset-library" element={<AssetLibrary />} />
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
