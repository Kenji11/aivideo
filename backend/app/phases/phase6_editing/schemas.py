"""
Pydantic models for Phase 6 editing actions and responses.
"""
from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Dict, Literal, Union
from enum import Enum


class EditingActionType(str, Enum):
    """Types of editing actions"""
    REPLACE = "replace"
    SELECT_VERSION = "select_version"
    REORDER = "reorder"
    DELETE = "delete"
    SPLIT = "split"
    UNDO_SPLIT = "undo_split"


class ChunkVersion(BaseModel):
    """Model for chunk version (original, replacement_1, etc.)"""
    version_id: str = Field(..., description="Version identifier (e.g., 'original', 'replacement_1')")
    url: str = Field(..., description="S3 URL of the chunk version")
    prompt: Optional[str] = Field(None, description="Prompt used for this version")
    model: Optional[str] = Field(None, description="Model used for this version")
    cost: Optional[float] = Field(None, description="Cost of generating this version")
    created_at: Optional[str] = Field(None, description="Timestamp when version was created")
    is_selected: bool = Field(False, description="Whether this version is currently selected")


class EditingAction(BaseModel):
    """Base class for editing actions"""
    action_type: EditingActionType = Field(..., description="Type of editing action")
    chunk_indices: List[int] = Field(..., description="List of chunk indices to apply action to")


class ReplaceChunkAction(EditingAction):
    """Replace chunks (generate new version, keep original)"""
    action_type: Literal[EditingActionType.REPLACE] = EditingActionType.REPLACE
    new_prompt: Optional[str] = Field(None, description="New prompt for replacement (if None, uses original)")
    new_model: Optional[str] = Field(None, description="New model for replacement (if None, uses original)")
    keep_original: bool = Field(True, description="Whether to keep original version for comparison")


class SelectVersionAction(EditingAction):
    """User selects which version to keep"""
    action_type: Literal[EditingActionType.SELECT_VERSION] = EditingActionType.SELECT_VERSION
    version: str = Field(..., description="Version to select (e.g., 'original', 'replacement_1')")


class ReorderChunkAction(EditingAction):
    """Reorder chunks"""
    action_type: Literal[EditingActionType.REORDER] = EditingActionType.REORDER
    new_order: List[int] = Field(..., description="New order of chunk indices")


class DeleteChunkAction(EditingAction):
    """Delete chunks"""
    action_type: Literal[EditingActionType.DELETE] = EditingActionType.DELETE


class SplitChunkAction(EditingAction):
    """Split chunk at specific time or frame"""
    action_type: Literal[EditingActionType.SPLIT] = EditingActionType.SPLIT
    split_time: Optional[float] = Field(None, description="Time in seconds to split at (preferred)")
    split_frame: Optional[int] = Field(None, description="Frame number to split at (fallback if split_time not provided)")
    split_percentage: Optional[float] = Field(None, description="Percentage (0-100) to split at (alternative to time)")

class UndoSplitAction(EditingAction):
    """Undo a split operation, restore original chunk"""
    action_type: Literal[EditingActionType.UNDO_SPLIT] = EditingActionType.UNDO_SPLIT


class EditingRequest(BaseModel):
    """Request model for editing endpoint"""
    actions: List[Union[
        ReplaceChunkAction,
        SelectVersionAction,
        ReorderChunkAction,
        DeleteChunkAction,
        SplitChunkAction,
        UndoSplitAction,
        EditingAction  # Fallback for base class
    ]] = Field(..., description="List of editing actions to perform")
    estimate_cost_only: bool = Field(False, description="If True, only estimate cost without executing")
    
    @field_validator('actions', mode='before')
    @classmethod
    def parse_actions(cls, v):
        """Parse actions based on action_type to use correct model"""
        if not isinstance(v, list):
            return v
        
        parsed_actions = []
        for action in v:
            if isinstance(action, dict):
                action_type = action.get('action_type')
                
                # Parse based on action_type
                if action_type == EditingActionType.REPLACE.value or action_type == 'replace':
                    parsed_actions.append(ReplaceChunkAction(**action))
                elif action_type == EditingActionType.SPLIT.value or action_type == 'split':
                    parsed_actions.append(SplitChunkAction(**action))
                elif action_type == EditingActionType.UNDO_SPLIT.value or action_type == 'undo_split':
                    parsed_actions.append(UndoSplitAction(**action))
                elif action_type == EditingActionType.SELECT_VERSION.value or action_type == 'select_version':
                    parsed_actions.append(SelectVersionAction(**action))
                elif action_type == EditingActionType.REORDER.value or action_type == 'reorder':
                    parsed_actions.append(ReorderChunkAction(**action))
                elif action_type == EditingActionType.DELETE.value or action_type == 'delete':
                    parsed_actions.append(DeleteChunkAction(**action))
                else:
                    # Fallback to base class
                    parsed_actions.append(EditingAction(**action))
            else:
                # Already parsed or not a dict
                parsed_actions.append(action)
        
        return parsed_actions


class EditingResponse(BaseModel):
    """Response model for editing endpoint"""
    video_id: str
    status: str = Field(..., description="Status: 'success', 'failed', 'processing'")
    message: Optional[str] = None
    updated_chunk_urls: Optional[List[str]] = Field(None, description="Updated list of chunk URLs after editing")
    updated_stitched_url: Optional[str] = Field(None, description="Updated stitched video URL")
    total_cost: Optional[float] = Field(None, description="Total cost of regeneration")
    estimated_cost: Optional[float] = Field(None, description="Estimated cost (if estimate_cost_only=True)")


class CostEstimate(BaseModel):
    """Cost estimation model"""
    video_id: str
    chunk_indices: List[int]
    model: str
    estimated_cost: float = Field(..., description="Estimated cost in USD")
    estimated_time_seconds: Optional[float] = Field(None, description="Estimated generation time in seconds")
    cost_per_chunk: Dict[int, float] = Field(default_factory=dict, description="Cost per chunk index")


class ChunkMetadata(BaseModel):
    """Metadata for a single chunk"""
    chunk_index: int
    url: str
    prompt: str
    model: str
    cost: float
    duration: float
    versions: List[ChunkVersion] = Field(default_factory=list, description="All versions of this chunk")
    current_version: str = Field("original", description="Currently selected version")


class ChunksListResponse(BaseModel):
    """Response model for listing chunks"""
    video_id: str
    chunks: List[ChunkMetadata]
    total_chunks: int
    stitched_video_url: Optional[str] = None

