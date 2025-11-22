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
      }
    } catch (error) {
      // If token retrieval fails, log the error
      console.error('[API] Failed to get auth token:', error);
    }
    
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
      console.error('[API] Error response:', error.response.data);
      throw new Error(error.response.data?.detail || error.response.data?.message || 'An error occurred');
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
  stitched_video_url?: string;
  final_video_url?: string;  // Phase 5 final video (with audio)
  current_chunk_index?: number;  // Current chunk being processed (0-based)
  total_chunks?: number;  // Total number of chunks
}

export interface VideoResponse {
  video_id: string;
  title: string;
  status: string;
  final_video_url?: string;
  cost_usd: number;
  generation_time_seconds?: number;
  created_at: string;
  completed_at?: string;
  spec?: any;
  animatic_urls?: string[];
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
  name?: string;
  asset_type: string;
  reference_asset_type?: string;
  file_size_bytes: number;
  s3_url: string;
  thumbnail_url?: string;
  width?: number;
  height?: number;
  is_logo?: boolean;
  primary_object?: string;  // For hover tooltip
  analysis?: any;  // Analysis status indicator
  similarity_score?: number;  // For search results
  created_at?: string;
}

export interface AssetDetail extends AssetListItem {
  description?: string;
  has_transparency?: boolean;
  logo_position_preference?: string;
  primary_object?: string;
  colors?: string[];
  dominant_colors_rgb?: number[][];
  style_tags?: string[];
  recommended_shot_types?: string[];
  usage_contexts?: string[];
  usage_count?: number;
  updated_at?: string;
}

export interface AssetListResponse {
  assets: AssetListItem[];
  total: number;
  limit?: number;
  offset?: number;
  user_id: string;
}

export interface VideoListItem {
  video_id: string;
  title: string;
  status: string;
  progress: number;
  current_phase?: string;
  final_video_url?: string;
  thumbnail_url?: string;
  cost_usd: number;
  created_at: string;
  completed_at?: string;
}

export interface VideoListResponse {
  videos: VideoListItem[];
  total: number;
}

// Phase 6 Editing Types
export interface ChunkVersion {
  version_id: string;
  url: string;
  prompt?: string;
  model?: string;
  cost?: number;
  created_at?: string;
  is_selected: boolean;
}

export interface ChunkMetadata {
  chunk_index: number;
  url: string;
  prompt: string;
  model: string;
  cost: number;
  duration: number;
  versions: ChunkVersion[];
  current_version: string;
}

export interface ChunksListResponse {
  video_id: string;
  chunks: ChunkMetadata[];
  total_chunks: number;
  stitched_video_url?: string;
}

export interface EditingAction {
  action_type: 'replace' | 'select_version' | 'reorder' | 'delete' | 'split' | 'undo_split';
  chunk_indices: number[];
  new_prompt?: string;
  new_model?: string;
  keep_original?: boolean;
  version?: string;
  new_order?: number[];
  split_time?: number;  // Time in seconds (preferred)
  split_frame?: number;  // Frame number (fallback)
  split_percentage?: number;  // Percentage 0-100 (alternative)
}

export interface EditingRequest {
  actions: EditingAction[];
  estimate_cost_only?: boolean;
}

export interface EditingResponse {
  video_id: string;
  status: string;
  message?: string;
  updated_chunk_urls?: string[];
  updated_stitched_url?: string;
  total_cost?: number;
  estimated_cost?: number;
}

export interface CostEstimate {
  video_id: string;
  chunk_indices: number[];
  model: string;
  estimated_cost: number;
  estimated_time_seconds?: number;
  cost_per_chunk: Record<number, number>;
}

export interface EditingStatus {
  video_id: string;
  status: string;
  updated_chunk_urls?: string[];
  updated_stitched_url?: string;
  total_cost?: number;
  error_message?: string;
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
  async getAssets(params?: {
    reference_asset_type?: string;
    is_logo?: boolean;
    limit?: number;
    offset?: number;
  }): Promise<AssetListResponse> {
    const response = await apiClient.get<AssetListResponse>('/api/assets', { params });
    return response.data;
  },

  /**
   * Get a single asset by ID
   */
  async getAsset(assetId: string): Promise<AssetDetail> {
    const response = await apiClient.get<AssetDetail>(`/api/assets/${assetId}`);
    return response.data;
  },

  /**
   * Update asset metadata
   */
  async updateAsset(
    assetId: string,
    updates: {
      name?: string;
      description?: string;
      reference_asset_type?: string;
      logo_position_preference?: string;
    }
  ): Promise<AssetDetail> {
    const formData = new FormData();
    if (updates.name !== undefined) formData.append('name', updates.name);
    if (updates.description !== undefined) formData.append('description', updates.description);
    if (updates.reference_asset_type !== undefined) formData.append('reference_asset_type', updates.reference_asset_type);
    if (updates.logo_position_preference !== undefined) formData.append('logo_position_preference', updates.logo_position_preference);

    const response = await apiClient.patch<AssetDetail>(`/api/assets/${assetId}`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  /**
   * Delete an asset
   */
  async deleteAsset(assetId: string): Promise<void> {
    await apiClient.delete(`/api/assets/${assetId}`);
  },

  /**
   * Upload assets with metadata
   */
  async uploadAssetsWithMetadata(
    files: File[],
    metadata?: {
      name?: string;
      description?: string;
      reference_asset_type?: string;
    },
    onProgress?: (progress: number) => void
  ): Promise<UploadResponse> {
    const formData = new FormData();
    files.forEach((file) => {
      formData.append('files', file);
    });
    if (metadata?.name) formData.append('name', metadata.name);
    if (metadata?.description) formData.append('description', metadata.description);
    if (metadata?.reference_asset_type) formData.append('reference_asset_type', metadata.reference_asset_type);

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

  // Phase 6 Editing API functions
  /**
   * Submit editing actions for a video
   */
  async submitEdits(videoId: string, request: EditingRequest): Promise<EditingResponse> {
    const response = await apiClient.post<EditingResponse>(`/api/video/${videoId}/edit`, request);
    return response.data;
  },

  /**
   * Get cost estimate for editing
   */
  async estimateEditCost(
    videoId: string,
    chunkIndices: number[],
    model: string = 'hailuo'
  ): Promise<CostEstimate> {
    const response = await apiClient.post<CostEstimate>(
      `/api/video/${videoId}/edit/estimate`,
      null,
      {
        params: {
          chunk_indices: chunkIndices.join(','),
          model,
        },
      }
    );
    return response.data;
  },

  /**
   * Get all chunks for a video
   */
  async getChunks(videoId: string): Promise<ChunksListResponse> {
    const response = await apiClient.get<ChunksListResponse>(`/api/video/${videoId}/chunks`);
    return response.data;
  },

  /**
   * Get specific chunk metadata
   */
  async getChunk(videoId: string, chunkIndex: number): Promise<ChunkMetadata> {
    const response = await apiClient.get<ChunkMetadata>(
      `/api/video/${videoId}/chunks/${chunkIndex}`
    );
    return response.data;
  },

  /**
   * Get all versions of a chunk
   */
  async getChunkVersions(videoId: string, chunkIndex: number): Promise<ChunkVersion[]> {
    const response = await apiClient.get<ChunkVersion[]>(
      `/api/video/${videoId}/chunks/${chunkIndex}/versions`
    );
    return response.data;
  },

  /**
   * Get chunk preview URL
   */
  async getChunkPreview(
    videoId: string,
    chunkIndex: number,
    version: string = 'current'
  ): Promise<{ preview_url: string }> {
    const response = await apiClient.get<{ preview_url: string }>(
      `/api/video/${videoId}/chunks/${chunkIndex}/preview`,
      {
        params: { version },
      }
    );
    return response.data;
  },

  /**
   * Select which version to keep for a chunk
   */
  async selectChunkVersion(
    videoId: string,
    chunkIndex: number,
    version: string
  ): Promise<{ status: string; message: string }> {
    const response = await apiClient.post<{ status: string; message: string }>(
      `/api/video/${videoId}/chunks/${chunkIndex}/select-version`,
      null,
      {
        params: { version },
      }
    );
    return response.data;
  },

  /**
   * Get split info for a chunk (check if it can be undone)
   */
  async getChunkSplitInfo(
    videoId: string,
    chunkIndex: number
  ): Promise<{ is_split_part: boolean; original_index?: number; part_number?: number; original_url?: string; split_time?: number; part1_index?: number; part2_index?: number }> {
    const response = await apiClient.get(`/api/video/${videoId}/chunks/${chunkIndex}/split-info`);
    return response.data;
  },

  /**
   * Get editing status for a video
   */
  async getEditingStatus(videoId: string): Promise<EditingStatus> {
    const response = await apiClient.get<EditingStatus>(`/api/video/${videoId}/editing/status`);
    return response.data;
  },

  /**
   * Search assets by text query
   */
  async searchAssets(params: {
    q: string;
    asset_type?: string;
    limit?: number;
  }): Promise<AssetListResponse & { query: string }> {
    const response = await apiClient.get<AssetListResponse & { query: string }>('/api/assets/search', { params });
    return response.data;
  },

  /**
   * Find similar assets to a given asset
   */
  async getSimilarAssets(
    assetId: string,
    params?: {
      limit?: number;
      exclude_self?: boolean;
    }
  ): Promise<AssetListResponse & { reference_asset_id: string }> {
    const response = await apiClient.get<AssetListResponse & { reference_asset_id: string }>(
      `/api/assets/${assetId}/similar`,
      { params }
    );
    return response.data;
  },

  /**
   * Get style-consistent asset recommendations
   */
  async recommendAssets(selectedAssetIds: string[], limit?: number): Promise<AssetListResponse & { selected_asset_ids: string[] }> {
    const response = await apiClient.post<AssetListResponse & { selected_asset_ids: string[] }>(
      '/api/assets/recommend',
      {
        selected_asset_ids: selectedAssetIds,
        limit: limit || 10,
      }
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

export default api;

