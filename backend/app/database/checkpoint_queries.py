"""
Raw SQL query functions for checkpoint operations.

Uses psycopg2 for direct SQL execution instead of SQLAlchemy ORM.
Connection pooling is handled by SQLAlchemy engine.
"""
import uuid
import os
from typing import Dict, List, Optional, Any
from datetime import datetime
import psycopg2
from psycopg2.extras import RealDictCursor


def get_connection():
    """Get a database connection using psycopg2 directly."""
    # Try to import from app.database first (normal operation)
    try:
        from app.database import engine
        return engine.raw_connection()
    except Exception:
        # Fallback to direct connection using DATABASE_URL environment variable
        database_url = os.environ.get('DATABASE_URL', 'postgresql://dev:devpass@localhost:5434/videogen')
        return psycopg2.connect(database_url)


def create_checkpoint(
    video_id: str,
    branch_name: str,
    phase_number: int,
    version: int,
    phase_output: Dict,
    cost_usd: float,
    user_id: str,
    parent_checkpoint_id: Optional[str] = None,
    edit_description: Optional[str] = None
) -> str:
    """
    Create a checkpoint record.

    Returns:
        checkpoint_id: The ID of the created checkpoint
    """
    checkpoint_id = f"cp-{uuid.uuid4()}"

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO video_checkpoints (
                    id, video_id, branch_name, phase_number, version,
                    parent_checkpoint_id, status, phase_output, cost_usd,
                    user_id, edit_description
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
            """, (
                checkpoint_id, video_id, branch_name, phase_number, version,
                parent_checkpoint_id, 'pending', psycopg2.extras.Json(phase_output),
                cost_usd, user_id, edit_description
            ))
        conn.commit()
        return checkpoint_id
    finally:
        conn.close()


def get_checkpoint(checkpoint_id: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve checkpoint by ID.

    Returns:
        Checkpoint record as dictionary, or None if not found
    """
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT * FROM video_checkpoints
                WHERE id = %s
            """, (checkpoint_id,))
            result = cur.fetchone()
            return dict(result) if result else None
    finally:
        conn.close()


def list_checkpoints(
    video_id: str,
    branch_name: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    List checkpoints for a video, optionally filtered by branch.

    Returns:
        List of checkpoint records ordered by created_at
    """
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            if branch_name:
                cur.execute("""
                    SELECT * FROM video_checkpoints
                    WHERE video_id = %s AND branch_name = %s
                    ORDER BY created_at
                """, (video_id, branch_name))
            else:
                cur.execute("""
                    SELECT * FROM video_checkpoints
                    WHERE video_id = %s
                    ORDER BY created_at
                """, (video_id,))
            return [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()


def approve_checkpoint(checkpoint_id: str) -> bool:
    """
    Approve a checkpoint by setting approved_at timestamp.

    Returns:
        True if checkpoint was approved, False if not found
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE video_checkpoints
                SET status = 'approved', approved_at = NOW()
                WHERE id = %s
            """, (checkpoint_id,))
            updated = cur.rowcount > 0
        conn.commit()
        return updated
    finally:
        conn.close()


def get_checkpoint_tree(video_id: str) -> List[Dict[str, Any]]:
    """
    Get checkpoint tree structure using recursive CTE.

    Returns:
        List of checkpoint records with parent-child relationships
    """
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                WITH RECURSIVE checkpoint_tree AS (
                    -- Base case: root checkpoints (no parent)
                    SELECT *, 0 as depth
                    FROM video_checkpoints
                    WHERE video_id = %s AND parent_checkpoint_id IS NULL

                    UNION ALL

                    -- Recursive case: children
                    SELECT c.*, t.depth + 1
                    FROM video_checkpoints c
                    JOIN checkpoint_tree t ON c.parent_checkpoint_id = t.id
                )
                SELECT * FROM checkpoint_tree
                ORDER BY depth, created_at
            """, (video_id,))
            return [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()


def get_current_checkpoint(video_id: str) -> Optional[Dict[str, Any]]:
    """
    Get the most recent pending checkpoint for a video.

    Returns:
        Most recent pending checkpoint, or None if all approved
    """
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT * FROM video_checkpoints
                WHERE video_id = %s AND status = 'pending'
                ORDER BY created_at DESC
                LIMIT 1
            """, (video_id,))
            result = cur.fetchone()
            return dict(result) if result else None
    finally:
        conn.close()


def get_leaf_checkpoints(video_id: str) -> List[Dict[str, Any]]:
    """
    Get leaf checkpoints (checkpoints with no children) - active branches.

    Returns:
        List of checkpoint records that have no children
    """
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT c.* FROM video_checkpoints c
                WHERE c.video_id = %s
                AND c.id NOT IN (
                    SELECT parent_checkpoint_id
                    FROM video_checkpoints
                    WHERE parent_checkpoint_id IS NOT NULL
                )
                ORDER BY c.created_at DESC
            """, (video_id,))
            return [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()


def create_artifact(
    checkpoint_id: str,
    artifact_type: str,
    artifact_key: str,
    s3_url: str,
    s3_key: str,
    version: int,
    parent_artifact_id: Optional[str] = None,
    metadata: Optional[Dict] = None,
    file_size_bytes: Optional[int] = None
) -> str:
    """
    Create an artifact record.

    Returns:
        artifact_id: The ID of the created artifact
    """
    artifact_id = f"art-{uuid.uuid4()}"

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO checkpoint_artifacts (
                    id, checkpoint_id, artifact_type, artifact_key,
                    s3_url, s3_key, version, parent_artifact_id,
                    metadata, file_size_bytes
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
            """, (
                artifact_id, checkpoint_id, artifact_type, artifact_key,
                s3_url, s3_key, version, parent_artifact_id,
                psycopg2.extras.Json(metadata) if metadata else None,
                file_size_bytes
            ))
        conn.commit()
        return artifact_id
    finally:
        conn.close()


def get_checkpoint_artifacts(checkpoint_id: str) -> List[Dict[str, Any]]:
    """
    Get all artifacts for a checkpoint.

    Returns:
        List of artifact records ordered by artifact_key
    """
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT * FROM checkpoint_artifacts
                WHERE checkpoint_id = %s
                ORDER BY artifact_key
            """, (checkpoint_id,))
            return [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()


def get_latest_artifact_version(
    checkpoint_id: str,
    artifact_type: str,
    artifact_key: str
) -> Optional[Dict[str, Any]]:
    """
    Get the latest version of a specific artifact.

    Returns:
        Latest artifact record, or None if not found
    """
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT * FROM checkpoint_artifacts
                WHERE checkpoint_id = %s
                AND artifact_type = %s
                AND artifact_key = %s
                ORDER BY version DESC
                LIMIT 1
            """, (checkpoint_id, artifact_type, artifact_key))
            result = cur.fetchone()
            return dict(result) if result else None
    finally:
        conn.close()


def get_latest_artifacts_for_checkpoint(
    checkpoint_id: str
) -> Dict[str, Dict[str, Any]]:
    """
    Get the latest version of each artifact type/key combination.
    Handles mixed versions (e.g., beat_0 v1, beat_1 v2, beat_2 v1).

    Returns:
        Dictionary mapping artifact_key to artifact record
    """
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT DISTINCT ON (artifact_type, artifact_key) *
                FROM checkpoint_artifacts
                WHERE checkpoint_id = %s
                ORDER BY artifact_type, artifact_key, version DESC
            """, (checkpoint_id,))
            results = [dict(row) for row in cur.fetchall()]
            return {row['artifact_key']: row for row in results}
    finally:
        conn.close()


def get_next_version_number(
    video_id: str,
    branch_name: str,
    phase_number: int
) -> int:
    """
    Calculate the next version number for a phase on a branch.

    Returns:
        Next version number (1 if no previous versions exist)
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT MAX(version) FROM video_checkpoints
                WHERE video_id = %s
                AND branch_name = %s
                AND phase_number = %s
            """, (video_id, branch_name, phase_number))
            result = cur.fetchone()
            max_version = result[0] if result and result[0] else 0
            return max_version + 1
    finally:
        conn.close()


def generate_branch_name(parent_branch: str, video_id: str) -> str:
    """
    Generate a new branch name based on parent branch.

    Examples:
        main -> main-1
        main-1 -> main-1-1
        main-1-1 -> main-1-1-1

    Returns:
        New branch name with incremented counter
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            # Find all existing branches that start with parent_branch-
            cur.execute("""
                SELECT branch_name FROM video_checkpoints
                WHERE video_id = %s
                AND branch_name LIKE %s
            """, (video_id, f"{parent_branch}-%"))

            existing_branches = [row[0] for row in cur.fetchall()]

            # Extract numeric suffixes
            counters = []
            prefix = f"{parent_branch}-"
            for branch in existing_branches:
                if branch.startswith(prefix):
                    suffix = branch[len(prefix):]
                    # Only consider immediate children (single number)
                    if suffix.isdigit():
                        counters.append(int(suffix))

            # Get next counter
            next_counter = max(counters) + 1 if counters else 1
            return f"{parent_branch}-{next_counter}"
    finally:
        conn.close()


def has_checkpoint_been_edited(checkpoint_id: str) -> bool:
    """
    Check if any artifact has version > 1 (indicating edits).

    Returns:
        True if checkpoint has edited artifacts, False otherwise
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT EXISTS (
                    SELECT 1 FROM checkpoint_artifacts
                    WHERE checkpoint_id = %s
                    AND version > 1
                )
            """, (checkpoint_id,))
            result = cur.fetchone()
            return result[0] if result else False
    finally:
        conn.close()


def create_branch_from_checkpoint(
    checkpoint_id: str,
    user_id: str
) -> str:
    """
    Create a new branch when continuing from an edited checkpoint.

    Returns:
        New branch name
    """
    checkpoint = get_checkpoint(checkpoint_id)
    if not checkpoint:
        raise ValueError(f"Checkpoint {checkpoint_id} not found")

    new_branch = generate_branch_name(
        checkpoint['branch_name'],
        checkpoint['video_id']
    )

    return new_branch


def build_checkpoint_tree(video_id: str) -> List[Dict[str, Any]]:
    """
    Build a hierarchical tree structure from flat checkpoint list.

    Returns:
        List of root checkpoints with nested children
    """
    checkpoints = get_checkpoint_tree(video_id)

    # Build lookup map
    checkpoint_map = {cp['id']: {**cp, 'children': []} for cp in checkpoints}

    # Build tree structure
    roots = []
    for cp in checkpoints:
        if cp['parent_checkpoint_id']:
            parent = checkpoint_map.get(cp['parent_checkpoint_id'])
            if parent:
                parent['children'].append(checkpoint_map[cp['id']])
        else:
            roots.append(checkpoint_map[cp['id']])

    return roots


def update_artifact(
    artifact_id: str,
    s3_url: Optional[str] = None,
    s3_key: Optional[str] = None,
    version: Optional[int] = None,
    metadata: Optional[Dict] = None,
    parent_artifact_id: Optional[str] = None
) -> bool:
    """
    Update an existing artifact's fields.

    Args:
        artifact_id: ID of artifact to update
        s3_url: New S3 URL (optional)
        s3_key: New S3 key (optional)
        version: New version number (optional)
        metadata: New metadata (optional)
        parent_artifact_id: New parent artifact ID (optional)

    Returns:
        True if updated successfully
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            # Build dynamic UPDATE query
            updates = []
            params = []

            if s3_url is not None:
                updates.append("s3_url = %s")
                params.append(s3_url)

            if s3_key is not None:
                updates.append("s3_key = %s")
                params.append(s3_key)

            if version is not None:
                updates.append("version = %s")
                params.append(version)

            if metadata is not None:
                updates.append("metadata = %s")
                params.append(psycopg2.extras.Json(metadata))

            if parent_artifact_id is not None:
                updates.append("parent_artifact_id = %s")
                params.append(parent_artifact_id)

            if not updates:
                return False

            params.append(artifact_id)
            query = f"""
                UPDATE checkpoint_artifacts
                SET {", ".join(updates)}
                WHERE id = %s
            """

            cur.execute(query, params)
            updated = cur.rowcount > 0
        conn.commit()
        return updated
    finally:
        conn.close()


def update_checkpoint_phase_output(
    checkpoint_id: str,
    phase_output_updates: Dict
) -> bool:
    """
    Update checkpoint's phase_output field (merge with existing).

    Returns:
        True if updated successfully
    """
    checkpoint = get_checkpoint(checkpoint_id)
    if not checkpoint:
        return False

    # Merge updates with existing phase_output
    updated_output = {**checkpoint['phase_output'], **phase_output_updates}

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE video_checkpoints
                SET phase_output = %s
                WHERE id = %s
            """, (psycopg2.extras.Json(updated_output), checkpoint_id))
            updated = cur.rowcount > 0
        conn.commit()
        return updated
    finally:
        conn.close()
