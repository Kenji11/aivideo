import { ArrowLeft, Moon, Bell, Download, Zap, HelpCircle } from 'lucide-react';
import { useState } from 'react';

interface SettingsProps {
  onBack: () => void;
}

export function Settings({ onBack }: SettingsProps) {
  const [theme, setTheme] = useState<'light' | 'dark'>('light');
  const [notifications, setNotifications] = useState(true);
  const [autoDownload, setAutoDownload] = useState(false);
  const [quality, setQuality] = useState<'high' | 'medium' | 'ultra'>('high');
  const [emailDigest, setEmailDigest] = useState(true);

  const toggleSwitch = (value: boolean) => value;

  return (
    <div className="max-w-3xl mx-auto animate-fade-in">
      <button
        onClick={onBack}
        className="flex items-center space-x-2 text-slate-600 hover:text-slate-900 mb-6 transition-colors"
      >
        <ArrowLeft className="w-5 h-5" />
        <span>Back</span>
      </button>

      <div className="mb-8">
        <h1 className="text-3xl font-bold text-slate-900">Settings</h1>
        <p className="text-slate-600 mt-1">Customize your VideoAI Studio experience</p>
      </div>

      <div className="space-y-6">
        <div className="card p-6">
          <div className="flex items-start justify-between mb-6">
            <div>
              <h3 className="text-lg font-semibold text-slate-900 flex items-center space-x-2">
                <Moon className="w-5 h-5 text-blue-600" />
                <span>Appearance</span>
              </h3>
              <p className="text-sm text-slate-600 mt-1">Customize how VideoAI Studio looks</p>
            </div>
          </div>

          <div className="space-y-4">
            <div className="flex items-center justify-between p-4 bg-slate-50 rounded-lg">
              <div>
                <p className="font-medium text-slate-900">Theme</p>
                <p className="text-sm text-slate-500">Light or dark mode</p>
              </div>
              <select
                value={theme}
                onChange={(e) => setTheme(e.target.value as 'light' | 'dark')}
                className="px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              >
                <option value="light">Light</option>
                <option value="dark">Dark</option>
              </select>
            </div>
          </div>
        </div>

        <div className="card p-6">
          <div className="flex items-start justify-between mb-6">
            <div>
              <h3 className="text-lg font-semibold text-slate-900 flex items-center space-x-2">
                <Bell className="w-5 h-5 text-orange-600" />
                <span>Notifications</span>
              </h3>
              <p className="text-sm text-slate-600 mt-1">Manage how you receive updates</p>
            </div>
          </div>

          <div className="space-y-3">
            <div className="flex items-center justify-between p-4 bg-slate-50 rounded-lg">
              <div>
                <p className="font-medium text-slate-900">Push Notifications</p>
                <p className="text-sm text-slate-500">Get notified when videos are ready</p>
              </div>
              <button
                onClick={() => setNotifications(!notifications)}
                className={`relative inline-flex h-6 w-11 flex-shrink-0 cursor-pointer rounded-full transition-colors ${
                  notifications ? 'bg-blue-600' : 'bg-slate-300'
                }`}
              >
                <span
                  className={`inline-block h-5 w-5 transform rounded-full bg-white transition-transform ${
                    notifications ? 'translate-x-5' : 'translate-x-1'
                  }`}
                />
              </button>
            </div>

            <div className="flex items-center justify-between p-4 bg-slate-50 rounded-lg">
              <div>
                <p className="font-medium text-slate-900">Email Digest</p>
                <p className="text-sm text-slate-500">Weekly summary of your activity</p>
              </div>
              <button
                onClick={() => setEmailDigest(!emailDigest)}
                className={`relative inline-flex h-6 w-11 flex-shrink-0 cursor-pointer rounded-full transition-colors ${
                  emailDigest ? 'bg-blue-600' : 'bg-slate-300'
                }`}
              >
                <span
                  className={`inline-block h-5 w-5 transform rounded-full bg-white transition-transform ${
                    emailDigest ? 'translate-x-5' : 'translate-x-1'
                  }`}
                />
              </button>
            </div>
          </div>
        </div>

        <div className="card p-6">
          <div className="flex items-start justify-between mb-6">
            <div>
              <h3 className="text-lg font-semibold text-slate-900 flex items-center space-x-2">
                <Download className="w-5 h-5 text-green-600" />
                <span>Downloads</span>
              </h3>
              <p className="text-sm text-slate-600 mt-1">Control your video downloads</p>
            </div>
          </div>

          <div className="space-y-4">
            <div className="flex items-center justify-between p-4 bg-slate-50 rounded-lg">
              <div>
                <p className="font-medium text-slate-900">Auto-download Videos</p>
                <p className="text-sm text-slate-500">Automatically save videos when ready</p>
              </div>
              <button
                onClick={() => setAutoDownload(!autoDownload)}
                className={`relative inline-flex h-6 w-11 flex-shrink-0 cursor-pointer rounded-full transition-colors ${
                  autoDownload ? 'bg-blue-600' : 'bg-slate-300'
                }`}
              >
                <span
                  className={`inline-block h-5 w-5 transform rounded-full bg-white transition-transform ${
                    autoDownload ? 'translate-x-5' : 'translate-x-1'
                  }`}
                />
              </button>
            </div>

            <div className="flex items-center justify-between p-4 bg-slate-50 rounded-lg">
              <div>
                <p className="font-medium text-slate-900">Quality</p>
                <p className="text-sm text-slate-500">Default video quality preference</p>
              </div>
              <select
                value={quality}
                onChange={(e) => setQuality(e.target.value as 'high' | 'medium' | 'ultra')}
                className="px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              >
                <option value="medium">Medium (720p)</option>
                <option value="high">High (1080p)</option>
                <option value="ultra">Ultra (4K)</option>
              </select>
            </div>
          </div>
        </div>

        <div className="card p-6">
          <div className="flex items-start justify-between mb-6">
            <div>
              <h3 className="text-lg font-semibold text-slate-900 flex items-center space-x-2">
                <Zap className="w-5 h-5 text-yellow-600" />
                <span>Performance</span>
              </h3>
              <p className="text-sm text-slate-600 mt-1">Optimize your experience</p>
            </div>
          </div>

          <div className="space-y-3">
            <button className="w-full p-4 bg-slate-50 rounded-lg hover:bg-slate-100 transition-colors text-left">
              <p className="font-medium text-slate-900">Clear Cache</p>
              <p className="text-sm text-slate-500">Remove temporary files to free up space</p>
            </button>
          </div>
        </div>

        <div className="card p-6">
          <div className="flex items-start justify-between mb-6">
            <div>
              <h3 className="text-lg font-semibold text-slate-900 flex items-center space-x-2">
                <HelpCircle className="w-5 h-5 text-blue-600" />
                <span>Help & Support</span>
              </h3>
              <p className="text-sm text-slate-600 mt-1">Get help and learn more</p>
            </div>
          </div>

          <div className="space-y-3">
            <button className="w-full p-4 bg-slate-50 rounded-lg hover:bg-slate-100 transition-colors text-left">
              <p className="font-medium text-slate-900">Documentation</p>
              <p className="text-sm text-slate-500">Learn how to use VideoAI Studio</p>
            </button>
            <button className="w-full p-4 bg-slate-50 rounded-lg hover:bg-slate-100 transition-colors text-left">
              <p className="font-medium text-slate-900">Contact Support</p>
              <p className="text-sm text-slate-500">Get help from our support team</p>
            </button>
            <button className="w-full p-4 bg-slate-50 rounded-lg hover:bg-slate-100 transition-colors text-left">
              <p className="font-medium text-slate-900">About</p>
              <p className="text-sm text-slate-500">Learn about VideoAI Studio v1.0</p>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
