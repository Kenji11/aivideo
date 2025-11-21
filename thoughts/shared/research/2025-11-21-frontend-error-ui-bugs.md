---
date: 2025-11-21T08:37:40-06:00
researcher: Claude (Sonnet 4.5)
git_commit: 8469c318156c8ac8e7fe31798bad688cd1bd4a2f
branch: refactor/vincent
repository: aivideo
topic: "Frontend UI Bugs: Failed Video State Handling"
tags: [research, codebase, frontend, ui-bugs, error-handling, video-status]
status: complete
last_updated: 2025-11-21
last_updated_by: Claude (Sonnet 4.5)
---

# Research: Frontend UI Bugs - Failed Video State Handling

**Date**: 2025-11-21T08:37:40-06:00
**Researcher**: Claude (Sonnet 4.5)
**Git Commit**: 8469c318156c8ac8e7fe31798bad688cd1bd4a2f
**Branch**: refactor/vincent
**Repository**: aivideo

## Research Question

Document the two frontend UI bugs identified in the walkthrough findings document that prevent proper display and interaction with failed videos:
1. Failed videos are not clickable from the projects page
2. Failed state shows processing UI instead of error state

## Summary

Two UI bugs exist in the frontend that impact the user experience when video generation fails. Both bugs are in the rendering logic rather than data handling - the backend correctly provides error information through the API, and the status flow works properly. However:

1. **Navigation Bug (App.tsx:113)**: Failed videos are explicitly excluded from the click handler, making them unclickable on the projects page
2. **Rendering Bug (VideoStatus.tsx:306-326)**: The VideoStatus component always renders the "AI is Creating Your Video" UI regardless of status, with no conditional rendering for the failed state

The backend error handling is production-ready, but these frontend display issues prevent users from viewing error details or understanding why their video failed.

## Detailed Findings

### Bug #1: Failed Videos Not Clickable from Projects Page

**Location**: `frontend/src/App.tsx:108-117`

#### Current Implementation

```typescript
const handleProjectSelect = (project: VideoListItem) => {
  setSelectedProject(project);
  if (project.status === 'complete' && project.final_video_url) {
    setTitle(project.title);
    navigate(`/preview/${project.video_id}`);
  } else if (project.status !== 'complete' && project.status !== 'failed') {
    // Navigate to processing page for videos that are still processing
    navigate(`/processing/${project.video_id}`);
  }
};
```

#### The Problem

Line 113 contains the condition: `project.status !== 'complete' && project.status !== 'failed'`

This explicitly excludes the 'failed' status from navigation, meaning:
- Failed videos are displayed in the projects list with a red "Failed" badge
- Clicking on a failed video does nothing
- The only available action is deletion via the delete button

#### What This Means for Users

- **No error details visible**: Users cannot see what caused the failure
- **No checkpoint access**: Users cannot view checkpoints that completed before the failure
- **No retry option**: Users cannot attempt to retry or debug the issue
- **Limited visibility**: Error messages are only visible in temporary notifications

#### Status Badge Display

Failed videos DO show correctly in the project list with visual indication:

**File**: `frontend/src/components/ProjectCard.tsx:15-28`
```typescript
const statusConfig: Record<string, {
  variant: 'default' | 'secondary' | 'destructive' | 'outline';
  label: string
}> = {
  // ... other statuses
  failed: { variant: 'destructive', label: 'Failed' },
};

export function ProjectCard({ project, onSelect, onDelete }: ProjectCardProps) {
  const status = statusConfig[project.status] || statusConfig.queued;
  const isProcessing = project.status !== 'complete' && project.status !== 'failed';

  return (
    <Card>
      <Badge variant={status.variant}>
        {status.label}
      </Badge>
    </Card>
  );
}
```

The ProjectCard correctly displays failed status as a red/destructive badge, but clicking the card triggers nothing due to the App.tsx handler.

#### Data Flow for Failed Videos

Failed videos are properly returned in the API response:

**API Response Structure** (`frontend/src/lib/api.ts:239-249`):
```typescript
export interface VideoListItem {
  video_id: string;
  title: string;
  status: string;        // Contains 'failed'
  progress: number;
  current_phase?: string; // Shows which phase failed
  final_video_url?: string;
  cost_usd: number;
  created_at: string;
  completed_at?: string;
}
```

The data is available, but the UI handler prevents navigation.

#### Current Workaround

Users can manually navigate by typing the URL directly:
```
http://localhost:5173/processing/{video_id}
```

This bypasses the click handler and loads the VideoStatus page, which then encounters Bug #2.

---

### Bug #2: Failed State Shows Processing UI

**Location**: `frontend/src/pages/VideoStatus.tsx:306-326`

#### Current Implementation

The VideoStatus component always renders the same UI regardless of status:

```typescript
return (
  <>
    <NotificationCenter
      notifications={notifications}
      onDismiss={(id) => setNotifications((prev) => prev.filter((n) => n.id !== id))}
    />

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

      {/* Checkpoint UI, storyboard images, etc. rendered below */}
    </div>
  </>
);
```

**The Problem**: No conditional rendering based on status. The component always shows:
- "AI is Creating Your Video" heading
- Pulsing video icon animation
- "Sit back and relax..." message
- Processing steps indicator

This is misleading when the video has failed.

#### Error Detection Exists

The component DOES detect failures and handles them internally:

**File**: `frontend/src/pages/VideoStatus.tsx:279-283`
```typescript
} else if (status.status === 'failed') {
  console.error('[VideoStatus] Video generation failed:', status.error);
  setIsProcessing(false);
  addNotification('error', 'Generation Failed', status.error || 'Unknown error');
}
```

This handler:
- Logs the error to console
- Stops the processing timer
- Shows a temporary notification with the error message
- But does NOT change the UI rendering

#### The API Response is Correct

The backend correctly provides error information:

**StatusResponse when failed** (`frontend/src/lib/api.ts:92-109`):
```typescript
export interface StatusResponse {
  video_id: string;
  status: string;           // Contains 'failed'
  progress: number;
  current_phase?: string;   // Shows which phase failed (e.g., 'phase2_storyboard')
  error?: string;           // Contains error message
  // ... other fields
  current_checkpoint?: CheckpointInfo;  // Contains completed checkpoints
  checkpoint_tree?: CheckpointTreeNode[]; // Shows checkpoint history
}
```

Example from walkthrough findings:
```json
{
  "status": "failed",
  "current_phase": "phase2_storyboard",
  "error": "Failed to generate storyboard image for beat 0: Replicate API error: You've hit your monthly spend limit...",
  "current_checkpoint": null
}
```

The error data is available in the `streamStatus` variable (line 279), but it's only used for console logging and temporary notifications.

#### What Users See vs What They Should See

**Current Experience**:
1. User sees "AI is Creating Your Video" with animated spinner
2. Processing steps show as incomplete
3. A temporary error notification appears (auto-dismisses after 5 seconds)
4. Page continues to look like processing is ongoing
5. No indication of which phase failed
6. No persistent error message

**Data Available (but not displayed)**:
- `streamStatus.status` = `'failed'`
- `streamStatus.error` = Full error message from backend
- `streamStatus.current_phase` = Phase where failure occurred
- `streamStatus.current_checkpoint` = Completed checkpoints before failure

---

### Related Components and Error Patterns

#### Error Handling Patterns in Other Components

The codebase has established patterns for displaying error states. Here are examples that VideoStatus.tsx does NOT follow:

**Pattern 1: Conditional Rendering with Status Icons**

**File**: `frontend/src/components/ProcessingSteps.tsx:32-43`
```typescript
{step.status === 'completed' && (
  <CheckCircle2 className="w-6 h-6 text-primary" />
)}
{step.status === 'processing' && (
  <Loader2 className="w-6 h-6 text-primary animate-spin" />
)}
{step.status === 'failed' && (
  <AlertCircle className="w-6 h-6 text-destructive" />
)}
{step.status === 'pending' && (
  <div className="w-6 h-6 rounded-full bg-muted" />
)}
```

This component conditionally renders different icons based on status, including a red AlertCircle for failed status.

**Pattern 2: Page-Level Error State**

**File**: `frontend/src/pages/Preview.tsx:97-114`
```typescript
{error && (
  <div className="card overflow-hidden animate-fade-in">
    <div className="aspect-video bg-gradient-to-br from-card to-muted flex items-center justify-center">
      <div className="text-center text-white">
        <Film className="w-20 h-20 mx-auto mb-4 opacity-50" />
        <p className="text-lg font-medium opacity-75">{error}</p>
        <button
          onClick={() => navigate('/projects')}
          className="mt-4 px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90"
        >
          Back to Projects
        </button>
      </div>
    </div>
  </div>
)}
```

The Preview component shows error state with:
- Error icon
- Error message text
- Navigation button to recover

**Pattern 3: Toast Notifications for Async Errors**

**File**: `frontend/src/App.tsx:98-105`
```typescript
const addNotification = (type: Notification['type'], title: string, message: string) => {
  const variant = type === 'error' ? 'destructive' : 'default';
  toast({
    variant,
    title,
    description: message,
  });
};
```

Used throughout the application for transient error messages, but NOT sufficient for permanent error states like video generation failure.

#### Icons Available for Error States

**File**: Imported from `lucide-react` throughout the codebase
- `AlertCircle` - Warning/error icon (used in ProcessingSteps)
- `XCircle` - Failed/error state icon (used in UploadZone)
- `CheckCircle2` - Success/completed icon
- `Loader2` - Loading/processing spinner

VideoStatus.tsx only imports `Video` icon (line 3), not error icons.

---

### Status Flow Documentation

#### How Status Reaches VideoStatus Component

**1. useVideoStatusStream Hook** (`frontend/src/lib/useVideoStatusStream.ts:18-201`)

The hook provides real-time status updates via Server-Sent Events (SSE) with automatic fallback to polling:

```typescript
export function useVideoStatusStream(
  videoId: string | null,
  enabled: boolean = true
): UseVideoStatusStreamResult

interface UseVideoStatusStreamResult {
  status: StatusResponse | null;  // Contains all status info
  error: Error | null;            // Connection errors (not video errors)
  isConnected: boolean;
}
```

**2. VideoStatus Component Usage** (`frontend/src/pages/VideoStatus.tsx:128-131`)

```typescript
const { status: streamStatus, error: streamError, isConnected } = useVideoStatusStream(
  videoId || null,
  isProcessing
);
```

**3. Status Update Effect** (`frontend/src/pages/VideoStatus.tsx:152-284`)

The component processes status updates in a useEffect:
```typescript
useEffect(() => {
  if (!streamStatus || !isProcessing) return;

  const status = streamStatus;

  // Update processing progress
  const currentStep = getProcessingStepFromPhase(status.current_phase, status.progress);
  setProcessingProgress(currentStep);

  // ... handle storyboard URLs, checkpoints, etc.

  // Handle completion
  if (status.status === 'complete') {
    setIsProcessing(false);
    navigate(`/preview/${videoId}`);
  }

  // Handle failure (only logs and notifies)
  else if (status.status === 'failed') {
    console.error('[VideoStatus] Video generation failed:', status.error);
    setIsProcessing(false);
    addNotification('error', 'Generation Failed', status.error || 'Unknown error');
  }
}, [streamStatus, isProcessing, navigate, videoId]);
```

The status data is available in the component state (`streamStatus`), but the render function doesn't use it to conditionally display UI.

#### StatusResponse Complete Structure

**File**: `frontend/src/lib/api.ts:92-109`

```typescript
export interface StatusResponse {
  video_id: string;
  status: string;                 // 'failed' | 'complete' | 'queued' | 'validating' | etc.
  progress: number;               // 0-100
  current_phase?: string;         // Phase where error occurred
  estimated_time_remaining?: number;
  error?: string;                 // Error message from backend
  reference_assets?: ReferenceAssets;
  storyboard_urls?: string[];
  stitched_video_url?: string;
  final_video_url?: string;
  current_chunk_index?: number;
  total_chunks?: number;
  current_checkpoint?: CheckpointInfo;      // Completed checkpoints
  checkpoint_tree?: CheckpointTreeNode[];   // Full checkpoint history
  active_branches?: BranchInfo[];
}
```

All fields are properly populated by the backend when a video fails, including:
- `status: 'failed'`
- `error: 'Detailed error message...'`
- `current_phase: 'phase2_storyboard'` (or whichever phase failed)
- `current_checkpoint: {...}` (if any phase completed before failure)

---

### Checkpoint System and Failed Videos

#### Checkpoint Data Available for Failed Videos

When a video fails after completing one or more phases, checkpoint data is preserved:

**Database State from Walkthrough** (from walkthrough-findings.md):
```sql
-- video_generations table
status: FAILED
current_phase: phase2_storyboard
error_message: Failed to generate storyboard image for beat 0: Replicate API error...

-- video_checkpoints table (Phase 1 completed successfully)
checkpoint_id: cp-fbb2927c-db76-4e81-a67e-6292eca99e03
branch_name: main
phase_number: 1
version: 1
status: approved
cost_usd: 0.0008
```

This shows:
- Phase 1 completed successfully with checkpoint
- Phase 2 failed during execution
- Checkpoint is preserved and approved
- Error message stored in database

The API correctly returns this checkpoint data in `StatusResponse.current_checkpoint` even when the video status is 'failed'.

#### CheckpointCard Component

**File**: `frontend/src/components/CheckpointCard.tsx:14-163`

The CheckpointCard component exists and is already integrated into VideoStatus.tsx:

**VideoStatus.tsx:329-349**:
```typescript
{currentCheckpoint && videoId && (
  <div className="mt-8 pt-8 border-t border-border max-w-4xl mx-auto space-y-6">
    {/* Branch Selector */}
    {activeBranches.length > 0 && (
      <div className="flex justify-end">
        <BranchSelector
          branches={activeBranches}
          currentBranch={currentCheckpoint.branch_name}
          disabled={true}
        />
      </div>
    )}

    {/* Current Checkpoint Card */}
    <CheckpointCard
      checkpoint={currentCheckpoint}
      videoId={videoId}
      onEdit={handleEdit}
      onContinue={handleContinue}
      isProcessing={isContinuing}
    />

    {/* ... CheckpointTree below */}
  </div>
)}
```

This checkpoint UI is rendered conditionally based on `currentCheckpoint` existing, but it appears BELOW the "AI is Creating Your Video" section. For failed videos, this creates a confusing experience where:
1. Top section says "AI is Creating Your Video" (misleading)
2. Bottom section shows completed checkpoint (correct)
3. No indication anywhere that generation has failed

---

## Code References

### Bug #1: Navigation Handler
- `frontend/src/App.tsx:108-117` - handleProjectSelect function with failed status exclusion
- `frontend/src/App.tsx:113` - Line excluding 'failed' status from navigation
- `frontend/src/components/ProjectCard.tsx:15-28` - Status badge configuration including 'failed'

### Bug #2: UI Rendering
- `frontend/src/pages/VideoStatus.tsx:306-326` - Always-rendered processing UI
- `frontend/src/pages/VideoStatus.tsx:279-283` - Error handler that only logs and notifies
- `frontend/src/pages/VideoStatus.tsx:128-131` - useVideoStatusStream hook providing status
- `frontend/src/pages/VideoStatus.tsx:152-284` - useEffect processing status updates

### Related Type Definitions
- `frontend/src/lib/api.ts:92-109` - StatusResponse interface
- `frontend/src/lib/api.ts:239-249` - VideoListItem interface

### Related Components
- `frontend/src/components/ProjectCard.tsx` - Project list display with status badges
- `frontend/src/components/ProcessingSteps.tsx:32-43` - Example of conditional status rendering
- `frontend/src/components/CheckpointCard.tsx` - Checkpoint display component
- `frontend/src/pages/Preview.tsx:97-114` - Example of error state UI

### Hooks and Utilities
- `frontend/src/lib/useVideoStatusStream.ts:18-201` - SSE stream with polling fallback
- `frontend/src/hooks/use-toast.ts` - Toast notification system

---

## Architecture Documentation

### Current Error Handling Architecture

**Backend → Frontend Flow**:
```
Backend API (Correct)
    ↓
    Sets status='failed', error='message', current_phase='phase2_storyboard'
    ↓
API Response (Correct)
    ↓
    StatusResponse { status, error, current_phase, current_checkpoint }
    ↓
useVideoStatusStream Hook (Correct)
    ↓
    Returns { status: StatusResponse, error: null, isConnected: true }
    ↓
VideoStatus Component Effect (Partial)
    ↓
    Detects status.status === 'failed'
    Logs to console
    Shows temporary notification
    Sets isProcessing=false
    ↓
VideoStatus Component Render (Broken)
    ↓
    Always renders "AI is Creating Your Video" UI
    No conditional rendering for failed state
```

**Projects List Flow**:
```
Backend API
    ↓
GET /api/videos → VideoListResponse
    ↓
App Component
    ↓
    Stores in projects state
    Renders ProjectCard for each video
    ↓
ProjectCard (Correct Display)
    ↓
    Shows red "Failed" badge
    But click handler in App excludes 'failed' status
    ↓
User Clicks Failed Video
    ↓
    Nothing happens (no navigation)
```

### Error State Management Pattern (Should Be Used)

Based on other components in the codebase, the pattern should be:

```typescript
// State management
const [error, setError] = useState<string | null>(null);
const [isLoading, setIsLoading] = useState(true);

// Effect to process status
useEffect(() => {
  if (status.status === 'failed') {
    setError(status.error || 'Unknown error');
    setIsLoading(false);
  }
}, [status]);

// Render with conditional UI
return (
  <>
    {error ? (
      // Error UI
      <ErrorDisplay error={error} phase={status.current_phase} />
    ) : isLoading ? (
      // Processing UI
      <ProcessingDisplay />
    ) : (
      // Complete UI
      <CompleteDisplay />
    )}
  </>
);
```

This pattern is NOT currently implemented in VideoStatus.tsx.

---

## Related Research

- **Checkpoint System Documentation**: See `user-flow.md` for expected checkpoint behavior
- **Walkthrough Findings**: See `walkthrough-findings.md` for detailed test results
- **Backend Error Handling**: Backend correctly captures and returns error information (production-ready)

---

## Open Questions

1. **Should failed videos allow retry?** The checkpoint system could support retrying from the last successful checkpoint, but no UI currently exists for this.

2. **Should failed videos show checkpoint tree?** The CheckpointTree component exists and could show which phases succeeded before failure, but it's below the misleading "Creating Video" UI.

3. **Should the projects page indicate clickability for failed videos?** Once Bug #1 is fixed, should failed videos have a visual indicator that they're clickable to view details?

4. **How should temporary vs permanent failures be distinguished?** API rate limits (like in the walkthrough) might be temporary, while validation errors are permanent. Should the UI differentiate?

---

## Summary of Findings

### Bug #1: Failed Videos Not Clickable
- **Location**: App.tsx:113
- **Issue**: Explicit exclusion: `project.status !== 'failed'`
- **Impact**: Failed videos cannot be clicked to view details
- **Data Flow**: Backend provides correct data, UI handler blocks interaction
- **Workaround**: Manual URL navigation

### Bug #2: Failed State Shows Processing UI
- **Location**: VideoStatus.tsx:306-326
- **Issue**: No conditional rendering based on status
- **Impact**: Misleading "AI is Creating Your Video" shown for failed videos
- **Data Flow**: Backend provides error data, component logs it but doesn't render it
- **Error Detection**: Exists in effect (line 279), but doesn't affect rendering

### Root Cause
Both bugs are UI rendering/interaction issues, not data problems. The backend, API, hooks, and data types all work correctly. The issues are:
1. Navigation logic that explicitly excludes a valid status
2. Render function that doesn't conditionally display different UI based on status

### Architecture Assessment
- ✅ Backend error handling: Production-ready
- ✅ API error responses: Complete and accurate
- ✅ Status streaming: Working correctly
- ✅ Type definitions: Properly defined
- ❌ UI navigation: Excludes failed videos
- ❌ UI rendering: No conditional error state display
