import { Sliders, Volume2, Palette, Type } from 'lucide-react';
import { useState } from 'react';

interface VideoEditorProps {
  onSave: (settings: VideoSettings) => void;
  onCancel: () => void;
}

interface VideoSettings {
  duration: number;
  volume: number;
  backgroundColor: string;
  fontSize: number;
  musicTrack: string;
}

export function VideoEditor({ onSave, onCancel }: VideoEditorProps) {
  const [settings, setSettings] = useState<VideoSettings>({
    duration: 60,
    volume: 80,
    backgroundColor: '#000000',
    fontSize: 32,
    musicTrack: 'uplifting',
  });

  const handleSave = () => {
    onSave(settings);
  };

  return (
    <div className="card p-6 space-y-6 animate-fade-in">
      <div>
        <h3 className="font-semibold text-slate-900 dark:text-slate-100 mb-4 flex items-center space-x-2">
          <Sliders className="w-5 h-5 text-blue-600" />
          <span>Video Settings</span>
        </h3>
      </div>

      <div className="space-y-4">
        <div>
          <label className="flex items-center justify-between text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
            <span>Duration</span>
            <span className="text-blue-600">{settings.duration}s</span>
          </label>
          <input
            type="range"
            min="15"
            max="300"
            step="5"
            value={settings.duration}
            onChange={(e) =>
              setSettings({ ...settings, duration: parseInt(e.target.value) })
            }
            className="w-full"
          />
        </div>

        <div>
          <label className="flex items-center justify-between text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
            <span className="flex items-center space-x-2">
              <Volume2 className="w-4 h-4" />
              <span>Volume</span>
            </span>
            <span className="text-blue-600">{settings.volume}%</span>
          </label>
          <input
            type="range"
            min="0"
            max="100"
            value={settings.volume}
            onChange={(e) =>
              setSettings({ ...settings, volume: parseInt(e.target.value) })
            }
            className="w-full"
          />
        </div>

        <div>
          <label className="flex items-center space-x-2 text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
            <Palette className="w-4 h-4" />
            <span>Background Color</span>
          </label>
          <div className="flex items-center space-x-3">
            <input
              type="color"
              value={settings.backgroundColor}
              onChange={(e) =>
                setSettings({ ...settings, backgroundColor: e.target.value })
              }
              className="w-12 h-10 rounded border border-slate-300 dark:border-slate-600 cursor-pointer"
            />
            <input
              type="text"
              value={settings.backgroundColor}
              onChange={(e) =>
                setSettings({ ...settings, backgroundColor: e.target.value })
              }
              className="flex-1 px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg text-sm"
            />
          </div>
        </div>

        <div>
          <label className="flex items-center justify-between text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
            <span className="flex items-center space-x-2">
              <Type className="w-4 h-4" />
              <span>Text Size</span>
            </span>
            <span className="text-blue-600">{settings.fontSize}px</span>
          </label>
          <input
            type="range"
            min="16"
            max="72"
            step="2"
            value={settings.fontSize}
            onChange={(e) =>
              setSettings({ ...settings, fontSize: parseInt(e.target.value) })
            }
            className="w-full"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
            Background Music
          </label>
          <select
            value={settings.musicTrack}
            onChange={(e) =>
              setSettings({ ...settings, musicTrack: e.target.value })
            }
            className="w-full px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg focus:ring-2 focus:ring-blue-500"
          >
            <option value="uplifting">Uplifting (Royalty-Free)</option>
            <option value="ambient">Ambient (Royalty-Free)</option>
            <option value="energetic">Energetic (Royalty-Free)</option>
            <option value="dramatic">Dramatic (Royalty-Free)</option>
            <option value="none">None</option>
          </select>
        </div>
      </div>

      <div className="flex space-x-3 pt-4 border-t border-slate-200 dark:border-slate-700">
        <button onClick={onCancel} className="flex-1 btn-secondary">
          Cancel
        </button>
        <button onClick={handleSave} className="flex-1 btn-primary">
          Save Settings
        </button>
      </div>
    </div>
  );
}
