import { ArrowLeft, Copy, Check, Code } from 'lucide-react';
import { useState } from 'react';

interface APIProps {
  onBack: () => void;
}

export function API({ onBack }: APIProps) {
  const [copiedEndpoint, setCopiedEndpoint] = useState<string | null>(null);

  const copyToClipboard = (text: string, id: string) => {
    navigator.clipboard.writeText(text);
    setCopiedEndpoint(id);
    setTimeout(() => setCopiedEndpoint(null), 2000);
  };

  const endpoints = [
    {
      id: 'create',
      method: 'POST',
      path: '/api/videos/create',
      description: 'Create a new video from prompt',
      example: `curl -X POST https://api.videoai.studio/videos/create \\
  -H "Authorization: Bearer YOUR_API_KEY" \\
  -H "Content-Type: application/json" \\
  -d '{
    "title": "My Video",
    "prompt": "Create a video about...",
    "template_id": "optional-template-id"
  }'`,
    },
    {
      id: 'status',
      method: 'GET',
      path: '/api/videos/{id}',
      description: 'Get video creation status',
      example: `curl https://api.videoai.studio/videos/vid_12345 \\
  -H "Authorization: Bearer YOUR_API_KEY"`,
    },
    {
      id: 'list',
      method: 'GET',
      path: '/api/videos',
      description: 'List all videos',
      example: `curl https://api.videoai.studio/videos \\
  -H "Authorization: Bearer YOUR_API_KEY"`,
    },
    {
      id: 'export',
      method: 'POST',
      path: '/api/videos/{id}/export',
      description: 'Export video in different formats',
      example: `curl -X POST https://api.videoai.studio/videos/vid_12345/export \\
  -H "Authorization: Bearer YOUR_API_KEY" \\
  -H "Content-Type: application/json" \\
  -d '{
    "format": "mp4",
    "quality": "high"
  }'`,
    },
  ];

  return (
    <div className="max-w-6xl mx-auto animate-fade-in">
      <button
        onClick={onBack}
        className="flex items-center space-x-2 text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:text-slate-100 mb-6 transition-colors"
      >
        <ArrowLeft className="w-5 h-5" />
        <span>Back</span>
      </button>

      <div className="mb-8">
        <h1 className="text-3xl font-bold text-slate-900 dark:text-slate-100">API Documentation</h1>
        <p className="text-slate-600 dark:text-slate-400 mt-1">Integrate VideoAI Studio into your application</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <div className="card p-6">
          <p className="text-sm text-slate-600 dark:text-slate-400 mb-1">Base URL</p>
          <p className="text-lg font-mono font-semibold text-slate-900 dark:text-slate-100 break-all">
            https://api.videoai.studio
          </p>
        </div>
        <div className="card p-6">
          <p className="text-sm text-slate-600 dark:text-slate-400 mb-1">Authentication</p>
          <p className="text-lg font-mono font-semibold text-slate-900 dark:text-slate-100">Bearer Token</p>
        </div>
        <div className="card p-6">
          <p className="text-sm text-slate-600 dark:text-slate-400 mb-1">Rate Limit</p>
          <p className="text-lg font-mono font-semibold text-slate-900 dark:text-slate-100">1000 req/min</p>
        </div>
      </div>

      <div className="card p-6 mb-8">
        <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100 mb-4">Getting Your API Key</h3>
        <ol className="space-y-3 text-slate-700 dark:text-slate-300">
          <li className="flex items-start space-x-3">
            <span className="font-bold text-blue-600">1.</span>
            <span>Go to your account settings</span>
          </li>
          <li className="flex items-start space-x-3">
            <span className="font-bold text-blue-600">2.</span>
            <span>Navigate to "API & Integrations"</span>
          </li>
          <li className="flex items-start space-x-3">
            <span className="font-bold text-blue-600">3.</span>
            <span>Click "Generate New Key"</span>
          </li>
          <li className="flex items-start space-x-3">
            <span className="font-bold text-blue-600">4.</span>
            <span>Copy your key and store it securely</span>
          </li>
        </ol>
      </div>

      <div className="space-y-6">
        <h2 className="text-2xl font-bold text-slate-900 dark:text-slate-100">Endpoints</h2>

        {endpoints.map((endpoint) => (
          <div key={endpoint.id} className="card p-6">
            <div className="mb-4 pb-4 border-b border-slate-200 dark:border-slate-700">
              <div className="flex items-center space-x-4 mb-2">
                <span
                  className={`px-3 py-1 rounded text-sm font-bold text-white ${
                    endpoint.method === 'POST' ? 'bg-green-600' : 'bg-blue-600'
                  }`}
                >
                  {endpoint.method}
                </span>
                <code className="font-mono text-slate-900 dark:text-slate-100">{endpoint.path}</code>
              </div>
              <p className="text-slate-600 dark:text-slate-400">{endpoint.description}</p>
            </div>

            <div className="bg-slate-900 rounded-lg p-4 mb-4 relative group">
              <pre className="text-slate-300 font-mono text-sm overflow-x-auto whitespace-pre-wrap break-words">
                {endpoint.example}
              </pre>
              <button
                onClick={() => copyToClipboard(endpoint.example, endpoint.id)}
                className="absolute top-2 right-2 p-2 bg-slate-700 rounded hover:bg-slate-600 transition-colors opacity-0 group-hover:opacity-100"
              >
                {copiedEndpoint === endpoint.id ? (
                  <Check className="w-4 h-4 text-green-400" />
                ) : (
                  <Copy className="w-4 h-4 text-slate-300" />
                )}
              </button>
            </div>
          </div>
        ))}
      </div>

      <div className="card p-6 mt-8">
        <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100 mb-4 flex items-center space-x-2">
          <Code className="w-5 h-5" />
          <span>Response Format</span>
        </h3>
        <div className="bg-slate-900 rounded-lg p-4">
          <pre className="text-slate-300 font-mono text-sm overflow-x-auto">
{`{
  "success": true,
  "data": {
    "id": "vid_12345",
    "title": "My Video",
    "status": "processing",
    "created_at": "2024-11-14T10:30:00Z",
    "download_url": "https://..."
  }
}`}
          </pre>
        </div>
      </div>

      <div className="card p-6 mt-8">
        <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100 mb-4">Need Help?</h3>
        <p className="text-slate-600 dark:text-slate-400 mb-4">
          Check our documentation, examples, and community forum for help with integration.
        </p>
        <div className="flex space-x-3">
          <button className="flex-1 btn-secondary">
            View Docs
          </button>
          <button className="flex-1 btn-secondary">
            Community
          </button>
          <button className="flex-1 btn-secondary">
            Support
          </button>
        </div>
      </div>
    </div>
  );
}
