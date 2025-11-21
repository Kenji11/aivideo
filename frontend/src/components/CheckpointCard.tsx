import { CheckpointInfo } from '../lib/api';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Button } from './ui/button';
import { Badge } from './ui/badge';

interface CheckpointCardProps {
  checkpoint: CheckpointInfo;
  videoId: string;
  onEdit?: () => void;
  onContinue?: () => void;
  isProcessing?: boolean;
}

export function CheckpointCard({
  checkpoint,
  videoId,
  onEdit,
  onContinue,
  isProcessing = false,
}: CheckpointCardProps) {
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

  // Extract artifacts by type
  const specArtifact = Object.values(checkpoint.artifacts || {}).find(
    (a) => a.artifact_type === 'spec'
  );
  const beatArtifacts = Object.values(checkpoint.artifacts || {})
    .filter((a) => a.artifact_type === 'beat_image')
    .sort((a, b) => a.artifact_key.localeCompare(b.artifact_key));
  const chunkArtifacts = Object.values(checkpoint.artifacts || {})
    .filter((a) => a.artifact_type === 'video_chunk')
    .sort((a, b) => a.artifact_key.localeCompare(b.artifact_key));
  const stitchedArtifact = Object.values(checkpoint.artifacts || {}).find(
    (a) => a.artifact_type === 'stitched'
  );
  const finalArtifact = Object.values(checkpoint.artifacts || {}).find(
    (a) => a.artifact_type === 'final_video'
  );

  return (
    <Card className="border-2 border-primary/20">
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-3">
            <span>Phase {checkpoint.phase_number}: {phaseNames[checkpoint.phase_number]}</span>
            <Badge variant="outline" className={statusColors[checkpoint.status]}>
              {checkpoint.status}
            </Badge>
            <Badge variant="outline">
              {checkpoint.branch_name} v{checkpoint.version}
            </Badge>
          </CardTitle>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Phase 1: Spec */}
        {checkpoint.phase_number === 1 && specArtifact && (
          <div>
            <h4 className="text-sm font-semibold mb-2">Video Specification</h4>
            <div className="bg-muted/50 p-3 rounded-md text-sm space-y-1">
              {specArtifact.metadata?.spec?.template && (
                <p><span className="font-medium">Template:</span> {specArtifact.metadata.spec.template}</p>
              )}
              {specArtifact.metadata?.spec?.duration && (
                <p><span className="font-medium">Duration:</span> {specArtifact.metadata.spec.duration}s</p>
              )}
              {specArtifact.metadata?.spec?.beats && (
                <p><span className="font-medium">Beats:</span> {specArtifact.metadata.spec.beats.length}</p>
              )}
            </div>
          </div>
        )}

        {/* Phase 2: Storyboard Images */}
        {checkpoint.phase_number === 2 && beatArtifacts.length > 0 && (
          <div>
            <h4 className="text-sm font-semibold mb-2">Storyboard Images ({beatArtifacts.length})</h4>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
              {beatArtifacts.map((artifact) => (
                <div key={artifact.id} className="relative group">
                  <img
                    src={artifact.s3_url}
                    alt={`Beat ${artifact.artifact_key}`}
                    className="rounded-lg border-2 border-primary w-full aspect-video object-cover"
                  />
                  <Badge variant="secondary" className="absolute top-1 right-1 text-xs">
                    v{artifact.version}
                  </Badge>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Phase 3: Video Chunks */}
        {checkpoint.phase_number === 3 && (
          <div className="space-y-3">
            {chunkArtifacts.length > 0 && (
              <div>
                <h4 className="text-sm font-semibold mb-2">Video Chunks ({chunkArtifacts.length})</h4>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
                  {chunkArtifacts.map((artifact) => (
                    <div key={artifact.id} className="relative group">
                      <video
                        src={artifact.s3_url}
                        className="rounded-lg border-2 border-primary w-full aspect-video object-cover"
                        controls
                      />
                      <Badge variant="secondary" className="absolute top-1 right-1 text-xs">
                        v{artifact.version}
                      </Badge>
                    </div>
                  ))}
                </div>
              </div>
            )}
            {stitchedArtifact && (
              <div>
                <h4 className="text-sm font-semibold mb-2">Stitched Video (No Audio)</h4>
                <video
                  src={stitchedArtifact.s3_url}
                  className="rounded-lg border-2 border-primary w-full max-w-md"
                  controls
                />
              </div>
            )}
          </div>
        )}

        {/* Phase 4: Final Video */}
        {checkpoint.phase_number === 4 && finalArtifact && (
          <div>
            <h4 className="text-sm font-semibold mb-2">Final Video (With Audio)</h4>
            <video
              src={finalArtifact.s3_url}
              className="rounded-lg border-2 border-primary w-full max-w-md"
              controls
            />
          </div>
        )}

        {/* Action Buttons */}
        {checkpoint.status === 'pending' && !isProcessing && (
          <div className="flex gap-2 pt-2">
            <Button variant="outline" onClick={onEdit} disabled={!onEdit}>
              Edit
            </Button>
            <Button onClick={onContinue} disabled={!onContinue}>
              Continue to Phase {checkpoint.phase_number + 1}
            </Button>
          </div>
        )}

        {isProcessing && (
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <div className="animate-spin h-4 w-4 border-2 border-primary border-t-transparent rounded-full" />
            Processing...
          </div>
        )}
      </CardContent>
    </Card>
  );
}
