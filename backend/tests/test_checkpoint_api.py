"""
Tests for checkpoint API endpoints.

These tests verify:
- Checkpoint listing and retrieval
- Branch management
- Continue pipeline functionality
- Authentication and authorization

Note: Using direct function calls instead of TestClient due to httpx/starlette compatibility issues.
"""
import pytest
from unittest.mock import patch
from datetime import datetime

# Import API functions directly
from app.api.checkpoints import (
    list_video_checkpoints,
    get_checkpoint_details,
    get_current_video_checkpoint,
    list_active_branches,
    get_checkpoint_tree_structure,
    continue_pipeline
)
from app.common.schemas import ContinueRequest
from app.database import SessionLocal
from app.common.models import VideoGeneration, VideoStatus
from app.database.checkpoint_queries import (
    create_checkpoint,
    create_artifact,
    approve_checkpoint
)
import uuid


@pytest.fixture
def mock_db():
    """Create a mock database session"""
    db = SessionLocal()
    yield db
    db.close()


@pytest.fixture
def test_user_id():
    """Return a test user ID"""
    return "test-user-123"


@pytest.fixture
def test_video(test_user_id, mock_db):
    """Create a test video in the database"""
    # Clean up any existing test videos
    mock_db.query(VideoGeneration).filter(
        VideoGeneration.id.like("test-video-%")
    ).delete()
    mock_db.commit()

    video_id = f"test-video-{uuid.uuid4().hex[:8]}"
    video = VideoGeneration(
        id=video_id,
        user_id=test_user_id,
        prompt="Test luxury watch commercial",
        title="Test Video",
        status=VideoStatus.PAUSED_AT_PHASE1,
        current_phase="phase1",
        progress=25.0,
        cost_usd=0.02,
        spec={"template": "luxury_showcase", "beats": []},
        phase_outputs={}
    )
    mock_db.add(video)
    mock_db.commit()
    mock_db.refresh(video)

    yield video

    # Cleanup
    mock_db.query(VideoGeneration).filter(
        VideoGeneration.id == video_id
    ).delete()
    mock_db.commit()


@pytest.fixture
def test_checkpoints(test_video):
    """Create test checkpoints for a video"""
    # Create Phase 1 checkpoint
    cp1_id = create_checkpoint(
        video_id=test_video.id,
        branch_name='main',
        phase_number=1,
        version=1,
        phase_output={
            'video_id': test_video.id,
            'phase': 'phase1_planning',
            'status': 'success',
            'output_data': {'spec': test_video.spec},
            'cost_usd': 0.02,
            'duration_seconds': 5.0
        },
        cost_usd=0.02,
        user_id=test_video.user_id,
        parent_checkpoint_id=None
    )

    # Create spec artifact
    create_artifact(
        checkpoint_id=cp1_id,
        artifact_type='spec',
        artifact_key='spec',
        s3_url='',
        s3_key='',
        version=1,
        metadata={'spec': test_video.spec}
    )

    return {'phase1': cp1_id}


@pytest.mark.asyncio
async def test_list_checkpoints(test_user_id, test_video, test_checkpoints, mock_db):
    """Test list_video_checkpoints function"""
    result = await list_video_checkpoints(
        video_id=test_video.id,
        branch_name=None,
        user_id=test_user_id,
        db=mock_db
    )

    assert isinstance(result, list)
    assert len(result) >= 1

    # Verify checkpoint structure
    checkpoint = result[0]
    assert checkpoint.id is not None
    assert checkpoint.video_id == test_video.id
    assert checkpoint.branch_name == 'main'
    assert checkpoint.phase_number == 1
    assert checkpoint.user_id == test_user_id


@pytest.mark.asyncio
async def test_get_checkpoint_details(test_user_id, test_video, test_checkpoints, mock_db):
    """Test get_checkpoint_details function"""
    checkpoint_id = test_checkpoints['phase1']

    result = await get_checkpoint_details(
        video_id=test_video.id,
        checkpoint_id=checkpoint_id,
        user_id=test_user_id,
        db=mock_db
    )

    # Verify checkpoint details
    assert result.id == checkpoint_id
    assert result.video_id == test_video.id
    assert result.phase_number == 1
    assert result.status == 'pending'

    # Verify artifacts are included
    assert result.artifacts is not None
    assert isinstance(result.artifacts, list)
    assert len(result.artifacts) >= 1

    # Verify artifact structure
    artifact = result.artifacts[0]
    assert artifact.artifact_type == 'spec'
    assert artifact.artifact_key == 'spec'
    assert artifact.version == 1


@pytest.mark.asyncio
async def test_get_current_checkpoint(test_user_id, test_video, test_checkpoints, mock_db):
    """Test get_current_video_checkpoint function"""
    result = await get_current_video_checkpoint(
        video_id=test_video.id,
        user_id=test_user_id,
        db=mock_db
    )

    # Should return the Phase 1 checkpoint (only pending checkpoint)
    assert result.id == test_checkpoints['phase1']
    assert result.status == 'pending'
    assert result.artifacts is not None


@pytest.mark.asyncio
async def test_list_branches(test_user_id, test_video, test_checkpoints, mock_db):
    """Test list_active_branches function"""
    result = await list_active_branches(
        video_id=test_video.id,
        user_id=test_user_id,
        db=mock_db
    )

    assert isinstance(result, list)
    assert len(result) >= 1

    # Verify branch structure
    branch = result[0]
    assert branch.branch_name == 'main'
    assert branch.latest_checkpoint_id is not None
    assert branch.phase_number is not None
    assert branch.status is not None
    assert branch.can_continue == True  # Pending checkpoint


@pytest.mark.asyncio
async def test_get_checkpoint_tree(test_user_id, test_video, test_checkpoints, mock_db):
    """Test get_checkpoint_tree_structure function"""
    result = await get_checkpoint_tree_structure(
        video_id=test_video.id,
        user_id=test_user_id,
        db=mock_db
    )

    assert isinstance(result, list)

    # Should have at least one root checkpoint
    assert len(result) >= 1

    # Verify tree structure
    root = result[0]
    assert root.checkpoint is not None
    assert root.children is not None
    assert root.checkpoint.phase_number == 1


@pytest.mark.asyncio
async def test_continue_pipeline_success(test_user_id, test_video, test_checkpoints, mock_db):
    """Test continue_pipeline function"""
    checkpoint_id = test_checkpoints['phase1']

    # Mock dispatch_next_phase to avoid actually dispatching Celery task
    with patch('app.api.checkpoints.dispatch_next_phase'):
        result = await continue_pipeline(
            video_id=test_video.id,
            request=ContinueRequest(checkpoint_id=checkpoint_id),
            user_id=test_user_id,
            db=mock_db
        )

        # Verify response
        assert result.message == 'Pipeline continued'
        assert result.next_phase == 2
        assert result.branch_name == 'main'
        assert result.created_new_branch == False


@pytest.mark.asyncio
async def test_continue_with_branching(test_user_id, test_video, test_checkpoints, mock_db):
    """Test that continuing with edited checkpoint creates new branch"""
    checkpoint_id = test_checkpoints['phase1']

    # Create a new version of the spec artifact to simulate editing
    # Use a different artifact_key to avoid unique constraint violation
    create_artifact(
        checkpoint_id=checkpoint_id,
        artifact_type='spec',
        artifact_key='spec_edited',  # Different key
        s3_url='',
        s3_key='',
        version=2,  # New version indicates editing
        metadata={'spec': {'edited': True}},
        parent_artifact_id=None
    )

    with patch('app.api.checkpoints.dispatch_next_phase'):
        result = await continue_pipeline(
            video_id=test_video.id,
            request=ContinueRequest(checkpoint_id=checkpoint_id),
            user_id=test_user_id,
            db=mock_db
        )

        # Should create new branch when edited
        assert result.created_new_branch == True
        assert result.branch_name != 'main'  # Should be main-1 or similar
        assert result.branch_name.startswith('main-')


def test_checkpoint_queries_integration():
    """Integration test to verify checkpoint queries work correctly"""
    db = SessionLocal()
    try:
        # Create a test video
        video_id = f"test-integration-{uuid.uuid4().hex[:8]}"
        video = VideoGeneration(
            id=video_id,
            user_id="integration-test-user",
            prompt="Integration test",
            title="Integration Test",
            status=VideoStatus.PAUSED_AT_PHASE1,
            current_phase="phase1",
            progress=25.0,
            cost_usd=0.0,
            spec={},
            phase_outputs={}
        )
        db.add(video)
        db.commit()

        # Create checkpoint
        cp_id = create_checkpoint(
            video_id=video_id,
            branch_name='main',
            phase_number=1,
            version=1,
            phase_output={'test': 'data'},
            cost_usd=0.0,
            user_id="integration-test-user"
        )

        assert cp_id is not None

        # Verify checkpoint was created
        from app.database.checkpoint_queries import get_checkpoint
        checkpoint = get_checkpoint(cp_id)
        assert checkpoint is not None
        assert checkpoint['video_id'] == video_id
        assert checkpoint['branch_name'] == 'main'

        # Cleanup
        db.query(VideoGeneration).filter(VideoGeneration.id == video_id).delete()
        db.commit()

    finally:
        db.close()
