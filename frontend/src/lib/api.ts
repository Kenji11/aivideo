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
  animatic_urls?: string[];
  stitched_video_url?: string;
  final_video_url?: string;  // Phase 5 final video (with audio)
  current_chunk_index?: number;  // Current chunk being processed (0-based)
  total_chunks?: number;  // Total number of chunks
}

export interface VideoResponse {
  video_id: string;
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
 * Delete a video
 */
export async function deleteVideo(videoId: string): Promise<void> {
  return api.deleteVideo(videoId);
}

export default api;

