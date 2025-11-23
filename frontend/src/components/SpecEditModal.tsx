import { useState } from 'react';
import { AlertCircle, Edit } from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from './ui/dialog';
import { Button } from './ui/button';
import { Alert, AlertDescription } from './ui/alert';
import { editSpec } from '../lib/api';
import { toast } from '@/hooks/use-toast';

interface SpecEditModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  videoId: string;
  checkpointId: string;
  currentSpec: any;
  onSaveSuccess: () => void;
}

export function SpecEditModal({
  open,
  onOpenChange,
  videoId,
  checkpointId,
  currentSpec,
  onSaveSuccess,
}: SpecEditModalProps) {
  const [specJson, setSpecJson] = useState(JSON.stringify(currentSpec, null, 2));
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSave = async () => {
    try {
      setIsSaving(true);
      setError(null);

      // Validate JSON
      const parsed = JSON.parse(specJson);

      // Call edit API
      await editSpec(videoId, checkpointId, parsed);

      toast({
        title: 'Spec Updated',
        description: 'A new branch has been created with your changes.',
      });

      onSaveSuccess();
      onOpenChange(false);
    } catch (err) {
      console.error('[SpecEditModal] Save failed:', err);
      if (err instanceof SyntaxError) {
        setError('Invalid JSON syntax');
      } else {
        const errorMessage = err instanceof Error ? err.message : 'Failed to save spec';
        setError(errorMessage);
        toast({
          variant: 'destructive',
          title: 'Failed to Save',
          description: errorMessage,
        });
      }
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-5xl max-h-[90vh] overflow-hidden flex flex-col">
        <DialogHeader>
          <DialogTitle className="flex items-center space-x-2">
            <Edit className="w-5 h-5" />
            <span>Edit Video Specification</span>
          </DialogTitle>
          <DialogDescription>
            Edit the JSON specification. Saving will create a new branch.
          </DialogDescription>
        </DialogHeader>

        <div className="flex-1 overflow-hidden flex flex-col min-h-[500px]">
          <textarea
            value={specJson}
            onChange={(e) => setSpecJson(e.target.value)}
            className="flex-1 font-mono text-sm p-3 border rounded bg-background resize-y"
            spellCheck={false}
          />
          {error && (
            <Alert variant="destructive" className="mt-3">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}
        </div>

        <DialogFooter>
          <Button
            variant="secondary"
            onClick={() => onOpenChange(false)}
            disabled={isSaving}
          >
            Cancel
          </Button>
          <Button onClick={handleSave} disabled={isSaving}>
            {isSaving ? 'Saving...' : 'Save Changes'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
