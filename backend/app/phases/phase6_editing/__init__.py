"""
Phase 6: User Editing & Chunk Regeneration

Enables users to edit, preview, and regenerate video chunks after Phase 3 (chunk generation)
and before Phase 4 (refinement).

Key Features:
- Preview individual chunks
- Replace chunks (generate new version while keeping original for comparison)
- Compare versions side-by-side (original vs new)
- Select which version to keep after comparison
- Delete chunks
- Reorder and split chunks
- Frame-level editing
- Cost preview and selective regeneration
"""

from .task import edit_chunks
from .service import EditingService
from .chunk_manager import ChunkManager
from .schemas import (
    EditingAction,
    ReplaceChunkAction,
    SelectVersionAction,
    ReorderChunkAction,
    DeleteChunkAction,
    SplitChunkAction,
    ChunkVersion,
    EditingRequest,
    EditingResponse,
    CostEstimate,
)

__all__ = [
    'edit_chunks',
    'EditingService',
    'ChunkManager',
    'EditingAction',
    'ReplaceChunkAction',
    'SelectVersionAction',
    'ReorderChunkAction',
    'DeleteChunkAction',
    'SplitChunkAction',
    'ChunkVersion',
    'EditingRequest',
    'EditingResponse',
    'CostEstimate',
]

