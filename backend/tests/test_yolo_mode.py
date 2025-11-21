"""
Tests for Phase 6: YOLO Mode (auto_continue)

YOLO mode allows videos to run through the entire pipeline without pausing at checkpoints.
When auto_continue=True, each phase automatically approves its checkpoint and dispatches
the next phase.
"""

import pytest
import uuid
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from app.database import SessionLocal
from app.common.models import VideoGeneration, VideoStatus
from app.database.checkpoint_queries import (
    create_checkpoint,
    get_checkpoint,
    approve_checkpoint,
    create_artifact
)
from app.orchestrator.pipeline import get_auto_continue_flag, dispatch_next_phase


# ============ Fixtures ============

@pytest.fixture
def mock_db():
    """Create a mock database session"""
    db = SessionLocal()
    yield db
    db.close()


@pytest.fixture
def video_id():
    """Generate unique video ID"""
    return f"video-{uuid.uuid4()}"


@pytest.fixture
def user_id():
    """Mock user ID"""
    return "test-user-123"


@pytest.fixture
def yolo_video(video_id, user_id, mock_db):
    """Create a video with auto_continue=True"""
    video = VideoGeneration(
        id=video_id,
        user_id=user_id,
        title="YOLO Test Video",
        prompt="Test video with auto-continue",
        status=VideoStatus.QUEUED,
        auto_continue=True
    )
    mock_db.add(video)
    mock_db.commit()
    mock_db.refresh(video)
    return video


@pytest.fixture
def manual_video(video_id, user_id, mock_db):
    """Create a video with auto_continue=False"""
    vid = f"video-manual-{uuid.uuid4()}"
    video = VideoGeneration(
        id=vid,
        user_id=user_id,
        title="Manual Test Video",
        prompt="Test video without auto-continue",
        status=VideoStatus.QUEUED,
        auto_continue=False
    )
    mock_db.add(video)
    mock_db.commit()
    mock_db.refresh(video)
    return video


# ============ Tests ============

def test_video_model_has_auto_continue_field(mock_db, video_id, user_id):
    """Test that VideoGeneration model has auto_continue field"""
    video = VideoGeneration(
        id=video_id,
        user_id=user_id,
        title="Test",
        prompt="Test prompt",
        status=VideoStatus.QUEUED,
        auto_continue=True
    )
    mock_db.add(video)
    mock_db.commit()
    mock_db.refresh(video)

    # Verify field exists and is accessible
    assert hasattr(video, 'auto_continue')
    assert video.auto_continue is True


def test_auto_continue_defaults_to_false(mock_db, video_id, user_id):
    """Test that auto_continue defaults to False"""
    video = VideoGeneration(
        id=video_id,
        user_id=user_id,
        title="Test",
        prompt="Test prompt",
        status=VideoStatus.QUEUED
        # Note: auto_continue not specified
    )
    mock_db.add(video)
    mock_db.commit()
    mock_db.refresh(video)

    assert video.auto_continue is False


def test_get_auto_continue_flag_returns_true(yolo_video):
    """Test get_auto_continue_flag() returns True for YOLO videos"""
    result = get_auto_continue_flag(yolo_video.id)
    assert result is True


def test_get_auto_continue_flag_returns_false(manual_video):
    """Test get_auto_continue_flag() returns False for manual videos"""
    result = get_auto_continue_flag(manual_video.id)
    assert result is False


def test_get_auto_continue_flag_nonexistent_video():
    """Test get_auto_continue_flag() returns False for nonexistent video"""
    result = get_auto_continue_flag("nonexistent-video-id")
    assert result is False


def test_yolo_checkpoint_auto_approved(yolo_video, user_id):
    """Test that checkpoints are auto-approved in YOLO mode"""
    # Create a Phase 1 checkpoint
    checkpoint_id = create_checkpoint(
        video_id=yolo_video.id,
        branch_name='main',
        phase_number=1,
        version=1,
        phase_output={
            'video_id': yolo_video.id,
            'phase': 'phase1',
            'status': 'success',
            'output_data': {'spec': {'beats': [], 'style': {}}}
        },
        cost_usd=0.05,
        user_id=user_id,
        parent_checkpoint_id=None
    )

    # Verify checkpoint starts as pending
    checkpoint = get_checkpoint(checkpoint_id)
    assert checkpoint['status'] == 'pending'
    assert checkpoint['approved_at'] is None

    # Simulate YOLO mode auto-approval (this would happen in phase tasks)
    if get_auto_continue_flag(yolo_video.id):
        approve_checkpoint(checkpoint_id)

    # Verify checkpoint is now approved
    checkpoint = get_checkpoint(checkpoint_id)
    assert checkpoint['status'] == 'approved'
    assert checkpoint['approved_at'] is not None


def test_manual_checkpoint_stays_pending(manual_video, user_id):
    """Test that checkpoints stay pending in manual mode"""
    # Create a Phase 1 checkpoint
    checkpoint_id = create_checkpoint(
        video_id=manual_video.id,
        branch_name='main',
        phase_number=1,
        version=1,
        phase_output={
            'video_id': manual_video.id,
            'phase': 'phase1',
            'status': 'success',
            'output_data': {'spec': {'beats': [], 'style': {}}}
        },
        cost_usd=0.05,
        user_id=user_id,
        parent_checkpoint_id=None
    )

    # Verify checkpoint stays pending
    checkpoint = get_checkpoint(checkpoint_id)
    assert checkpoint['status'] == 'pending'
    assert checkpoint['approved_at'] is None

    # Verify auto-continue flag is False
    assert get_auto_continue_flag(manual_video.id) is False


@patch('app.orchestrator.pipeline.generate_storyboard')
def test_dispatch_next_phase_from_phase1(mock_generate_storyboard, yolo_video, user_id):
    """Test dispatch_next_phase() dispatches Phase 2 after Phase 1"""
    # Create Phase 1 checkpoint
    checkpoint_id = create_checkpoint(
        video_id=yolo_video.id,
        branch_name='main',
        phase_number=1,
        version=1,
        phase_output={
            'video_id': yolo_video.id,
            'phase': 'phase1',
            'status': 'success',
            'output_data': {'spec': {'beats': [], 'style': {}, 'product': {}}}
        },
        cost_usd=0.05,
        user_id=user_id,
        parent_checkpoint_id=None
    )

    # Dispatch next phase (should dispatch Phase 2)
    dispatch_next_phase(yolo_video.id, checkpoint_id)

    # Verify Phase 2 was dispatched
    mock_generate_storyboard.delay.assert_called_once()
    call_args = mock_generate_storyboard.delay.call_args
    assert call_args[0][1] == user_id  # Second arg should be user_id


@patch('app.orchestrator.pipeline.generate_chunks')
def test_dispatch_next_phase_from_phase2(mock_generate_chunks, yolo_video, user_id):
    """Test dispatch_next_phase() dispatches Phase 3 after Phase 2"""
    # Create Phase 1 checkpoint (parent)
    phase1_checkpoint_id = create_checkpoint(
        video_id=yolo_video.id,
        branch_name='main',
        phase_number=1,
        version=1,
        phase_output={
            'video_id': yolo_video.id,
            'phase': 'phase1',
            'status': 'success',
            'output_data': {'spec': {'beats': [], 'style': {}}}
        },
        cost_usd=0.05,
        user_id=user_id,
        parent_checkpoint_id=None
    )

    # Create Phase 2 checkpoint
    checkpoint_id = create_checkpoint(
        video_id=yolo_video.id,
        branch_name='main',
        phase_number=2,
        version=1,
        phase_output={
            'video_id': yolo_video.id,
            'phase': 'phase2',
            'status': 'success',
            'output_data': {'storyboard_images': []}
        },
        cost_usd=0.10,
        user_id=user_id,
        parent_checkpoint_id=phase1_checkpoint_id
    )

    # Dispatch next phase (should dispatch Phase 3)
    dispatch_next_phase(yolo_video.id, checkpoint_id)

    # Verify Phase 3 was dispatched
    mock_generate_chunks.delay.assert_called_once()
    call_args = mock_generate_chunks.delay.call_args
    assert call_args[0][1] == user_id  # Second arg should be user_id


@patch('app.orchestrator.pipeline.refine_video')
def test_dispatch_next_phase_from_phase3(mock_refine_video, yolo_video, user_id):
    """Test dispatch_next_phase() dispatches Phase 4 after Phase 3"""
    # Create Phase 3 checkpoint
    checkpoint_id = create_checkpoint(
        video_id=yolo_video.id,
        branch_name='main',
        phase_number=3,
        version=1,
        phase_output={
            'video_id': yolo_video.id,
            'phase': 'phase3',
            'status': 'success',
            'output_data': {'chunk_urls': [], 'stitched_url': 's3://...'}
        },
        cost_usd=0.20,
        user_id=user_id,
        parent_checkpoint_id=None
    )

    # Dispatch next phase (should dispatch Phase 4)
    dispatch_next_phase(yolo_video.id, checkpoint_id)

    # Verify Phase 4 was dispatched
    mock_refine_video.delay.assert_called_once()
    call_args = mock_refine_video.delay.call_args
    assert call_args[0][1] == user_id  # Second arg should be user_id


def test_dispatch_next_phase_from_phase4_does_nothing(yolo_video, user_id):
    """Test dispatch_next_phase() does nothing after Phase 4 (terminal)"""
    # Create Phase 4 checkpoint
    checkpoint_id = create_checkpoint(
        video_id=yolo_video.id,
        branch_name='main',
        phase_number=4,
        version=1,
        phase_output={
            'video_id': yolo_video.id,
            'phase': 'phase4',
            'status': 'success',
            'output_data': {'final_video_url': 's3://...'}
        },
        cost_usd=0.15,
        user_id=user_id,
        parent_checkpoint_id=None
    )

    # Dispatch next phase (should do nothing - Phase 4 is terminal)
    # Just verify it doesn't raise an exception
    try:
        dispatch_next_phase(yolo_video.id, checkpoint_id)
        # If we get here without exception, the test passes
        assert True
    except Exception as e:
        pytest.fail(f"dispatch_next_phase raised exception for Phase 4: {e}")


def test_yolo_creates_checkpoints(yolo_video, user_id):
    """Test that YOLO mode still creates checkpoint records"""
    # Create checkpoints for all phases
    checkpoints = []
    for phase in range(1, 5):
        checkpoint_id = create_checkpoint(
            video_id=yolo_video.id,
            branch_name='main',
            phase_number=phase,
            version=1,
            phase_output={
                'video_id': yolo_video.id,
                'phase': f'phase{phase}',
                'status': 'success',
                'output_data': {}
            },
            cost_usd=0.05,
            user_id=user_id,
            parent_checkpoint_id=checkpoints[-1] if checkpoints else None
        )
        checkpoints.append(checkpoint_id)

    # Verify all checkpoints were created
    assert len(checkpoints) == 4

    # Verify each checkpoint exists
    for i, checkpoint_id in enumerate(checkpoints, start=1):
        checkpoint = get_checkpoint(checkpoint_id)
        assert checkpoint is not None
        assert checkpoint['phase_number'] == i
        assert checkpoint['video_id'] == yolo_video.id


def test_yolo_approved_at_timestamps_set(yolo_video, user_id):
    """Test that YOLO mode sets approved_at timestamps immediately"""
    # Create a checkpoint
    checkpoint_id = create_checkpoint(
        video_id=yolo_video.id,
        branch_name='main',
        phase_number=1,
        version=1,
        phase_output={
            'video_id': yolo_video.id,
            'phase': 'phase1',
            'status': 'success',
            'output_data': {'spec': {}}
        },
        cost_usd=0.05,
        user_id=user_id,
        parent_checkpoint_id=None
    )

    # Verify starts as pending with no approved_at
    checkpoint = get_checkpoint(checkpoint_id)
    assert checkpoint['approved_at'] is None

    # Simulate YOLO auto-approval
    if get_auto_continue_flag(yolo_video.id):
        approve_checkpoint(checkpoint_id)

    # Verify approved_at is now set
    checkpoint = get_checkpoint(checkpoint_id)
    assert checkpoint['approved_at'] is not None
    assert isinstance(checkpoint['approved_at'], datetime)


def test_yolo_all_on_main_branch(yolo_video, user_id):
    """Test that YOLO mode keeps all checkpoints on main branch"""
    # Create checkpoints for all phases (simulating YOLO flow)
    parent_id = None
    for phase in range(1, 5):
        checkpoint_id = create_checkpoint(
            video_id=yolo_video.id,
            branch_name='main',  # YOLO should stay on main
            phase_number=phase,
            version=1,
            phase_output={
                'video_id': yolo_video.id,
                'phase': f'phase{phase}',
                'status': 'success',
                'output_data': {}
            },
            cost_usd=0.05,
            user_id=user_id,
            parent_checkpoint_id=parent_id
        )

        # Auto-approve in YOLO mode
        approve_checkpoint(checkpoint_id)
        parent_id = checkpoint_id

        # Verify checkpoint is on main branch
        checkpoint = get_checkpoint(checkpoint_id)
        assert checkpoint['branch_name'] == 'main'


def test_generate_request_schema_accepts_auto_continue():
    """Test that GenerateRequest schema accepts auto_continue parameter"""
    from app.common.schemas import GenerateRequest

    # Test with auto_continue=True
    request = GenerateRequest(
        prompt="Test video prompt",
        auto_continue=True
    )
    assert request.auto_continue is True

    # Test with auto_continue=False
    request = GenerateRequest(
        prompt="Test video prompt",
        auto_continue=False
    )
    assert request.auto_continue is False

    # Test default value (should be False)
    request = GenerateRequest(
        prompt="Test video prompt"
    )
    assert request.auto_continue is False
