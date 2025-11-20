import { Sparkles } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { UploadZone } from '../components/UploadZone';
import { generateVideo } from '../lib/api';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';

interface UploadVideoProps {
  title: string;
  description: string;
  prompt: string;
  selectedModel: string;
  uploadedAssetIds: string[];
  onTitleChange: (title: string) => void;
  onDescriptionChange: (description: string) => void;
  onPromptChange: (prompt: string) => void;
  onModelChange: (model: string) => void;
  onAssetsUploaded: (assetIds: string[]) => void;
  onNotification?: (type: 'success' | 'error', title: string, message: string) => void;
}

export function UploadVideo({
  title,
  description,
  prompt,
  selectedModel,
  uploadedAssetIds,
  onTitleChange,
  onDescriptionChange,
  onPromptChange,
  onModelChange,
  onAssetsUploaded,
  onNotification,
}: UploadVideoProps) {
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    try {
      console.log('[UploadVideo] handleSubmit called, generating video...');
      const response = await generateVideo({
        title: title || 'Untitled Video',
        description: description || undefined,
        prompt: prompt,
        reference_assets: uploadedAssetIds,
        model: selectedModel
      });
      
      console.log('[UploadVideo] Video generation started, navigating to:', `/processing/${response.video_id}`);
      // Navigate to processing page with videoId in route
      navigate(`/processing/${response.video_id}`);
      onNotification?.('success', 'Generation Started', 'Your video is being created...');
    } catch (error) {
      console.error('[UploadVideo] Failed to generate video:', error);
      onNotification?.('error', 'Generation Failed', error instanceof Error ? error.message : 'Unknown error');
    }
  };

  return (
    <div className="card p-8 animate-fade-in">
      <div className="mb-8">
        <h2 className="text-2xl font-bold text-card-foreground mb-2">
          Create Your Video
        </h2>
        <p className="text-muted-foreground">
          Describe your vision and let AI bring it to life, or choose a template to get started
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        <div>
          <label className="block text-sm font-medium text-foreground mb-2">
            Project Title
          </label>
          <input
            type="text"
            value={title}
            onChange={(e) => onTitleChange(e.target.value)}
            placeholder="E.g., Summer Travel Vlog"
            className="input-field"
            required
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-foreground mb-2">
            Description (optional)
          </label>
          <textarea
            value={description}
            onChange={(e) => onDescriptionChange(e.target.value)}
            placeholder="Add more context about your project..."
            className="input-field resize-none h-20"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-foreground mb-2">
            What would you like to create?
          </label>
          <textarea
            value={prompt}
            onChange={(e) => onPromptChange(e.target.value)}
            placeholder="Describe your video in detail. E.g., Create a promotional video about sustainable living with nature scenes, uplifting music, and inspirational quotes..."
            className="input-field resize-none h-32"
            required
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-foreground mb-2">
            Reference Materials
          </label>
          <UploadZone 
            onAssetsUploaded={onAssetsUploaded}
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-foreground mb-2">
            Video Model
          </label>
          <Select
            value={selectedModel}
            onValueChange={onModelChange}
          >
            <SelectTrigger className="w-full h-auto py-3">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="veo_fast">Google Veo 3.1 Fast (Recommended)</SelectItem>
              <SelectItem value="veo">Google Veo 3.1</SelectItem>
              <SelectItem value="hailuo">Hailuo 2.3 Fast</SelectItem>
              <SelectItem value="hailuo_23">Minimax Hailuo 2.3</SelectItem>
              <SelectItem value="runway_gen4_turbo">Runway Gen-4 Turbo (Test)</SelectItem>
              <SelectItem value="runway">Runway Gen-2</SelectItem>
            </SelectContent>
          </Select>
          <p className="mt-1 text-xs text-muted-foreground">
            Choose the AI model for video generation. Different models have different quality, speed, and cost characteristics.
          </p>
        </div>

        <button
          type="submit"
          disabled={!prompt || !title}
          className="w-full btn-primary flex items-center justify-center space-x-2"
        >
          <Sparkles className="w-5 h-5" />
          <span>Start Creating</span>
        </button>
      </form>
    </div>
  );
}

