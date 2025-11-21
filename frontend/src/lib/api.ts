import axios from 'axios';
import { getIdToken } from './firebase';

// Get API URL from environment variable, default to localhost:8000
const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// Create axios instance with base configuration
const apiClient = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor for adding Firebase auth token and logging
apiClient.interceptors.request.use(
  async (config) => {
    // Add Firebase ID token to request headers if user is authenticated
    try {
      const token = await getIdToken();
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
        console.log(`[API] Added auth token to ${config.method?.toUpperCase()} ${config.url}`);
      } else {
        console.warn(`[API] No auth token available for ${config.method?.toUpperCase()} ${config.url}`);
      }
    } catch (error) {
      // If token retrieval fails, log the error
      console.error('[API] Failed to get auth token:', error);
      console.warn(`[API] Request will proceed without token: ${config.method?.toUpperCase()} ${config.url}`);
    }
    
    console.log(`[API] ${config.method?.toUpperCase()} ${config.url}`);
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor for error handling
apiClient.interceptors.response.use(
  (response) => {
    return response;
  },
  (error) => {
    if (error.response) {
      // Server responded with error status
      const status = error.response.status;
      const detail = error.response.data?.detail || error.response.data?.message || 'An error occurred';
      
      // Don't log 404 errors for status endpoint - these are expected for completed videos
      const isStatusEndpoint404 = status === 404 && error.config?.url?.includes('/api/status/');
      if (!isStatusEndpoint404) {
        console.error('[API] Error response:', error.response.data);
      }
      
      throw new Error(detail);
    } else if (error.request) {
      // Request was made but no response received
      console.error('[API] No response received:', error.request);
      throw new Error('Unable to connect to server. Please check your connection.');
    } else {
      // Something else happened
      console.error('[API] Error:', error.message);
      throw error;
    }
  }
);

// API types
export interface GenerateRequest {
  title?: string;
  description?: string;
  prompt: string;
  assets?: string[]; // For backward compatibility, can also be reference_assets
  reference_assets?: string[];
  model?: string; // Video generation model to use (e.g., 'hailuo', 'kling', 'sora')
}

export interface GenerateResponse {
  video_id: string;
  status: string;
  message: string;
}

export interface ReferenceAssets {
  style_guide_url?: string;
  product_reference_url?: string;
  uploaded_assets?: Array<{
    asset_id: string;
    filename: string;
    asset_type: string;
    file_size_bytes: number;
    s3_url: string;
  }>;
}

export interface StatusResponse {
  video_id: string;
  status: string;
  progress: number;
  current_phase?: string;
  estimated_time_remaining?: number;
  error?: string;
  reference_assets?: ReferenceAssets;
  storyboard_urls?: string[];
  chunk_urls?: string[];  // Phase 3 individual chunk videos
  stitched_video_url?: string;
  final_video_url?: string;  // Phase 5 final video (with audio)
  current_chunk_index?: number;  // Current chunk being processed (0-based)
  total_chunks?: number;  // Total number of chunks
  // Checkpoint fields
  current_checkpoint?: CheckpointInfo;
  checkpoint_tree?: CheckpointTreeNode[];
  active_branches?: BranchInfo[];
}

export interface VideoResponse {
  video_id: string;
  title: string;
  description?: string;
  status: string;
  final_video_url?: string;
  cost_usd: number;
  generation_time_seconds?: number;
  created_at: string;
  completed_at?: string;
  spec?: any;
  animatic_urls?: string[];
  storyboard_urls?: string[];
  chunk_urls?: string[];
}

export interface UploadedAsset {
  asset_id: string;
  filename: string;
  asset_type: string;
  file_size_bytes: number;
  s3_url: string;
}

export interface UploadResponse {
  assets: UploadedAsset[];
  total: number;
  errors?: string[];
  partial_success?: boolean;
}

export interface AssetListItem {
  asset_id: string;
  filename: string;
  asset_type: string;
  file_size_bytes: number;
  s3_url: string;
  created_at?: string;
}

export interface AssetListResponse {
  assets: AssetListItem[];
  total: number;
  user_id: string;
}

export interface VideoListItem {
  video_id: string;
  title: string;
  status: string;
  progress: number;
  current_phase?: string;
  final_video_url?: string;
  cost_usd: number;
  created_at: string;
  completed_at?: string;
}

export interface VideoListResponse {
  videos: VideoListItem[];
  total: number;
}

// Checkpoint-related types
export interface CheckpointListResponse {
  checkpoints: CheckpointResponse[];
  tree: CheckpointTreeNode[];
}

export interface CheckpointDetailResponse {
  checkpoint: CheckpointResponse;
  artifacts: ArtifactResponse[];
}

export interface ContinueRequest {
  checkpoint_id: string;
}

export interface ContinueResponse {
  message: string;
  next_phase: number;
  branch_name: string;
  created_new_branch: boolean;
}

export interface SpecEditRequest {
  beats?: any[];
  style?: any;
  product?: any;
  audio?: any;
}

export interface RegenerateBeatRequest {
  beat_index: number;
  prompt_override?: string;
}

export interface RegenerateChunkRequest {
  chunk_index: number;
  model_override?: string;
}

// API functions
export const api = {
  /**
   * Generate a new video
   */
  async generateVideo(request: GenerateRequest): Promise<GenerateResponse> {
    const response = await apiClient.post<GenerateResponse>('/api/generate', request);
    return response.data;
  },

  /**
   * Get video generation status
   */
  async getStatus(videoId: string): Promise<StatusResponse> {
    const response = await apiClient.get<StatusResponse>(`/api/status/${videoId}`);
    return response.data;
  },

  /**
   * Get video details
   */
  async getVideo(videoId: string): Promise<VideoResponse> {
    const response = await apiClient.get<VideoResponse>(`/api/video/${videoId}`);
    return response.data;
  },

  /**
   * Upload assets (images, videos, PDFs)
   */
  async uploadAssets(
    files: File[],
    onProgress?: (progress: number) => void
  ): Promise<UploadResponse> {
    const formData = new FormData();
    files.forEach((file) => {
      formData.append('files', file);
    });

    const response = await apiClient.post<UploadResponse>('/api/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      onUploadProgress: (progressEvent: any) => {
        if (onProgress && progressEvent.total) {
          const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total);
          onProgress(percentCompleted);
        }
      },
    });

    return response.data;
  },

  /**
   * Get all assets for a user
   */
  async getAssets(userId?: string): Promise<AssetListResponse> {
    const params = userId ? { user_id: userId } : {};
    const response = await apiClient.get<AssetListResponse>('/api/assets', { params });
    return response.data;
  },

  /**
   * Get all videos
   */
  async getVideos(): Promise<VideoListResponse> {
    const response = await apiClient.get<VideoListResponse>('/api/videos');
    return response.data;
  },

  /**
   * Delete a video
   */
  async deleteVideo(videoId: string): Promise<void> {
    await apiClient.delete(`/api/video/${videoId}`);
  },

  // Checkpoint endpoints

  /**
   * List all checkpoints for a video
   */
  async listCheckpoints(videoId: string, branch?: string): Promise<CheckpointListResponse> {
    const params = branch ? { branch } : {};
    const response = await apiClient.get<CheckpointListResponse>(
      `/api/video/${videoId}/checkpoints`,
      { params }
    );
    return response.data;
  },

  /**
   * Get checkpoint details
   */
  async getCheckpoint(videoId: string, checkpointId: string): Promise<CheckpointDetailResponse> {
    const response = await apiClient.get<CheckpointDetailResponse>(
      `/api/video/${videoId}/checkpoints/${checkpointId}`
    );
    return response.data;
  },

  /**
   * Get current checkpoint (most recent pending)
   */
  async getCurrentCheckpoint(videoId: string): Promise<{ checkpoint: CheckpointResponse | null }> {
    const response = await apiClient.get<{ checkpoint: CheckpointResponse | null }>(
      `/api/video/${videoId}/checkpoints/current`
    );
    return response.data;
  },

  /**
   * Get checkpoint tree structure
   */
  async getCheckpointTree(videoId: string): Promise<{ tree: CheckpointTreeNode[] }> {
    const response = await apiClient.get<{ tree: CheckpointTreeNode[] }>(
      `/api/video/${videoId}/checkpoints/tree`
    );
    return response.data;
  },

  /**
   * List active branches
   */
  async listBranches(videoId: string): Promise<{ branches: BranchInfo[] }> {
    const response = await apiClient.get<{ branches: BranchInfo[] }>(
      `/api/video/${videoId}/branches`
    );
    return response.data;
  },

  /**
   * Continue pipeline from checkpoint
   */
  async continueVideo(videoId: string, checkpointId: string): Promise<ContinueResponse> {
    const response = await apiClient.post<ContinueResponse>(
      `/api/video/${videoId}/continue`,
      { checkpoint_id: checkpointId }
    );
    return response.data;
  },

  // Artifact editing endpoints

  /**
   * Edit spec at Phase 1
   */
  async editSpec(
    videoId: string,
    checkpointId: string,
    edits: SpecEditRequest
  ): Promise<{ artifact_id: string; version: number }> {
    const response = await apiClient.patch<{ artifact_id: string; version: number }>(
      `/api/video/${videoId}/checkpoints/${checkpointId}/spec`,
      edits
    );
    return response.data;
  },

  /**
   * Upload replacement image for beat at Phase 2
   */
  async uploadBeatImage(
    videoId: string,
    checkpointId: string,
    beatIndex: number,
    file: File
  ): Promise<{ artifact_id: string; s3_url: string; version: number }> {
    const formData = new FormData();
    formData.append('beat_index', beatIndex.toString());
    formData.append('image', file);

    const response = await apiClient.post<{ artifact_id: string; s3_url: string; version: number }>(
      `/api/video/${videoId}/checkpoints/${checkpointId}/upload-image`,
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      }
    );
    return response.data;
  },

  /**
   * Regenerate beat image at Phase 2
   */
  async regenerateBeat(
    videoId: string,
    checkpointId: string,
    request: RegenerateBeatRequest
  ): Promise<{ artifact_id: string; s3_url: string; version: number }> {
    const response = await apiClient.post<{ artifact_id: string; s3_url: string; version: number }>(
      `/api/video/${videoId}/checkpoints/${checkpointId}/regenerate-beat`,
      request
    );
    return response.data;
  },

  /**
   * Regenerate video chunk at Phase 3
   */
  async regenerateChunk(
    videoId: string,
    checkpointId: string,
    request: RegenerateChunkRequest
  ): Promise<{ artifact_id: string; s3_url: string; version: number }> {
    const response = await apiClient.post<{ artifact_id: string; s3_url: string; version: number }>(
      `/api/video/${videoId}/checkpoints/${checkpointId}/regenerate-chunk`,
      request
    );
    return response.data;
  },
};

// Named exports for convenience
/**
 * Generate a new video
 */
export async function generateVideo(request: GenerateRequest): Promise<GenerateResponse> {
  // Normalize request: map assets to reference_assets if needed for backward compatibility
  const normalizedRequest: Omit<GenerateRequest, 'assets'> & { reference_assets: string[] } = {
    title: request.title,
    description: request.description,
    prompt: request.prompt,
    reference_assets: request.reference_assets || request.assets || [],
    model: request.model, // Include model selection
  };
  return api.generateVideo(normalizedRequest);
}

/**
 * Get video generation status
 */
export async function getVideoStatus(videoId: string): Promise<StatusResponse> {
  return api.getStatus(videoId);
}

/**
 * Get all videos
 */
export async function listVideos(): Promise<VideoListResponse> {
  return api.getVideos();
}

/**
 * Get video details
 */
export async function getVideo(videoId: string): Promise<VideoResponse> {
  return api.getVideo(videoId);
}

/**
 * Delete a video
 */
export async function deleteVideo(videoId: string): Promise<void> {
  return api.deleteVideo(videoId);
}

// Checkpoint convenience exports

/**
 * List checkpoints for a video
 */
export async function listCheckpoints(videoId: string, branch?: string): Promise<CheckpointListResponse> {
  return api.listCheckpoints(videoId, branch);
}

/**
 * Get checkpoint details
 */
export async function getCheckpoint(videoId: string, checkpointId: string): Promise<CheckpointDetailResponse> {
  return api.getCheckpoint(videoId, checkpointId);
}

/**
 * Get current checkpoint
 */
export async function getCurrentCheckpoint(videoId: string): Promise<{ checkpoint: CheckpointResponse | null }> {
  return api.getCurrentCheckpoint(videoId);
}

/**
 * Get checkpoint tree
 */
export async function getCheckpointTree(videoId: string): Promise<{ tree: CheckpointTreeNode[] }> {
  return api.getCheckpointTree(videoId);
}

/**
 * List active branches
 */
export async function listBranches(videoId: string): Promise<{ branches: BranchInfo[] }> {
  return api.listBranches(videoId);
}

/**
 * Continue pipeline from checkpoint
 */
export async function continueVideo(videoId: string, checkpointId: string): Promise<ContinueResponse> {
  return api.continueVideo(videoId, checkpointId);
}

/**
 * Edit spec at Phase 1
 */
export async function editSpec(
  videoId: string,
  checkpointId: string,
  edits: SpecEditRequest
): Promise<{ artifact_id: string; version: number }> {
  return api.editSpec(videoId, checkpointId, edits);
}

/**
 * Upload replacement image for beat
 */
export async function uploadBeatImage(
  videoId: string,
  checkpointId: string,
  beatIndex: number,
  file: File
): Promise<{ artifact_id: string; s3_url: string; version: number }> {
  return api.uploadBeatImage(videoId, checkpointId, beatIndex, file);
}

/**
 * Regenerate beat image
 */
export async function regenerateBeat(
  videoId: string,
  checkpointId: string,
  request: RegenerateBeatRequest
): Promise<{ artifact_id: string; s3_url: string; version: number }> {
  return api.regenerateBeat(videoId, checkpointId, request);
}

/**
 * Regenerate video chunk
 */
export async function regenerateChunk(
  videoId: string,
  checkpointId: string,
  request: RegenerateChunkRequest
): Promise<{ artifact_id: string; s3_url: string; version: number }> {
  return api.regenerateChunk(videoId, checkpointId, request);
}

export default api;

