# Checkpoint Retry from Failed Video - Issue & Solutions

**Date**: 2025-11-21
**Status**: Issue Identified - Needs Backend Fix
**Component**: Checkpoint System, Video Pipeline
**Severity**: Medium - Impacts user experience when retrying failed videos

---

## Issue Summary

When a video generation fails at a later phase (e.g., Phase 2), users cannot retry from the last successful checkpoint because the backend rejects the request with error: **"Checkpoint already approved"**.

This prevents users from easily recovering from failures without manual intervention.

---

## Background Context

### Checkpoint System Design

The video generation pipeline uses a checkpoint system with the following flow:

1. **Phase N completes** → Checkpoint created with `status: "pending"`
2. **Auto-continue OR manual continue** → Checkpoint marked as `status: "approved"`
3. **Phase N+1 starts** using artifacts from approved checkpoint
4. If **Phase N+1 fails** → Video status becomes "failed"

### Current Behavior

**Scenario**: Video fails in Phase 2 after Phase 1 completed successfully

```
Phase 1: ✅ Complete → Checkpoint created → Approved → Phase 2 started
Phase 2: ❌ Failed → Video status = "failed"

User Action: Click "Retry from Last Checkpoint"
API Call: POST /api/video/{video_id}/continue { checkpoint_id: "phase1_checkpoint_id" }
Response: 400 Bad Request { "detail": "Checkpoint already approved" }
```

**Why it fails**: The backend's continue endpoint validates that checkpoints can only be approved once. Once a checkpoint is approved and the pipeline continues from it, that checkpoint cannot be used again.

---

## Discovery Process

### How We Found This

1. Implemented failed video UI improvements (Phase 1-3 from `2025-11-21-fix-failed-video-ui-bugs.md`)
2. Added "Retry from Last Checkpoint" button to error display
3. User clicked retry on a failed video (Phase 2 failed, Phase 1 succeeded)
4. Backend rejected with "Checkpoint already approved"

### API Response Analysis

**Status API Response for Failed Video**:
```json
{
  "video_id": "0a706f65-3c30-466b-b70e-9d865c7f0ca4",
  "status": "failed",
  "current_phase": "phase2_storyboard",
  "error": "Failed to generate storyboard image for beat 0: Replicate API error...",
  "current_checkpoint": null,  // ← No current checkpoint (video failed, not paused)
  "checkpoint_tree": [
    {
      "checkpoint": {
        "id": "cp-fbb2927c-db76-4e81-a67e-6292eca99e03",
        "phase_number": 1,
        "status": "approved",  // ← Already approved
        "created_at": "2025-11-21T14:18:37.763126Z",
        "approved_at": "2025-11-21T14:21:00.523409Z"
      },
      "children": []
    }
  ],
  "active_branches": [
    {
      "branch_name": "main",
      "latest_checkpoint_id": "cp-fbb2927c-db76-4e81-a67e-6292eca99e03",
      "phase_number": 1,
      "status": "approved",
      "can_continue": true  // ← Backend says we can continue, but...
    }
  ]
}
```

**Continue API Request** (what frontend sends):
```json
POST /api/video/0a706f65-3c30-466b-b70e-9d865c7f0ca4/continue
{
  "checkpoint_id": "cp-fbb2927c-db76-4e81-a67e-6292eca99e03"
}
```

**Continue API Response** (error):
```json
400 Bad Request
{
  "detail": "Checkpoint already approved"
}
```

### The Discrepancy

The status API says `"can_continue": true` but the continue API rejects the request. This is confusing and creates a poor user experience.

---

## Root Cause Analysis

### Backend Validation Logic

The backend's `/continue` endpoint likely has validation like:

```python
# Pseudo-code of current backend logic
def continue_from_checkpoint(video_id, checkpoint_id):
    checkpoint = get_checkpoint(checkpoint_id)

    if checkpoint.status == "approved":
        raise BadRequest("Checkpoint already approved")

    # Mark checkpoint as approved and continue pipeline
    checkpoint.status = "approved"
    checkpoint.approved_at = now()
    continue_pipeline(video_id, checkpoint_id)
```

**Problem**: This validation doesn't account for the retry-from-failure scenario.

### Why This Design Exists

The "already approved" validation likely prevents:
- Accidentally re-running the same checkpoint multiple times
- Creating duplicate branches from the same checkpoint
- Data consistency issues with checkpoint versioning

These are valid concerns, but the validation is too strict for the failure recovery use case.

---

## Proposed Solutions

### Option 1: Allow Retry from Approved Checkpoints for Failed Videos (Recommended)

**Change**: Modify backend `/continue` endpoint to allow retrying from approved checkpoints when video status is "failed"

**Implementation**:

```python
def continue_from_checkpoint(video_id, checkpoint_id):
    checkpoint = get_checkpoint(checkpoint_id)
    video = get_video(video_id)

    # Allow retry if video failed, even if checkpoint already approved
    if checkpoint.status == "approved" and video.status != "failed":
        raise BadRequest("Checkpoint already approved")

    # For failed videos, we're retrying - don't change checkpoint status
    # For normal flow, mark as approved
    if checkpoint.status == "pending":
        checkpoint.status = "approved"
        checkpoint.approved_at = now()

    continue_pipeline(video_id, checkpoint_id)
```

**Pros**:
- ✅ Simple user experience - just click "Retry"
- ✅ Minimal code changes
- ✅ Preserves existing checkpoint (for historical tracking)
- ✅ Makes sense semantically - "retry from this checkpoint"

**Cons**:
- ⚠️ Might create multiple continuation attempts from same checkpoint (need to handle in pipeline)
- ⚠️ Need to ensure pipeline can restart cleanly from a previously-used checkpoint

**Testing Requirements**:
- Video fails in Phase 2 → Retry → Should start Phase 2 again
- Video fails in Phase 3 → Retry → Should start Phase 3 again
- Verify no duplicate work/artifacts created
- Verify checkpoint tree structure remains clean

---

### Option 2: Auto-Create New Checkpoint Version on Retry

**Change**: When retrying from a failed video, automatically create a new version of the checkpoint

**Implementation**:

```python
def continue_from_checkpoint(video_id, checkpoint_id):
    checkpoint = get_checkpoint(checkpoint_id)
    video = get_video(video_id)

    # If checkpoint already approved and video failed, create new version
    if checkpoint.status == "approved" and video.status == "failed":
        # Clone checkpoint as new version
        new_checkpoint = clone_checkpoint(checkpoint)
        new_checkpoint.version = checkpoint.version + 1
        new_checkpoint.status = "pending"
        new_checkpoint.parent_checkpoint_id = checkpoint.id
        save(new_checkpoint)
        checkpoint_id = new_checkpoint.id
        checkpoint = new_checkpoint
    elif checkpoint.status == "approved":
        raise BadRequest("Checkpoint already approved")

    checkpoint.status = "approved"
    checkpoint.approved_at = now()
    continue_pipeline(video_id, checkpoint_id)
```

**Pros**:
- ✅ Preserves checkpoint immutability (each approval is a unique checkpoint)
- ✅ Clean audit trail in checkpoint tree
- ✅ Follows existing versioning patterns
- ✅ No risk of duplicate work from same checkpoint

**Cons**:
- ⚠️ More complex implementation
- ⚠️ Creates "redundant" checkpoints (same data, different version number)
- ⚠️ Checkpoint tree becomes cluttered with retry versions
- ⚠️ Might be confusing in UI ("why do I have version 1 and version 2 of the same thing?")

**Testing Requirements**:
- Video fails → Retry → New checkpoint version created
- Verify new checkpoint has incremented version number
- Verify checkpoint tree shows version history correctly
- Verify artifacts are copied correctly to new version
- Verify pipeline starts from new version

---

### Option 3: Require Manual Edit Before Retry (Current Workaround)

**Change**: No backend changes - users must click "Edit Previous Phase" to create a new version before retrying

**Current Flow**:
1. Video fails in Phase 2
2. User clicks "Edit Previous Phase"
3. Artifact editor opens with Phase 1 artifacts
4. User can make changes OR just click "Save" without changes
5. New checkpoint version created
6. User clicks "Retry from Last Checkpoint" (now uses new version)

**Pros**:
- ✅ No backend changes needed
- ✅ Works with existing code
- ✅ Forces user to review Phase 1 outputs before retrying

**Cons**:
- ❌ Poor user experience - requires 2 clicks + understanding the flow
- ❌ Confusing - "why can't I just retry?"
- ❌ Creating a new version when you didn't edit anything feels wrong
- ❌ Doesn't match user mental model

**Status**: This is the current workaround but should not be the final solution

---

### Option 4: Add "Force Retry" Flag to Continue API

**Change**: Add optional `force_retry: true` flag to continue endpoint

**Implementation**:

```python
def continue_from_checkpoint(video_id, checkpoint_id, force_retry=False):
    checkpoint = get_checkpoint(checkpoint_id)
    video = get_video(video_id)

    # Allow force retry for failed videos
    if checkpoint.status == "approved":
        if not force_retry:
            raise BadRequest("Checkpoint already approved. Use force_retry=true to retry.")
        if video.status != "failed":
            raise BadRequest("Cannot force retry unless video status is failed")

    # Don't modify approved checkpoints on retry
    if checkpoint.status == "pending":
        checkpoint.status = "approved"
        checkpoint.approved_at = now()

    continue_pipeline(video_id, checkpoint_id)
```

**Frontend Change**:
```typescript
// In handleContinue function
const response = await continueVideo(
  videoId,
  activeCheckpoint.checkpoint_id,
  { force_retry: true }  // Add this parameter
);
```

**Pros**:
- ✅ Explicit intent - clear this is a retry, not a normal continue
- ✅ Backward compatible - existing clients don't send force_retry
- ✅ Self-documenting API
- ✅ Easy to add additional retry-specific logic later

**Cons**:
- ⚠️ Requires API contract change
- ⚠️ Frontend needs to know when to use force_retry vs normal continue
- ⚠️ Still need to handle pipeline restart from approved checkpoint

---

## Recommendation

**Primary Recommendation: Option 1 + Option 4 Combined**

Implement Option 1 (allow retry from approved checkpoints for failed videos) with Option 4's explicit flag for clarity:

```python
def continue_from_checkpoint(video_id, checkpoint_id, force_retry=False):
    checkpoint = get_checkpoint(checkpoint_id)
    video = get_video(video_id)

    # Validation
    if checkpoint.status == "approved":
        # For failed videos, allow retry with explicit flag
        if video.status == "failed" and force_retry:
            logger.info(f"Retrying failed video {video_id} from checkpoint {checkpoint_id}")
            # Don't modify checkpoint - it's already approved
        elif video.status == "failed":
            raise BadRequest("Checkpoint already approved. To retry, use force_retry=true")
        else:
            raise BadRequest("Checkpoint already approved")
    else:
        # Normal flow - approve pending checkpoint
        checkpoint.status = "approved"
        checkpoint.approved_at = now()

    # Clear any previous failure state
    video.status = "processing"
    video.error = None

    continue_pipeline(video_id, checkpoint_id)
```

**Why This Combination**:
- ✅ Clear intent with `force_retry` flag
- ✅ Simple user experience (one click)
- ✅ Preserves checkpoint history
- ✅ Backward compatible
- ✅ Easy to add retry-specific logging/metrics

---

## Implementation Checklist

### Backend Changes

- [ ] Update `/api/video/{video_id}/continue` endpoint:
  - [ ] Add optional `force_retry: bool = False` parameter
  - [ ] Modify checkpoint approval validation
  - [ ] Add logic to clear video failure state on retry
  - [ ] Add logging for retry attempts
- [ ] Update API documentation
- [ ] Add unit tests:
  - [ ] Test retry from approved checkpoint with `force_retry=true`
  - [ ] Test retry fails without `force_retry` flag
  - [ ] Test retry fails when video status is not "failed"
  - [ ] Test normal continue still works for pending checkpoints
- [ ] Add integration tests:
  - [ ] Full retry flow: Phase 2 fails → Retry → Phase 2 restarts
  - [ ] Verify no duplicate artifacts created
  - [ ] Verify checkpoint tree structure

### Frontend Changes

- [ ] Update `api.ts`:
  - [ ] Add `force_retry` parameter to `ContinueRequest` interface
  - [ ] Update `continueVideo` function signature
- [ ] Update `VideoStatus.tsx`:
  - [ ] Modify `handleContinue` to pass `force_retry: true` when retrying from failed video
  - [ ] Differentiate between normal continue and retry continue
- [ ] Update error handling:
  - [ ] Handle "Checkpoint already approved" error gracefully
  - [ ] Show helpful message if retry fails
- [ ] Add tests:
  - [ ] Test retry button appears for failed videos
  - [ ] Test retry button calls API with correct parameters

### Testing Scenarios

1. **Happy Path - Retry Success**:
   - Create video → Phase 1 succeeds → Phase 2 fails
   - Click "Retry from Last Checkpoint"
   - Verify Phase 2 restarts
   - Verify video completes successfully

2. **Multiple Retries**:
   - Phase 2 fails → Retry → Fails again → Retry again
   - Verify each retry works
   - Verify no duplicate work

3. **Edit Then Retry**:
   - Phase 2 fails → Edit Phase 1 → Retry
   - Verify new checkpoint version used
   - Verify Phase 2 uses edited artifacts

4. **Branch Handling**:
   - Phase 2 fails on branch "main"
   - Create new branch from Phase 1
   - Retry on "main" branch
   - Verify both branches work independently

---

## Related Files

### Frontend
- `frontend/src/pages/VideoStatus.tsx:89-113` - handleContinue function
- `frontend/src/lib/api.ts:390-396` - continueVideo API function
- `frontend/src/pages/VideoStatus.tsx:340-423` - Error card with retry button

### Backend (assumed locations)
- `backend/api/video.py` - Continue endpoint
- `backend/models/checkpoint.py` - Checkpoint model
- `backend/services/pipeline.py` - Pipeline continuation logic

### Documentation
- `thoughts/shared/plans/2025-11-21-fix-failed-video-ui-bugs.md` - Original UI improvements plan
- `docs/checkpoint-retry-from-failed-video.md` - This document

---

## Open Questions

1. **Pipeline State**: Can the pipeline cleanly restart from an approved checkpoint, or does it assume checkpoints are only approved once?

2. **Artifact Cleanup**: If a retry creates new artifacts, do we clean up the failed artifacts from the previous attempt?

3. **Cost Tracking**: If a user retries 3 times, should each retry's cost be tracked separately?

4. **Rate Limiting**: Should there be a limit on retry attempts (e.g., max 5 retries per video)?

5. **Branch Behavior**: When retrying, should it always create a new branch, or retry on the same branch?

6. **Status Indicators**: Should the UI show "Retry #2" vs "Retry #1" to indicate multiple retry attempts?

---

## Success Criteria

Implementation is successful when:

1. ✅ User can click "Retry from Last Checkpoint" on a failed video
2. ✅ Video generation restarts from the last successful phase
3. ✅ No "Checkpoint already approved" error
4. ✅ Checkpoint history remains clean and understandable
5. ✅ Multiple retries work without issues
6. ✅ Edit + Retry flow still works
7. ✅ No duplicate artifacts or data corruption

---

## Timeline Estimate

- **Backend Changes**: 2-4 hours
  - API modification: 1 hour
  - Testing: 1-2 hours
  - Code review + fixes: 1 hour

- **Frontend Changes**: 1 hour
  - API client update: 15 min
  - Component update: 15 min
  - Testing: 30 min

- **Total**: 3-5 hours for complete implementation

---

## Contact / Handoff

**Implemented By**: Claude (AI Assistant)
**Date**: 2025-11-21
**Context**: User was testing failed video UI improvements and discovered retry functionality didn't work

**For Questions**:
- Frontend implementation details: See git history for VideoStatus.tsx changes
- Backend requirements: See "Proposed Solutions" section above
- Testing approach: See "Testing Scenarios" section above

**Next Steps**:
1. Review this document with team
2. Decide on solution approach (recommend Option 1 + Option 4)
3. Create backend ticket for API changes
4. Implement backend changes
5. Update frontend to pass `force_retry` flag
6. Test end-to-end retry flow
7. Deploy and monitor retry success rate
