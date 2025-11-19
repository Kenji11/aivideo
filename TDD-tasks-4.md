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
- Store all progress/status data in Redis during video generation (TTL: 10 minutes)
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
- Standard approach: Redis pub/sub for push notifications (or polling fallback)

**Redis Key Structure:**
```
video:{video_id}:progress      → Number (0-100)
video:{video_id}:status        → String (queued, validating, complete, failed, etc.)
video:{video_id}:current_phase → String (phase1_validate, phase2_storyboard, etc.)
video:{video_id}:error_message → String (if failed)
video:{video_id}:metadata      → JSON (video_id, title, description, prompt, etc.)
video:{video_id}:phase_outputs → JSON (all phase outputs for frontend)
video:{video_id}:spec         → JSON (video spec - also persisted to DB for testing)
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
- ✅ Status endpoint checks Redis first, DB fallback
- ✅ Status endpoint converted to SSE
- ✅ Pipeline writes to DB only at start/failure/completion
- ✅ Spec still persisted to DB (for testing/debugging)
- ❌ Migration of existing in-progress videos (out of scope)

**Files to Modify:**
- `backend/app/services/redis.py` (NEW - Redis client wrapper)
- `backend/app/orchestrator/progress.py` (Refactor to use Redis)
- `backend/app/api/status.py` (Check Redis, convert to SSE)
- `backend/app/orchestrator/pipeline.py` (DB writes only at start/failure/completion)
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
  - `get_video_data(video_id)` - Get all video data as dict
  - `delete_video_data(video_id)` - Delete all keys for video (cleanup)
  - All methods should set TTL: 600 seconds (10 minutes)

- [ ] Implement error handling:
  - Wrap all Redis operations in try/except
  - Log errors but don't raise (graceful degradation)
  - Return None/False on failure (caller can fallback to DB)

- [ ] Implement TTL management:
  - Use `EX` parameter in SET commands: `client.set(key, value, ex=600)`
  - Or use `EXPIRE` after SET: `client.expire(key, 600)`
  - Ensure all keys have 10-minute TTL

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
  - Store `phase_outputs` in Redis (for frontend access)

- [ ] Keep DB writes for critical updates:
  - Still write to DB if this is initial creation (video doesn't exist)
  - Still write to DB if status is "complete" or "failed" (final states)
  - This ensures DB always has final state even if Redis expires

- [ ] Update `update_cost()` function:
  - Store cost in Redis metadata
  - Still update DB cost_breakdown (for final persistence)

- [ ] Test progress tracking:
  - Verify Redis writes work
  - Verify DB fallback works when Redis unavailable
  - Verify TTL expiration (wait 10 minutes, check keys deleted)
  - Verify concurrent updates don't conflict

---

### Task 10.3: Update Status Endpoint to Check Redis First

**File:** `backend/app/api/status.py`

**Goal:** Modify status endpoint to check Redis first, fallback to DB if Redis key missing.

- [ ] Import Redis client:
  ```python
  from app.services.redis import RedisClient
  redis_client = RedisClient()
  ```

- [ ] Refactor `get_status()` function:
  - Check Redis first: `redis_client.get_video_data(video_id)`
  - If Redis data exists: Use it to build StatusResponse
  - If Redis data missing: Fallback to DB query (existing logic)
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
            # ... existing DB logic
    ```

- [ ] Handle Redis data structure:
  - Extract progress, status, current_phase from Redis
  - Extract metadata (title, description, etc.)
  - Extract phase_outputs (convert to StatusResponse format)
  - Handle presigned URL generation for S3 URLs (same as DB logic)

- [ ] Maintain backward compatibility:
  - If Redis missing, DB query should work exactly as before
  - Ensure all StatusResponse fields are populated from either source

- [ ] Test status endpoint:
  - Test with Redis data (video in progress)
  - Test with DB fallback (Redis expired or missing)
  - Test with video not found (404)
  - Test error handling (Redis connection failure)

---

### Task 10.4: Convert Status Endpoint to Server-Sent Events (SSE)

**File:** `backend/app/api/status.py`

**Goal:** Replace polling endpoint with SSE stream for real-time updates.

- [ ] Add SSE dependencies:
  ```python
  from fastapi.responses import StreamingResponse
  import asyncio
  import json
  ```

- [ ] Create SSE endpoint:
  ```python
  @router.get("/api/status/{video_id}/stream")
  async def stream_status(video_id: str):
      """Server-Sent Events stream for real-time status updates"""
      async def event_generator():
          while True:
              # Check Redis for updates
              redis_data = redis_client.get_video_data(video_id)
              
              if redis_data:
                  # Format as SSE event
                  data = {
                      'video_id': redis_data['video_id'],
                      'status': redis_data['status'],
                      'progress': redis_data['progress'],
                      # ... all StatusResponse fields
                  }
                  yield f"data: {json.dumps(data)}\n\n"
              
              # Check if complete or failed (stop streaming)
              if redis_data and redis_data['status'] in ['complete', 'failed']:
                  yield "event: close\ndata: {}\n\n"
                  break
              
              # Poll every 1 second (or use Redis pub/sub if implemented)
              await asyncio.sleep(1)
      
      return StreamingResponse(
          event_generator(),
          media_type="text/event-stream",
          headers={
              "Cache-Control": "no-cache",
              "Connection": "keep-alive",
          }
      )
  ```

- [ ] Implement Redis pub/sub (optional enhancement):
  - Subscribe to Redis channel: `video:{video_id}:updates`
  - Publish updates in `update_progress()`: `redis_client.publish(f"video:{video_id}:updates", json.dumps(data))`
  - Use pub/sub in SSE stream instead of polling
  - Fallback to polling if pub/sub unavailable

- [ ] Keep existing GET endpoint:
  - Keep `/api/status/{video_id}` for compatibility
  - Frontend can choose: SSE stream or polling
  - Both endpoints check Redis first, DB fallback

- [ ] Handle connection cleanup:
  - Close Redis pub/sub connection on client disconnect
  - Handle client disconnection gracefully
  - Log connection events

- [ ] Test SSE endpoint:
  - Test SSE stream with video in progress
  - Test stream closes when video completes
  - Test multiple concurrent streams
  - Test client disconnection handling

---

### Task 10.5: Update Pipeline to Write DB Only at Critical Points

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

### Task 10.6: Handle Spec Persistence to DB

**File:** `backend/app/orchestrator/pipeline.py`, `backend/app/orchestrator/progress.py`

**Goal:** Ensure spec is persisted to DB (for testing) while other data uses Redis.

- [ ] Update spec storage:
  - Write spec to DB when video is created (pipeline start)
  - Also write spec to Redis (for status endpoint access)
  - Update spec in DB if it changes during pipeline (rare, but handle it)

- [ ] Update `update_progress()`:
  - If `spec` in kwargs: Write to both Redis and DB
  - This ensures spec is always in DB for testing/debugging
  - Other fields (progress, status, phase_outputs) go to Redis only

- [ ] Test spec persistence:
  - Verify spec in DB after video creation
  - Verify spec in Redis during pipeline
  - Verify spec accessible from status endpoint (from Redis)
  - Verify spec in DB after completion

---

### Task 10.7: Frontend Integration (Optional - Document Only)

**File:** Documentation only (frontend changes out of scope for this PR)

**Goal:** Document frontend changes needed to use SSE endpoint.

- [ ] Document SSE endpoint usage:
  - Endpoint: `GET /api/status/{video_id}/stream`
  - Response: Server-Sent Events stream
  - Example frontend code:
    ```typescript
    const eventSource = new EventSource(`/api/status/${videoId}/stream`);
    eventSource.onmessage = (event) => {
      const data = JSON.parse(event.data);
      // Update UI with status, progress, etc.
    };
    eventSource.onerror = () => {
      // Handle error, fallback to polling
    };
    ```

- [ ] Document fallback strategy:
  - If SSE unavailable: Fallback to polling `/api/status/{video_id}`
  - Poll interval: 2-3 seconds (reduced from current)
  - Both endpoints check Redis first, DB fallback

- [ ] Document status response format:
  - Same StatusResponse schema (no changes)
  - Frontend code doesn't need changes (same data structure)
  - Only change: Use SSE stream instead of polling

---

### Task 10.8: Testing and Verification

**Goal:** Comprehensive testing of Redis-based progress tracking and SSE.

- [ ] Test Redis operations:
  - Test all Redis helper methods
  - Test TTL expiration (wait 10 minutes)
  - Test concurrent writes (multiple phases updating same video)
  - Test Redis connection failure (fallback to DB)

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
  - Monitor Redis memory usage (should be reasonable with 10min TTL)
  - Verify status endpoint works throughout pipeline

- [ ] Performance testing:
  - Measure DB write reduction (should be 90%+)
  - Measure status endpoint latency (Redis vs DB)
  - Measure SSE connection overhead
  - Verify system handles high concurrent video generation

- [ ] Edge case testing:
  - Test Redis TTL expiration during pipeline (should fallback to DB)
  - Test Redis connection loss (should fallback to DB)
  - Test video completion while SSE stream active
  - Test multiple status requests for same video

---

**Key Implementation Notes:**
1. **Redis TTL**: 10 minutes (600 seconds) for all video keys
2. **DB Writes**: Only at start, failure, completion (3 writes per video)
3. **Fallback Strategy**: Always fallback to DB if Redis unavailable
4. **Spec Persistence**: Write to both DB and Redis (for testing)
5. **SSE Implementation**: Polling-based (can enhance with pub/sub later)
6. **Backward Compatibility**: Existing GET endpoint still works (checks Redis first)
7. **Error Handling**: Graceful degradation (Redis failure doesn't break system)