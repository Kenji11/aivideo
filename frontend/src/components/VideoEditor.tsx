import { Sliders, Volume2, Palette, Type } from 'lucide-react';
import { useState } from 'react';
import { Slider } from '@/components/ui/slider';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';

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
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <Label>Duration</Label>
            <span className="text-sm text-blue-600">{settings.duration}s</span>
          </div>
          <Slider
            min={15}
            max={300}
            step={5}
            value={[settings.duration]}
            onValueChange={(value) =>
              setSettings({ ...settings, duration: value[0] })
            }
          />
        </div>

        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <Label className="flex items-center space-x-2">
              <Volume2 className="w-4 h-4" />
              <span>Volume</span>
            </Label>
            <span className="text-sm text-blue-600">{settings.volume}%</span>
          </div>
          <Slider
            min={0}
            max={100}
            value={[settings.volume]}
            onValueChange={(value) =>
              setSettings({ ...settings, volume: value[0] })
            }
          />
        </div>

        <div className="space-y-2">
          <Label className="flex items-center space-x-2">
            <Palette className="w-4 h-4" />
            <span>Background Color</span>
          </Label>
          <div className="flex items-center space-x-3">
            <Input
              type="color"
              value={settings.backgroundColor}
              onChange={(e) =>
                setSettings({ ...settings, backgroundColor: e.target.value })
              }
              className="w-12 h-10 rounded border cursor-pointer"
            />
            <Input
              type="text"
              value={settings.backgroundColor}
              onChange={(e) =>
                setSettings({ ...settings, backgroundColor: e.target.value })
              }
              className="flex-1"
            />
          </div>
        </div>

        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <Label className="flex items-center space-x-2">
              <Type className="w-4 h-4" />
              <span>Text Size</span>
            </Label>
            <span className="text-sm text-blue-600">{settings.fontSize}px</span>
          </div>
          <Slider
            min={16}
            max={72}
            step={2}
            value={[settings.fontSize]}
            onValueChange={(value) =>
              setSettings({ ...settings, fontSize: value[0] })
            }
          />
        </div>

        <div className="space-y-2">
          <Label>Background Music</Label>
          <Select
            value={settings.musicTrack}
            onValueChange={(value) =>
              setSettings({ ...settings, musicTrack: value })
            }
          >
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="uplifting">Uplifting (Royalty-Free)</SelectItem>
              <SelectItem value="ambient">Ambient (Royalty-Free)</SelectItem>
              <SelectItem value="energetic">Energetic (Royalty-Free)</SelectItem>
              <SelectItem value="dramatic">Dramatic (Royalty-Free)</SelectItem>
              <SelectItem value="none">None</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      <div className="flex space-x-3 pt-4 border-t border-slate-200 dark:border-slate-700">
        <Button onClick={onCancel} variant="secondary" className="flex-1">
          Cancel
        </Button>
        <Button onClick={handleSave} className="flex-1">
          Save Settings
        </Button>
      </div>
    </div>
  );
}
