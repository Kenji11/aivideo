import { useState, useEffect } from 'react';
import { RefreshCw, Trash2, Scissors, DollarSign, Loader2, Undo2 } from 'lucide-react';
import { api, ChunkMetadata, EditingAction, CostEstimate, getModelDisplayName } from '../../lib/api';
import { toast } from '@/hooks/use-toast';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Slider } from '@/components/ui/slider';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';

interface EditActionsProps {
  videoId: string;
  selectedChunks: number[];
  chunks: ChunkMetadata[];
  onEditComplete: () => void;
  onProcessingChange: (processing: boolean) => void;
}

export function EditActions({
  videoId,
  selectedChunks,
  chunks,
  onEditComplete,
  onProcessingChange,
}: EditActionsProps) {
  const [replaceDialogOpen, setReplaceDialogOpen] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [splitDialogOpen, setSplitDialogOpen] = useState(false);
  const [costEstimateDialogOpen, setCostEstimateDialogOpen] = useState(false);
  
  const [newPrompt, setNewPrompt] = useState('');
  const [newModel, setNewModel] = useState('veo_fast');
  const [originalModel, setOriginalModel] = useState<string>('veo_fast');
  const [splitTime, setSplitTime] = useState<number | ''>('');
  const [splitMethod, setSplitMethod] = useState<'time' | 'percentage'>('time');
  const [costEstimate, setCostEstimate] = useState<CostEstimate | null>(null);
  const [isLoadingEstimate, setIsLoadingEstimate] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [splitInfo, setSplitInfo] = useState<{ is_split_part: boolean; part_number?: number; original_index?: number } | null>(null);
  
  // Check if selected chunk is a split part and get original model
  useEffect(() => {
    const checkSplitInfo = async () => {
      if (selectedChunks.length === 1 && videoId) {
        try {
          const info = await api.getChunkSplitInfo(videoId, selectedChunks[0]);
          setSplitInfo(info);
        } catch {
          setSplitInfo(null);
        }
      } else {
        setSplitInfo(null);
      }
    };
    
    // Set original model from first selected chunk
    if (selectedChunks.length > 0 && chunks.length > 0) {
      const firstChunk = chunks[selectedChunks[0]];
      if (firstChunk?.model) {
        setOriginalModel(firstChunk.model);
        setNewModel(firstChunk.model); // Default to the original model
      }
    }
    
    checkSplitInfo();
  }, [selectedChunks, videoId, chunks]);

  const models = [
    { value: 'veo_fast', label: 'Google Veo 3.1 Fast (Default)' },
    { value: 'hailuo_fast', label: 'Minimax Hailuo 2.3 Fast' },
    { value: 'veo', label: 'Google Veo 3.1' },
    { value: 'hailuo_23', label: 'Minimax Hailuo 2.3' },
    { value: 'kling_16_pro', label: 'Kling 1.6 Pro' },
    { value: 'kling_21', label: 'Kling 2.1 (720p)' },
    { value: 'kling_21_1080p', label: 'Kling 2.1 (1080p)' },
    { value: 'kling_25_pro', label: 'Kling 2.5 Turbo Pro' },
    { value: 'minimax_video_01', label: 'Minimax Video-01 (Subject Reference)' },
    { value: 'runway', label: 'Runway Gen-2' },
  ];

  const handleReplace = async () => {
    if (selectedChunks.length === 0) {
      toast({
        variant: 'destructive',
        title: 'No chunks selected',
        description: 'Please select at least one chunk to replace',
      });
      return;
    }

    setIsProcessing(true);
    onProcessingChange(true);
    setReplaceDialogOpen(false);

    try {
      const actions: EditingAction[] = [
        {
          action_type: 'replace',
          chunk_indices: selectedChunks,
          new_prompt: newPrompt || undefined,
          new_model: newModel !== originalModel ? newModel : undefined,
          keep_original: true,
        },
      ];

      await api.submitEdits(videoId, { actions });
      
      toast({
        variant: 'default',
        title: 'Replacement Started',
        description: `Regenerating ${selectedChunks.length} chunk(s)...`,
      });

      // Reset form
      setNewPrompt('');
      setNewModel(originalModel);
      setSplitTime(''); // Reset split time
      
      // Poll for completion
      pollEditingStatus();
    } catch (error: any) {
      toast({
        variant: 'destructive',
        title: 'Error',
        description: error.message || 'Failed to replace chunks',
      });
      setIsProcessing(false);
      onProcessingChange(false);
    }
  };

  const handleDelete = async () => {
    if (selectedChunks.length === 0) {
      toast({
        variant: 'destructive',
        title: 'No chunks selected',
        description: 'Please select at least one chunk to delete',
      });
      return;
    }

    setIsProcessing(true);
    onProcessingChange(true);
    setDeleteDialogOpen(false);

    try {
      const actions: EditingAction[] = [
        {
          action_type: 'delete',
          chunk_indices: selectedChunks,
        },
      ];

      await api.submitEdits(videoId, { actions });
      
      toast({
        variant: 'default',
        title: 'Deletion Started',
        description: `Deleting ${selectedChunks.length} chunk(s)...`,
      });

      pollEditingStatus();
    } catch (error: any) {
      toast({
        variant: 'destructive',
        title: 'Error',
        description: error.message || 'Failed to delete chunks',
      });
      setIsProcessing(false);
      onProcessingChange(false);
    }
  };

  const handleUndoSplit = async () => {
    if (selectedChunks.length !== 1) {
      toast({
        variant: 'destructive',
        title: 'Invalid selection',
        description: 'Please select exactly one chunk to undo split',
      });
      return;
    }

    setIsProcessing(true);
    onProcessingChange(true);

    try {
      const actions: EditingAction[] = [
        {
          action_type: 'undo_split',
          chunk_indices: selectedChunks,
        },
      ];

      await api.submitEdits(videoId, { actions });
      
      toast({
        variant: 'default',
        title: 'Undo Split Started',
        description: 'Merging split chunks back together...',
      });

      pollEditingStatus();
    } catch (error: any) {
      toast({
        variant: 'destructive',
        title: 'Error',
        description: error.message || 'Failed to undo split',
      });
      setIsProcessing(false);
      onProcessingChange(false);
    }
  };

  const handleSplit = async () => {
    if (selectedChunks.length !== 1) {
      toast({
        variant: 'destructive',
        title: 'Invalid selection',
        description: 'Please select exactly one chunk to split',
      });
      return;
    }

    if (!selectedChunk) {
      toast({
        variant: 'destructive',
        title: 'Error',
        description: 'No chunk selected',
      });
      return;
    }

    const chunkDuration = selectedChunk.duration;
    
    // Validate input based on method
    if (splitTime === '' || splitTime === null || splitTime === undefined) {
      toast({
        variant: 'destructive',
        title: 'Value required',
        description: splitMethod === 'time' 
          ? 'Please enter a time in seconds to split at'
          : 'Please enter a percentage to split at',
      });
      return;
    }
    
    const value = Number(splitTime);
    if (isNaN(value) || value <= 0) {
      toast({
        variant: 'destructive',
        title: 'Invalid value',
        description: 'Value must be greater than 0',
      });
      return;
    }

    // Validate based on method
    if (splitMethod === 'time') {
      if (value >= chunkDuration) {
        toast({
          variant: 'destructive',
          title: 'Invalid time',
          description: `Time must be less than chunk duration (${chunkDuration.toFixed(1)}s)`,
        });
        return;
      }
    } else if (splitMethod === 'percentage') {
      if (value >= 100) {
        toast({
          variant: 'destructive',
          title: 'Invalid percentage',
          description: 'Percentage must be less than 100%',
        });
        return;
      }
    }

    setIsProcessing(true);
    onProcessingChange(true);
    setSplitDialogOpen(false);

    try {
      const actions: EditingAction[] = [
        {
          action_type: 'split',
          chunk_indices: selectedChunks,
          ...(splitMethod === 'time' 
            ? { split_time: value }
            : { split_percentage: value }
          ),
        },
      ];

      await api.submitEdits(videoId, { actions });
      
      toast({
        variant: 'default',
        title: 'Split Started',
        description: 'Splitting chunk...',
      });

      pollEditingStatus();
    } catch (error: any) {
      toast({
        variant: 'destructive',
        title: 'Error',
        description: error.message || 'Failed to split chunk',
      });
      setIsProcessing(false);
      onProcessingChange(false);
    }
  };

  const handleEstimateCost = async () => {
    if (selectedChunks.length === 0) {
      toast({
        variant: 'destructive',
        title: 'No chunks selected',
        description: 'Please select chunks to estimate cost',
      });
      return;
    }

    setIsLoadingEstimate(true);
    setCostEstimateDialogOpen(true);

    try {
      const estimate = await api.estimateEditCost(videoId, selectedChunks, newModel);
      setCostEstimate(estimate);
    } catch (error: any) {
      toast({
        variant: 'destructive',
        title: 'Error',
        description: error.message || 'Failed to estimate cost',
      });
      setCostEstimateDialogOpen(false);
    } finally {
      setIsLoadingEstimate(false);
    }
  };

  const pollEditingStatus = async () => {
    const maxAttempts = 60; // 5 minutes max
    let attempts = 0;

    const poll = async () => {
      try {
        const status = await api.getEditingStatus(videoId);
        
        if (status.status === 'success' || status.status === 'complete') {
          setIsProcessing(false);
          onProcessingChange(false);
          onEditComplete();
          toast({
            variant: 'default',
            title: 'Editing Complete',
            description: 'Chunks have been updated successfully',
          });
          return;
        }
        
        if (status.status === 'failed') {
          setIsProcessing(false);
          onProcessingChange(false);
          toast({
            variant: 'destructive',
            title: 'Editing Failed',
            description: status.error_message || 'Failed to process editing request',
          });
          return;
        }

        attempts++;
        if (attempts < maxAttempts) {
          setTimeout(poll, 5000); // Poll every 5 seconds
        } else {
          setIsProcessing(false);
          onProcessingChange(false);
          toast({
            variant: 'destructive',
            title: 'Timeout',
            description: 'Editing is taking longer than expected',
          });
        }
      } catch (error: any) {
        console.error('Polling error:', error);
        attempts++;
        if (attempts < maxAttempts) {
          setTimeout(poll, 5000);
        } else {
          setIsProcessing(false);
          onProcessingChange(false);
        }
      }
    };

    poll();
  };

  const hasSelection = selectedChunks.length > 0;
  const selectedChunk = selectedChunks.length === 1 ? chunks[selectedChunks[0]] : null;

  return (
    <div className="space-y-4">
      {!hasSelection && (
        <div className="text-sm text-muted-foreground text-center py-4">
          Select chunks from the timeline to edit
        </div>
      )}

      {hasSelection && (
        <>
          <div className="text-sm text-muted-foreground">
            {selectedChunks.length} chunk(s) selected
          </div>

          {/* Replace */}
          <Button
            onClick={() => {
              // Initialize prompt with original prompt from first selected chunk
              if (selectedChunks.length > 0 && chunks.length > 0) {
                const firstChunk = chunks[selectedChunks[0]];
                setNewPrompt(firstChunk?.prompt || '');
              }
              setReplaceDialogOpen(true);
            }}
            disabled={isProcessing}
            className="w-full flex items-center gap-2"
            variant="default"
          >
            <RefreshCw className="w-4 h-4" />
            Replace Selected
          </Button>

          {/* Delete */}
          <Button
            onClick={() => setDeleteDialogOpen(true)}
            disabled={isProcessing}
            className="w-full flex items-center gap-2"
            variant="destructive"
          >
            <Trash2 className="w-4 h-4" />
            Delete Selected
          </Button>

          {/* Undo Split (only if chunk is a split part) */}
          {selectedChunks.length === 1 && splitInfo?.is_split_part && (
            <Button
              onClick={handleUndoSplit}
              disabled={isProcessing}
              className="w-full flex items-center gap-2"
              variant="outline"
            >
              <Undo2 className="w-4 h-4" />
              Undo Split (Part {splitInfo.part_number})
            </Button>
          )}

          {/* Split (only for single selection, not if it's already a split part) */}
          {selectedChunks.length === 1 && !splitInfo?.is_split_part && (
            <Button
              onClick={() => setSplitDialogOpen(true)}
              disabled={isProcessing}
              className="w-full flex items-center gap-2"
              variant="outline"
            >
              <Scissors className="w-4 h-4" />
              Split Chunk
            </Button>
          )}

          {/* Cost Estimate */}
          <Button
            onClick={handleEstimateCost}
            disabled={isProcessing || isLoadingEstimate}
            className="w-full flex items-center gap-2"
            variant="outline"
          >
            {isLoadingEstimate ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <DollarSign className="w-4 h-4" />
            )}
            Estimate Cost
          </Button>
        </>
      )}

      {isProcessing && (
        <div className="text-sm text-muted-foreground text-center py-2">
          <Loader2 className="w-4 h-4 animate-spin inline-block mr-2" />
          Processing edits...
        </div>
      )}

      {/* Replace Dialog */}
      <Dialog 
        open={replaceDialogOpen} 
        onOpenChange={(open) => {
          setReplaceDialogOpen(open);
          // Reset prompt when dialog closes without saving
          if (!open && selectedChunks.length > 0 && chunks.length > 0) {
            const firstChunk = chunks[selectedChunks[0]];
            setNewPrompt(firstChunk?.prompt || '');
          }
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Replace Chunks</DialogTitle>
            <DialogDescription>
              Generate new versions of selected chunks. Original versions will be kept for comparison.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="prompt">Prompt</Label>
              <Textarea
                id="prompt"
                placeholder="Enter prompt for video generation"
                value={newPrompt}
                onChange={(e) => setNewPrompt(e.target.value)}
                className="resize-y min-h-[80px]"
              />
              <p className="text-xs text-muted-foreground">
                {selectedChunks.length === 1 
                  ? 'Edit the prompt to generate a new version of this chunk'
                  : `This prompt will be applied to all ${selectedChunks.length} selected chunks`}
              </p>
            </div>
            <div className="space-y-2">
              <Label htmlFor="model">Model</Label>
              <Select value={newModel} onValueChange={setNewModel}>
                <SelectTrigger id="model">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {models.map((model) => (
                    <SelectItem key={model.value} value={model.value}>
                      {model.label}
                      {model.value === originalModel && (
                        <span className="text-xs text-muted-foreground ml-2">(Original)</span>
                      )}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              {newModel === originalModel && (
                <p className="text-xs text-muted-foreground">
                  Using the same model as original chunk
                </p>
              )}
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setReplaceDialogOpen(false)}>
              Cancel
            </Button>
            <Button onClick={handleReplace}>Replace</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Dialog */}
      <Dialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete Chunks</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete {selectedChunks.length} chunk(s)? This action cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteDialogOpen(false)}>
              Cancel
            </Button>
            <Button variant="destructive" onClick={handleDelete}>
              Delete
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Split Dialog */}
      <Dialog open={splitDialogOpen} onOpenChange={setSplitDialogOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Split Chunk</DialogTitle>
            <DialogDescription>
              Split this chunk into two parts. Choose how to specify the split point.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            {/* Visual Timeline Scrubber */}
            {selectedChunk && (
              <div className="space-y-2">
                <Label>Timeline Preview</Label>
                <div className="relative w-full h-16 bg-muted rounded-lg overflow-hidden border-2 border-border">
                  {/* Full chunk bar */}
                  <div 
                    className="absolute inset-0 bg-primary/20"
                    style={{ width: '100%' }}
                  />
                  
                  {/* Split indicator */}
                  {splitTime && (
                    <>
                      <div 
                        className="absolute top-0 bottom-0 bg-primary border-l-2 border-primary z-10"
                        style={{ 
                          left: splitMethod === 'percentage' 
                            ? `${Number(splitTime)}%` 
                            : `${(Number(splitTime) / (selectedChunk.duration || 1)) * 100}%`,
                          width: '2px'
                        }}
                      />
                      {/* Split point label */}
                      <div 
                        className="absolute top-1 text-xs font-medium text-primary bg-background px-1 rounded z-20"
                        style={{ 
                          left: splitMethod === 'percentage' 
                            ? `${Number(splitTime)}%` 
                            : `${(Number(splitTime) / (selectedChunk.duration || 1)) * 100}%`,
                          transform: 'translateX(-50%)'
                        }}
                      >
                        {splitMethod === 'percentage' 
                          ? `${Number(splitTime).toFixed(0)}%`
                          : `${Number(splitTime).toFixed(1)}s`
                        }
                      </div>
                    </>
                  )}
                  
                  {/* Clickable area to set split point */}
                  <div 
                    className="absolute inset-0 cursor-pointer"
                    onClick={(e) => {
                      const rect = e.currentTarget.getBoundingClientRect();
                      const clickX = e.clientX - rect.left;
                      const percentage = (clickX / rect.width) * 100;
                      
                      if (splitMethod === 'percentage') {
                        setSplitTime(Math.max(1, Math.min(99, Math.round(percentage))));
                      } else {
                        const time = (percentage / 100) * (selectedChunk.duration || 1);
                        setSplitTime(Math.max(0.1, Math.min((selectedChunk.duration || 1) - 0.1, Number(time.toFixed(1)))));
                      }
                    }}
                    title="Click to set split point"
                  />
                  
                  {/* Start and end labels */}
                  <div className="absolute bottom-1 left-2 text-xs text-muted-foreground">
                    0s
                  </div>
                  <div className="absolute bottom-1 right-2 text-xs text-muted-foreground">
                    {selectedChunk.duration.toFixed(1)}s
                  </div>
                </div>
                <p className="text-xs text-muted-foreground">
                  Click on the timeline to set the split point
                </p>
              </div>
            )}
            
            {/* Split Method Selection */}
            <div className="space-y-2">
              <Label>Split Method</Label>
              <Select value={splitMethod} onValueChange={(val: 'time' | 'percentage') => {
                setSplitMethod(val);
                setSplitTime('');
              }}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="time">Time (seconds)</SelectItem>
                  <SelectItem value="percentage">Percentage</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {/* Input Field */}
            <div className="space-y-2">
              <Label htmlFor="splitTime">
                {splitMethod === 'time' ? 'Time (seconds)' : 'Percentage (%)'}
              </Label>
              
              {/* Quick percentage buttons (only for percentage method) */}
              {splitMethod === 'percentage' && (
                <div className="flex gap-2 mb-2">
                  {[25, 50, 75].map((pct) => (
                    <Button
                      key={pct}
                      type="button"
                      variant="outline"
                      size="sm"
                      onClick={() => setSplitTime(pct)}
                      className="flex-1"
                    >
                      {pct}%
                    </Button>
                  ))}
                </div>
              )}
              
              {/* Slider for easier adjustment */}
              {selectedChunk && (
                <div className="space-y-2">
                  <Slider
                    value={[splitTime || (splitMethod === 'time' ? (selectedChunk.duration / 2) : 50)]}
                    onValueChange={(values) => {
                      const val = values[0];
                      if (!isNaN(val)) {
                        setSplitTime(splitMethod === 'time' ? Number(val.toFixed(1)) : Math.round(val));
                      }
                    }}
                    min={splitMethod === 'time' ? 0.1 : 1}
                    max={splitMethod === 'time' ? selectedChunk.duration : 99}
                    step={splitMethod === 'time' ? 0.1 : 1}
                    className="w-full"
                  />
                  <div className="flex justify-between text-xs text-muted-foreground">
                    <span>{splitMethod === 'time' ? '0.1s' : '1%'}</span>
                    <span>{splitMethod === 'time' ? `${selectedChunk.duration.toFixed(1)}s` : '99%'}</span>
                  </div>
                </div>
              )}
              
              <Input
                id="splitTime"
                type="number"
                step={splitMethod === 'time' ? '0.1' : '1'}
                min={0.1}
                max={splitMethod === 'time' ? selectedChunk?.duration : 99}
                placeholder={
                  splitMethod === 'time' 
                    ? `Enter time (0.1 - ${selectedChunk?.duration.toFixed(1)}s)`
                    : 'Enter percentage (1 - 99%)'
                }
                value={splitTime}
                onChange={(e) => {
                  const val = e.target.value;
                  if (val === '') {
                    setSplitTime('');
                  } else {
                    const num = parseFloat(val);
                    if (!isNaN(num)) {
                      setSplitTime(splitMethod === 'time' ? Number(num.toFixed(1)) : Math.round(num));
                    }
                  }
                }}
                required
              />
              
              {/* Preview of split parts */}
              <div className="text-xs text-muted-foreground space-y-1 p-3 bg-muted rounded-md">
                <p className="font-medium">Chunk duration: {selectedChunk?.duration.toFixed(1)}s</p>
                {splitTime && (
                  <>
                    {splitMethod === 'time' ? (
                      <>
                        <div className="mt-2 space-y-1">
                          <p className="text-primary">
                            Part 1: 0s → {Number(splitTime).toFixed(1)}s 
                            <span className="text-muted-foreground ml-1">
                              ({((Number(splitTime) / (selectedChunk?.duration || 1)) * 100).toFixed(0)}%)
                            </span>
                          </p>
                          <p className="text-primary">
                            Part 2: {Number(splitTime).toFixed(1)}s → {selectedChunk?.duration.toFixed(1)}s
                            <span className="text-muted-foreground ml-1">
                              ({(((selectedChunk?.duration || 0) - Number(splitTime)) / (selectedChunk?.duration || 1) * 100).toFixed(0)}%)
                            </span>
                          </p>
                        </div>
                      </>
                    ) : (
                      <>
                        <div className="mt-2 space-y-1">
                          <p className="text-primary">
                            Part 1: 0% → {Number(splitTime).toFixed(0)}%
                            <span className="text-muted-foreground ml-1">
                              ({(selectedChunk?.duration || 0) * Number(splitTime) / 100}s)
                            </span>
                          </p>
                          <p className="text-primary">
                            Part 2: {Number(splitTime).toFixed(0)}% → 100%
                            <span className="text-muted-foreground ml-1">
                              ({(selectedChunk?.duration || 0) * (100 - Number(splitTime)) / 100}s)
                            </span>
                          </p>
                        </div>
                      </>
                    )}
                  </>
                )}
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => {
              setSplitDialogOpen(false);
              setSplitTime('');
            }}>
              Cancel
            </Button>
            <Button onClick={handleSplit}>Split Chunk</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Cost Estimate Dialog */}
      <Dialog open={costEstimateDialogOpen} onOpenChange={setCostEstimateDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Cost Estimate</DialogTitle>
            <DialogDescription>
              Estimated cost for regenerating selected chunks
            </DialogDescription>
          </DialogHeader>
          {isLoadingEstimate ? (
            <div className="py-8 text-center">
              <Loader2 className="w-8 h-8 animate-spin mx-auto mb-4 text-primary" />
              <p className="text-muted-foreground">Calculating...</p>
            </div>
          ) : costEstimate ? (
            <div className="space-y-4 py-4">
              <div className="space-y-2">
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Total Cost:</span>
                  <span className="text-2xl font-bold text-primary">
                    ${costEstimate.estimated_cost.toFixed(4)}
                  </span>
                </div>
                {costEstimate.estimated_time_seconds && (
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Estimated Time:</span>
                    <span className="font-medium">
                      {Math.ceil(costEstimate.estimated_time_seconds / 60)} minutes
                    </span>
                  </div>
                )}
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Model:</span>
                  <span className="font-medium">{getModelDisplayName(costEstimate.model)}</span>
                </div>
              </div>
              {Object.keys(costEstimate.cost_per_chunk).length > 0 && (
                <div className="space-y-1 pt-2 border-t">
                  <p className="text-sm font-medium">Cost per chunk:</p>
                  {Object.entries(costEstimate.cost_per_chunk).map(([idx, cost]) => (
                    <div key={idx} className="flex justify-between text-sm">
                      <span className="text-muted-foreground">Chunk {parseInt(idx) + 1}:</span>
                      <span>${cost.toFixed(4)}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          ) : null}
          <DialogFooter>
            <Button onClick={() => setCostEstimateDialogOpen(false)}>Close</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

