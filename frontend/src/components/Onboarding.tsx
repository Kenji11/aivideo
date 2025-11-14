import { ChevronRight, CheckCircle2 } from 'lucide-react';
import { useState } from 'react';

interface OnboardingProps {
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

export function Onboarding({ onComplete }: OnboardingProps) {
  const [currentStep, setCurrentStep] = useState(0);

  const step = steps[currentStep];
  const isLast = currentStep === steps.length - 1;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl shadow-xl max-w-md w-full animate-fade-in">
        <div className="h-1 bg-slate-200 flex">
          {steps.map((_, idx) => (
            <div
              key={idx}
              className={`flex-1 transition-colors ${
                idx <= currentStep ? 'bg-blue-600' : 'bg-slate-200'
              }`}
            />
          ))}
        </div>

        <div className="p-8 space-y-6">
          <div className="text-center space-y-2">
            <h2 className="text-2xl font-bold text-slate-900 dark:text-slate-100">{step.title}</h2>
            <p className="text-slate-600 dark:text-slate-400">{step.description}</p>
          </div>

          <div className="h-32 bg-gradient-to-br from-blue-100 to-purple-100 rounded-lg flex items-center justify-center">
            <p className="text-center text-slate-700 dark:text-slate-300 px-4">{step.content}</p>
          </div>

          <div className="space-y-2">
            <div className="flex items-center space-x-2">
              <CheckCircle2 className="w-5 h-5 text-green-600 flex-shrink-0" />
              <span className="text-sm text-slate-700 dark:text-slate-300">
                Step {currentStep + 1} of {steps.length}
              </span>
            </div>
          </div>
        </div>

        <div className="flex space-x-3 p-6 border-t border-slate-200 dark:border-slate-700">
          {currentStep > 0 && (
            <button
              onClick={() => setCurrentStep(currentStep - 1)}
              className="flex-1 btn-secondary"
            >
              Back
            </button>
          )}
          <button
            onClick={
              isLast ? onComplete : () => setCurrentStep(currentStep + 1)
            }
            className="flex-1 btn-primary flex items-center justify-center space-x-2"
          >
            <span>{isLast ? 'Get Started' : 'Next'}</span>
            {!isLast && <ChevronRight className="w-4 h-4" />}
          </button>
        </div>
      </div>
    </div>
  );
}
