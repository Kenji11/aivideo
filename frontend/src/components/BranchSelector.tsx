import { BranchInfo } from '../lib/api';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from './ui/select';
import { Badge } from './ui/badge';
import { GitBranch } from 'lucide-react';

interface BranchSelectorProps {
  branches: BranchInfo[];
  currentBranch: string;
  onBranchSelect?: (branchName: string) => void;
  disabled?: boolean;
}

export function BranchSelector({
  branches,
  currentBranch,
  onBranchSelect,
  disabled = false,
}: BranchSelectorProps) {
  if (!branches || branches.length === 0) {
    return null;
  }

  // const phaseNames: Record<number, string> = {
  //   1: 'Planning',
  //   2: 'Storyboard',
  //   3: 'Chunks',
  //   4: 'Refinement',
  // };

  return (
    <div className="flex items-center gap-2">
      <GitBranch className="h-4 w-4 text-muted-foreground" />
      <Select
        value={currentBranch}
        onValueChange={onBranchSelect}
        disabled={disabled || branches.length <= 1}
      >
        <SelectTrigger className="w-[200px]">
          <SelectValue placeholder="Select branch" />
        </SelectTrigger>
        <SelectContent>
          {branches.map((branch) => (
            <SelectItem key={branch.branch_name} value={branch.branch_name}>
              <div className="flex items-center gap-2">
                <span className="font-medium">{branch.branch_name}</span>
                <Badge variant="outline" className="text-xs">
                  Phase {branch.phase_number}
                </Badge>
                {branch.can_continue && (
                  <Badge variant="default" className="text-xs">
                    Pending
                  </Badge>
                )}
              </div>
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
      <span className="text-sm text-muted-foreground">
        {branches.length} active {branches.length === 1 ? 'branch' : 'branches'}
      </span>
    </div>
  );
}
