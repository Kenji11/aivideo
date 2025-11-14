export interface GenerateVideoRequest {
  projectTitle: string
  description?: string
  prompt: string
  assets: File[]
}

export interface VideoGeneration {
  video_id: string
  status: 'queued' | 'validating' | 'generating_animatic' | 'generating_references' | 
          'generating_chunks' | 'refining' | 'exporting' | 'complete' | 'failed'
  progress: number
  current_phase?: string
  error_message?: string
}
