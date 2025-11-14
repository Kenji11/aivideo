import { Film, ArrowRight } from 'lucide-react';

interface AuthProps {
  onAuthSuccess: () => void;
}

export function Auth({ onAuthSuccess }: AuthProps) {
  const handleDemoMode = () => {
    onAuthSuccess();
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center p-4">
      <div className="max-w-md w-full">
        {/* Logo */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-20 h-20 bg-gradient-to-br from-blue-600 to-indigo-600 rounded-3xl mb-6 shadow-xl">
            <Film className="w-11 h-11 text-white" />
          </div>
          <h1 className="text-4xl font-bold text-slate-900 mb-3">VideoAI Studio</h1>
          <p className="text-lg text-slate-600">Create professional videos with AI</p>
        </div>

        <div className="bg-white rounded-2xl shadow-xl p-8 border border-slate-200">
          {/* Demo Mode Button - Large and Prominent */}
          <button
            onClick={handleDemoMode}
            className="w-full bg-gradient-to-r from-blue-600 to-indigo-600 text-white py-5 px-6 rounded-xl font-bold text-lg
                     hover:from-blue-700 hover:to-indigo-700 transition-all duration-200
                     flex items-center justify-center space-x-3 shadow-lg hover:shadow-2xl transform hover:scale-[1.02]
                     active:scale-[0.98]"
          >
            <ArrowRight className="w-6 h-6" />
            <span>Enter Studio (No Login Required)</span>
          </button>

          <div className="mt-6 p-5 bg-gradient-to-br from-blue-50 to-indigo-50 border border-blue-200 rounded-xl">
            <h3 className="font-semibold text-blue-900 mb-2 flex items-center">
              <span className="text-2xl mr-2">✨</span>
              Demo Mode Enabled
            </h3>
            <p className="text-sm text-blue-800 leading-relaxed">
              Explore all features of VideoAI Studio without signing up! Authentication will be available once the backend is connected.
            </p>
          </div>

          <div className="mt-8 space-y-3">
            <div className="flex items-start space-x-3 text-sm text-slate-600">
              <span className="text-green-500 text-lg">✓</span>
              <span>Full access to video creation tools</span>
            </div>
            <div className="flex items-start space-x-3 text-sm text-slate-600">
              <span className="text-green-500 text-lg">✓</span>
              <span>Browse templates and settings</span>
            </div>
            <div className="flex items-start space-x-3 text-sm text-slate-600">
              <span className="text-green-500 text-lg">✓</span>
              <span>Test all UI features</span>
            </div>
          </div>
        </div>

        <p className="text-center text-sm text-slate-500 mt-8">
          Frontend-only demo • Backend integration coming soon
        </p>
      </div>
    </div>
  );
}
