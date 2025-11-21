import { CheckpointTreeNode } from '../lib/api';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Badge } from './ui/badge';
import { ChevronRight, GitBranch } from 'lucide-react';

interface CheckpointTreeProps {
  tree: CheckpointTreeNode[];
  currentCheckpointId?: string;
  onCheckpointClick?: (checkpointId: string) => void;
}

export function CheckpointTree({
  tree,
  currentCheckpointId,
  onCheckpointClick,
}: CheckpointTreeProps) {
  if (!tree || tree.length === 0) {
    return null;
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <GitBranch className="h-5 w-5" />
          Checkpoint Tree
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-1">
          {tree.map((node) => (
            <TreeNode
              key={node.checkpoint.id}
              node={node}
              level={0}
              currentCheckpointId={currentCheckpointId}
              onCheckpointClick={onCheckpointClick}
            />
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

interface TreeNodeProps {
  node: CheckpointTreeNode;
  level: number;
  currentCheckpointId?: string;
  onCheckpointClick?: (checkpointId: string) => void;
}

function TreeNode({
  node,
  level,
  currentCheckpointId,
  onCheckpointClick,
}: TreeNodeProps) {
  const isCurrentCheckpoint = node.checkpoint.id === currentCheckpointId;
  const hasChildren = node.children && node.children.length > 0;

  const phaseNames: Record<number, string> = {
    1: 'Planning',
    2: 'Storyboard',
    3: 'Chunks',
    4: 'Refinement',
  };

  const statusColors: Record<string, string> = {
    pending: 'bg-yellow-500/10 text-yellow-500 border-yellow-500/20',
    approved: 'bg-green-500/10 text-green-500 border-green-500/20',
    abandoned: 'bg-gray-500/10 text-gray-500 border-gray-500/20',
  };

  return (
    <div>
      <div
        className={`
          flex items-center gap-2 p-2 rounded-md hover:bg-muted/50 cursor-pointer transition-colors
          ${isCurrentCheckpoint ? 'bg-primary/10 border border-primary' : 'border border-transparent'}
        `}
        style={{ paddingLeft: `${level * 24 + 8}px` }}
        onClick={() => onCheckpointClick?.(node.checkpoint.id)}
      >
        {hasChildren && <ChevronRight className="h-4 w-4 text-muted-foreground" />}
        {!hasChildren && <div className="w-4" />}

        <Badge variant="outline" className="text-xs">
          Phase {node.checkpoint.phase_number}
        </Badge>

        <span className="text-sm font-medium">
          {phaseNames[node.checkpoint.phase_number]}
        </span>

        <Badge variant="outline" className="text-xs">
          {node.checkpoint.branch_name}
        </Badge>

        <Badge variant="outline" className={`text-xs ${statusColors[node.checkpoint.status]}`}>
          {node.checkpoint.status}
        </Badge>

        {node.checkpoint.version > 1 && (
          <Badge variant="secondary" className="text-xs">
            v{node.checkpoint.version}
          </Badge>
        )}
      </div>

      {/* Render children recursively */}
      {hasChildren && (
        <div className="ml-4 border-l-2 border-muted">
          {node.children.map((child) => (
            <TreeNode
              key={child.checkpoint.id}
              node={child}
              level={level + 1}
              currentCheckpointId={currentCheckpointId}
              onCheckpointClick={onCheckpointClick}
            />
          ))}
        </div>
      )}
    </div>
  );
}
