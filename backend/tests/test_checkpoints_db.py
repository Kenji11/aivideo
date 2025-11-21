"""
Tests for checkpoint database operations.

Phase 1: Database Schema & Models
"""
import pytest
import uuid
import os
import psycopg2
from datetime import datetime
from app.database.checkpoint_queries import (
    create_checkpoint,
    get_checkpoint,
    list_checkpoints,
    approve_checkpoint,
    get_checkpoint_tree,
    get_current_checkpoint,
    get_leaf_checkpoints,
    create_artifact,
    get_checkpoint_artifacts,
    get_latest_artifact_version,
    get_latest_artifacts_for_checkpoint,
    get_next_version_number,
    generate_branch_name,
    has_checkpoint_been_edited,
    create_branch_from_checkpoint,
    build_checkpoint_tree,
    update_checkpoint_phase_output,
)


@pytest.fixture
def test_user_id():
    """Create a test user ID."""
    return f"usr-{uuid.uuid4()}"


@pytest.fixture
def test_video_id(test_user_id):
    """Create a test video ID and insert video record in database."""
    video_id = f"vid-{uuid.uuid4()}"

    print(f"\n[FIXTURE] Creating video {video_id} for user {test_user_id}")

    # Insert video_generation record so foreign key constraint is satisfied
    conn = get_test_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO video_generations (
                    id, user_id, title, prompt, status
                ) VALUES (%s, %s, %s, %s, %s)
            """, (video_id, test_user_id, 'Test Video', 'Test prompt', 'QUEUED'))
        conn.commit()
        print(f"[FIXTURE] Video {video_id} created successfully")

        # Verify it was inserted
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM video_generations WHERE id = %s", (video_id,))
            result = cur.fetchone()
            print(f"[FIXTURE] Verification: {result}")
    except Exception as e:
        print(f"[FIXTURE] Error creating video: {e}")
        raise
    finally:
        conn.close()

    yield video_id

    # Cleanup - delete the test video (cascade will delete checkpoints/artifacts)
    print(f"[FIXTURE] Cleaning up video {video_id}")
    conn = get_test_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM video_generations WHERE id = %s", (video_id,))
        conn.commit()
    finally:
        conn.close()


@pytest.fixture
def sample_phase_output():
    """Sample phase output data."""
    return {
        "video_id": "test-video",
        "phase": "phase1_planning",
        "status": "success",
        "output_data": {
            "spec": {
                "template": "luxury_showcase",
                "duration": 30,
                "beats": [
                    {"beat_id": "hero_shot", "duration": 10},
                    {"beat_id": "detail_showcase", "duration": 10},
                    {"beat_id": "call_to_action", "duration": 10}
                ]
            }
        },
        "cost_usd": 0.02,
        "duration_seconds": 5.3
    }


def get_test_connection():
    """Get a test database connection."""
    database_url = os.environ.get('DATABASE_URL', 'postgresql://dev:devpass@postgres:5432/videogen')
    return psycopg2.connect(database_url)


def test_migration_applies():
    """Test that migration can be applied without errors."""
    # This test assumes migration has been run
    # Verify by checking if tables exist
    conn = get_test_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = 'video_checkpoints'
                )
            """)
            assert cur.fetchone()[0], "video_checkpoints table should exist"
    finally:
        conn.close()


def test_checkpoint_table_exists():
    """Test that video_checkpoints table exists with correct columns."""
    conn = get_test_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_name = 'video_checkpoints'
                ORDER BY ordinal_position
            """)
            columns = {row[0]: row[1] for row in cur.fetchall()}

            # Check required columns exist
            required_columns = [
                'id', 'video_id', 'branch_name', 'phase_number', 'version',
                'parent_checkpoint_id', 'status', 'approved_at', 'created_at',
                'phase_output', 'cost_usd', 'user_id', 'edit_description'
            ]
            for col in required_columns:
                assert col in columns, f"Column {col} should exist"
    finally:
        conn.close()


def test_artifact_table_exists():
    """Test that checkpoint_artifacts table exists with correct columns."""
    conn = get_test_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_name = 'checkpoint_artifacts'
                ORDER BY ordinal_position
            """)
            columns = {row[0]: row[1] for row in cur.fetchall()}

            # Check required columns exist
            required_columns = [
                'id', 'checkpoint_id', 'artifact_type', 'artifact_key',
                's3_url', 's3_key', 'version', 'parent_artifact_id',
                'metadata', 'file_size_bytes', 'created_at'
            ]
            for col in required_columns:
                assert col in columns, f"Column {col} should exist"
    finally:
        conn.close()


def test_create_checkpoint(test_video_id, test_user_id, sample_phase_output):
    """Test creating a checkpoint."""
    checkpoint_id = create_checkpoint(
        video_id=test_video_id,
        branch_name='main',
        phase_number=1,
        version=1,
        phase_output=sample_phase_output,
        cost_usd=0.02,
        user_id=test_user_id
    )

    assert checkpoint_id.startswith('cp-')

    # Verify checkpoint was created
    checkpoint = get_checkpoint(checkpoint_id)
    assert checkpoint is not None
    assert checkpoint['video_id'] == test_video_id
    assert checkpoint['branch_name'] == 'main'
    assert checkpoint['phase_number'] == 1
    assert checkpoint['version'] == 1
    assert checkpoint['status'] == 'pending'
    assert checkpoint['user_id'] == test_user_id

    # Cleanup
    conn = get_test_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM video_checkpoints WHERE id = %s", (checkpoint_id,))
        conn.commit()
    finally:
        conn.close()


def test_create_artifact(test_video_id, test_user_id, sample_phase_output):
    """Test creating an artifact."""
    # Create checkpoint first
    checkpoint_id = create_checkpoint(
        video_id=test_video_id,
        branch_name='main',
        phase_number=1,
        version=1,
        phase_output=sample_phase_output,
        cost_usd=0.02,
        user_id=test_user_id
    )

    # Create artifact
    artifact_id = create_artifact(
        checkpoint_id=checkpoint_id,
        artifact_type='spec',
        artifact_key='spec',
        s3_url='',
        s3_key='',
        version=1,
        metadata={'spec': sample_phase_output['output_data']['spec']}
    )

    assert artifact_id.startswith('art-')

    # Verify artifact was created
    artifacts = get_checkpoint_artifacts(checkpoint_id)
    assert len(artifacts) == 1
    assert artifacts[0]['artifact_type'] == 'spec'
    assert artifacts[0]['artifact_key'] == 'spec'
    assert artifacts[0]['version'] == 1

    # Cleanup
    conn = get_test_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM checkpoint_artifacts WHERE id = %s", (artifact_id,))
            cur.execute("DELETE FROM video_checkpoints WHERE id = %s", (checkpoint_id,))
        conn.commit()
    finally:
        conn.close()


def test_get_checkpoint(test_video_id, test_user_id, sample_phase_output):
    """Test retrieving a checkpoint by ID."""
    checkpoint_id = create_checkpoint(
        video_id=test_video_id,
        branch_name='main',
        phase_number=1,
        version=1,
        phase_output=sample_phase_output,
        cost_usd=0.02,
        user_id=test_user_id
    )

    checkpoint = get_checkpoint(checkpoint_id)
    assert checkpoint is not None
    assert checkpoint['id'] == checkpoint_id
    assert checkpoint['video_id'] == test_video_id

    # Test non-existent checkpoint
    non_existent = get_checkpoint('cp-nonexistent')
    assert non_existent is None

    # Cleanup
    conn = get_test_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM video_checkpoints WHERE id = %s", (checkpoint_id,))
        conn.commit()
    finally:
        conn.close()


def test_list_checkpoints_by_branch(test_video_id, test_user_id, sample_phase_output):
    """Test listing checkpoints filtered by branch."""
    # Create checkpoints on different branches
    cp1_id = create_checkpoint(
        video_id=test_video_id,
        branch_name='main',
        phase_number=1,
        version=1,
        phase_output=sample_phase_output,
        cost_usd=0.02,
        user_id=test_user_id
    )

    cp2_id = create_checkpoint(
        video_id=test_video_id,
        branch_name='main-1',
        phase_number=2,
        version=1,
        phase_output=sample_phase_output,
        cost_usd=0.03,
        user_id=test_user_id
    )

    # List all checkpoints
    all_checkpoints = list_checkpoints(test_video_id)
    assert len(all_checkpoints) == 2

    # List main branch only
    main_checkpoints = list_checkpoints(test_video_id, branch_name='main')
    assert len(main_checkpoints) == 1
    assert main_checkpoints[0]['branch_name'] == 'main'

    # Cleanup
    conn = get_test_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM video_checkpoints WHERE id IN (%s, %s)", (cp1_id, cp2_id))
        conn.commit()
    finally:
        conn.close()


def test_checkpoint_tree_query(test_video_id, test_user_id, sample_phase_output):
    """Test recursive CTE returns tree structure."""
    # Create parent checkpoint
    parent_id = create_checkpoint(
        video_id=test_video_id,
        branch_name='main',
        phase_number=1,
        version=1,
        phase_output=sample_phase_output,
        cost_usd=0.02,
        user_id=test_user_id
    )

    # Create child checkpoint
    child_id = create_checkpoint(
        video_id=test_video_id,
        branch_name='main',
        phase_number=2,
        version=1,
        phase_output=sample_phase_output,
        cost_usd=0.03,
        user_id=test_user_id,
        parent_checkpoint_id=parent_id
    )

    # Get tree
    tree = get_checkpoint_tree(test_video_id)
    assert len(tree) == 2
    assert tree[0]['depth'] == 0  # Parent
    assert tree[1]['depth'] == 1  # Child

    # Cleanup
    conn = get_test_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM video_checkpoints WHERE id IN (%s, %s)", (child_id, parent_id))
        conn.commit()
    finally:
        conn.close()


def test_approve_checkpoint(test_video_id, test_user_id, sample_phase_output):
    """Test approving a checkpoint sets approved_at timestamp."""
    checkpoint_id = create_checkpoint(
        video_id=test_video_id,
        branch_name='main',
        phase_number=1,
        version=1,
        phase_output=sample_phase_output,
        cost_usd=0.02,
        user_id=test_user_id
    )

    # Approve checkpoint
    result = approve_checkpoint(checkpoint_id)
    assert result is True

    # Verify approved_at is set
    checkpoint = get_checkpoint(checkpoint_id)
    assert checkpoint['status'] == 'approved'
    assert checkpoint['approved_at'] is not None

    # Cleanup
    conn = get_test_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM video_checkpoints WHERE id = %s", (checkpoint_id,))
        conn.commit()
    finally:
        conn.close()


def test_next_version_number(test_video_id, test_user_id, sample_phase_output):
    """Test calculating next version number (v1, v2, v3)."""
    # First version should be 1
    next_v = get_next_version_number(test_video_id, 'main', 1)
    assert next_v == 1

    # Create v1
    cp1_id = create_checkpoint(
        video_id=test_video_id,
        branch_name='main',
        phase_number=1,
        version=1,
        phase_output=sample_phase_output,
        cost_usd=0.02,
        user_id=test_user_id
    )

    # Next version should be 2
    next_v = get_next_version_number(test_video_id, 'main', 1)
    assert next_v == 2

    # Cleanup
    conn = get_test_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM video_checkpoints WHERE id = %s", (cp1_id,))
        conn.commit()
    finally:
        conn.close()


def test_branch_name_generation(test_video_id, test_user_id, sample_phase_output):
    """Test branch name generation: main → main-1 → main-1-1."""
    # main → main-1
    branch1 = generate_branch_name('main', test_video_id)
    assert branch1 == 'main-1'

    # Create checkpoint on main-1
    cp1_id = create_checkpoint(
        video_id=test_video_id,
        branch_name='main-1',
        phase_number=1,
        version=1,
        phase_output=sample_phase_output,
        cost_usd=0.02,
        user_id=test_user_id
    )

    # main-1 → main-1-1
    branch2 = generate_branch_name('main-1', test_video_id)
    assert branch2 == 'main-1-1'

    # Create another branch from main should give main-2
    branch3 = generate_branch_name('main', test_video_id)
    assert branch3 == 'main-2'  # main-2 since main-1 already exists

    # Cleanup
    conn = get_test_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM video_checkpoints WHERE id = %s", (cp1_id,))
        conn.commit()
    finally:
        conn.close()


def test_foreign_key_constraints(test_video_id, test_user_id, sample_phase_output):
    """Test cascading deletes work correctly."""
    # Create checkpoint
    checkpoint_id = create_checkpoint(
        video_id=test_video_id,
        branch_name='main',
        phase_number=1,
        version=1,
        phase_output=sample_phase_output,
        cost_usd=0.02,
        user_id=test_user_id
    )

    # Create artifact
    artifact_id = create_artifact(
        checkpoint_id=checkpoint_id,
        artifact_type='spec',
        artifact_key='spec',
        s3_url='',
        s3_key='',
        version=1
    )

    # Delete checkpoint (should cascade to artifact)
    conn = get_test_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM video_checkpoints WHERE id = %s", (checkpoint_id,))
        conn.commit()

        # Verify artifact was also deleted
        artifacts = get_checkpoint_artifacts(checkpoint_id)
        assert len(artifacts) == 0
    finally:
        conn.close()


def test_get_current_checkpoint(test_video_id, test_user_id, sample_phase_output):
    """Test getting most recent pending checkpoint."""
    # Create two checkpoints
    cp1_id = create_checkpoint(
        video_id=test_video_id,
        branch_name='main',
        phase_number=1,
        version=1,
        phase_output=sample_phase_output,
        cost_usd=0.02,
        user_id=test_user_id
    )

    cp2_id = create_checkpoint(
        video_id=test_video_id,
        branch_name='main',
        phase_number=2,
        version=1,
        phase_output=sample_phase_output,
        cost_usd=0.03,
        user_id=test_user_id
    )

    # Get current (should be most recent)
    current = get_current_checkpoint(test_video_id)
    assert current is not None
    assert current['id'] == cp2_id

    # Approve both
    approve_checkpoint(cp1_id)
    approve_checkpoint(cp2_id)

    # Should return None now
    current = get_current_checkpoint(test_video_id)
    assert current is None

    # Cleanup
    conn = get_test_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM video_checkpoints WHERE id IN (%s, %s)", (cp1_id, cp2_id))
        conn.commit()
    finally:
        conn.close()


def test_get_leaf_checkpoints(test_video_id, test_user_id, sample_phase_output):
    """Test finding checkpoints with no children."""
    # Create parent
    parent_id = create_checkpoint(
        video_id=test_video_id,
        branch_name='main',
        phase_number=1,
        version=1,
        phase_output=sample_phase_output,
        cost_usd=0.02,
        user_id=test_user_id
    )

    # Create child (leaf)
    child_id = create_checkpoint(
        video_id=test_video_id,
        branch_name='main',
        phase_number=2,
        version=1,
        phase_output=sample_phase_output,
        cost_usd=0.03,
        user_id=test_user_id,
        parent_checkpoint_id=parent_id
    )

    # Get leaf checkpoints
    leaves = get_leaf_checkpoints(test_video_id)
    assert len(leaves) == 1
    assert leaves[0]['id'] == child_id  # Only child is a leaf

    # Cleanup
    conn = get_test_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM video_checkpoints WHERE id IN (%s, %s)", (child_id, parent_id))
        conn.commit()
    finally:
        conn.close()


def test_latest_artifacts_mixed_versions(test_video_id, test_user_id, sample_phase_output):
    """Test get_latest_artifacts returns all artifacts for a checkpoint."""
    # Create checkpoint
    checkpoint_id = create_checkpoint(
        video_id=test_video_id,
        branch_name='main',
        phase_number=2,
        version=1,
        phase_output=sample_phase_output,
        cost_usd=0.02,
        user_id=test_user_id
    )

    # Create beat artifacts (each checkpoint can only have one version of each artifact due to unique constraint)
    art1_id = create_artifact(
        checkpoint_id=checkpoint_id,
        artifact_type='beat_image',
        artifact_key='beat_0',
        s3_url='s3://bucket/beat_0_v1.png',
        s3_key='beat_0_v1.png',
        version=1
    )

    art2_id = create_artifact(
        checkpoint_id=checkpoint_id,
        artifact_type='beat_image',
        artifact_key='beat_1',
        s3_url='s3://bucket/beat_1_v1.png',
        s3_key='beat_1_v1.png',
        version=1
    )

    art3_id = create_artifact(
        checkpoint_id=checkpoint_id,
        artifact_type='spec',
        artifact_key='spec',
        s3_url='s3://bucket/spec_v1.json',
        s3_key='spec_v1.json',
        version=1
    )

    # Get latest artifacts
    latest = get_latest_artifacts_for_checkpoint(checkpoint_id)

    # All artifacts should be returned
    assert len(latest) == 3
    assert 'beat_0' in latest
    assert 'beat_1' in latest
    assert 'spec' in latest
    assert latest['beat_0']['version'] == 1
    assert latest['beat_1']['version'] == 1
    assert latest['spec']['version'] == 1

    # Cleanup
    conn = get_test_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM checkpoint_artifacts WHERE checkpoint_id = %s", (checkpoint_id,))
            cur.execute("DELETE FROM video_checkpoints WHERE id = %s", (checkpoint_id,))
        conn.commit()
    finally:
        conn.close()


def test_indexes_created():
    """Test that all required indexes were created."""
    conn = get_test_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT indexname FROM pg_indexes
                WHERE tablename IN ('video_checkpoints', 'checkpoint_artifacts')
            """)
            indexes = [row[0] for row in cur.fetchall()]

            required_indexes = [
                'idx_checkpoints_video',
                'idx_checkpoints_branch',
                'idx_checkpoints_parent',
                'idx_checkpoints_status',
                'idx_artifacts_checkpoint',
                'idx_artifacts_type',
                'idx_artifacts_parent'
            ]

            for idx in required_indexes:
                assert idx in indexes, f"Index {idx} should exist"
    finally:
        conn.close()


def test_check_constraints_enforced(test_video_id, test_user_id, sample_phase_output):
    """Test that check constraints work (phase_number must be 1-4)."""
    # Try to create checkpoint with invalid phase_number
    conn = get_test_connection()
    try:
        with conn.cursor() as cur:
            with pytest.raises(Exception):  # Should raise constraint violation
                cur.execute("""
                    INSERT INTO video_checkpoints (
                        id, video_id, branch_name, phase_number, version,
                        status, phase_output, cost_usd, user_id
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    f"cp-{uuid.uuid4()}", test_video_id, 'main', 5, 1,
                    'pending', '{}', 0.0, test_user_id
                ))
        conn.rollback()
    finally:
        conn.close()


def test_unique_constraints_work(test_video_id, test_user_id, sample_phase_output):
    """Test that unique constraint on (video_id, branch, phase, version) works."""
    # Create checkpoint
    checkpoint_id = create_checkpoint(
        video_id=test_video_id,
        branch_name='main',
        phase_number=1,
        version=1,
        phase_output=sample_phase_output,
        cost_usd=0.02,
        user_id=test_user_id
    )

    # Try to create duplicate
    conn = get_test_connection()
    try:
        with conn.cursor() as cur:
            with pytest.raises(Exception):  # Should raise unique violation
                cur.execute("""
                    INSERT INTO video_checkpoints (
                        id, video_id, branch_name, phase_number, version,
                        status, phase_output, cost_usd, user_id
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    f"cp-{uuid.uuid4()}", test_video_id, 'main', 1, 1,
                    'pending', '{}', 0.0, test_user_id
                ))
        conn.rollback()

        # Cleanup
        with conn.cursor() as cur:
            cur.execute("DELETE FROM video_checkpoints WHERE id = %s", (checkpoint_id,))
        conn.commit()
    finally:
        conn.close()
