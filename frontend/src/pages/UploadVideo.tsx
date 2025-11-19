import { Sparkles } from 'lucide-react';
import { UploadZone } from '../components/UploadZone';

interface UploadVideoProps {
  title: string;
  description: string;
  prompt: string;
  isProcessing: boolean;
  selectedModel: string;
  onTitleChange: (title: string) => void;
  onDescriptionChange: (description: string) => void;
  onPromptChange: (prompt: string) => void;
  onModelChange: (model: string) => void;
  onAssetsUploaded: (assetIds: string[]) => void;
  onSubmit: (e: React.FormEvent) => void;
}

export function UploadVideo({
  title,
  description,
  prompt,
  isProcessing,
  selectedModel,
  onTitleChange,
  onDescriptionChange,
  onPromptChange,
  onModelChange,
  onAssetsUploaded,
  onSubmit,
}: UploadVideoProps) {
  return (
    <div className="card p-8 animate-fade-in">
      <div className="mb-8">
        <h2 className="text-2xl font-bold text-slate-900 dark:text-slate-100 mb-2">
          Create Your Video
        </h2>
        <p className="text-slate-600 dark:text-slate-400">
          Describe your vision and let AI bring it to life, or choose a template to get started
        </p>
      </div>

      <form onSubmit={onSubmit} className="space-y-6">
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-2">
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
          <label className="block text-sm font-medium text-slate-700 mb-2">
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
          <label className="block text-sm font-medium text-slate-700 mb-2">
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
          <label className="block text-sm font-medium text-slate-700 mb-2">
            Reference Materials
          </label>
          <UploadZone 
            disabled={isProcessing} 
            onAssetsUploaded={onAssetsUploaded}
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-slate-700 mb-2">
            Video Model
          </label>
          <select
            value={selectedModel}
            onChange={(e) => onModelChange(e.target.value)}
            className="input-field"
            disabled={isProcessing}
          >
            <option value="veo_fast">Google Veo 3.1 Fast (Recommended)</option>
            <option value="veo">Google Veo 3.1</option>
            <option value="hailuo">Hailuo 2.3 Fast</option>
            <option value="hailuo_23">Minimax Hailuo 2.3</option>
            <option value="runway_gen4_turbo">Runway Gen-4 Turbo (Test)</option>
            <option value="runway">Runway Gen-2</option>
          </select>
          <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
            Choose the AI model for video generation. Different models have different quality, speed, and cost characteristics.
          </p>
        </div>

        <button
          type="submit"
          disabled={!prompt || !title || isProcessing}
          className="w-full btn-primary flex items-center justify-center space-x-2"
        >
          <Sparkles className="w-5 h-5" />
          <span>{isProcessing ? 'Processing...' : 'Start Creating'}</span>
        </button>
      </form>
    </div>
  );
}

