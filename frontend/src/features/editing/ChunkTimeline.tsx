import { useState } from 'react';
import { GripVertical, Play, Clock } from 'lucide-react';
import { ChunkMetadata } from '../../lib/api';
import { Badge } from '@/components/ui/badge';

interface ChunkTimelineProps {
  chunks: ChunkMetadata[];
  selectedChunks: number[];
  onChunkSelect: (chunkIndex: number, multiSelect?: boolean) => void;
  onReorder: (newOrder: number[]) => void;
}

export function ChunkTimeline({
  chunks,
  selectedChunks,
  onChunkSelect,
  onReorder,
}: ChunkTimelineProps) {
  const [draggedIndex, setDraggedIndex] = useState<number | null>(null);

  const handleDragStart = (index: number) => {
    setDraggedIndex(index);
  };

  const handleDragOver = (e: React.DragEvent, index: number) => {
    e.preventDefault();
    if (draggedIndex === null || draggedIndex === index) return;

    const newChunks = [...chunks];
    const draggedChunk = newChunks[draggedIndex];
    newChunks.splice(draggedIndex, 1);
    newChunks.splice(index, 0, draggedChunk);

    // Update order (map old indices to new indices)
    const newOrder = newChunks.map((_, idx) => idx);
    onReorder(newOrder);
    setDraggedIndex(index);
  };

  const handleDragEnd = () => {
    setDraggedIndex(null);
  };

  const formatDuration = (seconds: number) => {
    return `${seconds.toFixed(1)}s`;
  };

  return (
    <div className="space-y-2">
      {chunks.length === 0 ? (
        <div className="text-center py-8 text-muted-foreground">
          No chunks available
        </div>
      ) : (
        chunks.map((chunk, index) => {
          const isSelected = selectedChunks.includes(index);
          const hasMultipleVersions = chunk.versions.length > 1;
          const isDragging = draggedIndex === index;

          return (
            <div
              key={`chunk-${index}`}
              draggable
              onDragStart={() => handleDragStart(index)}
              onDragOver={(e) => handleDragOver(e, index)}
              onDragEnd={handleDragEnd}
              onClick={() => onChunkSelect(index, false)}
              onMouseDown={(e) => {
                if (e.shiftKey) {
                  e.preventDefault();
                  onChunkSelect(index, true);
                }
              }}
              className={`
                group relative flex items-center gap-4 p-4 rounded-lg border-2 cursor-pointer
                transition-all duration-200
                ${
                  isSelected
                    ? 'border-primary bg-primary/10'
                    : 'border-border hover:border-primary/50'
                }
                ${isDragging ? 'opacity-50' : ''}
              `}
            >
              {/* Drag Handle */}
              <div className="flex-shrink-0 text-muted-foreground group-hover:text-foreground">
                <GripVertical className="w-5 h-5" />
              </div>

              {/* Chunk Number */}
              <div className="flex-shrink-0 w-10 h-10 rounded-full bg-primary/20 flex items-center justify-center font-semibold text-primary relative">
                {index + 1}
                {/* Split indicator badge */}
                {chunk.versions.some(v => v.version_id === 'split_part1' || v.version_id === 'split_part2') && (
                  <span className="absolute -top-1 -right-1 w-3 h-3 bg-orange-500 rounded-full border-2 border-background" title="Split chunk" />
                )}
              </div>

              {/* Chunk Info */}
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <h3 className="font-medium text-foreground truncate">
                    Chunk {index + 1}
                  </h3>
                  {hasMultipleVersions && (
                    <Badge variant="secondary" className="text-xs">
                      {chunk.versions.length} versions
                    </Badge>
                  )}
                </div>
                <p className="text-sm text-muted-foreground truncate mb-2">
                  {chunk.prompt || 'No prompt'}
                </p>
                <div className="flex items-center gap-4 text-xs text-muted-foreground">
                  <div className="flex items-center gap-1">
                    <Clock className="w-3 h-3" />
                    {formatDuration(chunk.duration)}
                  </div>
                  <div>Model: {chunk.model}</div>
                  <div>Cost: ${chunk.cost.toFixed(4)}</div>
                </div>
              </div>

              {/* Play Button */}
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onChunkSelect(index, false);
                }}
                className="flex-shrink-0 p-2 rounded-full hover:bg-primary/10 text-muted-foreground hover:text-primary transition-colors"
              >
                <Play className="w-5 h-5" />
              </button>
            </div>
          );
        })
      )}
    </div>
  );
}

