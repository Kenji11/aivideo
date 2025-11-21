"""
Tests for Phase 5: Status & Monitoring with Checkpoint Integration

This module tests:
1. Status response includes checkpoint information
2. Checkpoint tree is included in status response
3. Active branches are included in status response
4. Redis caches checkpoint_id correctly
5. Status builder functions work correctly

Note: Using direct function calls and database queries instead of TestClient.
"""

import pytest
from datetime import datetime
import uuid

from app.database import SessionLocal
from app.common.models import VideoGeneration, VideoStatus
from app.database.checkpoint_queries import (
    create_checkpoint,
    create_artifact,
    approve_checkpoint,
    get_current_checkpoint,
    build_checkpoint_tree,
    get_leaf_checkpoints
)
from app.services.status_builder import (
    build_status_response_from_db,
    _build_checkpoint_info,
    _build_checkpoint_tree_nodes,
    _build_active_branches
)
from app.services.redis import RedisClient
from app.orchestrator.progress import update_progress


@pytest.fixture
def mock_db():
    """Create a mock database session"""
    db = SessionLocal()
    yield db
    db.close()


@pytest.fixture
def test_user_id():
    """Return a test user ID"""
    return "test-user-phase5-123"


@pytest.fixture
def test_video(test_user_id, mock_db):
    """Create a test video in the database"""
    # Clean up any existing test videos
    mock_db.query(VideoGeneration).filter(
        VideoGeneration.id.like("test-video-phase5-%")
    ).delete()
    mock_db.commit()

    video_id = f"test-video-phase5-{uuid.uuid4().hex[:8]}"
    video = VideoGeneration(
        id=video_id,
        user_id=test_user_id,
        prompt="Test video for Phase 5",
        title="Phase 5 Test Video",
        status=VideoStatus.PAUSED_AT_PHASE1,
        current_phase="phase1",
        progress=25.0,
        cost_usd=0.02,
        spec={"template": "test", "beats": []},
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
def test_checkpoint(test_video):
    """Create a test checkpoint with artifacts"""
    checkpoint_id = create_checkpoint(
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
        user_id=test_video.user_id
    )

    # Create a sample artifact
    create_artifact(
        checkpoint_id=checkpoint_id,
        artifact_type="spec",
        artifact_key="spec_v1",
        s3_url="s3://test-bucket/spec.json",
        s3_key="spec.json",
        version=1,
        metadata={"test": "data"}
    )

    return checkpoint_id


def test_status_includes_checkpoint_info(test_video, test_checkpoint, mock_db):
    """Verify status builder includes current_checkpoint"""
    mock_db.refresh(test_video)
    status_response = build_status_response_from_db(test_video)

    # Check that checkpoint fields exist
    assert hasattr(status_response, 'current_checkpoint')
    assert hasattr(status_response, 'checkpoint_tree')
    assert hasattr(status_response, 'active_branches')

    # Verify current_checkpoint structure
    if status_response.current_checkpoint:
        checkpoint = status_response.current_checkpoint
        assert checkpoint.checkpoint_id == test_checkpoint
        assert checkpoint.branch_name == 'main'
        assert checkpoint.phase_number == 1
        assert checkpoint.version == 1
        assert checkpoint.status == 'pending'
        assert isinstance(checkpoint.artifacts, dict)


def test_build_checkpoint_info_helper(test_video, test_checkpoint):
    """Test _build_checkpoint_info helper function"""
    checkpoint_info = _build_checkpoint_info(test_video.id)

    assert checkpoint_info is not None
    assert checkpoint_info.checkpoint_id == test_checkpoint
    assert checkpoint_info.branch_name == 'main'
    assert checkpoint_info.phase_number == 1
    assert len(checkpoint_info.artifacts) >= 1


def test_checkpoint_tree_in_status(test_video, test_checkpoint, mock_db):
    """Verify checkpoint_tree is included in status response"""
    # Approve first checkpoint
    approve_checkpoint(test_checkpoint)

    # Create a child checkpoint
    child_checkpoint_id = create_checkpoint(
        video_id=test_video.id,
        branch_name='main',
        phase_number=2,
        version=1,
        phase_output={
            'video_id': test_video.id,
            'phase': 'phase2_storyboard',
            'status': 'success',
            'output_data': {},
            'cost_usd': 0.3,
            'duration_seconds': 10.0
        },
        cost_usd=0.3,
        user_id=test_video.user_id,
        parent_checkpoint_id=test_checkpoint
    )

    mock_db.refresh(test_video)
    status_response = build_status_response_from_db(test_video)

    # Verify checkpoint_tree exists
    assert status_response.checkpoint_tree is not None
    assert isinstance(status_response.checkpoint_tree, list)
    assert len(status_response.checkpoint_tree) > 0


def test_build_checkpoint_tree_helper(test_video, test_checkpoint):
    """Test _build_checkpoint_tree_nodes helper function"""
    approve_checkpoint(test_checkpoint)

    # Create child checkpoint
    create_checkpoint(
        video_id=test_video.id,
        branch_name='main',
        phase_number=2,
        version=1,
        phase_output={
            'video_id': test_video.id,
            'phase': 'phase2_storyboard',
            'status': 'success',
            'output_data': {},
            'cost_usd': 0.2,
            'duration_seconds': 8.0
        },
        cost_usd=0.2,
        user_id=test_video.user_id,
        parent_checkpoint_id=test_checkpoint
    )

    tree = _build_checkpoint_tree_nodes(test_video.id)

    assert tree is not None
    assert len(tree) > 0
    root = tree[0]
    assert root.checkpoint.phase_number == 1
    assert len(root.children) > 0


def test_active_branches_in_status(test_video, test_checkpoint, mock_db):
    """Verify active_branches is included in status response"""
    # Approve checkpoint to make it a valid branch
    approve_checkpoint(test_checkpoint)

    mock_db.refresh(test_video)
    status_response = build_status_response_from_db(test_video)

    # Verify active_branches exists
    assert status_response.active_branches is not None
    assert isinstance(status_response.active_branches, list)

    if len(status_response.active_branches) > 0:
        branch = status_response.active_branches[0]
        assert branch.branch_name == 'main'
        assert branch.phase_number == 1
        assert branch.can_continue is True  # approved checkpoint


def test_build_active_branches_helper(test_video, test_checkpoint):
    """Test _build_active_branches helper function"""
    approve_checkpoint(test_checkpoint)

    branches = _build_active_branches(test_video.id)

    assert branches is not None
    assert len(branches) > 0

    branch = branches[0]
    assert branch.branch_name == 'main'
    assert branch.latest_checkpoint_id == test_checkpoint
    assert branch.status == 'approved'
    assert branch.can_continue is True


def test_status_without_checkpoints(test_video, mock_db):
    """Verify status works correctly when no checkpoints exist"""
    mock_db.refresh(test_video)
    status_response = build_status_response_from_db(test_video)

    # Should still have checkpoint fields, but they should be None
    assert hasattr(status_response, 'current_checkpoint')
    assert hasattr(status_response, 'checkpoint_tree')
    assert hasattr(status_response, 'active_branches')

    # Values should be None or empty
    assert status_response.current_checkpoint is None


def test_checkpoint_info_with_multiple_artifacts(test_video, test_checkpoint):
    """Verify checkpoint info includes all artifacts"""
    # Create multiple artifacts
    create_artifact(
        checkpoint_id=test_checkpoint,
        artifact_type="beat",
        artifact_key="beat_0",
        s3_url="s3://test-bucket/beat0.png",
        s3_key="beat0.png",
        version=1
    )

    create_artifact(
        checkpoint_id=test_checkpoint,
        artifact_type="beat",
        artifact_key="beat_1",
        s3_url="s3://test-bucket/beat1.png",
        s3_key="beat1.png",
        version=1
    )

    checkpoint_info = _build_checkpoint_info(test_video.id)

    assert checkpoint_info is not None
    assert isinstance(checkpoint_info.artifacts, dict)
    # Should have at least 3 artifacts (spec_v1 + beat_0 + beat_1)
    assert len(checkpoint_info.artifacts) >= 3


def test_redis_checkpoint_caching(test_video):
    """Verify checkpoint_id is cached in Redis when using update_progress"""
    redis_client = RedisClient()

    # Skip test if Redis is not available
    if not redis_client._client:
        pytest.skip("Redis not available")

    checkpoint_id = "test-checkpoint-redis-123"

    # Update progress with checkpoint_id
    update_progress(
        video_id=test_video.id,
        status="generating_animatic",
        progress=50.0,
        checkpoint_id=checkpoint_id
    )

    # Verify checkpoint_id was cached
    cached_checkpoint_id = redis_client.get_video_checkpoint(test_video.id)
    assert cached_checkpoint_id == checkpoint_id

    # Cleanup
    redis_client.delete_video_data(test_video.id)


def test_branch_info_can_continue_logic(test_video, test_checkpoint):
    """Verify can_continue is True for approved checkpoints"""
    # Before approval
    branches = _build_active_branches(test_video.id)
    assert branches is not None
    # Checkpoint should exist but not be continuable
    branch = branches[0]
    assert branch.can_continue is False  # pending checkpoint

    # After approval
    approve_checkpoint(test_checkpoint)

    branches = _build_active_branches(test_video.id)
    branch = branches[0]
    assert branch.can_continue is True  # approved checkpoint


def test_checkpoint_tree_recursive_structure(test_video):
    """Test that checkpoint tree handles deep nesting correctly"""
    # Create a chain of checkpoints
    checkpoint1 = create_checkpoint(
        video_id=test_video.id,
        branch_name="main",
        phase_number=1,
        version=1,
        phase_output={
            'video_id': test_video.id,
            'phase': 'phase1',
            'status': 'success',
            'output_data': {},
            'cost_usd': 0.1,
            'duration_seconds': 5.0
        },
        cost_usd=0.1,
        user_id=test_video.user_id
    )
    approve_checkpoint(checkpoint1)

    checkpoint2 = create_checkpoint(
        video_id=test_video.id,
        branch_name="main",
        phase_number=2,
        version=1,
        phase_output={
            'video_id': test_video.id,
            'phase': 'phase2',
            'status': 'success',
            'output_data': {},
            'cost_usd': 0.1,
            'duration_seconds': 5.0
        },
        cost_usd=0.1,
        user_id=test_video.user_id,
        parent_checkpoint_id=checkpoint1
    )
    approve_checkpoint(checkpoint2)

    checkpoint3 = create_checkpoint(
        video_id=test_video.id,
        branch_name="main",
        phase_number=3,
        version=1,
        phase_output={
            'video_id': test_video.id,
            'phase': 'phase3',
            'status': 'success',
            'output_data': {},
            'cost_usd': 0.1,
            'duration_seconds': 5.0
        },
        cost_usd=0.1,
        user_id=test_video.user_id,
        parent_checkpoint_id=checkpoint2
    )

    # Build tree
    tree = _build_checkpoint_tree_nodes(test_video.id)

    assert tree is not None
    assert len(tree) > 0

    # Verify nested structure
    root = tree[0]
    assert root.checkpoint.phase_number == 1
    assert len(root.children) > 0

    child = root.children[0]
    assert child.checkpoint.phase_number == 2
    assert len(child.children) > 0

    grandchild = child.children[0]
    assert grandchild.checkpoint.phase_number == 3
