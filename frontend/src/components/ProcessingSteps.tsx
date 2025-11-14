import { Loader2, CheckCircle2, AlertCircle } from 'lucide-react';

interface ProcessingStep {
  name: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
}

interface ProcessingStepsProps {
  steps: ProcessingStep[];
  elapsedTime?: number;
}

export function ProcessingSteps({ steps, elapsedTime = 0 }: ProcessingStepsProps) {
  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}m ${secs}s`;
  };

  return (
    <div className="space-y-3">
      {steps.map((step, idx) => (
        <div
          key={idx}
          className="flex items-center space-x-4 p-4 bg-slate-50 rounded-lg border border-slate-200 animate-slide-in"
          style={{ animationDelay: `${idx * 100}ms` }}
        >
          <div className="flex-shrink-0">
            {step.status === 'completed' && (
              <CheckCircle2 className="w-6 h-6 text-green-500" />
            )}
            {step.status === 'processing' && (
              <Loader2 className="w-6 h-6 text-blue-600 animate-spin" />
            )}
            {step.status === 'failed' && (
              <AlertCircle className="w-6 h-6 text-red-500" />
            )}
            {step.status === 'pending' && (
              <div className="w-6 h-6 rounded-full bg-slate-300" />
            )}
          </div>
          <span
            className={`text-sm font-medium ${
              step.status === 'pending'
                ? 'text-slate-400'
                : step.status === 'processing'
                  ? 'text-slate-900'
                  : step.status === 'completed'
                    ? 'text-slate-700'
                    : 'text-red-700'
            }`}
          >
            {step.name}
          </span>
        </div>
      ))}

      {elapsedTime > 0 && (
        <div className="text-center text-sm text-slate-500 mt-4">
          Elapsed time: {formatTime(elapsedTime)}
        </div>
      )}
    </div>
  );
}
