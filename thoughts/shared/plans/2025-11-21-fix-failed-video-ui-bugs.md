# Fix Failed Video UI Bugs Implementation Plan

## Overview

Fix two critical frontend UI bugs that prevent users from properly interacting with and understanding failed video generation attempts. The bugs are purely UI-level issues - the backend correctly provides all error information through the API.

## Current State Analysis

### Bug #1: Failed Videos Not Clickable (App.tsx:113)
- Failed videos are displayed in the projects list with red "Failed" badge
- Click handler explicitly excludes `status === 'failed'` from navigation
- Users cannot access error details or view completed checkpoints
- Only available action is deletion

### Bug #2: No Error Display at Phase Level (VideoStatus.tsx:306-326)
- Component always renders "AI is Creating Your Video" regardless of status
- Error detection exists (line 279-283) but only logs and shows temporary toast
- No phase-specific error display in the checkpoint/pipeline UI
- Users see misleading "processing" state when video has failed

### What Works Correctly
- ✅ Backend provides complete error information via StatusResponse
- ✅ API includes error message, failed phase, and completed checkpoints
- ✅ ProjectCard displays failed status badge correctly
- ✅ useVideoStatusStream delivers status updates properly
- ✅ Checkpoint system preserves data from phases that completed before failure

### Key Discoveries

**StatusResponse Structure** (`frontend/src/lib/api.ts:92-109`):
```typescript
export interface StatusResponse {
  status: string;              // Contains 'failed'
  error?: string;              // Error message from backend
  current_phase?: string;      // Phase where failure occurred
  current_checkpoint?: CheckpointInfo;  // Last successful checkpoint
  checkpoint_tree?: CheckpointTreeNode[];
  // ... other fields
}
```

**Existing Error Patterns** (from research):
- `ProcessingSteps.tsx:32-43` - Conditional icon rendering with AlertCircle for failed state
- `Alert` component - Supports `variant="destructive"` for error states
- Checkpoint UI already renders conditionally based on data presence

## Desired End State

After implementation:
1. **Projects Page**: Failed videos are clickable and show hover hint "Click to view details"
2. **VideoStatus Page**: Error information displayed at the specific phase/checkpoint level where failure occurred
3. **Pipeline View**: Completed checkpoints from earlier phases remain visible
4. **Error Persistence**: Error details remain visible throughout session (not just temporary toast)

### Verification
- User can click failed video from projects list → navigates to `/processing/{videoId}`
- VideoStatus page shows error details at the failed phase section
- Earlier successful phases show their checkpoint cards normally
- Error message is clear and persistent
- Toast notification still appears initially but error remains visible

## What We're NOT Doing

- NOT implementing retry functionality (future enhancement)
- NOT adding error banners at pipeline level (error is phase-specific)
- NOT changing the "AI is Creating Your Video" header for failed states
- NOT modifying backend API or error handling (already correct)
- NOT adding new API endpoints
- NOT changing checkpoint system behavior

## Implementation Approach

Fix both bugs independently in separate phases:
1. Fix navigation handler to include failed videos
2. Add phase-level error display in checkpoint UI
3. Add visual affordance for clickable failed videos

Each phase is independently testable and provides immediate value.

---

## Phase 1: Enable Navigation for Failed Videos

### Overview
Remove the explicit exclusion of `status === 'failed'` from the click handler to allow users to access the VideoStatus page for failed videos.

### Changes Required

#### 1. App.tsx - Update handleProjectSelect
**File**: `frontend/src/App.tsx:108-117`

**Current Code**:
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

**Change**: Remove `&& project.status !== 'failed'` from line 113

**New Code**:
```typescript
const handleProjectSelect = (project: VideoListItem) => {
  setSelectedProject(project);
  if (project.status === 'complete' && project.final_video_url) {
    setTitle(project.title);
    navigate(`/preview/${project.video_id}`);
  } else if (project.status !== 'complete') {
    // Navigate to processing page for videos that are still processing or failed
    navigate(`/processing/${project.video_id}`);
  }
};
```

**Rationale**: Failed videos should navigate to the processing page where error details and completed checkpoints can be viewed.

### Success Criteria

#### Automated Verification:
- [x] TypeScript compilation passes: `cd frontend && npm run build`
- [x] No linting errors: `cd frontend && npm run lint` (no new errors in App.tsx)
- [x] Component renders without errors: Start dev server `cd frontend && npm run dev`

#### Manual Verification:
- [ ] Click on a failed video in projects list → navigates to `/processing/{videoId}`
- [ ] URL updates correctly with video ID
- [ ] VideoStatus page loads (will show current "processing" UI until Phase 2)
- [ ] Complete videos still navigate to preview page
- [ ] In-progress videos still navigate to processing page

**Implementation Note**: After completing this phase and all automated verification passes, pause here for manual confirmation from the human that the navigation works correctly before proceeding to Phase 2.

---

## Phase 2: Add Phase-Level Error Display

### Overview
Display error information at the specific phase/checkpoint level where failure occurred, integrated into the existing checkpoint UI structure.

### Changes Required

#### 1. VideoStatus.tsx - Add Error State Tracking
**File**: `frontend/src/pages/VideoStatus.tsx`

**Add state variable after line 31** (after `const [currentPhase, setCurrentPhase] = useState...`):
```typescript
const [failedPhase, setFailedPhase] = useState<{
  phase: string;
  error: string;
} | null>(null);
```

#### 2. VideoStatus.tsx - Update Status Effect to Track Failed Phase
**File**: `frontend/src/pages/VideoStatus.tsx:279-283`

**Current Code**:
```typescript
} else if (status.status === 'failed') {
  console.error('[VideoStatus] Video generation failed:', status.error);
  setIsProcessing(false);
  addNotification('error', 'Generation Failed', status.error || 'Unknown error');
}
```

**New Code**:
```typescript
} else if (status.status === 'failed') {
  console.error('[VideoStatus] Video generation failed:', status.error);
  setIsProcessing(false);
  addNotification('error', 'Generation Failed', status.error || 'Unknown error');

  // Track failed phase for display
  setFailedPhase({
    phase: status.current_phase || 'unknown',
    error: status.error || 'Unknown error',
  });
}
```

#### 3. VideoStatus.tsx - Add Import for Alert Components
**File**: `frontend/src/pages/VideoStatus.tsx:1-13`

**Add to imports** (after line 3):
```typescript
import { AlertCircle } from 'lucide-react';
import { Alert, AlertDescription } from '../components/ui/alert';
```

#### 4. VideoStatus.tsx - Add Error Display Component
**File**: `frontend/src/pages/VideoStatus.tsx`

**Add new component before the main return statement** (around line 305):
```typescript
// Render error card for failed phase
const renderFailedPhaseCard = () => {
  if (!failedPhase) return null;

  return (
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
        </div>
      </div>
    </div>
  );
};
```

#### 5. VideoStatus.tsx - Integrate Error Display into Checkpoint Section
**File**: `frontend/src/pages/VideoStatus.tsx:329-368`

**Current Structure**:
```typescript
{currentCheckpoint && videoId && (
  <div className="mt-8 pt-8 border-t border-border max-w-4xl mx-auto space-y-6">
    {/* Branch Selector */}
    {/* Checkpoint Card */}
    {/* Checkpoint Tree */}
    {/* Artifact Editor Modal */}
  </div>
)}
```

**New Structure** - Add error card before or after checkpoint card:
```typescript
{(currentCheckpoint || failedPhase) && videoId && (
  <div className="mt-8 pt-8 border-t border-border max-w-4xl mx-auto space-y-6">
    {/* Branch Selector */}
    {activeBranches.length > 0 && currentCheckpoint && (
      <div className="flex justify-end">
        <BranchSelector
          branches={activeBranches}
          currentBranch={currentCheckpoint.branch_name}
          disabled={true}
        />
      </div>
    )}

    {/* Current Checkpoint Card (if exists) */}
    {currentCheckpoint && (
      <CheckpointCard
        checkpoint={currentCheckpoint}
        videoId={videoId}
        onEdit={handleEdit}
        onContinue={handleContinue}
        isProcessing={isContinuing}
      />
    )}

    {/* Failed Phase Card (if exists) */}
    {failedPhase && renderFailedPhaseCard()}

    {/* Checkpoint Tree */}
    {checkpointTree.length > 0 && (
      <CheckpointTree
        tree={checkpointTree}
        currentCheckpointId={currentCheckpoint?.checkpoint_id}
      />
    )}

    {/* Artifact Editor Modal */}
    {currentCheckpoint && (
      <ArtifactEditor
        open={editDialogOpen}
        onOpenChange={setEditDialogOpen}
        checkpoint={currentCheckpoint}
        videoId={videoId}
        onArtifactUpdated={handleArtifactUpdated}
      />
    )}
  </div>
)}
```

**Rationale**:
- Error card appears in the checkpoint section where phases are displayed
- If a checkpoint exists from a previous phase, it's shown first
- Failed phase error appears after checkpoint card
- Checkpoint tree shows all branches and completed checkpoints
- Structure maintains the phase-by-phase pipeline view

### Success Criteria

#### Automated Verification:
- [x] TypeScript compilation passes: `cd frontend && npm run build`
- [x] No linting errors: `cd frontend && npm run lint` (no new errors in VideoStatus.tsx)
- [x] Component renders without errors: Start dev server `cd frontend && npm run dev`
- [x] No React key warnings in console
- [x] Alert component imports correctly from ui/alert

#### Manual Verification:
- [ ] Navigate to a failed video → see error card in checkpoint section
- [ ] Error card shows correct phase name (e.g., "phase2_storyboard")
- [ ] Error message displays complete text from backend
- [ ] Error card uses destructive styling (red border, red icon)
- [ ] If Phase 1 completed before Phase 2 failed, Phase 1 checkpoint card appears above error card
- [ ] Checkpoint tree (if present) shows all branches correctly
- [ ] Error persists throughout session (doesn't disappear like toast)
- [ ] Toast notification still appears on initial failure detection

**Implementation Note**: After completing this phase and all automated verification passes, pause here for manual confirmation from the human that the error display works correctly before proceeding to Phase 3.

---

## Phase 3: Add Visual Affordance for Failed Videos

### Overview
Add hover hint to ProjectCard to indicate that failed videos are clickable and can be viewed for details.

### Changes Required

#### 1. ProjectCard.tsx - Add Hover Title Attribute
**File**: `frontend/src/components/ProjectCard.tsx`

**Locate the Card component** (around line 31) - the main container element:
```typescript
<Card
  className="cursor-pointer hover:shadow-lg transition-shadow"
  onClick={() => onSelect(project)}
>
```

**Add conditional title attribute**:
```typescript
<Card
  className="cursor-pointer hover:shadow-lg transition-shadow"
  onClick={() => onSelect(project)}
  title={project.status === 'failed' ? 'Click to view error details' : undefined}
>
```

**Rationale**:
- Native HTML title attribute provides browser-default tooltip on hover
- Only shows for failed videos to indicate they're interactive
- Non-intrusive, doesn't change layout or styling
- Follows established patterns (title attribute commonly used for hints)

### Success Criteria

#### Automated Verification:
- [x] TypeScript compilation passes: `cd frontend && npm run build`
- [x] No linting errors: `cd frontend && npm run lint`
- [x] Component renders without errors: Start dev server `cd frontend && npm run dev`

#### Manual Verification:
- [ ] Hover over failed video card → tooltip appears saying "Click to view error details"
- [ ] Hover over in-progress video → no tooltip appears
- [ ] Hover over completed video → no tooltip appears
- [ ] Click on failed video → navigates to processing page
- [ ] Tooltip appearance is consistent across browsers (Chrome, Firefox)

**Implementation Note**: After completing this phase and all automated verification passes, pause here for manual confirmation from the human that tooltips work correctly and the feature is complete.

---

## Testing Strategy

### Unit Tests (Future Enhancement)
While this plan focuses on implementation, future test coverage should include:
- App.tsx: Test that handleProjectSelect navigates correctly for all status values
- VideoStatus.tsx: Test that failedPhase state updates when status.status === 'failed'
- VideoStatus.tsx: Test renderFailedPhaseCard returns null when no error
- VideoStatus.tsx: Test renderFailedPhaseCard returns card when error exists

### Integration Tests (Future Enhancement)
- Full flow: Create failed video → appears in projects list → click → shows error in VideoStatus
- Checkpoint preservation: Phase 1 succeeds, Phase 2 fails → both cards visible

### Manual Testing Steps

#### Test Case 1: Failed Video Navigation
1. Navigate to `/projects` page
2. Locate a video with "Failed" badge (red/destructive variant)
3. Hover over the card → verify tooltip "Click to view error details" appears
4. Click the failed video card
5. Verify navigation to `/processing/{videoId}`
6. Verify URL in browser address bar updates correctly

#### Test Case 2: Error Display at Phase Level
1. On VideoStatus page for failed video
2. Verify toast notification appears briefly with error message
3. Scroll down to checkpoint section
4. Verify error card appears with:
   - Red AlertCircle icon
   - Heading "Phase Failed: {phase_name}"
   - Red Alert box with error message
   - Destructive styling (red border, light red background)

#### Test Case 3: Multiple Phases with Failure
1. For video that completed Phase 1 but failed in Phase 2:
2. Verify Phase 1 checkpoint card appears first
3. Verify Phase 2 error card appears below it
4. Verify checkpoint tree (if available) shows Phase 1 in tree
5. Verify branch selector (if multiple branches) still functions

#### Test Case 4: Status Values Coverage
Test all status values work correctly:
- `status: 'complete'` → navigates to preview page
- `status: 'failed'` → navigates to processing page with error card
- `status: 'queued'` → navigates to processing page (no error card)
- `status: 'validating'` → navigates to processing page (no error card)
- `status: 'generating_chunks'` → navigates to processing page (no error card)

#### Test Case 5: Error Persistence
1. Navigate to failed video
2. Note error card is visible
3. Click Continue button on a checkpoint (if available)
4. Verify error card remains visible (doesn't disappear)
5. Refresh page
6. Verify error card still appears after page reload

---

## Performance Considerations

### Impact Analysis
- **Minimal Performance Impact**: Changes are UI-only with no additional API calls
- **State Variables**: Added one new state variable `failedPhase` (negligible memory)
- **Rendering**: Error card only renders when failure exists (conditional)
- **No Additional Network**: Uses existing StatusResponse data, no new fetches

### Optimization Notes
- Error card renders once when failure is detected, not on every status update
- Conditional rendering prevents unnecessary DOM updates
- Alert component uses optimized Radix UI primitives
- No animation or heavy computation in error display

---

## Migration Notes

### No Database Changes Required
- All changes are frontend-only
- Backend API already provides all necessary data
- No schema migrations needed

### Backwards Compatibility
- Changes are additive, no breaking changes
- Existing functionality preserved
- Failed videos that were previously inaccessible become accessible
- No changes to API contracts or data structures

### Rollout Strategy
1. Deploy Phase 1 → Failed videos become clickable (safe, no display changes)
2. Deploy Phase 2 → Error display appears (safe, only visible for failed videos)
3. Deploy Phase 3 → Tooltips appear (safe, minor UX enhancement)

Each phase can be deployed independently without breaking existing functionality.

---

## Edge Cases and Error Handling

### Edge Case 1: No Error Message from Backend
**Scenario**: `status.error` is undefined or empty string

**Handling**:
```typescript
error: status.error || 'Unknown error'
```
Shows "Unknown error" as fallback (line 190, 285 in updated code)

### Edge Case 2: Phase Name Missing
**Scenario**: `status.current_phase` is undefined

**Handling**:
```typescript
phase: status.current_phase || 'unknown'
```
Shows "Phase Failed: unknown" (line 286 in updated code)

### Edge Case 3: Failed Video with No Checkpoints
**Scenario**: Video fails in Phase 1 before any checkpoint is created

**Handling**: Conditional rendering checks both `currentCheckpoint` and `failedPhase`:
```typescript
{(currentCheckpoint || failedPhase) && videoId && (
```
Error card will render even without checkpoint data

### Edge Case 4: Multiple Status Updates
**Scenario**: Status changes from 'failed' back to processing (if user retries)

**Handling**: `failedPhase` state will be overwritten by new status. If status changes to non-failed, error card won't render (failedPhase only set when status === 'failed')

### Edge Case 5: Very Long Error Messages
**Scenario**: Backend returns multi-paragraph error message

**Handling**: Alert component with AlertDescription uses proper text wrapping and scrolling if needed. No truncation required.

---

## References

- Original research: `thoughts/shared/research/2025-11-21-frontend-error-ui-bugs.md`
- Walkthrough findings: `walkthrough-findings.md` (shows real failure example)
- Backend implementation: Backend correctly handles errors (production-ready)
- Similar patterns:
  - `frontend/src/components/ProcessingSteps.tsx:32-43` - Conditional status icons
  - `frontend/src/pages/Auth.tsx:106-111` - Alert component for errors
  - `frontend/src/pages/Preview.tsx:97-114` - Error state display
  - `frontend/src/components/AssetList.tsx:80-91` - Retry button pattern

---

## Success Metrics

After implementation, the following metrics should improve:

### User Experience Metrics
- ✅ Failed videos accessible from projects page (previously 0%, target 100%)
- ✅ Error details visible to users (previously temporary toast only)
- ✅ Checkpoint preservation visible (users can see what succeeded)
- ✅ Clear indication of where failure occurred (phase-level granularity)

### Technical Metrics
- No increase in API calls (uses existing data)
- No new console errors
- No accessibility regressions
- Maintains responsive design on mobile

### Validation
Success will be confirmed when:
1. User can click any failed video and see error details
2. Error information persists throughout session
3. Completed checkpoints remain visible alongside error
4. All three phases pass automated and manual verification
