---
date: 2025-11-21T03:12:45-06:00
researcher: lousydropout
git_commit: a9f9d20e8a070e93ce1f182d2a66d9dbec34488f
branch: refactor/vincent
repository: aivideo
topic: "Frontend codebase research for checkpoint feature refactor"
tags: [research, codebase, frontend, checkpoints, react, typescript]
status: complete
last_updated: 2025-11-21
last_updated_by: lousydropout
related_plans: thoughts/shared/plans/2025-11-20-checkpoint-feature.md
related_flows: user-flow.md
---

# Research: Frontend Codebase for Checkpoint Feature Refactor

**Date**: 2025-11-21T03:12:45-06:00
**Researcher**: lousydropout
**Git Commit**: a9f9d20e8a070e93ce1f182d2a66d9dbec34488f
**Branch**: refactor/vincent
**Repository**: aivideo

## Research Question

Research the frontend codebase in preparation to refactor it to align with the checkpoint feature plan (`thoughts/shared/plans/2025-11-20-checkpoint-feature.md`) and user flow (`user-flow.md`).

**Goal**: Understand current frontend architecture, component structure, API integration patterns, and identify what needs to be modified or created to support:
- Pausing after each of 4 pipeline phases
- Displaying checkpoints and artifacts at each phase
- Editing artifacts (spec, images, chunks)
- Branch visualization and navigation
- YOLO mode (auto_continue flag)

## Summary

The frontend is a **React 18.3 + TypeScript** application using **Vite** as the build tool, with **Tailwind CSS** for styling and **Radix UI** (via Shadcn/ui) for accessible component primitives. The current architecture uses a simple status polling/SSE system to monitor video generation progress, but does NOT support:

- ❌ Checkpoint-based pausing (currently runs continuously in "YOLO mode" only)
- ❌ Artifact editing at checkpoints
- ❌ Branch visualization
- ❌ Manual continuation via API calls
- ❌ Displaying checkpoint metadata or tree structure

**Key Findings**:
1. **Clean separation** between pages (UploadVideo, VideoStatus, Preview) makes it easy to insert checkpoint UI
2. **SSE + polling fallback** already exists for real-time updates - can be extended for checkpoint events
3. **No tree visualization** component exists - will need custom implementation
4. **API client** uses axios with Firebase JWT auth - ready for new checkpoint endpoints
5. **UI patterns** are consistent (Shadcn/Radix) - new components will match existing design

**Recommended Approach**:
- Extend `VideoStatus` page to show checkpoints and editing UI
- Add new checkpoint-specific components (CheckpointTree, ArtifactEditor, BranchSelector)
- Update API client with checkpoint endpoints
- Modify status polling to handle new paused states
- Reuse existing UI patterns (dialog for editing, progress bars, image grids)

---

## Detailed Findings

### 1. Frontend Architecture

**Framework & Tools**:
- **React 18.3.1** with **TypeScript**
- **Vite 5.4.2** for build tooling
- **React Router DOM 7.9.6** for routing
- **Tailwind CSS 3.4.1** for styling
- **Shadcn/ui** component library (Radix UI primitives)
- **Firebase 12.6.0** for authentication
- **Axios 1.13.2** for HTTP requests

**Directory Structure** (`frontend/src/`):
```
frontend/src/
├── components/
│   ├── ui/               # 17 Shadcn/ui components (button, dialog, input, etc.)
│   ├── AssetList.tsx
│   ├── ProcessingSteps.tsx
│   ├── ProjectCard.tsx
│   ├── UploadZone.tsx
│   └── VideoEditor.tsx
├── contexts/
│   └── AuthContext.tsx   # Authentication state
├── hooks/
│   └── use-toast.ts
├── lib/
│   ├── api.ts            # API client
│   ├── firebase.ts       # Auth integration
│   ├── useVideoStatusStream.ts  # SSE/polling hook
│   └── utils.ts
├── pages/
│   ├── AssetLibrary.tsx
│   ├── Dashboard.tsx
│   ├── Preview.tsx       # Final video display
│   ├── UploadVideo.tsx   # Video creation form
│   └── VideoStatus.tsx   # Real-time status monitoring
├── App.tsx               # Router & global state
└── main.tsx              # Entry point
```

**Key Files**:
- `frontend/src/pages/UploadVideo.tsx:1-411` - Video creation form
- `frontend/src/pages/VideoStatus.tsx:1-379` - Status monitoring page
- `frontend/src/pages/Preview.tsx:1-192` - Final video player
- `frontend/src/lib/api.ts:1-288` - API client with all endpoints
- `frontend/src/lib/useVideoStatusStream.ts:1-191` - SSE/polling hook
- `frontend/src/App.tsx:1-476` - Main router and state

**Current Routes**:
- `/` - UploadVideo (main creation page)
- `/processing/:videoId` - VideoStatus (real-time monitoring)
- `/preview/:videoId` - Preview (completed video)
- `/projects` - Video library
- `/asset-library` - Asset management

---

### 2. Current Video Generation Flow

**User Journey** (Manual Mode - NOT CURRENTLY IMPLEMENTED):
1. User fills form on `UploadVideo` page (title, prompt, assets, model)
2. Submits form → calls `generateVideo()` API
3. Navigates to `/processing/:videoId`
4. `VideoStatus` page uses `useVideoStatusStream` hook for SSE/polling
5. Shows processing steps, storyboard images when available
6. On completion → navigates to `/preview/:videoId`

**Current Implementation Details**:

**Form Submission** (`UploadVideo.tsx:42-63`):
```typescript
const handleSubmit = async (e: React.FormEvent) => {
  e.preventDefault();
  const response = await generateVideo({
    title: title || 'Untitled Video',
    description: description || undefined,
    prompt: prompt,
    reference_assets: uploadedAssetIds,
    model: selectedModel
  });
  navigate(`/processing/${response.video_id}`);
  onNotification?.('success', 'Generation Started', 'Your video is being created...');
};
```

**API Call** (`api.ts:247-257`):
```typescript
async generateVideo(request: GenerateRequest): Promise<GenerateResponse> {
  const response = await apiClient.post<GenerateResponse>('/api/generate', request);
  return response.data;
}
```

**Status Monitoring** (`VideoStatus.tsx:71-74`):
```typescript
const { status: streamStatus, error: streamError, isConnected } = useVideoStatusStream(
  videoId || null,
  isProcessing
);
```

**Status Processing** (`VideoStatus.tsx:96-206`):
- Maps phases to step index (0-2)
- Updates storyboard URLs when available
- Updates chunk progress during Phase 4
- Navigates to preview on completion

**Gap**: No checkpoint awareness - treats video generation as continuous process.

---

### 3. Status Polling & Real-Time Updates

**Primary Mechanism**: Server-Sent Events (SSE) with automatic polling fallback

**Hook**: `useVideoStatusStream` (`useVideoStatusStream.ts:18-189`)

**SSE Implementation**:
1. Fetches Firebase auth token
2. Creates EventSource with token as query parameter:
   ```typescript
   const sseUrl = `${API_URL}/api/status/${videoId}/stream?token=${encodeURIComponent(token)}`;
   const eventSource = new EventSource(sseUrl);
   ```
3. Listens for `message` events and parses `StatusResponse`
4. Handles `close` event from server
5. Falls back to polling on any error

**Polling Fallback**:
- Calls `getVideoStatus(videoId)` every 2.5 seconds
- Uses `setInterval` with cleanup on unmount

**Status Update Processing** (`VideoStatus.tsx:96-206`):
- Phase mapping to progress steps
- Storyboard image display
- Chunk progress tracking
- Video URL updates
- Completion/failure handling

**Current Status Fields** (`api.ts:91-104`):
```typescript
interface StatusResponse {
  video_id: string;
  status: string;
  progress: number;
  current_phase?: string;
  estimated_time_remaining?: number;
  error?: string;
  reference_assets?: ReferenceAssets;
  storyboard_urls?: string[];
  stitched_video_url?: string;
  final_video_url?: string;
  current_chunk_index?: number;
  total_chunks?: number;
}
```

**Gap**: No checkpoint fields (`current_checkpoint`, `checkpoint_tree`, `active_branches`) - need to extend `StatusResponse` interface.

---

### 4. API Integration Patterns

**HTTP Client**: Axios with interceptors

**Base Configuration** (`api.ts:8-13`):
```typescript
const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const apiClient = axios.create({
  baseURL: API_URL,
  headers: { 'Content-Type': 'application/json' }
});
```

**Authentication** (`api.ts:16-39`):
- Request interceptor adds Firebase JWT token to all requests
- Token retrieved via `getIdToken()` from `firebase.ts`
- Format: `Authorization: Bearer {token}`
- Graceful fallback if token unavailable

**Error Handling** (`api.ts:42-61`):
- Response interceptor catches errors globally
- Extracts `detail` or `message` from backend errors
- User-friendly messages for network errors
- Logs all errors to console

**TypeScript Types** (`api.ts:64-163`):
- `GenerateRequest` / `GenerateResponse`
- `StatusResponse`
- `VideoResponse`
- `UploadResponse`
- `VideoListItem`
- `AssetListItem`

**Request Patterns**:
- **GET**: `await apiClient.get<T>(url)`
- **POST**: `await apiClient.post<T>(url, data)`
- **DELETE**: `await apiClient.delete(url)`
- **File Upload**: FormData with `Content-Type: multipart/form-data`

**State Management**:
- **Global auth**: React Context API (`AuthContext.tsx`)
- **Local state**: `useState` hooks in components
- **Side effects**: `useEffect` for data fetching
- **No Redux** or other global state libraries

**Gap**: Need to add checkpoint-specific API calls and types.

---

### 5. Video-Related Components

**Main Components**:

1. **`UploadVideo.tsx`** (`pages/UploadVideo.tsx:1-411`)
   - Video creation form
   - Fields: title, description, prompt, assets, model
   - Integrates `UploadZone` for file uploads
   - Calls `generateVideo()` API
   - **Route**: `/` and `/projects`

2. **`VideoStatus.tsx`** (`pages/VideoStatus.tsx:1-379`)
   - Real-time status monitoring
   - Uses `ProcessingSteps` component
   - Displays storyboard images in grid
   - Shows chunk progress
   - **Route**: `/processing/:videoId`

3. **`Preview.tsx`** (`pages/Preview.tsx:1-192`)
   - Final video player
   - Uses HTML5 `<video>` element
   - Download functionality
   - **Route**: `/preview/:videoId`

4. **`ProcessingSteps.tsx`** (`components/ProcessingSteps.tsx:14-70`)
   - Visual step indicators
   - Status icons (pending, processing, completed, failed)
   - Elapsed time display

5. **`ProjectCard.tsx`** (`components/ProjectCard.tsx:26-125`)
   - Video thumbnail cards
   - Status badge
   - Progress bar during processing
   - Hover-to-play video preview

6. **`UploadZone.tsx`** (`components/UploadZone.tsx:1-232`)
   - Drag-and-drop file upload
   - Progress tracking
   - Multi-file support
   - Status indicators per file

7. **`AssetList.tsx`** (`components/AssetList.tsx:1-127`)
   - Asset selection grid
   - Thumbnails with type icons
   - Multi-select checkboxes

**Supporting Components**:
- `ShareModal.tsx` - Share dialog
- `ExportPanel.tsx` - Export settings
- `VideoEditor.tsx` - Video settings editor (not currently used)
- `NotificationCenter.tsx` - Toast notifications

**Gap**: No checkpoint-specific components (tree view, artifact editor, branch selector).

---

### 6. UI/UX Patterns

**Component Library**: Shadcn/ui (Radix UI + Tailwind)

**Styling Approach**:
- Tailwind utility classes
- CSS variables for colors (OKLCH color space)
- Dark mode via class strategy
- Custom animations (fadeIn, slideIn, pulse-subtle, float)
- Claymorphism aesthetic with backdrop blur

**Key UI Components** (`components/ui/`):
- `button.tsx` - Button with variants (default, destructive, outline, secondary, ghost, link)
- `dialog.tsx` - Modal dialogs
- `input.tsx` - Text inputs
- `select.tsx` - Dropdown selects
- `progress.tsx` - Progress bars
- `slider.tsx` - Range sliders
- `badge.tsx` - Status badges
- `card.tsx` - Card containers
- `sheet.tsx` - Side panels
- `toast.tsx` - Notifications
- `skeleton.tsx` - Loading skeletons

**Common Patterns**:

**1. Button Actions**:
```tsx
<Button variant="default">Continue</Button>
<Button variant="destructive">Delete</Button>
<Button variant="outline">Cancel</Button>
<Button variant="secondary">Done</Button>
```

**2. Form Fields**:
```tsx
<div>
  <Label>Field Label</Label>
  <Input type="text" placeholder="Placeholder" />
  <p className="text-xs text-muted-foreground">Help text</p>
</div>
```

**3. Modal Dialogs**:
```tsx
<Dialog open={open} onOpenChange={setOpen}>
  <DialogContent>
    <DialogHeader>
      <DialogTitle>Title</DialogTitle>
    </DialogHeader>
    <div className="space-y-4">{/* Content */}</div>
    <DialogFooter>
      <Button variant="secondary">Cancel</Button>
      <Button>Save</Button>
    </DialogFooter>
  </DialogContent>
</Dialog>
```

**4. Image Grid with Status**:
```tsx
<div className="grid grid-cols-2 md:grid-cols-4 gap-4">
  {images.map((url, idx) => (
    <div key={idx} className="relative group">
      <img
        src={url}
        className={`rounded-lg border-2 ${
          isProcessing ? 'border-primary ring-4 ring-primary/30' :
          isCompleted ? 'border-primary' : 'border-border'
        }`}
      />
      {isProcessing && (
        <div className="absolute inset-0 bg-primary/20 flex items-center justify-center">
          <Loader2 className="animate-spin" />
        </div>
      )}
    </div>
  ))}
</div>
```

**5. Progress Display**:
```tsx
<ProcessingSteps
  steps={[
    { name: 'Step 1', status: 'completed' },
    { name: 'Step 2', status: 'processing' },
    { name: 'Step 3', status: 'pending' }
  ]}
  elapsedTime={45}
/>
```

**6. File Upload**:
```tsx
<div
  className="border-2 border-dashed rounded-xl p-8 cursor-pointer hover:border-primary"
  onClick={() => fileInputRef.current?.click()}
>
  <Upload className="w-12 h-12 mx-auto mb-3" />
  <p>Drag & drop or click to upload</p>
</div>
```

**7. Toast Notifications**:
```tsx
const { toast } = useToast();

toast({
  title: "Success",
  description: "Your changes have been saved.",
});

toast({
  variant: "destructive",
  title: "Error",
  description: "Something went wrong.",
});
```

**Gap**: No tree visualization pattern - will need custom implementation for checkpoint tree.

---

## Code References

### Key Files for Modification

**High Priority** (Must Change):
- `frontend/src/pages/VideoStatus.tsx:1-379` - Add checkpoint UI and editing
- `frontend/src/lib/api.ts:1-288` - Add checkpoint endpoints
- `frontend/src/lib/useVideoStatusStream.ts:1-191` - Handle checkpoint events
- `frontend/src/pages/UploadVideo.tsx:1-411` - Add `auto_continue` flag
- `frontend/src/App.tsx:1-476` - Add checkpoint routes if needed

**Medium Priority** (New Components):
- Create `frontend/src/components/CheckpointTree.tsx` - Tree visualization
- Create `frontend/src/components/ArtifactEditor.tsx` - Edit spec/images
- Create `frontend/src/components/BranchSelector.tsx` - Branch navigation
- Create `frontend/src/components/CheckpointCard.tsx` - Checkpoint display

**Low Priority** (Extensions):
- `frontend/src/components/ProcessingSteps.tsx:1-70` - Extend for 4 phases
- `frontend/src/pages/Preview.tsx:1-192` - Show checkpoint history

### Component Hierarchy for Checkpoint Feature

```
VideoStatus (processing/:videoId)
├── ProcessingSteps (extended to 4 phases)
├── CheckpointCard (NEW) - Current checkpoint display
│   ├── Phase indicator
│   ├── Branch name
│   ├── Artifact list
│   └── Edit/Continue buttons
├── CheckpointTree (NEW) - Tree visualization
│   └── Recursive tree nodes
├── ArtifactEditor (NEW) - Modal for editing
│   ├── SpecEditor (Phase 1)
│   ├── ImageEditor (Phase 2)
│   └── ChunkEditor (Phase 3)
├── BranchSelector (NEW) - Branch navigation dropdown
└── Existing: Storyboard grid, video preview
```

---

## Gap Analysis

### What Exists ✅

1. ✅ **Video generation form** with model selection
2. ✅ **Real-time status updates** via SSE + polling
3. ✅ **Processing step visualization** (3 steps currently)
4. ✅ **Storyboard image grid** display
5. ✅ **Video preview** on completion
6. ✅ **File upload** with drag-and-drop
7. ✅ **API client** with auth and error handling
8. ✅ **Modal dialogs** for editing
9. ✅ **Toast notifications** for feedback
10. ✅ **Progress bars** and loading states
11. ✅ **Image grid** with status indicators
12. ✅ **Form patterns** with validation

### What's Missing ❌

1. ❌ **Checkpoint-based pausing** - Currently only YOLO mode
2. ❌ **Manual continue button** - No POST /continue endpoint call
3. ❌ **Checkpoint tree visualization** - No tree component
4. ❌ **Branch selector** - No branch navigation
5. ❌ **Artifact editing UI** - No edit spec/images/chunks
6. ❌ **Checkpoint metadata display** - No checkpoint info in status
7. ❌ **auto_continue flag** - No toggle in generation form
8. ❌ **Phase 4 visualization** - Only 3 steps shown
9. ❌ **Upload replacement image** - No multipart upload for beat images
10. ❌ **Regenerate beat/chunk buttons** - No regeneration UI
11. ❌ **Branch creation feedback** - No "created new branch" messaging
12. ❌ **Checkpoint history** - No past checkpoint display

---

## Architecture Documentation

### Current Data Flow

```
User Input (UploadVideo)
  ↓
generateVideo() API call
  ↓
Navigate to /processing/:videoId
  ↓
useVideoStatusStream hook
  ├─ Try SSE connection
  └─ Fallback to polling (2.5s interval)
  ↓
StatusResponse received
  ↓
VideoStatus processes update
  ├─ Map phase to step (0-2)
  ├─ Update storyboard URLs
  ├─ Update chunk progress
  └─ Check completion
  ↓
Navigate to /preview/:videoId
  ↓
Display final video
```

### Required Data Flow for Checkpoints

```
User Input (UploadVideo) + auto_continue flag
  ↓
generateVideo() API call
  ↓
Navigate to /processing/:videoId
  ↓
useVideoStatusStream hook (extended)
  ├─ SSE receives checkpoint_created event
  └─ StatusResponse includes checkpoint fields
  ↓
VideoStatus processes checkpoint
  ├─ Show CheckpointCard with current checkpoint
  ├─ Display artifacts (spec/images/chunks)
  ├─ Show "Edit" button (opens ArtifactEditor)
  ├─ Show "Continue" button
  └─ Display CheckpointTree with branches
  ↓
User clicks "Edit"
  ↓
ArtifactEditor modal opens
  ├─ Phase 1: Edit spec (PATCH /spec)
  ├─ Phase 2: Upload/regenerate image (POST /upload-image or /regenerate-beat)
  └─ Phase 3: Regenerate chunk (POST /regenerate-chunk)
  ↓
API creates new artifact version
  ↓
Checkpoint marked as edited
  ↓
User clicks "Continue"
  ↓
POST /continue with checkpoint_id
  ↓
Backend checks if edited → creates new branch
  ↓
Response: { next_phase, branch_name, created_new_branch }
  ↓
Show toast: "Created new branch: main-1"
  ↓
Next phase starts
  ↓
Loop back to checkpoint display
```

---

## Recommended Implementation Approach

### Phase 1: Extend API Client

**Files**: `frontend/src/lib/api.ts`

**Add Types**:
```typescript
// Extend StatusResponse
interface StatusResponse {
  // ... existing fields
  current_checkpoint?: CheckpointInfo;
  checkpoint_tree?: CheckpointTreeNode[];
  active_branches?: BranchInfo[];
}

interface CheckpointInfo {
  checkpoint_id: string;
  branch_name: string;
  phase_number: number;
  version: number;
  status: 'pending' | 'approved' | 'abandoned';
  created_at: string;
  artifacts: Record<string, ArtifactResponse>;
}

interface CheckpointTreeNode {
  checkpoint: CheckpointResponse;
  children: CheckpointTreeNode[];
}

interface BranchInfo {
  branch_name: string;
  latest_checkpoint_id: string;
  phase_number: number;
  status: string;
  can_continue: boolean;
}

interface ContinueRequest {
  checkpoint_id: string;
}

interface ContinueResponse {
  message: string;
  next_phase: number;
  branch_name: string;
  created_new_branch: boolean;
}
```

**Add Methods**:
```typescript
// Checkpoint endpoints
async listCheckpoints(videoId: string): Promise<CheckpointListResponse>
async getCheckpoint(videoId: string, checkpointId: string): Promise<CheckpointDetailResponse>
async getCurrentCheckpoint(videoId: string): Promise<CheckpointResponse>
async listBranches(videoId: string): Promise<BranchListResponse>
async continueVideo(videoId: string, checkpointId: string): Promise<ContinueResponse>

// Artifact editing endpoints
async editSpec(videoId: string, checkpointId: string, edits: SpecEditRequest): Promise<ArtifactResponse>
async uploadBeatImage(videoId: string, checkpointId: string, beatIndex: number, file: File): Promise<ArtifactResponse>
async regenerateBeat(videoId: string, checkpointId: string, beatIndex: number, promptOverride?: string): Promise<ArtifactResponse>
async regenerateChunk(videoId: string, checkpointId: string, chunkIndex: number, modelOverride?: string): Promise<ArtifactResponse>
```

### Phase 2: Extend Status Polling

**Files**: `frontend/src/lib/useVideoStatusStream.ts`

**Handle checkpoint events**:
```typescript
// Add checkpoint event listener in SSE
eventSource.addEventListener('checkpoint_created', (event) => {
  const data = JSON.parse(event.data);
  console.log('[SSE] Checkpoint created:', data);
  // Trigger checkpoint state update
});
```

**Update StatusResponse handling** to include checkpoint fields.

### Phase 3: Create New Components

**1. CheckpointCard Component**
- Display current checkpoint info
- Show artifacts (spec text, image grid, video preview)
- "Edit" button → opens ArtifactEditor
- "Continue" button → calls continueVideo()
- Branch name badge
- Phase indicator

**2. CheckpointTree Component**
- Recursive tree visualization
- Indent child branches
- Highlight current branch
- Click to view checkpoint details
- Show phase number and status

**3. ArtifactEditor Component**
- Modal dialog with tabs for each phase
- Phase 1: Textarea for spec editing
- Phase 2: Image upload + regenerate buttons
- Phase 3: Chunk regenerate buttons
- Save button → calls appropriate API endpoint

**4. BranchSelector Component**
- Dropdown showing active branches
- Current branch highlighted
- Click to switch branch view (future enhancement)

### Phase 4: Modify VideoStatus Page

**Files**: `frontend/src/pages/VideoStatus.tsx`

**Add State**:
```typescript
const [currentCheckpoint, setCurrentCheckpoint] = useState<CheckpointInfo | null>(null);
const [checkpointTree, setCheckpointTree] = useState<CheckpointTreeNode[]>([]);
const [activeBranches, setActiveBranches] = useState<BranchInfo[]>([]);
const [editDialogOpen, setEditDialogOpen] = useState(false);
```

**Handle Checkpoint Events**:
```typescript
useEffect(() => {
  if (streamStatus?.current_checkpoint) {
    setCurrentCheckpoint(streamStatus.current_checkpoint);
    setCheckpointTree(streamStatus.checkpoint_tree || []);
    setActiveBranches(streamStatus.active_branches || []);

    // Check if paused
    if (streamStatus.status.includes('PAUSED_AT_PHASE')) {
      setIsProcessing(false); // Stop elapsed time counter
    }
  }
}, [streamStatus]);
```

**Add Continue Handler**:
```typescript
const handleContinue = async () => {
  if (!currentCheckpoint) return;

  try {
    const response = await continueVideo(videoId, currentCheckpoint.checkpoint_id);

    if (response.created_new_branch) {
      toast({
        title: "New Branch Created",
        description: `Created branch: ${response.branch_name}`,
      });
    }

    toast({
      title: "Pipeline Continued",
      description: `Starting Phase ${response.next_phase}`,
    });

    setIsProcessing(true); // Resume monitoring
  } catch (error) {
    toast({
      variant: "destructive",
      title: "Continue Failed",
      description: error.message,
    });
  }
};
```

**Layout**:
```tsx
<div className="space-y-6">
  {/* Existing ProcessingSteps */}
  <ProcessingSteps steps={processingSteps} elapsedTime={elapsedTime} />

  {/* NEW: Current Checkpoint Card */}
  {currentCheckpoint && (
    <CheckpointCard
      checkpoint={currentCheckpoint}
      onEdit={() => setEditDialogOpen(true)}
      onContinue={handleContinue}
    />
  )}

  {/* NEW: Checkpoint Tree */}
  {checkpointTree.length > 0 && (
    <CheckpointTree tree={checkpointTree} currentCheckpointId={currentCheckpoint?.checkpoint_id} />
  )}

  {/* Existing storyboard grid */}
  {storyboardUrls && storyboardUrls.length > 0 && (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
      {/* ... existing image grid */}
    </div>
  )}

  {/* NEW: Artifact Editor Modal */}
  <ArtifactEditor
    open={editDialogOpen}
    onOpenChange={setEditDialogOpen}
    checkpoint={currentCheckpoint}
    videoId={videoId}
    onArtifactUpdated={(artifact) => {
      // Refresh checkpoint data
      toast({ title: "Artifact Updated", description: `Version ${artifact.version} created` });
    }}
  />
</div>
```

### Phase 5: Add auto_continue Flag to Form

**Files**: `frontend/src/pages/UploadVideo.tsx`

**Add Checkbox**:
```tsx
<div className="flex items-center space-x-2">
  <Checkbox
    id="auto-continue"
    checked={autoContinue}
    onCheckedChange={setAutoContinue}
  />
  <Label htmlFor="auto-continue">
    YOLO Mode (Auto-continue without pausing)
  </Label>
</div>
```

**Include in API call**:
```typescript
const response = await generateVideo({
  // ... existing fields
  auto_continue: autoContinue,
});
```

### Phase 6: Extend ProcessingSteps to 4 Phases

**Files**: `frontend/src/components/ProcessingSteps.tsx`

**Update step labels**:
```typescript
const steps = [
  { name: 'Content planning with AI', status: getStepStatus(0) },
  { name: 'Generating storyboard images', status: getStepStatus(1) },
  { name: 'Generating video chunks', status: getStepStatus(2) },
  { name: 'Adding music and finalizing', status: getStepStatus(3) }, // NEW
];
```

**Update phase mapping** (`VideoStatus.tsx:31-40`):
```typescript
function getProcessingStepFromPhase(phase: string, progress: number): number {
  if (phase === 'phase1_validate') return 0;
  if (phase === 'phase2_storyboard' || phase === 'phase2_animatic') return 1;
  if (phase === 'phase3_chunks') return 2;
  if (phase === 'phase4_refine') return 3; // NEW
  return Math.min(Math.floor(progress / 25), 3);
}
```

---

## Open Questions

1. **Tree Visualization Library**: Should we use a third-party library (e.g., react-d3-tree, react-organizational-chart) or build custom with nested divs?
   - **Recommendation**: Start with custom nested divs for MVP, can upgrade later if needed

2. **Checkpoint History**: Should we show all historical checkpoints or just active branches?
   - **Recommendation**: Show full tree initially, add filter to show only active branches

3. **Branch Switching**: Should users be able to switch between branches in the UI, or just view the current branch?
   - **Recommendation**: MVP shows current branch only, add switching in future iteration

4. **Artifact Preview Size**: Should artifact images/videos be full-size or thumbnails?
   - **Recommendation**: Thumbnails with click-to-expand (use existing pattern)

5. **Mobile Layout**: How should checkpoint tree and artifacts display on mobile?
   - **Recommendation**: Stack vertically, collapse tree by default with expand button

6. **Real-time Updates During Edit**: Should editing artifacts pause SSE polling?
   - **Recommendation**: Keep polling active to show if backend continues processing

7. **Notification Spam**: With 4 checkpoints, will we get too many notifications?
   - **Recommendation**: Only notify on first checkpoint and completion, suppress intermediate notifications unless errors

---

## Related Research

- Backend implementation plan: `thoughts/shared/plans/2025-11-20-checkpoint-feature.md`
- User flow documentation: `user-flow.md`

---

## Next Steps

### Immediate Actions:
1. ✅ Complete this research document
2. ⏭️ Create technical design document for frontend refactor
3. ⏭️ Implement Phase 1: Extend API client with checkpoint endpoints
4. ⏭️ Implement Phase 2: Extend status polling for checkpoint events
5. ⏭️ Implement Phase 3: Create new checkpoint components
6. ⏭️ Implement Phase 4: Modify VideoStatus page
7. ⏭️ Implement Phase 5: Add auto_continue flag to form
8. ⏭️ Implement Phase 6: Test end-to-end with backend

### Testing Strategy:
- Unit tests for new components (CheckpointCard, CheckpointTree, ArtifactEditor)
- Integration tests for API client methods
- E2E tests for checkpoint flow (manual mode)
- E2E tests for YOLO mode (auto_continue=true)
- Visual regression tests for tree visualization

---

**End of Research Document**
