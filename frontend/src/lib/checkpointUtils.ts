import type { CheckpointTreeNode, CheckpointResponse } from './api';

/**
 * Recursively flattens a checkpoint tree into an array of all checkpoints
 */
export function getAllCheckpointsFromTree(tree: CheckpointTreeNode[]): CheckpointResponse[] {
  const result: CheckpointResponse[] = [];
  function traverse(node: CheckpointTreeNode) {
    result.push(node.checkpoint);
    node.children.forEach(traverse);
  }
  tree.forEach(traverse);
  return result;
}

/**
 * Rebuilds tree structure from flat checkpoint list by inferring parent-child
 * relationships based on phase_number and created_at timestamps
 */
export function rebuildTreeFromPhases(checkpoints: CheckpointResponse[]): CheckpointTreeNode[] {
  // Sort by phase_number, then by created_at
  const sorted = [...checkpoints].sort((a, b) => {
    if (a.phase_number !== b.phase_number) {
      return a.phase_number - b.phase_number;
    }
    return new Date(a.created_at).getTime() - new Date(b.created_at).getTime();
  });

  // Build a map of checkpoint ID to tree node
  const nodeMap = new Map<string, CheckpointTreeNode>();
  sorted.forEach(cp => {
    nodeMap.set(cp.id, {
      checkpoint: cp,
      children: []
    });
  });

  // Build parent-child relationships
  const roots: CheckpointTreeNode[] = [];
  sorted.forEach(cp => {
    const node = nodeMap.get(cp.id)!;

    if (cp.phase_number === 1) {
      // Phase 1 checkpoints are roots
      roots.push(node);
    } else {
      // Find parent: the most recent checkpoint from the previous phase
      const parentPhase = cp.phase_number - 1;
      const parentCandidates = sorted.filter(
        p => p.phase_number === parentPhase &&
        new Date(p.created_at).getTime() < new Date(cp.created_at).getTime()
      );

      if (parentCandidates.length > 0) {
        // Use the most recent parent candidate
        const parent = parentCandidates[parentCandidates.length - 1];
        const parentNode = nodeMap.get(parent.id);
        if (parentNode) {
          parentNode.children.push(node);
        } else {
          // Fallback: make it a root if parent not found
          roots.push(node);
        }
      } else {
        // No parent found, make it a root
        roots.push(node);
      }
    }
  });

  return roots;
}

/**
 * Gets all phase 1 checkpoints from tree, sorted by creation time
 */
export function getPhase1Checkpoints(tree: CheckpointTreeNode[]): CheckpointResponse[] {
  // Phase 1 checkpoints are roots (no parent)
  return tree
    .filter(node => node.checkpoint.phase_number === 1)
    .map(node => node.checkpoint)
    .sort((a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime());
}

/**
 * Gets children of a specific checkpoint from the tree
 */
export function getChildrenOfCheckpoint(
  tree: CheckpointTreeNode[],
  parentId: string
): CheckpointResponse[] {
  function findNode(nodes: CheckpointTreeNode[], id: string): CheckpointTreeNode | null {
    for (const node of nodes) {
      if (node.checkpoint.id === id) {
        return node;
      }
      const found = findNode(node.children, id);
      if (found) return found;
    }
    return null;
  }

  const parentNode = findNode(tree, parentId);
  if (!parentNode) {
    console.warn('[checkpointUtils] getChildrenOfCheckpoint: Parent node not found for', parentId, 'in tree with', tree.length, 'root nodes');
    return [];
  }

  const children = parentNode.children
    .map(node => node.checkpoint)
    .sort((a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime());

  console.log('[checkpointUtils] getChildrenOfCheckpoint: Found', children.length, 'children for parent', parentId, ':', children.map(c => ({ id: c.id, phase: c.phase_number })));

  return children;
}

/**
 * Gets the lineage of a checkpoint from root to the specified checkpoint
 */
export function getCheckpointLineage(
  checkpointId: string,
  tree: CheckpointTreeNode[]
): CheckpointResponse[] {
  const allCheckpoints = getAllCheckpointsFromTree(tree);
  const checkpointMap = new Map(allCheckpoints.map(cp => [cp.id, cp]));

  const lineage: CheckpointResponse[] = [];
  let currentId: string | undefined = checkpointId;

  while (currentId) {
    const checkpoint = checkpointMap.get(currentId);
    if (!checkpoint) break;
    lineage.unshift(checkpoint);
    currentId = checkpoint.parent_checkpoint_id || undefined;
  }

  return lineage;
}

/**
 * Interface for checkpoint indices across phases
 */
export interface CheckpointIndices {
  phase1: number;
  phase2: number | null;
  phase3: number | null;
  phase4: number | null;
}

/**
 * Gets the selected checkpoint for a given phase based on checkpoint indices
 */
export function getSelectedCheckpoint(
  phase: 1 | 2 | 3 | 4,
  indices: CheckpointIndices,
  tree: CheckpointTreeNode[]
): CheckpointResponse | null {
  if (phase === 1) {
    const phase1Checkpoints = getPhase1Checkpoints(tree);
    return phase1Checkpoints[indices.phase1] || null;
  }

  if (phase === 2 && indices.phase2 !== null) {
    const phase1Checkpoint = getSelectedCheckpoint(1, indices, tree);
    if (!phase1Checkpoint) return null;
    const phase2Checkpoints = getChildrenOfCheckpoint(tree, phase1Checkpoint.id);
    return phase2Checkpoints[indices.phase2] || null;
  }

  if (phase === 3 && indices.phase3 !== null) {
    const phase2Checkpoint = getSelectedCheckpoint(2, indices, tree);
    if (!phase2Checkpoint) return null;
    const phase3Checkpoints = getChildrenOfCheckpoint(tree, phase2Checkpoint.id);
    return phase3Checkpoints[indices.phase3] || null;
  }

  if (phase === 4 && indices.phase4 !== null) {
    const phase3Checkpoint = getSelectedCheckpoint(3, indices, tree);
    if (!phase3Checkpoint) return null;
    const phase4Checkpoints = getChildrenOfCheckpoint(tree, phase3Checkpoint.id);
    return phase4Checkpoints[indices.phase4] || null;
  }

  return null;
}
