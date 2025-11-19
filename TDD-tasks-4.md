## PR #10: Redis-Based Progress Tracking with Server-Sent Events

**Goal:** Reduce database load by using Redis for mid-pipeline progress tracking and switch status endpoint to Server-Sent Events (SSE) for real-time updates

**OVERVIEW:**

### Current Problem:
- **Database Overload**: Every progress update (dozens per video) writes to PostgreSQL
- **Status Endpoint Polling**: Frontend polls `/api/status/{video_id}` repeatedly, each query hits DB
- **Scaling Issues**: High DB connection usage, slow queries under load
- **Unnecessary Writes**: Mid-pipeline data doesn't need persistence (only final state matters)

### Solution Architecture:

**Redis as Mid-Pipeline Cache:**
- Store all progress/status data in Redis during video generation (TTL: 60 minutes)
- Only write to DB at 3 critical points:
  1. **Video Creation**: Initial record creation when pipeline starts
  2. **Pipeline Failure**: Write error state and cleanup
  3. **Pipeline Completion**: Write final state (all fields) for persistence

**Data Flow:**
```
Pipeline Start → DB Write (create record) → Redis (all updates) → Status Endpoint (checks Redis)
                                                                    ↓
Pipeline Complete → DB Write (final state) → Redis Update (cache until TTL)
                                                                    ↓
Status Endpoint → Redis (if exists) → DB (if Redis expired/missing)
```

**Server-Sent Events (SSE):**
- Replace polling with SSE stream
- Frontend opens connection, receives real-time updates
- Reduces requests from N polls/second to 1 connection per video
- Redis pub/sub

**Redis Key Structure:**
```
video:{video_id}:progress      → Number (0-100)
video:{video_id}:status        → String (queued, validating, complete, failed, etc.)
video:{video_id}:current_phase → String (phase1_validate, phase2_storyboard, etc.)
video:{video_id}:error_message → String (if failed)
video:{video_id}:metadata      → JSON (video_id, title, description, prompt, etc.)
video:{video_id}:phase_outputs → JSON (all phase outputs for frontend - nested structure, same as DB)
video:{video_id}:spec         → JSON (video spec - stored in Redis during pipeline, written to DB only on final submission)
video:{video_id}:presigned_urls → JSON (cached presigned URLs for S3 assets - expires with 60min TTL)
```

**Fallback Strategy:**
- If Redis unavailable: Fall back to DB writes (graceful degradation)
- Status endpoint: Check Redis first, fallback to DB if Redis key missing
- Ensures system continues working even if Redis fails

**Benefits:**
- **Reduced DB Load**: 90%+ reduction in DB writes during pipeline execution
- **Faster Status Checks**: Redis reads are ~10x faster than DB queries
- **Better Scaling**: Redis handles high read/write throughput easily
- **Real-Time Updates**: SSE provides instant updates without polling overhead
- **Cost Effective**: Redis already running (Celery broker), no additional infrastructure

**Scope:**
- ✅ Progress tracking refactored to Redis
- ✅ Status endpoint checks Redis first, DB fallback (re-adds to Redis if DB entry found but Redis missing)
- ✅ Status endpoint converted to SSE (polling-based)
- ✅ Frontend implements SSE stream with automatic fallback to GET endpoint
- ✅ Pipeline writes to DB only at start/failure/completion
- ✅ Spec persisted to DB only on final submission (completion/failure) for testing/debugging
- ✅ StatusResponse schema updated with current_chunk_index and total_chunks
- ✅ Presigned URLs cached in Redis (60min TTL)
- ❌ Migration of existing in-progress videos (out of scope)

**Files to Modify:**
- `backend/app/services/redis.py` (NEW - Redis client wrapper)
- `backend/app/orchestrator/progress.py` (Refactor to use Redis)
- `backend/app/api/status.py` (Check Redis, convert to SSE, re-add to Redis if missing)
- `backend/app/orchestrator/pipeline.py` (DB writes only at start/failure/completion)
- `backend/app/common/schemas.py` (Add current_chunk_index and total_chunks to StatusResponse)
- `frontend/src/` (Status polling components - implement SSE with fallback)
- All phase tasks (update to use new progress tracking)

**NEW DEPENDENCY:**
- None (Redis client already in requirements: `redis==5.0.1`)

---

### Task 10.1: Create Redis Service Client

**File:** `backend/app/services/redis.py` (NEW)

**Goal:** Create a reusable Redis client wrapper for video progress tracking with proper error handling and fallback.

- [ ] Create `backend/app/services/redis.py`:
  - Import `redis` client library
  - Import `settings` from `app.config`
  - Create `RedisClient` class (singleton pattern)

- [ ] Implement Redis connection:
  ```python
  class RedisClient:
      _instance = None
      _client = None
      
      def __new__(cls):
          if cls._instance is None:
              cls._instance = super().__new__(cls)
          return cls._instance
      
      def __init__(self):
          if self._client is None:
              try:
                  self._client = redis.from_url(settings.redis_url, decode_responses=True)
                  # Test connection
                  self._client.ping()
              except Exception as e:
                  logger.error(f"Failed to connect to Redis: {e}")
                  self._client = None
  ```

- [ ] Implement helper methods:
  - `set_video_progress(video_id, progress)` - Set progress (0-100)
  - `set_video_status(video_id, status)` - Set status string
  - `set_video_phase(video_id, phase)` - Set current phase
  - `set_video_metadata(video_id, metadata_dict)` - Set video metadata
  - `set_video_phase_outputs(video_id, phase_outputs_dict)` - Set phase outputs
  - `set_video_spec(video_id, spec_dict)` - Set video spec
  - `set_video_presigned_urls(video_id, urls_dict)` - Cache presigned URLs for S3 assets
  - `get_video_data(video_id)` - Get all video data as dict
  - `delete_video_data(video_id)` - Delete all keys for video (cleanup)
  - All methods should set TTL: 3600 seconds (60 minutes)

- [ ] Implement error handling:
  - Wrap all Redis operations in try/except
  - Log errors but don't raise (graceful degradation)
  - Return None/False on failure (caller can fallback to DB)

- [ ] Implement TTL management:
  - Use `EX` parameter in SET commands: `client.set(key, value, ex=3600)`
  - Or use `EXPIRE` after SET: `client.expire(key, 3600)`
  - Ensure all keys have 60-minute TTL (no refresh logic - fixed TTL)

- [ ] Test Redis connection:
  - Test connection on import
  - Test all helper methods
  - Test TTL expiration
  - Test error handling (disconnect Redis, verify graceful failure)

---

### Task 10.2: Refactor Progress Tracking to Use Redis

**File:** `backend/app/orchestrator/progress.py`

**Goal:** Update `update_progress()` to write to Redis instead of DB, with DB fallback.

- [ ] Import Redis client:
  ```python
  from app.services.redis import RedisClient
  redis_client = RedisClient()
  ```

- [ ] Refactor `update_progress()` function:
  - Keep same signature: `update_progress(video_id, status, progress, **kwargs)`
  - Write to Redis first (if Redis available)
  - Fallback to DB write if Redis fails
  - Structure:
    ```python
    def update_progress(video_id, status, progress, **kwargs):
        # Try Redis first
        if redis_client._client:
            try:
                # Set progress, status, phase in Redis
                redis_client.set_video_progress(video_id, progress)
                redis_client.set_video_status(video_id, status)
                if 'current_phase' in kwargs:
                    redis_client.set_video_phase(video_id, kwargs['current_phase'])
                # ... set other fields
            except Exception as e:
                logger.warning(f"Redis update failed, falling back to DB: {e}")
                # Fall through to DB write
        
        # Fallback to DB (always write if Redis failed or unavailable)
        if not redis_client._client or <redis_write_failed>:
            # Existing DB write logic (keep as-is)
            # ...
    ```

- [ ] Update metadata storage:
  - Store `title`, `prompt`, `description` in Redis metadata
  - Store `error_message` in Redis
  - Store `phase_outputs` in Redis as nested JSON (same structure as DB, for retry logic)

- [ ] Keep DB writes for critical updates:
  - Still write to DB if this is initial creation (video doesn't exist)
  - Still write to DB if status is "complete" or "failed" (final states)
  - This ensures DB always has final state even if Redis expires
  - **Complete fallback**: If Redis fails, fall back to DB for all operations (all or nothing approach)

- [ ] Update `update_cost()` function:
  - Store cost in Redis metadata
  - Still update DB cost_breakdown (for final persistence)

- [ ] Test progress tracking:
  - Verify Redis writes work
  - Verify DB fallback works when Redis unavailable (complete fallback, not partial)
  - Verify TTL expiration (wait 60 minutes, check keys deleted)
  - Verify concurrent updates don't conflict

---

### Task 10.3: Update StatusResponse Schema

**File:** `backend/app/common/schemas.py`

**Goal:** Add current_chunk_index and total_chunks fields to StatusResponse schema.

- [ ] Update StatusResponse model:
  ```python
  class StatusResponse(BaseModel):
      """Response from status endpoint"""
      video_id: str
      status: str
      progress: float
      current_phase: Optional[str]
      estimated_time_remaining: Optional[int]
      error: Optional[str]
      animatic_urls: Optional[List[str]] = None
      reference_assets: Optional[Dict] = None
      stitched_video_url: Optional[str] = None
      final_video_url: Optional[str] = None
      current_chunk_index: Optional[int] = None  # NEW: Current chunk being processed in Phase 4
      total_chunks: Optional[int] = None  # NEW: Total number of chunks in Phase 4
  ```

- [ ] Verify schema matches current status endpoint usage:
  - Check that status endpoint already extracts these fields from phase_outputs
  - Ensure schema matches implementation

---

### Task 10.4: Update Status Endpoint to Check Redis First

**File:** `backend/app/api/status.py`

**Goal:** Modify status endpoint to check Redis first, fallback to DB if Redis key missing. Re-add to Redis if DB entry exists but Redis doesn't.

- [ ] Import Redis client:
  ```python
  from app.services.redis import RedisClient
  redis_client = RedisClient()
  ```

- [ ] Refactor `get_status()` function:
  - Check Redis first: `redis_client.get_video_data(video_id)`
  - If Redis data exists: Use it to build StatusResponse
  - If Redis data missing: Fallback to DB query (existing logic)
  - **NEW**: If DB entry found but Redis missing, re-add to Redis with 60min TTL
  - Structure:
    ```python
    @router.get("/api/status/{video_id}")
    async def get_status(video_id: str, db: Session = Depends(get_db)) -> StatusResponse:
        # Try Redis first
        redis_data = None
        if redis_client._client:
            try:
                redis_data = redis_client.get_video_data(video_id)
            except Exception as e:
                logger.warning(f"Redis read failed, using DB: {e}")
        
        if redis_data:
            # Build StatusResponse from Redis data
            return StatusResponse(
                video_id=redis_data['video_id'],
                status=redis_data['status'],
                progress=redis_data['progress'],
                # ... extract from Redis
            )
        else:
            # Fallback to DB (existing logic)
            video = db.query(VideoGeneration).filter(...).first()
            
            if video:
                # Re-add to Redis if DB entry exists but Redis doesn't
                if redis_client._client:
                    try:
                        # Reconstruct Redis data from DB entry
                        redis_client.set_video_progress(video_id, video.progress)
                        redis_client.set_video_status(video_id, video.status.value)
                        # ... populate all Redis keys from DB
                    except Exception as e:
                        logger.warning(f"Failed to re-add to Redis: {e}")
            
            # ... existing DB logic to build StatusResponse
    ```

- [ ] Handle Redis data structure:
  - Extract progress, status, current_phase from Redis
  - Extract metadata (title, description, etc.)
  - Extract phase_outputs (convert to StatusResponse format)
  - Use cached presigned URLs from Redis if available, otherwise generate and cache

- [ ] Implement presigned URL caching:
  - Check Redis for cached presigned URLs first
  - If missing, generate presigned URLs (same as current logic)
  - Cache generated URLs in Redis with 60min TTL
  - Use cached URLs in subsequent requests

- [ ] Maintain backward compatibility:
  - If Redis missing, DB query should work exactly as before
  - Ensure all StatusResponse fields are populated from either source

- [ ] Test status endpoint:
  - Test with Redis data (video in progress)
  - Test with DB fallback (Redis expired or missing)
  - Test re-adding to Redis when DB entry found
  - Test presigned URL caching (verify URLs cached and reused)
  - Test with video not found (404)
  - Test error handling (Redis connection failure)

---

### Task 10.5: Convert Status Endpoint to Server-Sent Events (SSE)

**File:** `backend/app/api/status.py`

**Goal:** Replace polling endpoint with SSE stream for real-time updates using polling-based approach.

- [ ] Add SSE dependencies:
  ```python
  from fastapi.responses import StreamingResponse
  import asyncio
  import json
  ```

- [ ] Create SSE endpoint:
  ```python
  @router.get("/api/status/{video_id}/stream")
  async def stream_status(video_id: str, db: Session = Depends(get_db)):
      """Server-Sent Events stream for real-time status updates (polling-based)"""
      async def event_generator():
          last_data = None
          while True:
              # Check Redis for updates (same logic as GET endpoint)
              redis_data = None
              if redis_client._client:
                  try:
                      redis_data = redis_client.get_video_data(video_id)
                  except Exception as e:
                      logger.warning(f"Redis read failed in SSE: {e}")
              
              # Fallback to DB if Redis missing
              if not redis_data:
                  video = db.query(VideoGeneration).filter(...).first()
                  if video:
                      # Re-add to Redis (same as GET endpoint)
                      # ... re-add logic ...
                      # Build redis_data from video
              
              # Only send event if data changed
              if redis_data and redis_data != last_data:
                  # Build StatusResponse from Redis/DB data
                  status_response = build_status_response(redis_data or video)
                  
                  # Format as SSE event
                  yield f"data: {json.dumps(status_response.dict())}\n\n"
                  last_data = redis_data
              
              # Check if complete or failed (stop streaming)
              if redis_data and redis_data.get('status') in ['complete', 'failed']:
                  yield "event: close\ndata: {}\n\n"
                  break
              
              # Poll every 1-2 seconds
              await asyncio.sleep(1.5)
      
      return StreamingResponse(
          event_generator(),
          media_type="text/event-stream",
          headers={
              "Cache-Control": "no-cache",
              "Connection": "keep-alive",
          }
      )
  ```

- [ ] Extract common status building logic:
  - Create helper function `build_status_response()` that both GET and SSE endpoints use
  - Handles Redis/DB data extraction and StatusResponse construction
  - Handles presigned URL caching/generation

- [ ] Keep existing GET endpoint:
  - Keep `/api/status/{video_id}` for compatibility (fallback only)
  - Frontend will use SSE primarily, GET endpoint only if SSE fails
  - Both endpoints check Redis first, DB fallback
  - Both endpoints use same status building logic

- [ ] Handle connection cleanup:
  - Handle client disconnection gracefully (FastAPI handles this automatically)
  - Log connection events (connect/disconnect)
  - Ensure no resource leaks

- [ ] Test SSE endpoint:
  - Test SSE stream with video in progress
  - Test stream updates in real-time (verify events sent on changes)
  - Test stream closes when video completes
  - Test multiple concurrent streams (different video_ids)
  - Test client disconnection handling
  - Test Redis fallback in SSE stream

---

### Task 10.6: Update Pipeline to Write DB Only at Critical Points

**File:** `backend/app/orchestrator/pipeline.py`

**Goal:** Ensure pipeline only writes to DB at start, failure, and completion.

- [ ] Review current pipeline implementation:
  - Identify all DB write locations
  - Document which writes are critical vs. mid-pipeline

- [ ] Update pipeline start:
  - Keep DB write for initial video creation
  - Write to Redis immediately after DB write
  - Ensure spec is written to both DB and Redis

- [ ] Update pipeline failure handling:
  - On failure: Write error state to DB (final state)
  - Also update Redis (for immediate status endpoint access)
  - Clean up Redis keys after DB write (optional, or let TTL expire)

- [ ] Update pipeline completion:
  - On completion: Write all final data to DB
  - Update Redis with final state (cache until TTL expires)
  - Ensure all fields written: final_video_url, cost, phase_outputs, etc.

- [ ] Remove mid-pipeline DB writes:
  - Remove DB writes from `update_progress()` calls (now Redis-only)
  - Keep DB writes only for:
    1. Initial creation (pipeline start)
    2. Final state (completion)
    3. Error state (failure)
  - All other updates go to Redis only

- [ ] Update phase tasks:
  - Ensure all phases use `update_progress()` (which now writes to Redis)
  - Remove any direct DB writes from phase tasks
  - Keep phase_outputs storage in Redis (not DB until completion)

- [ ] Test pipeline execution:
  - Test video creation (DB write + Redis write)
  - Test mid-pipeline updates (Redis only, no DB writes)
  - Test completion (DB write + Redis update)
  - Test failure (DB write + Redis update)
  - Verify DB only has 3 writes per video (start, completion/failure)

---

### Task 10.7: Handle Spec Persistence to DB

**File:** `backend/app/orchestrator/pipeline.py`, `backend/app/orchestrator/progress.py`

**Goal:** Ensure spec is persisted to DB only on final submission (completion/failure) for testing/debugging purposes.

- [ ] Update spec storage strategy:
  - **During pipeline**: Store spec in Redis only (for status endpoint access)
  - **On completion/failure**: Write spec to DB (final submission)
  - **On pipeline start**: Do NOT write spec to DB (only create video record)

- [ ] Update `update_progress()`:
  - If `spec` in kwargs: Write to Redis only (not DB)
  - Spec goes to Redis during pipeline execution
  - Other fields (progress, status, phase_outputs) also go to Redis only

- [ ] Update pipeline completion/failure handlers:
  - On completion: Write spec to DB along with final state
  - On failure: Write spec to DB along with error state
  - This ensures spec is in DB for testing/debugging after pipeline finishes

- [ ] Test spec persistence:
  - Verify spec in Redis during pipeline (status endpoint access)
  - Verify spec NOT in DB during pipeline (only after completion/failure)
  - Verify spec in DB after completion
  - Verify spec in DB after failure

---

### Task 10.8: Frontend Integration - SSE with Fallback

**File:** `frontend/src/` (status polling components)

**Goal:** Implement SSE stream for real-time status updates with automatic fallback to GET endpoint if SSE fails.

- [ ] Identify current status polling implementation:
  - Find component(s) that poll `/api/status/{video_id}`
  - Document current polling interval and logic
  - Identify where status updates are handled in UI

- [ ] Create SSE connection hook/utility:
  - Create `useVideoStatusStream(videoId)` hook or utility function
  - Use `EventSource` API to connect to `/api/status/{video_id}/stream`
  - Handle SSE events: `onmessage`, `onerror`, `onopen`
  - Structure:
    ```typescript
    const useVideoStatusStream = (videoId: string) => {
      const [status, setStatus] = useState<StatusResponse | null>(null);
      const [error, setError] = useState<Error | null>(null);
      
      useEffect(() => {
        const eventSource = new EventSource(`/api/status/${videoId}/stream`);
        
        eventSource.onmessage = (event) => {
          const data = JSON.parse(event.data) as StatusResponse;
          setStatus(data);
        };
        
        eventSource.onerror = () => {
          // SSE failed, fallback to polling
          eventSource.close();
          // Trigger fallback polling
        };
        
        return () => eventSource.close();
      }, [videoId]);
      
      return { status, error };
    };
    ```

- [ ] Implement fallback to GET endpoint:
  - If SSE connection fails (`onerror`), automatically fallback to polling
  - Use existing GET endpoint: `/api/status/{video_id}`
  - Poll interval: 2-3 seconds (reduced from current)
  - Log fallback event for debugging

- [ ] Update status display components:
  - Replace current polling logic with SSE hook
  - Handle SSE stream updates in real-time
  - Handle fallback polling if SSE unavailable
  - Ensure UI updates smoothly with both approaches

- [ ] Handle SSE stream closure:
  - When status is "complete" or "failed", SSE stream closes
  - Detect closure event and stop any fallback polling
  - Update UI to show final state

- [ ] Error handling:
  - Handle SSE connection errors gracefully
  - Handle network disconnections
  - Handle invalid video_id (404 errors)
  - Show appropriate error messages to user

- [ ] Test frontend implementation:
  - Test SSE stream with video in progress (real-time updates)
  - Test SSE fallback when stream fails (should switch to polling)
  - Test SSE stream closure on completion
  - Test multiple concurrent video status streams
  - Test error scenarios (network failure, invalid video_id)

**Key Points:**
- **Primary**: Use SSE stream (`/api/status/{video_id}/stream`) for real-time updates
- **Fallback**: Only use GET endpoint (`/api/status/{video_id}`) if SSE fails
- **Same Data**: StatusResponse schema unchanged, frontend handles same data structure
- **Automatic**: Fallback should happen automatically, user shouldn't notice

---

### Task 10.9: Testing and Verification

**Goal:** Comprehensive testing of Redis-based progress tracking and SSE.

- [ ] Test Redis operations:
  - Test all Redis helper methods
  - Test TTL expiration (wait 60 minutes, or use shorter TTL for testing)
  - Test concurrent writes (multiple phases updating same video)
  - Test Redis connection failure (complete fallback to DB)

- [ ] Test progress tracking:
  - Create video, verify Redis write
  - Update progress multiple times, verify Redis updates
  - Complete video, verify DB write + Redis update
  - Fail video, verify DB write + Redis update

- [ ] Test status endpoint:
  - Test Redis-first lookup (video in progress)
  - Test DB fallback (Redis expired)
  - Test video not found (404)
  - Test error handling (Redis down, DB works)

- [ ] Test SSE endpoint:
  - Test SSE stream with video in progress
  - Test stream updates in real-time
  - Test stream closes on completion
  - Test multiple concurrent streams
  - Test client disconnection

- [ ] Test pipeline execution:
  - Run full pipeline, verify DB writes only at start/completion
  - Monitor DB connection usage (should be much lower)
  - Monitor Redis memory usage (should be reasonable with 60min TTL)
  - Verify status endpoint works throughout pipeline
  - Verify spec NOT in DB during pipeline, only after completion

- [ ] Performance testing:
  - Measure DB write reduction (should be 90%+)
  - Measure status endpoint latency (Redis vs DB)
  - Measure SSE connection overhead
  - Verify system handles high concurrent video generation

- [ ] Edge case testing:
  - Test Redis TTL expiration during pipeline (should fallback to DB, re-add to Redis)
  - Test Redis connection loss (should fallback to DB completely)
  - Test video completion while SSE stream active (stream should close gracefully)
  - Test multiple status requests for same video (presigned URLs should be cached)
  - Test re-adding to Redis when DB entry found (verify 60min TTL set)

---

**Key Implementation Notes:**
1. **Redis TTL**: 60 minutes (3600 seconds) for all video keys (no refresh logic - fixed TTL)
2. **DB Writes**: Only at start, failure, completion (3 writes per video)
3. **Fallback Strategy**: Complete fallback to DB if Redis unavailable (all or nothing, not partial)
4. **Spec Persistence**: Write to Redis during pipeline, write to DB only on final submission (completion/failure)
5. **SSE Implementation**: Polling-based (check Redis every 1-2 seconds)
6. **Status Endpoint**: Re-adds to Redis if DB entry found but Redis missing (60min TTL)
7. **Presigned URLs**: Cached in Redis (60min TTL) to avoid regenerating on each request
8. **Phase Outputs**: Stored as nested JSON in Redis (same structure as DB, for retry logic)
9. **StatusResponse Schema**: Includes current_chunk_index and total_chunks fields
10. **Backward Compatibility**: Existing GET endpoint still works (checks Redis first, DB fallback) - used as fallback if SSE fails
11. **Frontend Implementation**: SSE stream is primary, GET endpoint only used as fallback
11. **Error Handling**: Graceful degradation (Redis failure doesn't break system)
12. **Redis Connection**: Uses same Redis instance as Celery (via settings.redis_url)