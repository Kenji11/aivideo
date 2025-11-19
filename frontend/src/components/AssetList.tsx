import { useState, useEffect } from 'react';
import { Image, Video, FileText, Loader2, RefreshCw, CheckSquare, Square } from 'lucide-react';
import { api, AssetListItem } from '../lib/api';

interface AssetListProps {
  selectedAssetIds: string[];
  onSelectionChange: (assetIds: string[]) => void;
  disabled?: boolean;
  refreshTrigger?: number; // Increment to trigger refresh
}

export function AssetList({ selectedAssetIds, onSelectionChange, disabled = false, refreshTrigger }: AssetListProps) {
  const [assets, setAssets] = useState<AssetListItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchAssets = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await api.getAssets();
      setAssets(response.assets);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to load assets';
      setError(errorMessage);
      console.error('Error fetching assets:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchAssets();
  }, [refreshTrigger]);

  const toggleAsset = (assetId: string) => {
    if (disabled) return;
    
    if (selectedAssetIds.includes(assetId)) {
      onSelectionChange(selectedAssetIds.filter(id => id !== assetId));
    } else {
      onSelectionChange([...selectedAssetIds, assetId]);
    }
  };

  const getAssetIcon = (assetType: string) => {
    switch (assetType) {
      case 'image':
        return <Image className="w-4 h-4 text-primary" />;
      case 'video':
        return <Video className="w-4 h-4 text-primary" />;
      case 'audio':
        return <FileText className="w-4 h-4 text-primary" />;
      default:
        return <FileText className="w-4 h-4 text-muted-foreground" />;
    }
  };

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
  };

  const formatDate = (dateString?: string) => {
    if (!dateString) return 'Unknown';
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
  };

  if (isLoading) {
    return (
      <div className="p-6 text-center">
        <Loader2 className="w-6 h-6 text-primary animate-spin mx-auto mb-2" />
        <p className="text-sm text-muted-foreground">Loading assets...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6 text-center">
        <p className="text-sm text-destructive mb-2">{error}</p>
        <button
          onClick={fetchAssets}
          className="text-sm text-primary hover:text-primary/80 underline"
        >
          Try again
        </button>
      </div>
    );
  }

  if (assets.length === 0) {
    return (
      <div className="p-6 text-center border-2 border-dashed border-border rounded-xl">
        <FileText className="w-8 h-8 text-muted-foreground mx-auto mb-2" />
        <p className="text-sm text-muted-foreground mb-2">No assets uploaded yet</p>
        <p className="text-xs text-muted-foreground">
          Upload files above to see them here
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-sm font-medium text-foreground">
          Previously Uploaded Assets ({assets.length})
        </h3>
        <button
          onClick={fetchAssets}
          disabled={isLoading || disabled}
          className="flex items-center space-x-1 text-xs text-primary hover:text-primary/80 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <RefreshCw className={`w-3 h-3 ${isLoading ? 'animate-spin' : ''}`} />
          <span>Refresh</span>
        </button>
      </div>

      <div className="space-y-2 max-h-64 overflow-y-auto">
        {assets.map((asset) => {
          const isSelected = selectedAssetIds.includes(asset.asset_id);
          return (
            <div
              key={asset.asset_id}
              onClick={() => toggleAsset(asset.asset_id)}
              className={`flex items-center space-x-3 p-3 rounded-lg border cursor-pointer transition-all ${
                isSelected
                  ? 'bg-primary/10 border-primary'
                  : 'bg-card border-border hover:bg-accent'
              } ${disabled ? 'opacity-50 cursor-not-allowed' : ''}`}
            >
              <div className="flex-shrink-0">
                {isSelected ? (
                  <CheckSquare className="w-5 h-5 text-primary" />
                ) : (
                  <Square className="w-5 h-5 text-muted-foreground" />
                )}
              </div>
              <div className="flex-shrink-0">
                {getAssetIcon(asset.asset_type)}
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-foreground truncate">
                  {asset.filename}
                </p>
                <div className="flex items-center space-x-2 mt-1">
                  <span className="text-xs text-muted-foreground">
                    {formatFileSize(asset.file_size_bytes)}
                  </span>
                  <span className="text-xs text-muted-foreground">•</span>
                  <span className="text-xs text-muted-foreground">
                    {formatDate(asset.created_at)}
                  </span>
                </div>
              </div>
              {asset.asset_type === 'image' && asset.s3_url && (
                <div className="flex-shrink-0">
                  <img
                    src={asset.s3_url}
                    alt={asset.filename}
                    className="w-12 h-12 object-cover rounded border border-border"
                    onError={(e) => {
                      (e.target as HTMLImageElement).style.display = 'none';
                    }}
                  />
                </div>
              )}
            </div>
          );
        })}
      </div>

      {selectedAssetIds.length > 0 && (
        <div className="mt-3 p-2 bg-primary/10 rounded-lg border border-primary/20">
          <p className="text-xs text-primary">
            {selectedAssetIds.length} asset{selectedAssetIds.length !== 1 ? 's' : ''} selected
          </p>
        </div>
      )}
    </div>
  );
}

