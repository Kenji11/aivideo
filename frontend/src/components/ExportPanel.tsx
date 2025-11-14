import { Download, Share2, Monitor } from 'lucide-react';
import { useState } from 'react';

interface ExportSettings {
  format: 'mp4' | 'webm' | 'mov' | 'gif';
  quality: 'low' | 'medium' | 'high' | 'ultra';
  includeWatermark: boolean;
  subtitles: boolean;
}

interface ExportPanelProps {
  onExport: (settings: ExportSettings) => void;
  onCancel: () => void;
}

const formatOptions = [
  { id: 'mp4', name: 'MP4', desc: 'Universal compatibility', icon: '🎬' },
  { id: 'webm', name: 'WebM', desc: 'Web-optimized', icon: '🌐' },
  { id: 'mov', name: 'MOV', desc: 'Apple devices', icon: '🍎' },
  { id: 'gif', name: 'GIF', desc: 'Social media', icon: '🎞️' },
];

export function ExportPanel({ onExport, onCancel }: ExportPanelProps) {
  const [settings, setSettings] = useState<ExportSettings>({
    format: 'mp4',
    quality: 'high',
    includeWatermark: false,
    subtitles: false,
  });

  const qualitySpecs = {
    low: { res: '720p', bitrate: '2.5 Mbps', size: '150 MB' },
    medium: { res: '1080p', bitrate: '5 Mbps', size: '300 MB' },
    high: { res: '1080p', bitrate: '8 Mbps', size: '500 MB' },
    ultra: { res: '4K', bitrate: '15 Mbps', size: '1.2 GB' },
  };

  const spec = qualitySpecs[settings.quality];

  return (
    <div className="card p-8 animate-fade-in space-y-8">
      <div>
        <h3 className="text-2xl font-bold text-slate-900 dark:text-slate-100 mb-2">Export Video</h3>
        <p className="text-slate-600 dark:text-slate-400">Choose format and quality for your final video</p>
      </div>

      <div>
        <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-4">
          Output Format
        </label>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {formatOptions.map((opt) => (
            <button
              key={opt.id}
              onClick={() => setSettings({ ...settings, format: opt.id as any })}
              className={`p-4 rounded-lg border-2 transition-all text-center ${
                settings.format === opt.id
                  ? 'border-blue-600 bg-blue-50'
                  : 'border-slate-200 dark:border-slate-700 hover:border-blue-400'
              }`}
            >
              <div className="text-2xl mb-2">{opt.icon}</div>
              <p className="font-medium text-slate-900 dark:text-slate-100">{opt.name}</p>
              <p className="text-xs text-slate-500 dark:text-slate-400">{opt.desc}</p>
            </button>
          ))}
        </div>
      </div>

      <div>
        <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-4">
          Quality
        </label>
        <div className="space-y-3">
          {(['low', 'medium', 'high', 'ultra'] as const).map((qual) => (
            <button
              key={qual}
              onClick={() => setSettings({ ...settings, quality: qual })}
              className={`w-full p-4 rounded-lg border-2 transition-all text-left ${
                settings.quality === qual
                  ? 'border-blue-600 bg-blue-50'
                  : 'border-slate-200 dark:border-slate-700 hover:border-blue-400'
              }`}
            >
              <div className="flex items-center justify-between">
                <div>
                  <p className="font-medium text-slate-900 dark:text-slate-100 capitalize">{qual}</p>
                  <p className="text-xs text-slate-500 dark:text-slate-400">
                    {qualitySpecs[qual].res} • {qualitySpecs[qual].bitrate}
                  </p>
                </div>
                <span className="text-xs font-medium text-slate-600 dark:text-slate-400">
                  ~{qualitySpecs[qual].size}
                </span>
              </div>
            </button>
          ))}
        </div>
      </div>

      <div className="border-t border-slate-200 dark:border-slate-700 pt-6 space-y-4">
        <div className="flex items-center justify-between p-4 bg-slate-50 dark:bg-slate-700/50 rounded-lg">
          <label className="flex items-center space-x-3 flex-1 cursor-pointer">
            <input
              type="checkbox"
              checked={settings.includeWatermark}
              onChange={(e) => setSettings({ ...settings, includeWatermark: e.target.checked })}
              className="w-5 h-5 rounded"
            />
            <div>
              <p className="font-medium text-slate-900 dark:text-slate-100">Include Watermark</p>
              <p className="text-xs text-slate-500 dark:text-slate-400">Add branding to your video</p>
            </div>
          </label>
        </div>

        <div className="flex items-center justify-between p-4 bg-slate-50 dark:bg-slate-700/50 rounded-lg">
          <label className="flex items-center space-x-3 flex-1 cursor-pointer">
            <input
              type="checkbox"
              checked={settings.subtitles}
              onChange={(e) => setSettings({ ...settings, subtitles: e.target.checked })}
              className="w-5 h-5 rounded"
            />
            <div>
              <p className="font-medium text-slate-900 dark:text-slate-100">Generate Subtitles</p>
              <p className="text-xs text-slate-500 dark:text-slate-400">Auto-generate from audio</p>
            </div>
          </label>
        </div>
      </div>

      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <div className="flex items-start space-x-3">
          <Monitor className="w-5 h-5 text-blue-600 flex-shrink-0 mt-0.5" />
          <div className="text-sm">
            <p className="font-medium text-blue-900">Export Details</p>
            <p className="text-blue-800 mt-1">
              Your video will be exported in {settings.format.toUpperCase()} format at {spec.res} resolution.
              Estimated file size: <strong>{spec.size}</strong>. Export typically takes 5-15 minutes.
            </p>
          </div>
        </div>
      </div>

      <div className="flex space-x-4">
        <button
          onClick={onCancel}
          className="flex-1 btn-secondary"
        >
          Cancel
        </button>
        <button
          onClick={() => onExport(settings)}
          className="flex-1 btn-primary flex items-center justify-center space-x-2"
        >
          <Download className="w-5 h-5" />
          <span>Export Video</span>
        </button>
      </div>
    </div>
  );
}
