import { ChevronRight, CheckCircle2 } from 'lucide-react';
import { useState } from 'react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog';
import { Progress } from '@/components/ui/progress';
import { Button } from '@/components/ui/button';

interface OnboardingProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onComplete: () => void;
}

const steps = [
  {
    title: 'Welcome to VideoAI Studio',
    description: 'Create professional videos with AI in minutes',
    content: 'Our platform uses advanced AI to generate stunning videos from just a text description.',
  },
  {
    title: 'Choose a Template',
    description: 'Start with a professionally designed template',
    content: 'Browse our collection of templates for marketing, education, entertainment, and more.',
  },
  {
    title: 'Write Your Story',
    description: 'Describe what you want to create',
    content: 'Be as detailed as possible. The more specific your description, the better the results.',
  },
  {
    title: 'Let AI Work',
    description: 'Sit back while AI generates your video',
    content: 'Our AI will create scenes, generate images, and compose everything into a finished video.',
  },
  {
    title: 'Review & Share',
    description: 'Preview and share your masterpiece',
    content: 'Download your video, share it with collaborators, or publish directly to social media.',
  },
];

export function Onboarding({ open, onOpenChange, onComplete }: OnboardingProps) {
  const [currentStep, setCurrentStep] = useState(0);

  const step = steps[currentStep];
  const isLast = currentStep === steps.length - 1;
  const progress = ((currentStep + 1) / steps.length) * 100;

  const handleNext = () => {
    if (isLast) {
      onComplete();
      onOpenChange(false);
    } else {
      setCurrentStep(currentStep + 1);
    }
  };

  const handleBack = () => {
    if (currentStep > 0) {
      setCurrentStep(currentStep - 1);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>{step.title}</DialogTitle>
        </DialogHeader>

        <div className="space-y-6 py-4">
          <Progress value={progress} className="h-1" />

          <div className="text-center space-y-2">
            <p className="text-muted-foreground">{step.description}</p>
          </div>

          <div className="h-32 bg-gradient-to-br from-blue-100 to-purple-100 dark:from-blue-900 dark:to-purple-900 rounded-lg flex items-center justify-center">
            <p className="text-center px-4">{step.content}</p>
          </div>

          <div className="flex items-center space-x-2">
            <CheckCircle2 className="w-5 h-5 text-green-600 flex-shrink-0" />
            <span className="text-sm text-muted-foreground">
              Step {currentStep + 1} of {steps.length}
            </span>
          </div>
        </div>

        <DialogFooter>
          {currentStep > 0 && (
            <Button onClick={handleBack} variant="secondary">
              Back
            </Button>
          )}
          <Button onClick={handleNext} className="flex-1">
            {isLast ? 'Get Started' : 'Next'}
            {!isLast && <ChevronRight className="w-4 h-4 ml-2" />}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
