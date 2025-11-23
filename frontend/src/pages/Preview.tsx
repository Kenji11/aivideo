import { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { Film, Download, BarChart3, ChevronDown, ChevronUp, Image as ImageIcon, Video, FileText, Sparkles, Play, AlertCircle, Edit } from 'lucide-react';
import { getVideoStatus, getVideo, getCheckpointTree, CheckpointTreeNode, CheckpointResponse, continueVideo } from '../lib/api';
import { toast } from '@/hooks/use-toast';
import { ChunkEditModal } from '../components/ChunkEditModal';
import { CheckpointSelector } from '../components/CheckpointSelector';
import { SpecEditModal } from '../components/SpecEditModal';
import { Button } from '../components/ui/button';
import { Alert, AlertDescription } from '../components/ui/alert';
import { ProcessingSteps } from '../components/ProcessingSteps';
import {
  getAllCheckpointsFromTree,
  rebuildTreeFromPhases,
  getPhase1Checkpoints,
  getChildrenOfCheckpoint,
  getCheckpointLineage,
  getSelectedCheckpoint,
  type CheckpointIndices
} from '../lib/checkpointUtils';

export function Preview() {
  const navigate = useNavigate();
  const { videoId } = useParams<{ videoId: string }>();
  
  const [videoUrl, setVideoUrl] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [retryCount, setRetryCount] = useState(0);
  const [checkpointTree, setCheckpointTree] = useState<CheckpointTreeNode[]>([]);
  const [checkpointIndices, setCheckpointIndices] = useState<CheckpointIndices>({
    phase1: 0,
    phase2: null,
    phase3: null,
  });
  const [checkpointSelections, setCheckpointSelections] = useState<{
    phase1: string | null;
    phase2: string | null;
    phase3: string | null;
  }>({
    phase1: null,
    phase2: null,
    phase3: null,
  });
  const [expandedPhases, setExpandedPhases] = useState<Set<string>>(new Set());
  const [videoTitle, setVideoTitle] = useState<string>('');
  const [videoDescription, setVideoDescription] = useState<string>('');
  const [processTime, setProcessTime] = useState<string>('');
  const [selectedChunkIndex, setSelectedChunkIndex] = useState<number | null>(null);
  const [chunkEditModalOpen, setChunkEditModalOpen] = useState(false);
  const [specEditModalOpen, setSpecEditModalOpen] = useState(false);
  const [isContinuing, setIsContinuing] = useState(false);

  // Processing state
  const [isProcessing, setIsProcessing] = useState<boolean>(false);
  const [isPaused, setIsPaused] = useState<boolean>(false);
  const [currentPhase, setCurrentPhase] = useState<string>('');
  const [progress, setProgress] = useState<number>(0);
  const [elapsedTime, setElapsedTime] = useState<number>(0);
  const [storyboardUrls, setStoryboardUrls] = useState<string[]>([]);
  const [failedPhase, setFailedPhase] = useState<{
    phase: string;
    error: string;
  } | null>(null);

  // Refs for polling and elapsed time
  const pollingIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const startTimeRef = useRef<number | null>(null);

  // Compute available checkpoints for each phase
  const phase1Checkpoints = useMemo(() => {
    const checkpoints = getPhase1Checkpoints(checkpointTree);
    console.log('[Preview] Phase 1 checkpoints:', checkpoints.length, checkpoints);
    return checkpoints;
  }, [checkpointTree]);
  
  const phase2Checkpoints = useMemo(() => {
    const phase1Checkpoint = getSelectedCheckpoint(1, checkpointIndices, checkpointTree);
    console.log('[Preview] Computing Phase 2 checkpoints. Selected Phase 1:', phase1Checkpoint?.id, 'phase:', phase1Checkpoint?.phase_number, 'checkpointTree nodes:', checkpointTree.length);
    if (!phase1Checkpoint) {
      console.log('[Preview] No Phase 1 checkpoint selected, returning empty Phase 2 list');
      return [];
    }
    const children = getChildrenOfCheckpoint(checkpointTree, phase1Checkpoint.id);
    console.log('[Preview] Found', children.length, 'Phase 2 children for Phase 1', phase1Checkpoint.id, ':', children.map(c => ({ id: c.id, phase: c.phase_number, parent: c.parent_checkpoint_id })));
    return children;
  }, [checkpointTree, checkpointIndices.phase1]);
  
  const phase3Checkpoints = useMemo(() => {
    const phase2Checkpoint = getSelectedCheckpoint(2, checkpointIndices, checkpointTree);
    if (!phase2Checkpoint) return [];
    return getChildrenOfCheckpoint(checkpointTree, phase2Checkpoint.id);
  }, [checkpointTree, checkpointIndices.phase1, checkpointIndices.phase2]);
  
  // Phase 4 removed from pipeline

  // Get selected checkpoints using ID-based selections
  const selectedPhase1 = useMemo(() => {
    if (!checkpointSelections.phase1) return null;
    return getAllCheckpointsFromTree(checkpointTree).find(cp => cp.id === checkpointSelections.phase1) || null;
  }, [checkpointSelections.phase1, checkpointTree]);

  const selectedPhase2 = useMemo(() => {
    if (!checkpointSelections.phase2) return null;
    return getAllCheckpointsFromTree(checkpointTree).find(cp => cp.id === checkpointSelections.phase2) || null;
  }, [checkpointSelections.phase2, checkpointTree]);

  const selectedPhase3 = useMemo(() => {
    if (!checkpointSelections.phase3) return null;
    return getAllCheckpointsFromTree(checkpointTree).find(cp => cp.id === checkpointSelections.phase3) || null;
  }, [checkpointSelections.phase3, checkpointTree]);
  // Phase 4 removed from pipeline

  // Initialize checkpoint indices based on current_checkpoint or first Phase 1
  const initializeCheckpointIndices = useCallback((tree: CheckpointTreeNode[], currentCheckpointId?: string) => {
    const phase1Checkpoints = getPhase1Checkpoints(tree);
    if (phase1Checkpoints.length === 0) {
      return { phase1: 0, phase2: null, phase3: null };
    }

    let initialPhase1Index = 0;

    // If current_checkpoint exists, walk up to find Phase 1 ancestor
    if (currentCheckpointId) {
      const lineage = getCheckpointLineage(currentCheckpointId, tree);
      const phase1InLineage = lineage.find(cp => cp.phase_number === 1);
      if (phase1InLineage) {
        initialPhase1Index = phase1Checkpoints.findIndex(cp => cp.id === phase1InLineage.id);
        if (initialPhase1Index === -1) initialPhase1Index = 0;
      }
    }

    // Set initial indices
    const indices: CheckpointIndices = {
      phase1: initialPhase1Index,
      phase2: null,
      phase3: null,
    };

    // Walk down to find corresponding Phase 2/3 if they exist
    const phase1Checkpoint = phase1Checkpoints[initialPhase1Index];
    if (phase1Checkpoint) {
      const phase2Children = getChildrenOfCheckpoint(tree, phase1Checkpoint.id);
      if (phase2Children.length > 0) {
        indices.phase2 = 0;
        const phase2Checkpoint = phase2Children[0];
        const phase3Children = getChildrenOfCheckpoint(tree, phase2Checkpoint.id);
        if (phase3Children.length > 0) {
          indices.phase3 = 0;
          // Phase 4 removed from pipeline
        }
      }
    }

    return indices;
  }, []);

  const fetchVideoData = useCallback(async (forceRefresh: boolean = false) => {
    if (!videoId) {
      setError('No video ID provided');
      setIsLoading(false);
      return;
    }

    if (!forceRefresh) {
      setIsLoading(true);
      setError(null);
    }

    try {
      // Fetch video details, status, and checkpoint tree in parallel
      const [videoData, statusData, treeData] = await Promise.all([
        getVideo(videoId).catch(err => {
          console.error('[Preview] Failed to fetch video:', err);
          return null;
        }),
        getVideoStatus(videoId).catch(err => {
          if (err.response?.status !== 404) {
            console.error('[Preview] Failed to fetch status:', err);
          }
          return null;
        }),
        getCheckpointTree(videoId).catch(err => {
          console.error('[Preview] Failed to fetch checkpoint tree:', err);
          return { tree: [] };
        })
      ]);

      // Handle processing state - check statusData first, fall back to videoData.status
      const statusSource = statusData || videoData;
      if (statusSource) {
        const status = statusSource.status;
        const statusLower = status.toLowerCase();
        const processingStatuses = ['queued', 'validating', 'generating_animatic', 'generating_chunks', 'refining', 'exporting'];
        const pausedStatuses = ['paused_at_phase1', 'paused_at_phase2', 'paused_at_phase3'];

        // PAUSED states should show checkpoint UI, not processing UI (case-insensitive)
        const isCurrentlyProcessing = processingStatuses.includes(statusLower);
        const isCurrentlyPaused = pausedStatuses.includes(statusLower);

        console.log('[Preview] Status detection:', { status, isCurrentlyProcessing, isCurrentlyPaused, statusData: !!statusData, videoData: !!videoData });

        setIsProcessing(isCurrentlyProcessing);
        setIsPaused(isCurrentlyPaused);

        // Only statusData has current_phase and progress fields
        if (statusData) {
          setCurrentPhase(statusData.current_phase || '');
          setProgress(statusData.progress || 0);

          // Handle storyboard updates
          if (statusData.storyboard_urls) {
            setStoryboardUrls(statusData.storyboard_urls);
          }

          // Handle failed state (case-insensitive)
          if (statusLower === 'failed') {
            setFailedPhase({
              phase: statusData.current_phase || 'unknown',
              error: statusData.error || 'Unknown error'
            });
            setIsProcessing(false);
          } else {
            setFailedPhase(null);
          }
        } else if (videoData) {
          // Fall back to videoData when statusData is unavailable
          // VideoData doesn't have current_phase or progress, so use defaults
          setCurrentPhase('');
          setProgress(0);

          if (statusLower === 'failed') {
            setFailedPhase({
              phase: 'unknown',
              error: 'Video generation failed'
            });
            setIsProcessing(false);
          } else {
            setFailedPhase(null);
          }
        }

        // Initialize elapsed time tracking
        if (isCurrentlyProcessing && !startTimeRef.current) {
          startTimeRef.current = Date.now();
        } else if (!isCurrentlyProcessing) {
          startTimeRef.current = null;
        }
      }

      // Extract checkpoint tree
      let tree = treeData?.tree || [];
      if (tree.length > 0) {
        const allCheckpoints = getAllCheckpointsFromTree(tree);
        const allAreRoots = allCheckpoints.every(cp => !cp.parent_checkpoint_id);

        if (allAreRoots) {
          console.log('[Preview] All checkpoints are roots, rebuilding tree from phases');
          tree = rebuildTreeFromPhases(allCheckpoints);
        }

        setCheckpointTree(tree);
      } else {
        setCheckpointTree([]);
      }

      // Extract video URL (prefer final, fallback to stitched)
      // Note: stitched_video_url and url may not exist on VideoResponse type, add optional chaining and type guards
      const videoUrlFromStatus =
        statusData?.final_video_url ||
        (statusData && 'stitched_video_url' in statusData ? (statusData as any).stitched_video_url : undefined);

      const videoUrlFromData =
        videoData?.final_video_url ||
        (videoData && 'stitched_video_url' in videoData ? (videoData as any).stitched_video_url : undefined) ||
        (videoData && 'url' in videoData ? (videoData as any).url : undefined);

      setVideoUrl(videoUrlFromStatus || videoUrlFromData || null);

      // Extract metadata
      if (videoData) {
        setVideoTitle(videoData.title || 'Untitled Video');
        setVideoDescription(videoData.description || '');
      }

      // Calculate process time
      if (videoData?.completed_at && videoData?.created_at) {
        const completedTime = new Date(videoData.completed_at).getTime();
        const createdTime = new Date(videoData.created_at).getTime();
        const durationMs = completedTime - createdTime;
        const minutes = Math.floor(durationMs / 60000);
        const seconds = Math.floor((durationMs % 60000) / 1000);
        setProcessTime(`${minutes}m ${seconds}s`);
      } else if (videoData?.generation_time_seconds) {
        const totalSeconds = videoData.generation_time_seconds;
        const minutes = Math.floor(totalSeconds / 60);
        const seconds = Math.floor(totalSeconds % 60);
        setProcessTime(`${minutes}m ${seconds}s`);
      }

      // Initialize checkpoint indices
      if (tree.length > 0) {
        const currentCheckpointId = statusData?.current_checkpoint?.checkpoint_id;
        const initialIndices = initializeCheckpointIndices(tree, currentCheckpointId);
        setCheckpointIndices(initialIndices);
      }

      setError(null);
    } catch (err) {
      console.error('[Preview] Error fetching video data:', err);
      setError(err instanceof Error ? err.message : 'Failed to load video');
    } finally {
      setIsLoading(false);
    }
  }, [videoId, initializeCheckpointIndices]);

  useEffect(() => {
    fetchVideoData();
  }, [fetchVideoData]);

  // Polling effect for processing videos
  useEffect(() => {
    if (!isProcessing) {
      // Clear polling interval if not processing
      if (pollingIntervalRef.current) {
        clearInterval(pollingIntervalRef.current);
        pollingIntervalRef.current = null;
      }
      return;
    }

    // Start polling every 2.5 seconds
    pollingIntervalRef.current = setInterval(() => {
      fetchVideoData(true); // forceRefresh = true
    }, 2500);

    return () => {
      if (pollingIntervalRef.current) {
        clearInterval(pollingIntervalRef.current);
        pollingIntervalRef.current = null;
      }
    };
  }, [isProcessing, fetchVideoData]);

  // Elapsed time counter
  useEffect(() => {
    if (!isProcessing || !startTimeRef.current) {
      return;
    }

    const interval = setInterval(() => {
      if (startTimeRef.current) {
        const elapsed = Math.floor((Date.now() - startTimeRef.current) / 1000);
        setElapsedTime(elapsed);
      }
    }, 1000);

    return () => clearInterval(interval);
  }, [isProcessing]);

  // Auto-select first checkpoint when children become available
  useEffect(() => {
    setCheckpointIndices(prev => {
      const next = { ...prev };
      let changed = false;

      // Auto-select Phase 2 if available and not selected
      if (phase2Checkpoints.length > 0 && next.phase2 === null) {
        console.log('[Preview] Auto-selecting Phase 2, found', phase2Checkpoints.length, 'checkpoints');
        next.phase2 = 0;
        changed = true;
      }

      // Auto-select Phase 3 if available and not selected
      if (phase3Checkpoints.length > 0 && next.phase3 === null) {
        console.log('[Preview] Auto-selecting Phase 3, found', phase3Checkpoints.length, 'checkpoints');
        next.phase3 = 0;
        changed = true;
      }

      // Phase 4 removed from pipeline

      return changed ? next : prev;
    });
  }, [phase2Checkpoints, phase3Checkpoints]);

  // Arrow key navigation
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Ignore if user is typing in inputs/textareas
      const target = e.target as HTMLElement;
      if (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.isContentEditable) {
        return;
      }

      if (e.key === 'ArrowLeft' || e.key === 'ArrowRight') {
        e.preventDefault();
        
        // Determine which phase to navigate based on current selections (Phase 4 removed)
        let targetPhase: 1 | 2 | 3 = 1;
        let targetCheckpoints: CheckpointResponse[] = [];
        let currentIndex: number | null = null;

        if (checkpointIndices.phase3 !== null && phase3Checkpoints.length > 0) {
          targetPhase = 3;
          targetCheckpoints = phase3Checkpoints;
          currentIndex = checkpointIndices.phase3;
        } else if (checkpointIndices.phase2 !== null && phase2Checkpoints.length > 0) {
          targetPhase = 2;
          targetCheckpoints = phase2Checkpoints;
          currentIndex = checkpointIndices.phase2;
        } else if (phase1Checkpoints.length > 0) {
          targetPhase = 1;
          targetCheckpoints = phase1Checkpoints;
          currentIndex = checkpointIndices.phase1;
        }

        if (targetCheckpoints.length <= 1) return;

        const newIndex = e.key === 'ArrowLeft' 
          ? (currentIndex! - 1 + targetCheckpoints.length) % targetCheckpoints.length
          : (currentIndex! + 1) % targetCheckpoints.length;

        setCheckpointIndices(prev => {
          const next = { ...prev };
          if (targetPhase === 1) {
            next.phase1 = newIndex;
            // Reset downstream phases when Phase 1 changes
            next.phase2 = null;
            next.phase3 = null;
          } else if (targetPhase === 2) {
            next.phase2 = newIndex;
            // Reset downstream phases when Phase 2 changes
            next.phase3 = null;
          } else if (targetPhase === 3) {
            next.phase3 = newIndex;
            // Phase 3 is now terminal (Phase 4 removed)
          }
          return next;
        });
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [checkpointIndices, phase1Checkpoints, phase2Checkpoints, phase3Checkpoints]);

  // Handle checkpoint selection change
  const handleCheckpointSelection = (phase: 1 | 2 | 3, checkpointId: string) => {
    if (phase === 1) {
      // Selecting Phase 1 clears Phase 2 and 3
      setCheckpointSelections({
        phase1: checkpointId,
        phase2: null,
        phase3: null,
      });
    } else if (phase === 2) {
      // Selecting Phase 2 clears Phase 3
      setCheckpointSelections(prev => ({
        ...prev,
        phase2: checkpointId,
        phase3: null,
      }));
    } else {
      // Selecting Phase 3
      setCheckpointSelections(prev => ({
        ...prev,
        phase3: checkpointId,
      }));
    }
  };

  // Handle spec edit success
  const handleSpecEditSuccess = useCallback(async () => {
    const checkpointsBeforeRefresh = getAllCheckpointsFromTree(checkpointTree);

    console.log('[Preview] handleSpecEditSuccess: Before refresh, checkpoint count:', checkpointsBeforeRefresh.length);

    await fetchVideoData(true); // Refresh checkpoint tree

    // Give React time to update the state after fetchVideoData completes
    requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        // This callback will run after the next two animation frames, ensuring state is updated
        setCheckpointTree(currentTree => {
          const allCheckpoints = getAllCheckpointsFromTree(currentTree);

          // Find new checkpoints that weren't there before
          const newCheckpoints = allCheckpoints.filter(
            cp => !checkpointsBeforeRefresh.some(oldCp => oldCp.id === cp.id)
          );

          // Find the newest Phase 1 checkpoint (most recently created)
          const newBranch = newCheckpoints
            .filter(cp => cp.phase_number === 1)
            .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())[0];

          console.log('[Preview] After refresh - all checkpoints:', allCheckpoints.map(cp => ({ id: cp.id, phase: cp.phase_number, branch: cp.branch_name, parent: cp.parent_checkpoint_id })));
          console.log('[Preview] New checkpoints:', newCheckpoints.map(cp => ({ id: cp.id, branch: cp.branch_name, created: cp.created_at })));
          console.log('[Preview] Found new branch:', newBranch ? { id: newBranch.id, branch: newBranch.branch_name } : null);

          if (newBranch) {
            console.log('[Preview] Auto-selecting new branch:', newBranch.id, newBranch.branch_name);
            setCheckpointSelections({
              phase1: newBranch.id,
              phase2: null,
              phase3: null,
            });
          }

          return currentTree; // Don't modify the tree, just use this to access current state
        });
      });
    });
  }, [checkpointTree, fetchVideoData]);

  // Handle continue/approve
  const handleContinue = async (checkpointId: string) => {
    if (!videoId || isContinuing) return;

    setIsContinuing(true);
    try {
      await continueVideo(videoId, checkpointId);
      toast({
        title: 'Pipeline Continued',
        description: 'Video generation will continue from this checkpoint',
      });
      // Refresh checkpoint tree
      await fetchVideoData();
    } catch (err) {
      toast({
        variant: 'destructive',
        title: 'Failed to Continue',
        description: err instanceof Error ? err.message : 'Unknown error',
      });
    } finally {
      setIsContinuing(false);
    }
  };

  // Extract artifacts from checkpoint
  const extractArtifacts = (checkpoint: CheckpointResponse | null) => {
    if (!checkpoint) return null;

    const artifacts = checkpoint.artifacts || [];
    
    if (checkpoint.phase_number === 1) {
      const specArtifact = artifacts.find(a => a.artifact_type === 'spec');
      return specArtifact ? { spec: specArtifact.metadata?.spec || specArtifact.metadata } : null;
    }
    
    if (checkpoint.phase_number === 2) {
      const beatArtifacts = artifacts
        .filter(a => a.artifact_type === 'beat_image')
        .sort((a, b) => a.artifact_key.localeCompare(b.artifact_key));
      return beatArtifacts.length > 0 ? { storyboardUrls: beatArtifacts.map(a => a.s3_url) } : null;
    }
    
    if (checkpoint.phase_number === 3) {
      const chunkArtifacts = artifacts
        .filter(a => a.artifact_type === 'video_chunk')
        .sort((a, b) => a.artifact_key.localeCompare(b.artifact_key));
      const stitchedArtifact = artifacts.find(a => a.artifact_type === 'stitched');
      return {
        chunkUrls: chunkArtifacts.map(a => a.s3_url),
        stitchedVideoUrl: stitchedArtifact?.s3_url,
      };
    }
    
    if (checkpoint.phase_number === 4) {
      const finalArtifact = artifacts.find(a => a.artifact_type === 'final_video');
      return finalArtifact ? { finalVideoUrl: finalArtifact.s3_url } : null;
    }
    
    return null;
  };

  const phase1Artifacts = extractArtifacts(selectedPhase1);
  const phase2Artifacts = extractArtifacts(selectedPhase2);
  const phase3Artifacts = extractArtifacts(selectedPhase3);
  // Phase 4 removed from pipeline

  const handleDownload = () => {
    if (videoUrl) {
      const link = document.createElement('a');
      link.href = videoUrl;
      link.download = `${videoId || 'video'}.mp4`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      toast({
        variant: 'default',
        title: 'Download Started',
        description: 'Your video download has started',
      });
    } else {
      toast({
        variant: 'destructive',
        title: 'Video Not Ready',
        description: 'Video is still processing',
      });
    }
  };

  const togglePhase = (phase: string) => {
    const newExpanded = new Set(expandedPhases);
    if (newExpanded.has(phase)) {
      newExpanded.delete(phase);
    } else {
      newExpanded.add(phase);
    }
    setExpandedPhases(newExpanded);
  };

  if (isLoading) {
    return (
      <div className="card overflow-hidden animate-fade-in">
        <div className="aspect-video bg-gradient-to-br from-card to-muted flex items-center justify-center">
          <div className="text-center text-white">
            <div className="inline-block animate-spin rounded-full h-12 w-12 border-4 border-primary border-t-transparent mb-4"></div>
            <p className="text-lg font-medium opacity-75">Loading video...</p>
          </div>
        </div>
      </div>
    );
  }

  // Processing state banner
  if (isProcessing) {
    const formatElapsedTime = (seconds: number) => {
      const mins = Math.floor(seconds / 60);
      const secs = seconds % 60;
      return `${mins}m ${secs}s`;
    };

    // Convert current phase to processing steps
    const getProcessingSteps = () => {
      const allPhases = [
        'queued',
        'validating',
        'generating_animatic',
        'generating_chunks',
        'refining',
        'exporting'
      ];

      return allPhases.map(phase => {
        const phaseIndex = allPhases.indexOf(phase);
        const currentIndex = allPhases.indexOf(currentPhase);

        let status: 'pending' | 'processing' | 'completed' | 'failed' = 'pending';
        if (phaseIndex < currentIndex) {
          status = 'completed';
        } else if (phaseIndex === currentIndex) {
          status = 'processing';
        }

        return {
          name: phase.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()),
          status
        };
      });
    };

    return (
      <div className="container mx-auto px-4 py-8 max-w-7xl">
        <div className="space-y-6">
          {/* Header */}
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-foreground">{videoTitle}</h1>
              {videoDescription && (
                <p className="text-muted-foreground mt-2">{videoDescription}</p>
              )}
            </div>
          </div>

          {/* Processing Status Card */}
          <div className="card p-6 space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-xl font-semibold">Video Generation in Progress</h2>
              <div className="text-sm text-muted-foreground">
                Elapsed: {formatElapsedTime(elapsedTime)}
              </div>
            </div>

            {/* Progress bar */}
            <div className="space-y-2">
              <div className="flex items-center justify-between text-sm">
                <span className="text-muted-foreground">Progress</span>
                <span className="font-medium">{Math.round(progress)}%</span>
              </div>
              <div className="w-full bg-secondary rounded-full h-2">
                <div
                  className="bg-primary rounded-full h-2 transition-all duration-300"
                  style={{ width: `${progress}%` }}
                />
              </div>
            </div>

            {/* Processing steps */}
            <ProcessingSteps steps={getProcessingSteps()} />

            {/* Current phase indicator */}
            {currentPhase && (
              <div className="text-sm text-muted-foreground">
                Current phase: <span className="font-medium text-foreground">{currentPhase}</span>
              </div>
            )}
          </div>

          {/* Storyboard preview (if available) */}
          {storyboardUrls.length > 0 && (
            <div className="card p-6 space-y-4">
              <h3 className="text-lg font-semibold">Storyboard Preview</h3>
              <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
                {storyboardUrls.map((url, index) => (
                  <div key={index} className="relative aspect-video bg-muted rounded-lg overflow-hidden">
                    <img
                      src={url}
                      alt={`Storyboard ${index + 1}`}
                      className="w-full h-full object-cover"
                      loading="lazy"
                    />
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Available checkpoints during processing */}
          {checkpointTree.length > 0 && (
            <div className="card p-6 space-y-4">
              <h3 className="text-lg font-semibold">Generation History</h3>
              <p className="text-sm text-muted-foreground">
                Checkpoint exploration will be available once generation completes.
              </p>
            </div>
          )}
        </div>
      </div>
    );
  }

  // Failed state banner
  if (failedPhase) {
    return (
      <div className="container mx-auto px-4 py-8 max-w-7xl">
        <div className="space-y-6">
          {/* Header */}
          <div>
            <h1 className="text-3xl font-bold text-foreground">{videoTitle}</h1>
            {videoDescription && (
              <p className="text-muted-foreground mt-2">{videoDescription}</p>
            )}
          </div>

          {/* Failed phase card */}
          <div className="card p-6 border-destructive/50 bg-destructive/5">
            <div className="flex items-start gap-3">
              <div className="flex-shrink-0 mt-0.5">
                <AlertCircle className="w-5 h-5 text-destructive" />
              </div>
              <div className="flex-1 min-w-0">
                <h3 className="text-lg font-semibold text-foreground mb-1">
                  Phase Failed: {failedPhase.phase}
                </h3>
                <Alert variant="destructive" className="mt-2">
                  <AlertDescription className="text-sm">
                    {failedPhase.error}
                  </AlertDescription>
                </Alert>

                {/* Available checkpoints for retry */}
                {checkpointTree.length > 0 && (
                  <div className="mt-4">
                    <p className="text-sm text-muted-foreground mb-2">
                      You can retry from the last successful checkpoint or return to projects.
                    </p>
                    <div className="flex gap-2">
                      <Button
                        variant="outline"
                        onClick={() => navigate('/projects')}
                      >
                        Back to Projects
                      </Button>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Show partial checkpoint tree if available */}
          {checkpointTree.length > 0 && (
            <div className="card p-6 space-y-4">
              <h3 className="text-lg font-semibold">Available Checkpoints</h3>
              <p className="text-sm text-muted-foreground">
                Checkpoints created before failure. You can continue from these points.
              </p>
            </div>
          )}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="card overflow-hidden animate-fade-in">
        <div className="aspect-video bg-gradient-to-br from-card to-muted flex items-center justify-center">
          <div className="text-center text-white">
            <Film className="w-20 h-20 mx-auto mb-4 opacity-50" />
            <p className="text-lg font-medium opacity-75">{error}</p>
            <div className="mt-4 flex gap-2 justify-center">
              <button
                onClick={() => {
                  setRetryCount(0);
                  fetchVideoData();
                }}
                className="px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90"
              >
                Retry
              </button>
              <button
                onClick={() => navigate('/projects')}
                className="px-4 py-2 bg-secondary text-secondary-foreground rounded-lg hover:bg-secondary/90"
              >
                Back to Projects
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="card overflow-hidden animate-fade-in">
      <div className="aspect-video bg-gradient-to-br from-card to-muted flex items-center justify-center">
        {videoUrl ? (
          <video
            key={videoUrl}
            src={videoUrl}
            controls
            className="w-full h-full object-contain"
            onError={(e) => {
              const videoElement = e.currentTarget;
              const errorCode = videoElement.error?.code;
              const errorMessage = videoElement.error?.message || 'Unknown error';
              
              console.error('Video load error:', {
                errorCode,
                errorMessage,
                videoUrl,
                networkState: videoElement.networkState,
                readyState: videoElement.readyState
              });

              if (errorCode === 4) {
                if (retryCount < 2 && videoUrl.includes('X-Amz-Signature')) {
                  console.log('[Preview] Video format error detected, refreshing URL...');
                  setRetryCount(retryCount + 1);
                  fetchVideoData(true);
                } else {
                  setError('Video format error. The video file may be corrupted or have incorrect metadata. Please try regenerating the video.');
                }
              } else if (retryCount < 2 && videoUrl.includes('X-Amz-Signature')) {
                console.log('[Preview] Presigned URL may be expired, refreshing...');
                setRetryCount(retryCount + 1);
                fetchVideoData(true);
              } else {
                setError(`Failed to load video: ${errorMessage || 'The video file may not be available.'}`);
              }
            }}
            onLoadedData={() => {
              if (retryCount > 0) {
                setRetryCount(0);
              }
            }}
          >
            Your browser does not support the video tag.
          </video>
        ) : isPaused ? (
          <div className="text-center text-white">
            <Film className="w-20 h-20 mx-auto mb-4 opacity-50 animate-float" />
            <p className="text-lg font-medium opacity-75">Generation Paused at Checkpoint</p>
            <p className="text-sm opacity-50 mt-2">Review and approve the current phase below to continue</p>
          </div>
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
            {videoTitle || 'Video Preview'}
          </h2>
          {videoDescription && (
            <p className="text-sm text-muted-foreground">
              {videoDescription}
            </p>
          )}
        </div>

        {/* Progress indicator for paused videos */}
        {isPaused && progress > 0 && (
          <div className="card p-6 space-y-4 bg-primary/5 border-primary/20">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-semibold text-foreground">Generation Progress</h3>
              <span className="text-sm font-medium text-primary">{Math.round(progress)}% Complete</span>
            </div>
            <div className="space-y-2">
              <div className="w-full bg-secondary rounded-full h-2">
                <div
                  className="bg-primary rounded-full h-2 transition-all duration-300"
                  style={{ width: `${progress}%` }}
                />
              </div>
              <p className="text-sm text-muted-foreground">
                Paused for review. Approve the current phase below to continue generation.
              </p>
            </div>
          </div>
        )}

        <div className="grid grid-cols-2 gap-4 p-4 bg-card rounded-lg">
          <div>
            <p className="text-xs text-muted-foreground">Process time</p>
            <p className="text-lg font-semibold text-foreground">{processTime || 'N/A'}</p>
          </div>
          <div>
            <p className="text-xs text-muted-foreground">Resolution</p>
            <p className="text-lg font-semibold text-foreground">1080p</p>
          </div>
        </div>

        {/* Phase Artifacts Section */}
        {checkpointTree.length > 0 ? (
          <div className="space-y-4">
            <h3 className="text-xl font-semibold text-foreground">Generation Phases & Artifacts</h3>

            {/* Checkpoint Selector */}
            <CheckpointSelector
              tree={checkpointTree}
              selections={checkpointSelections}
              onSelectionChange={handleCheckpointSelection}
            />

            {/* Phase 1: Validation & Spec */}
            {phase1Checkpoints.length > 0 && (
              <div className="border border-border rounded-lg overflow-hidden">
                <button
                  onClick={() => togglePhase('phase1')}
                  className="w-full px-4 py-3 bg-card hover:bg-muted/50 flex items-center justify-between transition-colors"
                >
                  <div className="flex items-center space-x-3">
                    <Sparkles className="w-5 h-5 text-primary" />
                    <span className="font-medium text-foreground">
                      Phase 1: Validation & Spec
                    </span>
                  </div>
                  <div className="flex items-center space-x-2">
                    {expandedPhases.has('phase1') ? (
                      <ChevronUp className="w-5 h-5 text-muted-foreground" />
                    ) : (
                      <ChevronDown className="w-5 h-5 text-muted-foreground" />
                    )}
                  </div>
                </button>
                {expandedPhases.has('phase1') && (
                  <div className="p-4 border-t border-border bg-muted/30">
                    {selectedPhase1 && phase1Artifacts?.spec ? (
                      <div className="space-y-2">
                        <div className="flex items-center justify-between mb-4">
                          <div className="flex items-center space-x-2 text-sm text-muted-foreground">
                            <FileText className="w-4 h-4" />
                            <span>Video Specification</span>
                          </div>
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => setSpecEditModalOpen(true)}
                          >
                            <Edit className="w-4 h-4 mr-2" />
                            Edit Spec
                          </Button>
                        </div>
                        <pre className="text-xs bg-background p-3 rounded border border-border overflow-auto max-h-64">
                          {JSON.stringify(phase1Artifacts.spec, null, 2)}
                        </pre>
                        {selectedPhase1.status === 'pending' && (
                          <div className="flex gap-2 pt-2">
                            <Button
                              onClick={() => handleContinue(selectedPhase1.id)}
                              disabled={isContinuing}
                            >
                              Continue to Phase 2
                            </Button>
                          </div>
                        )}

                        {/* Spec Edit Modal */}
                        <SpecEditModal
                          open={specEditModalOpen}
                          onOpenChange={setSpecEditModalOpen}
                          videoId={videoId!}
                          checkpointId={selectedPhase1.id}
                          currentSpec={phase1Artifacts.spec}
                          onSaveSuccess={handleSpecEditSuccess}
                        />
                      </div>
                    ) : (
                      <p className="text-sm text-muted-foreground">No spec available</p>
                    )}
                  </div>
                )}
              </div>
            )}

            {/* Phase 2: Storyboard */}
            {phase2Checkpoints.length > 0 && (
              <div className="border border-border rounded-lg overflow-hidden">
                <button
                  onClick={() => togglePhase('phase2')}
                  className="w-full px-4 py-3 bg-card hover:bg-muted/50 flex items-center justify-between transition-colors"
                >
                  <div className="flex items-center space-x-3">
                    <ImageIcon className="w-5 h-5 text-primary" />
                    <span className="font-medium text-foreground">
                      Phase 2: Storyboard
                    </span>
                  </div>
                  <div className="flex items-center space-x-2">
                    {expandedPhases.has('phase2') ? (
                      <ChevronUp className="w-5 h-5 text-muted-foreground" />
                    ) : (
                      <ChevronDown className="w-5 h-5 text-muted-foreground" />
                    )}
                  </div>
                </button>
                {expandedPhases.has('phase2') && (
                  <div className="p-4 border-t border-border bg-muted/30">
                    {selectedPhase2 && phase2Artifacts?.storyboardUrls && phase2Artifacts.storyboardUrls.length > 0 ? (
                      <div className="space-y-4">
                        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
                          {phase2Artifacts.storyboardUrls.map((url, index) => (
                            <div key={index} className="relative aspect-video rounded-lg overflow-hidden border border-border bg-card">
                              <img
                                src={url}
                                alt={`Storyboard beat ${index + 1}`}
                                className="w-full h-full object-cover"
                                onError={(e) => {
                                  const img = e.currentTarget;
                                  img.src = 'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" width="400" height="300"%3E%3Crect fill="%23ddd" width="400" height="300"/%3E%3Ctext fill="%23999" font-family="sans-serif" font-size="18" dy="10.5" font-weight="bold" x="50%25" y="50%25" text-anchor="middle"%3EImage not available%3C/text%3E%3C/svg%3E';
                                }}
                              />
                              <div className="absolute bottom-0 left-0 right-0 bg-black/60 text-white text-xs px-2 py-1 text-center">
                                Beat {index + 1}
                              </div>
                            </div>
                          ))}
                        </div>
                        {selectedPhase2.status === 'pending' && (
                          <div className="flex gap-2 pt-2">
                            <Button
                              onClick={() => handleContinue(selectedPhase2.id)}
                              disabled={isContinuing}
                            >
                              Continue to Phase 3
                            </Button>
                          </div>
                        )}
                      </div>
                    ) : (
                      <p className="text-sm text-muted-foreground">No storyboard images available</p>
                    )}
                  </div>
                )}
              </div>
            )}

            {/* Phase 3: Video Chunks */}
            {phase3Checkpoints.length > 0 && (
              <div className="border border-border rounded-lg overflow-hidden">
                <button
                  onClick={() => togglePhase('phase3')}
                  className="w-full px-4 py-3 bg-card hover:bg-muted/50 flex items-center justify-between transition-colors"
                >
                  <div className="flex items-center space-x-3">
                    <Video className="w-5 h-5 text-primary" />
                    <span className="font-medium text-foreground">
                      Phase 3: Video Chunks
                    </span>
                  </div>
                  <div className="flex items-center space-x-2">
                    {expandedPhases.has('phase3') ? (
                      <ChevronUp className="w-5 h-5 text-muted-foreground" />
                    ) : (
                      <ChevronDown className="w-5 h-5 text-muted-foreground" />
                    )}
                  </div>
                </button>
                {expandedPhases.has('phase3') && (
                  <div className="p-4 border-t border-border bg-muted/30">
                    {selectedPhase3 && phase3Artifacts?.chunkUrls && phase3Artifacts.chunkUrls.length > 0 ? (
                      <div className="space-y-4">
                        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
                          {phase3Artifacts.chunkUrls.map((_, index) => {
                            const beatImageUrl = phase1Artifacts?.spec?.beats?.[index]?.image_url || 
                                                phase2Artifacts?.storyboardUrls?.[index];
                            
                            return (
                              <div
                                key={index}
                                className="relative aspect-video rounded-lg overflow-hidden border border-border bg-card cursor-pointer hover:border-primary transition-colors group"
                                onClick={(e) => {
                                  console.log('[Preview] Chunk clicked:', index, 'chunkUrl:', phase3Artifacts.chunkUrls[index]);
                                  e.stopPropagation();
                                  setSelectedChunkIndex(index);
                                  setChunkEditModalOpen(true);
                                }}
                              >
                                {beatImageUrl ? (
                                  <img
                                    src={beatImageUrl}
                                    alt={`Chunk ${index + 1} keyframe`}
                                    className="w-full h-full object-cover"
                                    onError={(e) => {
                                      const img = e.currentTarget;
                                      img.src = 'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" width="400" height="300"%3E%3Crect fill="%23ddd" width="400" height="300"/%3E%3Ctext fill="%23999" font-family="sans-serif" font-size="18" dy="10.5" font-weight="bold" x="50%25" y="50%25" text-anchor="middle"%3EImage not available%3C/text%3E%3C/svg%3E';
                                    }}
                                  />
                                ) : (
                                  <div className="w-full h-full bg-muted flex items-center justify-center">
                                    <Video className="w-8 h-8 text-muted-foreground" />
                                  </div>
                                )}
                                <div className="absolute inset-0 bg-black/0 group-hover:bg-black/40 transition-colors flex items-center justify-center">
                                  <Play className="w-12 h-12 text-white opacity-0 group-hover:opacity-100 transition-opacity fill-current" />
                                </div>
                                <div className="absolute bottom-0 left-0 right-0 bg-black/60 text-white text-xs px-2 py-1 text-center">
                                  Chunk {index + 1}
                                </div>
                              </div>
                            );
                          })}
                        </div>
                        {/* Phase 3 is now terminal - no Phase 4 continuation */}
                      </div>
                    ) : (
                      <p className="text-sm text-muted-foreground">No video chunks available</p>
                    )}
                  </div>
                )}
              </div>
            )}

            {/* Phase 4 removed from pipeline - Phase 3 is now terminal */}
          </div>
        ) : (
          <div className="space-y-4">
            <h3 className="text-xl font-semibold text-foreground">Generation Phases & Artifacts</h3>
            <div className="p-4 border border-border rounded-lg bg-muted/30">
              <p className="text-sm text-muted-foreground">
                No checkpoint data available. Checkpoints will appear here once video generation begins.
              </p>
            </div>
          </div>
        )}

        <div className="flex flex-col space-y-3">
          <div className="grid grid-cols-2 gap-4">
            <button
              onClick={() => {
                navigate('/');
              }}
              className="btn-secondary"
            >
              Create Another
            </button>
            <button
              onClick={() => navigate(`/export/${videoId}`)}
              className="btn-primary flex items-center justify-center space-x-2"
            >
              <BarChart3 className="w-5 h-5" />
              <span>Export</span>
            </button>
          </div>
          <button
            onClick={handleDownload}
            disabled={!videoUrl}
            className="w-full btn-primary flex items-center justify-center space-x-2 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <Download className="w-5 h-5" />
            <span>Download Video</span>
          </button>
        </div>
      </div>

      {/* Chunk Edit Modal */}
      {selectedChunkIndex !== null && phase3Artifacts?.chunkUrls && (
        <ChunkEditModal
          open={chunkEditModalOpen}
          onOpenChange={(open) => {
            console.log('[Preview] Modal open change:', open);
            setChunkEditModalOpen(open);
          }}
          chunkIndex={selectedChunkIndex}
          chunkUrl={phase3Artifacts.chunkUrls[selectedChunkIndex]}
          beatImageUrl={
            phase1Artifacts?.spec?.beats?.[selectedChunkIndex]?.image_url ||
            phase2Artifacts?.storyboardUrls?.[selectedChunkIndex]
          }
        />
      )}
    </div>
  );
}
