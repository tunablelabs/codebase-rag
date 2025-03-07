import React, { useEffect, useState } from 'react';
import { Loader2, Check, AlertCircle, Clock, Database, Layers, Server, Cpu } from 'lucide-react';

export type UploadStep = 'uploading' | 'chunking' | 'indexing' | 'storing' | 'processing' | 'complete' | 'error';

interface UploadProgressProps {
  isActive: boolean;
  onComplete?: () => void;
  error?: string | null;
}

interface StepConfig {
  label: string;
  duration: number;
  description: string;
  icon: React.ReactNode;
}

const UploadProgress: React.FC<UploadProgressProps> = ({ 
  isActive, 
  onComplete,
  error
}) => {
  const [currentStep, setCurrentStep] = useState<UploadStep>('uploading');
  const [timeInStep, setTimeInStep] = useState(0);
  
  const steps: Record<UploadStep, StepConfig> = {
    uploading: {
      label: 'Repository Uploading',
      duration: 2000,
      description: 'Transferring repository files to server',
      icon: <Server className="w-5 h-5" />
    },
    chunking: {
      label: 'Chunking Content',
      duration: 3000,
      description: 'Breaking down code into analyzable segments',
      icon: <Layers className="w-5 h-5" />
    },
    indexing: {
      label: 'Indexing',
      duration: 2000,
      description: 'Creating searchable indexes for your codebase',
      icon: <Database className="w-5 h-5" />
    },
    storing: {
      label: 'Storing to Database',
      duration: 2000,
      description: 'Saving processed data for quick access',
      icon: <Server className="w-5 h-5" />
    },
    processing: {
      label: 'Final Processing',
      duration: 5000,
      description: 'Performing additional analysis, sit back and relax',
      icon: <Cpu className="w-5 h-5" />
    },
    complete: {
      label: 'Complete',
      duration: 0,
      description: 'Your repository is ready to use',
      icon: <Check className="w-5 h-5" />
    },
    error: {
      label: 'Error',
      duration: 0,
      description: 'There was an error processing your repository',
      icon: <AlertCircle className="w-5 h-5" />
    }
  };

  // Order of steps in the process
  const stepSequence: UploadStep[] = [
    'uploading', 
    'chunking', 
    'indexing', 
    'storing', 
    'processing', 
    'complete'
  ];

  useEffect(() => {
    if (!isActive) {
      setCurrentStep('uploading');
      setTimeInStep(0);
      return;
    }
    
    if (error) {
      setCurrentStep('error');
      return;
    }

    const interval = setInterval(() => {
      setTimeInStep(prev => prev + 100);
    }, 100);

    return () => clearInterval(interval);
  }, [isActive, error]);

  useEffect(() => {
    const currentStepConfig = steps[currentStep];
    
    if (timeInStep >= currentStepConfig.duration && currentStep !== 'complete' && currentStep !== 'error') {
      const currentIndex = stepSequence.indexOf(currentStep);
      if (currentIndex < stepSequence.length - 1) {
        const nextStep = stepSequence[currentIndex + 1];
        setCurrentStep(nextStep);
        setTimeInStep(0);
      }
    }
    
    if (currentStep === 'complete' && onComplete) {
      onComplete();
    }
  }, [timeInStep, currentStep, onComplete]);

  const getStepStatus = (step: UploadStep) => {
    const currentIndex = stepSequence.indexOf(currentStep);
    const stepIndex = stepSequence.indexOf(step);
    
    if (currentStep === 'error') {
      return stepIndex === stepSequence.indexOf('uploading') ? 'error' : 'pending';
    }
    
    if (stepIndex < currentIndex) return 'complete';
    if (stepIndex === currentIndex) return 'active';
    return 'pending';
  };

  const calculateProgress = () => {
    if (currentStep === 'complete') return 100;
    if (currentStep === 'error') return 0;
    
    const currentStepConfig = steps[currentStep];
    const percentInCurrentStep = (timeInStep / currentStepConfig.duration) * 100;
    
    const completedSteps = stepSequence.indexOf(currentStep);
    const totalSteps = stepSequence.length - 1; // Exclude 'complete'
    
    const baseProgress = (completedSteps / totalSteps) * 100;
    const stepContribution = (1 / totalSteps) * percentInCurrentStep;
    
    return Math.min(baseProgress + stepContribution, 99.9);
  };

  // Get estimated time remaining in seconds
  const getEstimatedTimeRemaining = () => {
    if (currentStep === 'complete' || currentStep === 'error') return 0;
    
    const currentIndex = stepSequence.indexOf(currentStep);
    const currentStepConfig = steps[currentStep];
    
    // Time remaining in current step
    const timeRemainingInCurrentStep = Math.max(0, currentStepConfig.duration - timeInStep);
    
    // Add time for remaining steps
    let totalTimeRemaining = timeRemainingInCurrentStep;
    for (let i = currentIndex + 1; i < stepSequence.length - 1; i++) {
      totalTimeRemaining += steps[stepSequence[i]].duration;
    }
    
    return Math.ceil(totalTimeRemaining / 1000);
  };

  const renderSegmentedProgressBar = () => {
    const totalSteps = stepSequence.length - 1; // Exclude 'complete'
    const segmentWidth = 100 / totalSteps;
    const currentStepIndex = stepSequence.indexOf(currentStep);
    
    return (
      <div className="w-full h-2 bg-base-200 rounded-full overflow-hidden flex">
        {stepSequence.slice(0, -1).map((step, index) => {
          const isCurrentStep = index === currentStepIndex;
          const isPastStep = index < currentStepIndex;
          const status = getStepStatus(step);
          
          let segmentFill = '0%';
          if (isPastStep) {
            segmentFill = '100%';
          } else if (isCurrentStep) {
            segmentFill = `${(timeInStep / steps[step].duration) * 100}%`;
          }
          
          return (
            <div 
              key={step} 
              className="h-full relative" 
              style={{ width: `${segmentWidth}%` }}
            >
              <div 
                className={`
                  absolute top-0 left-0 h-full
                  ${status === 'error' ? 'bg-error' : 'bg-primary'}
                  ${isCurrentStep ? 'animate-pulse-subtle' : ''}
                  transition-all duration-300 ease-out
                `}
                style={{ width: segmentFill }}
              />
            </div>
          );
        })}
      </div>
    );
  };

  return (
    <div className="w-full bg-base-100 rounded-xl p-6 shadow-sm border border-base-200">
      {/* Header with progress percentage */}
      <div className="flex items-center justify-between mb-5">
        <h2 className="text-lg font-semibold flex items-center">
          {currentStep === 'error' ? (
            <>
              <AlertCircle className="w-5 h-5 text-error mr-2" />
              <span className="text-error">Error Processing Repository</span>
            </>
          ) : currentStep === 'complete' ? (
            <>
              <Check className="w-5 h-5 text-success mr-2" />
              <span className="text-success">Repository Ready</span>
            </>
          ) : (
            <>
              <Loader2 className="w-5 h-5 text-primary mr-2 animate-spin" />
              <span>Processing Repository</span>
            </>
          )}
        </h2>
        
        {currentStep !== 'error' && currentStep !== 'complete' && (
          <div className="flex items-center gap-2">
            <div className="text-xs bg-primary/10 text-primary px-2 py-1 rounded-md font-mono">
              ~{getEstimatedTimeRemaining()}s remaining
            </div>
            <div className="text-lg font-semibold tabular-nums text-primary">
              {Math.round(calculateProgress())}%
            </div>
          </div>
        )}
      </div>
      
      {/* Segmented progress bar */}
      <div className="mb-6">
        {renderSegmentedProgressBar()}
        
        {/* Step labels under progress bar */}
        <div className="flex justify-between mt-1 px-1 text-xs text-base-content/60">
          {stepSequence.slice(0, -1).map((step, index) => (
            <div key={step} className="text-center" style={{ width: `${100 / (stepSequence.length - 1)}%` }}>
              {index === 0 && "Start"}
              {index === stepSequence.length - 2 && "Finish"}
            </div>
          ))}
        </div>
      </div>
      
      {/* Current step detailed info */}
      <div className={`
        p-4 mb-6 rounded-lg border 
        ${currentStep === 'error' 
          ? 'bg-error/5 border-error/20' 
          : currentStep === 'complete'
            ? 'bg-success/5 border-success/20'
            : 'bg-primary/5 border-primary/20'
        }
      `}>
        <div className="flex items-start gap-3">
          <div className={`
            p-2 rounded-full flex-shrink-0
            ${currentStep === 'error' 
              ? 'bg-error/20 text-error' 
              : currentStep === 'complete'
                ? 'bg-success/20 text-success'
                : 'bg-primary/20 text-primary'
            }
          `}>
            {currentStep === 'error' 
              ? <AlertCircle className="w-6 h-6" />
              : currentStep === 'complete'
                ? <Check className="w-6 h-6" />
                : steps[currentStep].icon || <Loader2 className="w-6 h-6 animate-spin" />
            }
          </div>
          
          <div>
            <h3 className={`text-base font-medium mb-1 ${
              currentStep === 'error' 
                ? 'text-error' 
                : currentStep === 'complete'
                  ? 'text-success'
                  : 'text-primary'
            }`}>
              {steps[currentStep].label}
            </h3>
            <p className="text-sm text-base-content/80">
              {currentStep === 'error' 
                ? (error || 'An unexpected error occurred. Please try again.') 
                : steps[currentStep].description}
            </p>
          </div>
        </div>
      </div>
      
      {/* Steps timeline */}
      <div className="space-y-0">
        {stepSequence.slice(0, -1).map((step, index) => {
          const status = getStepStatus(step);
          const isLast = index === stepSequence.length - 2;
          
          return (
            <div key={step} className="relative">
              <div className="flex items-center gap-4">
                {/* Step indicator */}
                <div className={`
                  z-10 w-8 h-8 rounded-full flex items-center justify-center
                  transition-all duration-300 border-2
                  ${status === 'complete' 
                    ? 'bg-primary text-white border-primary' 
                    : status === 'active'
                      ? 'bg-white border-primary text-primary'
                      : status === 'error'
                        ? 'bg-error text-white border-error'
                        : 'bg-base-200 border-base-300 text-base-content/50'
                  }
                `}>
                  {status === 'complete' ? (
                    <Check className="w-4 h-4" />
                  ) : status === 'active' ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : status === 'error' ? (
                    <AlertCircle className="w-4 h-4" />
                  ) : (
                    <span className="text-xs">{index + 1}</span>
                  )}
                </div>
                
                {/* Step content */}
                <div className={`flex-1 py-3 ${!isLast ? 'pb-6' : ''}`}>
                  <div className="flex items-center gap-2">
                    <div className={`
                      p-1.5 rounded
                      ${status === 'complete' 
                        ? 'text-primary' 
                        : status === 'active'
                          ? 'text-primary animate-pulse'
                          : status === 'error'
                            ? 'text-error'
                            : 'text-base-content/40'
                      }
                    `}>
                      {steps[step].icon}
                    </div>
                    <h4 className={`
                      text-sm font-medium
                      ${status === 'complete' 
                        ? 'text-base-content' 
                        : status === 'active'
                          ? 'text-primary'
                          : status === 'error'
                            ? 'text-error'
                            : 'text-base-content/50'
                      }
                    `}>
                      {steps[step].label}
                    </h4>
                  </div>
                  <p className={`
                    text-xs ml-9 mt-1
                    ${status === 'active' 
                      ? 'text-base-content/80' 
                      : 'text-base-content/50'
                    }
                  `}>
                    {steps[step].description}
                  </p>
                </div>
              </div>
              
              {/* Connecting line */}
              {!isLast && (
                <div className={`
                  absolute left-4 top-8 bottom-0 w-0.5
                  ${status === 'complete' 
                    ? 'bg-primary' 
                    : 'bg-base-300'
                  }
                `} />
              )}
            </div>
          );
        })}
      </div>
      
      {/* Error action button */}
      {currentStep === 'error' && (
        <div className="mt-6">
          <button 
            onClick={() => window.location.reload()}
            className="btn btn-error btn-sm"
          >
            Try Again
          </button>
        </div>
      )}
    </div>
  );
};


const globalStyles = `
@keyframes pulse-subtle {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.8;
  }
}
.animate-pulse-subtle {
  animation: pulse-subtle 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
}
`;

export default UploadProgress;