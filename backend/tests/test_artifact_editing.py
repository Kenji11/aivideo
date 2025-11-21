"""
Tests for artifact editing endpoints.

These tests verify:
- Spec editing at Phase 1
- Image upload for beat replacement at Phase 2
- Beat regeneration with FLUX at Phase 2
- Chunk regeneration at Phase 3
- Versioning and branching logic
- Phase restrictions (can only edit at correct phase)

Note: Using mocked AI services to avoid costs during testing.
"""
import pytest
from unittest.mock import patch, Mock, MagicMock
from datetime import datetime
import io

# Import API functions directly
from app.api.checkpoints import (
    edit_spec,
    upload_replacement_image,
    regenerate_beat,
    regenerate_chunk,
    continue_pipeline
)
from app.common.schemas import (
    SpecEditRequest,
    RegenerateBeatRequest,
    RegenerateChunkRequest,
    ContinueRequest
)
from app.database import SessionLocal
from app.common.models import VideoGeneration, VideoStatus
from app.database.checkpoint_queries import (
    create_checkpoint,
    create_artifact,
    get_latest_artifact_version,
    has_checkpoint_been_edited,
    get_checkpoint
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
def test_video_phase1(test_user_id, mock_db):
    """Create a test video at Phase 1"""
    video_id = f"test-video-{uuid.uuid4().hex[:8]}"
    video = VideoGeneration(
        id=video_id,
        user_id=test_user_id,
        prompt="Test luxury watch commercial",
        title="Test Video Phase 1",
        status=VideoStatus.PAUSED_AT_PHASE1,
        current_phase="phase1",
        progress=25.0,
        cost_usd=0.02,
        spec={
            "template": "luxury_showcase",
            "beats": [
                {"beat_id": "hero", "duration": 5},
                {"beat_id": "detail", "duration": 5}
            ],
            "style": {"mood": "luxury"},
            "product": {"category": "watch"}
        },
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
def test_video_phase2(test_user_id, mock_db):
    """Create a test video at Phase 2"""
    video_id = f"test-video-{uuid.uuid4().hex[:8]}"
    video = VideoGeneration(
        id=video_id,
        user_id=test_user_id,
        prompt="Test luxury watch commercial",
        title="Test Video Phase 2",
        status=VideoStatus.PAUSED_AT_PHASE2,
        current_phase="phase2",
        progress=50.0,
        cost_usd=0.10,
        spec={
            "template": "luxury_showcase",
            "beats": [
                {"beat_id": "hero", "duration": 5},
                {"beat_id": "detail", "duration": 5}
            ],
            "style": {"mood": "luxury"},
            "product": {"category": "watch"}
        },
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
def test_video_phase3(test_user_id, mock_db):
    """Create a test video at Phase 3"""
    video_id = f"test-video-{uuid.uuid4().hex[:8]}"
    video = VideoGeneration(
        id=video_id,
        user_id=test_user_id,
        prompt="Test luxury watch commercial",
        title="Test Video Phase 3",
        status=VideoStatus.PAUSED_AT_PHASE3,
        current_phase="phase3",
        progress=75.0,
        cost_usd=0.50,
        spec={
            "template": "luxury_showcase",
            "beats": [
                {"beat_id": "hero", "duration": 5},
                {"beat_id": "detail", "duration": 5}
            ]
        },
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
def checkpoint_phase1(test_video_phase1):
    """Create a Phase 1 checkpoint"""
    cp_id = create_checkpoint(
        video_id=test_video_phase1.id,
        branch_name='main',
        phase_number=1,
        version=1,
        phase_output={
            'video_id': test_video_phase1.id,
            'phase': 'phase1_planning',
            'status': 'success',
            'output_data': {'spec': test_video_phase1.spec},
            'cost_usd': 0.02,
            'duration_seconds': 5.0
        },
        cost_usd=0.02,
        user_id=test_video_phase1.user_id,
        parent_checkpoint_id=None
    )

    # Create spec artifact
    create_artifact(
        checkpoint_id=cp_id,
        artifact_type='spec',
        artifact_key='spec',
        s3_url='',
        s3_key='',
        version=1,
        metadata={'spec': test_video_phase1.spec}
    )

    return cp_id


@pytest.fixture
def checkpoint_phase2(test_video_phase2):
    """Create a Phase 2 checkpoint with beat images"""
    cp_id = create_checkpoint(
        video_id=test_video_phase2.id,
        branch_name='main',
        phase_number=2,
        version=1,
        phase_output={
            'video_id': test_video_phase2.id,
            'phase': 'phase2_storyboard',
            'status': 'success',
            'output_data': {
                'spec': test_video_phase2.spec,
                'beat_images': [
                    {'beat_id': 'hero', 'image_url': f's3://bucket/{test_video_phase2.user_id}/videos/{test_video_phase2.id}/beat_00_v1.png'},
                    {'beat_id': 'detail', 'image_url': f's3://bucket/{test_video_phase2.user_id}/videos/{test_video_phase2.id}/beat_01_v1.png'}
                ]
            },
            'cost_usd': 0.08,
            'duration_seconds': 30.0
        },
        cost_usd=0.08,
        user_id=test_video_phase2.user_id,
        parent_checkpoint_id=None
    )

    # Create beat image artifacts
    for i in range(2):
        create_artifact(
            checkpoint_id=cp_id,
            artifact_type='beat_image',
            artifact_key=f'beat_{i}',
            s3_url=f's3://bucket/{test_video_phase2.user_id}/videos/{test_video_phase2.id}/beat_{i:02d}_v1.png',
            s3_key=f'{test_video_phase2.user_id}/videos/{test_video_phase2.id}/beat_{i:02d}_v1.png',
            version=1,
            metadata={'beat_id': f'beat_{i}'}
        )

    return cp_id


@pytest.fixture
def checkpoint_phase3(test_video_phase3):
    """Create a Phase 3 checkpoint with chunks"""
    cp_id = create_checkpoint(
        video_id=test_video_phase3.id,
        branch_name='main',
        phase_number=3,
        version=1,
        phase_output={
            'video_id': test_video_phase3.id,
            'phase': 'phase3_chunks',
            'status': 'success',
            'output_data': {
                'spec': test_video_phase3.spec,
                'chunk_specs': [
                    {
                        'chunk_num': 0,
                        'video_id': test_video_phase3.id,
                        'user_id': test_video_phase3.user_id,
                        'prompt': 'Hero shot of luxury watch',
                        'duration': 5,
                        'start_time': 0,
                        'beat': {'beat_id': 'hero', 'duration': 5},
                        'fps': 24,
                        'model': 'hailuo',
                        'style_guide_url': f's3://bucket/{test_video_phase3.user_id}/videos/{test_video_phase3.id}/beat_00_v1.png'
                    }
                ],
                'beat_to_chunk_map': {0: 0}
            },
            'cost_usd': 0.40,
            'duration_seconds': 60.0
        },
        cost_usd=0.40,
        user_id=test_video_phase3.user_id,
        parent_checkpoint_id=None
    )

    # Create chunk artifacts
    create_artifact(
        checkpoint_id=cp_id,
        artifact_type='video_chunk',
        artifact_key='chunk_0',
        s3_url=f's3://bucket/{test_video_phase3.user_id}/videos/{test_video_phase3.id}/chunk_00_v1.mp4',
        s3_key=f'{test_video_phase3.user_id}/videos/{test_video_phase3.id}/chunk_00_v1.mp4',
        version=1,
        metadata={'chunk_index': 0}
    )

    return cp_id


# ============ Test Spec Editing ============

@pytest.mark.asyncio
async def test_edit_spec_creates_new_version(test_video_phase1, checkpoint_phase1, test_user_id, mock_db):
    """Test that editing spec creates a new artifact version"""
    spec_edits = SpecEditRequest(
        style={"mood": "elegant", "lighting": "warm"}
    )

    result = await edit_spec(
        video_id=test_video_phase1.id,
        checkpoint_id=checkpoint_phase1,
        spec_edits=spec_edits,
        user_id=test_user_id,
        db=mock_db
    )

    assert result.version == 2
    assert result.artifact_id is not None
    assert "version 2" in result.message

    # Verify new artifact was created
    new_artifact = get_latest_artifact_version(checkpoint_phase1, 'spec', 'spec')
    assert new_artifact['version'] == 2
    assert new_artifact['metadata']['spec']['style']['mood'] == 'elegant'


@pytest.mark.asyncio
async def test_edit_spec_merges_with_existing(test_video_phase1, checkpoint_phase1, test_user_id, mock_db):
    """Test that spec editing merges with existing spec"""
    spec_edits = SpecEditRequest(
        audio={"music_style": "orchestral"}
    )

    result = await edit_spec(
        video_id=test_video_phase1.id,
        checkpoint_id=checkpoint_phase1,
        spec_edits=spec_edits,
        user_id=test_user_id,
        db=mock_db
    )

    # Verify existing fields are preserved
    new_artifact = get_latest_artifact_version(checkpoint_phase1, 'spec', 'spec')
    spec = new_artifact['metadata']['spec']
    assert spec['template'] == 'luxury_showcase'
    assert len(spec['beats']) == 2
    assert spec['audio']['music_style'] == 'orchestral'


@pytest.mark.asyncio
async def test_edit_spec_only_at_phase1(test_video_phase2, checkpoint_phase2, test_user_id, mock_db):
    """Test that spec can only be edited at Phase 1"""
    spec_edits = SpecEditRequest(style={"mood": "elegant"})

    with pytest.raises(Exception) as exc_info:
        await edit_spec(
            video_id=test_video_phase2.id,
            checkpoint_id=checkpoint_phase2,
            spec_edits=spec_edits,
            user_id=test_user_id,
            db=mock_db
        )

    assert "Phase 1" in str(exc_info.value.detail)


# ============ Test Image Upload ============

@pytest.mark.asyncio
async def test_upload_image_creates_new_artifact(test_video_phase2, checkpoint_phase2, test_user_id, mock_db):
    """Test that uploading an image creates a new artifact version"""
    # Create a mock uploaded file
    mock_file = MagicMock()
    mock_file.filename = "test_image.png"

    # Mock read as an async function
    async def async_read():
        return b"fake image data"
    mock_file.read = async_read

    with patch('app.services.s3.s3_client.upload_file') as mock_upload:
        mock_upload.return_value = f's3://bucket/{test_user_id}/videos/{test_video_phase2.id}/beat_00_edited.png'

        result = await upload_replacement_image(
            video_id=test_video_phase2.id,
            checkpoint_id=checkpoint_phase2,
            beat_index=0,
            image=mock_file,
            user_id=test_user_id,
            db=mock_db
        )

        assert result.version == 2
        assert result.s3_url is not None
        assert "version 2" in result.message

        # Verify upload was called
        assert mock_upload.called


@pytest.mark.asyncio
async def test_upload_image_validates_beat_index(test_video_phase2, checkpoint_phase2, test_user_id, mock_db):
    """Test that upload validates beat index"""
    mock_file = MagicMock()
    mock_file.filename = "test_image.png"

    async def async_read():
        return b"fake image data"
    mock_file.read = async_read

    with pytest.raises(Exception) as exc_info:
        await upload_replacement_image(
            video_id=test_video_phase2.id,
            checkpoint_id=checkpoint_phase2,
            beat_index=99,  # Invalid index
            image=mock_file,
            user_id=test_user_id,
            db=mock_db
        )

    assert "out of range" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_upload_image_only_at_phase2(test_video_phase1, checkpoint_phase1, test_user_id, mock_db):
    """Test that images can only be uploaded at Phase 2"""
    mock_file = MagicMock()
    mock_file.filename = "test_image.png"

    async def async_read():
        return b"fake image data"
    mock_file.read = async_read

    with pytest.raises(Exception) as exc_info:
        await upload_replacement_image(
            video_id=test_video_phase1.id,
            checkpoint_id=checkpoint_phase1,
            beat_index=0,
            image=mock_file,
            user_id=test_user_id,
            db=mock_db
        )

    assert "Phase 2" in str(exc_info.value.detail)


# ============ Test Beat Regeneration ============

@pytest.mark.asyncio
async def test_regenerate_beat_calls_flux(test_video_phase2, checkpoint_phase2, test_user_id, mock_db):
    """Test that regenerating beat calls FLUX (mocked)"""
    request = RegenerateBeatRequest(beat_index=0, prompt_override="Close-up product shot")

    mock_beat_result = {
        'beat_id': 'hero',
        'beat_index': 0,
        'image_url': f's3://bucket/{test_user_id}/videos/{test_video_phase2.id}/beat_00_v2.png',
        's3_key': f'{test_user_id}/videos/{test_video_phase2.id}/beat_00_v2.png',
        'prompt_used': 'Close-up product shot',
        'shot_type': 'close-up'
    }

    with patch('app.api.checkpoints.generate_beat_image') as mock_generate:
        mock_generate.return_value = mock_beat_result

        result = await regenerate_beat(
            video_id=test_video_phase2.id,
            checkpoint_id=checkpoint_phase2,
            request=request,
            user_id=test_user_id,
            db=mock_db
        )

        assert result.version == 2
        assert result.s3_url is not None
        assert "version 2" in result.message

        # Verify FLUX was called
        assert mock_generate.called


@pytest.mark.asyncio
async def test_regenerate_beat_only_at_phase2(test_video_phase1, checkpoint_phase1, test_user_id, mock_db):
    """Test that beats can only be regenerated at Phase 2"""
    request = RegenerateBeatRequest(beat_index=0)

    with pytest.raises(Exception) as exc_info:
        await regenerate_beat(
            video_id=test_video_phase1.id,
            checkpoint_id=checkpoint_phase1,
            request=request,
            user_id=test_user_id,
            db=mock_db
        )

    assert "Phase 2" in str(exc_info.value.detail)


# ============ Test Chunk Regeneration ============

@pytest.mark.asyncio
async def test_regenerate_chunk_calls_model(test_video_phase3, checkpoint_phase3, test_user_id, mock_db):
    """Test that regenerating chunk calls video model (mocked)"""
    request = RegenerateChunkRequest(chunk_index=0, model_override="kling")

    mock_chunk_result = {
        'chunk_url': f's3://bucket/{test_user_id}/videos/{test_video_phase3.id}/chunk_00_v2.mp4',
        'cost': 0.40,
        'init_image_source': 'storyboard'
    }

    with patch('app.api.checkpoints.generate_single_chunk_with_storyboard') as mock_generate:
        mock_generate.return_value = mock_chunk_result

        result = await regenerate_chunk(
            video_id=test_video_phase3.id,
            checkpoint_id=checkpoint_phase3,
            request=request,
            user_id=test_user_id,
            db=mock_db
        )

        assert result.version == 2
        assert result.s3_url is not None
        assert "version 2" in result.message

        # Verify chunk generator was called
        assert mock_generate.called


@pytest.mark.asyncio
async def test_regenerate_chunk_only_at_phase3(test_video_phase2, checkpoint_phase2, test_user_id, mock_db):
    """Test that chunks can only be regenerated at Phase 3"""
    request = RegenerateChunkRequest(chunk_index=0)

    with pytest.raises(Exception) as exc_info:
        await regenerate_chunk(
            video_id=test_video_phase2.id,
            checkpoint_id=checkpoint_phase2,
            request=request,
            user_id=test_user_id,
            db=mock_db
        )

    assert "Phase 3" in str(exc_info.value.detail)


# ============ Test Branching Logic ============

@pytest.mark.asyncio
async def test_continue_with_edits_creates_branch(test_video_phase1, checkpoint_phase1, test_user_id, mock_db):
    """Test that continuing after editing creates a new branch"""
    # First, edit the spec
    spec_edits = SpecEditRequest(style={"mood": "elegant"})
    await edit_spec(
        video_id=test_video_phase1.id,
        checkpoint_id=checkpoint_phase1,
        spec_edits=spec_edits,
        user_id=test_user_id,
        db=mock_db
    )

    # Verify checkpoint has been edited
    assert has_checkpoint_been_edited(checkpoint_phase1) == True

    # Now continue
    request = ContinueRequest(checkpoint_id=checkpoint_phase1)

    with patch('app.orchestrator.pipeline.dispatch_next_phase') as mock_dispatch:
        result = await continue_pipeline(
            video_id=test_video_phase1.id,
            request=request,
            user_id=test_user_id,
            db=mock_db
        )

        assert result.created_new_branch == True
        assert result.branch_name == 'main-1'
        assert result.next_phase == 2


@pytest.mark.asyncio
async def test_continue_without_edits_same_branch(test_video_phase1, checkpoint_phase1, test_user_id, mock_db):
    """Test that continuing without editing stays on same branch"""
    # Don't edit anything

    # Verify checkpoint has not been edited
    assert has_checkpoint_been_edited(checkpoint_phase1) == False

    request = ContinueRequest(checkpoint_id=checkpoint_phase1)

    with patch('app.orchestrator.pipeline.dispatch_next_phase') as mock_dispatch:
        result = await continue_pipeline(
            video_id=test_video_phase1.id,
            request=request,
            user_id=test_user_id,
            db=mock_db
        )

        assert result.created_new_branch == False
        assert result.branch_name == 'main'
        assert result.next_phase == 2


@pytest.mark.asyncio
async def test_latest_artifacts_mixed_versions(test_video_phase2, checkpoint_phase2, test_user_id, mock_db):
    """Test that latest artifacts query handles mixed versions correctly"""
    # Edit beat 0 (creates v2)
    mock_file = MagicMock()
    mock_file.filename = "test_image.png"

    async def async_read():
        return b"fake image data"
    mock_file.read = async_read

    with patch('app.services.s3.s3_client.upload_file') as mock_upload:
        mock_upload.return_value = f's3://bucket/{test_user_id}/videos/{test_video_phase2.id}/beat_00_edited.png'

        await upload_replacement_image(
            video_id=test_video_phase2.id,
            checkpoint_id=checkpoint_phase2,
            beat_index=0,
            image=mock_file,
            user_id=test_user_id,
            db=mock_db
        )

    # Now beat_0 is v2, beat_1 is still v1
    beat_0_latest = get_latest_artifact_version(checkpoint_phase2, 'beat_image', 'beat_0')
    beat_1_latest = get_latest_artifact_version(checkpoint_phase2, 'beat_image', 'beat_1')

    assert beat_0_latest['version'] == 2
    assert beat_1_latest['version'] == 1
