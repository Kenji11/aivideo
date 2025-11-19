import { Loader2, CheckCircle2, AlertCircle } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';

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
        <Card
          key={idx}
          className="animate-slide-in border-border"
          style={{ animationDelay: `${idx * 100}ms` }}
        >
          <CardContent className="p-4">
            <div className="flex items-center space-x-4">
              <div className="flex-shrink-0">
                {step.status === 'completed' && (
                  <CheckCircle2 className="w-6 h-6 text-primary" />
                )}
                {step.status === 'processing' && (
                  <Loader2 className="w-6 h-6 text-primary animate-spin" />
                )}
                {step.status === 'failed' && (
                  <AlertCircle className="w-6 h-6 text-destructive" />
                )}
                {step.status === 'pending' && (
                  <div className="w-6 h-6 rounded-full bg-muted" />
                )}
              </div>
              <span
                className={`text-sm font-medium ${
                  step.status === 'pending'
                    ? 'text-muted-foreground'
                    : step.status === 'processing'
                      ? 'text-foreground'
                      : step.status === 'completed'
                        ? 'text-muted-foreground'
                        : 'text-destructive'
                }`}
              >
                {step.name}
              </span>
            </div>
          </CardContent>
        </Card>
      ))}

      {elapsedTime > 0 && (
        <div className="text-center text-sm text-muted-foreground mt-4">
          Elapsed time: {formatTime(elapsedTime)}
        </div>
      )}
    </div>
  );
}
