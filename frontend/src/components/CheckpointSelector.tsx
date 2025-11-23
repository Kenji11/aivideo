import { CheckpointTreeNode } from '../lib/api';
import { getPhase1Options, getPhase2Options, getPhase3Options } from '../lib/checkpointUtils';

interface CheckpointSelectorProps {
  tree: CheckpointTreeNode[];
  selections: {
    phase1: string | null;
    phase2: string | null;
    phase3: string | null;
  };
  onSelectionChange: (phase: 1 | 2 | 3, checkpointId: string) => void;
}

export function CheckpointSelector({
  tree,
  selections,
  onSelectionChange,
}: CheckpointSelectorProps) {
  const phase1Options = getPhase1Options(tree);
  const phase2Options = selections.phase1
    ? getPhase2Options(tree, selections.phase1)
    : [];
  const phase3Options = selections.phase2
    ? getPhase3Options(tree, selections.phase2)
    : [];

  console.log('[CheckpointSelector] Phase 1 options:', phase1Options.map(cp => ({ id: cp.id, branch: cp.branch_name, parent: cp.parent_checkpoint_id })));
  console.log('[CheckpointSelector] Current selections:', selections);

  return (
    <div className="border rounded-lg p-4 bg-card mb-6">
      <h3 className="text-sm font-medium mb-3 text-muted-foreground">
        Select Checkpoint Path
      </h3>
      <div className="grid grid-cols-3 gap-4">
        {/* Phase 1 Column */}
        <div>
          <div className="text-xs font-medium mb-2 text-muted-foreground">
            Phase 1: Validation
          </div>
          <div className="space-y-1">
            {phase1Options.map(cp => (
              <button
                key={cp.id}
                onClick={() => onSelectionChange(1, cp.id)}
                className={`w-full text-left px-3 py-2 text-sm rounded border transition-colors ${
                  selections.phase1 === cp.id
                    ? 'font-bold bg-primary/10 border-primary'
                    : 'hover:bg-muted border-transparent'
                }`}
              >
                {cp.branch_name}
              </button>
            ))}
          </div>
        </div>

        {/* Phase 2 Column */}
        <div>
          <div className="text-xs font-medium mb-2 text-muted-foreground">
            Phase 2: Storyboard
          </div>
          {selections.phase1 ? (
            <div className="space-y-1">
              {phase2Options.map(cp => (
                <button
                  key={cp.id}
                  onClick={() => onSelectionChange(2, cp.id)}
                  className={`w-full text-left px-3 py-2 text-sm rounded border transition-colors ${
                    selections.phase2 === cp.id
                      ? 'font-bold bg-primary/10 border-primary'
                      : 'hover:bg-muted border-transparent'
                  }`}
                >
                  {cp.branch_name}
                </button>
              ))}
            </div>
          ) : (
            <div className="text-xs text-muted-foreground italic">
              Select Phase 1 first
            </div>
          )}
        </div>

        {/* Phase 3 Column */}
        <div>
          <div className="text-xs font-medium mb-2 text-muted-foreground">
            Phase 3: Video Chunks
          </div>
          {selections.phase2 ? (
            <div className="space-y-1">
              {phase3Options.map(cp => (
                <button
                  key={cp.id}
                  onClick={() => onSelectionChange(3, cp.id)}
                  className={`w-full text-left px-3 py-2 text-sm rounded border transition-colors ${
                    selections.phase3 === cp.id
                      ? 'font-bold bg-primary/10 border-primary'
                      : 'hover:bg-muted border-transparent'
                  }`}
                >
                  {cp.branch_name}
                </button>
              ))}
            </div>
          ) : (
            <div className="text-xs text-muted-foreground italic">
              Select Phase 2 first
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
