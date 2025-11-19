import { useState, useEffect } from 'react';
import { api, AssetListItem } from '../lib/api';

export function AssetLibrary() {
  const [assets, setAssets] = useState<AssetListItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const fetchAssets = async () => {
      setIsLoading(true);
      try {
        const response = await api.getAssets();
        setAssets(response.assets);
      } catch (error) {
        console.error('Failed to fetch assets:', error);
      } finally {
        setIsLoading(false);
      }
    };

    fetchAssets();
  }, []);

  if (isLoading) {
    return (
      <div className="animate-fade-in">
        <div className="mb-8">
          <h2 className="text-3xl font-bold text-foreground mb-2">
            Asset Library
          </h2>
          <p className="text-muted-foreground">
            View and manage your uploaded assets
          </p>
        </div>
        <div className="text-center py-12">
          <p className="text-muted-foreground">Loading assets...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="animate-fade-in">
      <div className="mb-8">
        <h2 className="text-3xl font-bold text-foreground mb-2">
          Asset Library
        </h2>
        <p className="text-muted-foreground">
          View and manage your uploaded assets
        </p>
      </div>

      {assets.length > 0 && (
        <div className="mt-8 pt-8 border-t border-border">
          <h3 className="text-lg font-semibold text-foreground mb-4">
            Uploaded Assets ({assets.length})
          </h3>
          <div className="grid grid-cols-3 gap-2">
            {assets.map((asset, idx) => (
              <img
                key={asset.asset_id}
                src={asset.s3_url}
                alt={`Uploaded asset ${idx + 1}`}
                className="w-full h-24 object-cover rounded border border-border"
                onError={(e) => {
                  e.currentTarget.src = 'https://via.placeholder.com/200x200?text=Asset';
                }}
              />
            ))}
          </div>
        </div>
      )}

      {assets.length === 0 && (
        <div className="text-center py-12">
          <p className="text-muted-foreground">No assets uploaded yet</p>
        </div>
      )}
    </div>
  );
}

