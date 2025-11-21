import { useState, useEffect, useCallback } from 'react';
import { api, AssetListItem } from '../lib/api';
import { UploadAssetModal } from '../components/UploadAssetModal';
import { AssetDetailModal } from '../components/AssetDetailModal';
import { UploadZone } from '../components/UploadZone';
import { Image, Trash2, Filter, X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { toast } from '@/hooks/use-toast';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';

const REFERENCE_ASSET_TYPES = [
  { value: '', label: 'All Types' },
  { value: 'product', label: 'Product' },
  { value: 'logo', label: 'Logo' },
  { value: 'person', label: 'Person' },
  { value: 'environment', label: 'Environment' },
  { value: 'texture', label: 'Texture' },
  { value: 'prop', label: 'Prop' },
];

export function AssetLibrary() {
  const [assets, setAssets] = useState<AssetListItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false);
  const [selectedAsset, setSelectedAsset] = useState<AssetListItem | null>(null);
  const [isDetailModalOpen, setIsDetailModalOpen] = useState(false);
  const [filterType, setFilterType] = useState<string>('');
  const [filterLogo, setFilterLogo] = useState<boolean | null>(null);
  const [page, setPage] = useState(0);
  const [total, setTotal] = useState(0);
  const [limit] = useState(20);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [assetToDelete, setAssetToDelete] = useState<{ id: string; name: string } | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);

  const fetchAssets = useCallback(async () => {
    setIsLoading(true);
    try {
      const response = await api.getAssets({
        reference_asset_type: filterType || undefined,
        is_logo: filterLogo !== null ? filterLogo : undefined,
        limit,
        offset: page * limit,
      });
      setAssets(response.assets);
      setTotal(response.total || 0);
    } catch (error) {
      console.error('Failed to fetch assets:', error);
      toast({
        variant: 'destructive',
        title: 'Error',
        description: error instanceof Error ? error.message : 'Failed to load assets',
      });
    } finally {
      setIsLoading(false);
    }
  }, [filterType, filterLogo, page, limit]);

  useEffect(() => {
    fetchAssets();
  }, [fetchAssets]);

  const handleUploadSuccess = () => {
    fetchAssets();
    setIsUploadModalOpen(false);
  };

  const handleAssetsUploaded = (assetIds: string[]) => {
    // Refresh asset list when files are uploaded via UploadZone
    fetchAssets();
    toast({
      title: 'Success',
      description: `${assetIds.length} asset(s) uploaded successfully`,
    });
  };

  const handleDelete = (assetId: string, assetName: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setAssetToDelete({ id: assetId, name: assetName });
    setDeleteDialogOpen(true);
  };

  const confirmDelete = async () => {
    if (!assetToDelete) return;

    setIsDeleting(true);
    try {
      await api.deleteAsset(assetToDelete.id);
      toast({
        title: 'Success',
        description: 'Asset deleted successfully',
      });
      fetchAssets();
      setDeleteDialogOpen(false);
      setAssetToDelete(null);
    } catch (error) {
      console.error('Failed to delete asset:', error);
      toast({
        variant: 'destructive',
        title: 'Error',
        description: error instanceof Error ? error.message : 'Failed to delete asset',
      });
    } finally {
      setIsDeleting(false);
    }
  };

  const cancelDelete = () => {
    setDeleteDialogOpen(false);
    setAssetToDelete(null);
  };

  const handleAssetClick = (asset: AssetListItem) => {
    setSelectedAsset(asset);
    setIsDetailModalOpen(true);
  };

  const handleCloseDetailModal = () => {
    setIsDetailModalOpen(false);
    setSelectedAsset(null);
    fetchAssets(); // Refresh in case asset was updated
  };

  const totalPages = Math.ceil(total / limit);

  return (
    <div className="animate-fade-in">
      <div className="mb-8">
        <h2 className="text-3xl font-bold text-foreground mb-2">
          Asset Library
        </h2>
        <p className="text-muted-foreground">
          Upload and manage your reference assets
        </p>
      </div>

      {/* Upload Zone */}
      <div className="mb-8">
        <label className="block text-sm font-medium text-foreground mb-2">
          Upload Reference Assets
        </label>
        <UploadZone onAssetsUploaded={handleAssetsUploaded} />
      </div>

      {/* Filters */}
      <div className="mb-6 flex items-center gap-4 flex-wrap">
        <div className="flex items-center gap-2">
          <Filter className="w-4 h-4 text-muted-foreground" />
          <select
            value={filterType}
            onChange={(e) => {
              setFilterType(e.target.value);
              setPage(0);
            }}
            className="px-3 py-2 rounded-lg border border-border bg-background text-foreground"
          >
            {REFERENCE_ASSET_TYPES.map((type) => (
              <option key={type.value} value={type.value}>
                {type.label}
              </option>
            ))}
          </select>
        </div>
        <label className="flex items-center gap-2 cursor-pointer">
          <input
            type="checkbox"
            checked={filterLogo === true}
            onChange={(e) => {
              setFilterLogo(e.target.checked ? true : null);
              setPage(0);
            }}
            className="w-4 h-4 rounded border-border"
          />
          <span className="text-sm text-foreground">Show logos only</span>
        </label>
        {(filterType || filterLogo !== null) && (
          <Button
            variant="ghost"
            size="sm"
            onClick={() => {
              setFilterType('');
              setFilterLogo(null);
              setPage(0);
            }}
            className="flex items-center gap-1"
          >
            <X className="w-4 h-4" />
            Clear filters
          </Button>
        )}
      </div>

      {/* Loading state */}
      {isLoading && (
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
          {[...Array(8)].map((_, i) => (
            <div
              key={i}
              className="aspect-square bg-muted rounded-lg animate-pulse"
            />
          ))}
        </div>
      )}

      {/* Asset grid */}
      {!isLoading && assets.length > 0 && (
        <>
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
            {assets.map((asset) => (
              <div
                key={asset.asset_id}
                className="group relative aspect-square bg-muted rounded-lg overflow-hidden cursor-pointer hover:ring-2 hover:ring-primary transition-all"
                onClick={() => handleAssetClick(asset)}
              >
                {/* Thumbnail */}
                <img
                  src={asset.thumbnail_url || asset.s3_url}
                  alt={asset.name || asset.filename}
                  className="w-full h-full object-cover"
                  onError={(e) => {
                    e.currentTarget.src = 'https://via.placeholder.com/400x400?text=Asset';
                  }}
                />
                
                {/* Overlay on hover */}
                <div className="absolute inset-0 bg-black/60 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center gap-2">
                  <Button
                    variant="destructive"
                    size="sm"
                    onClick={(e) => handleDelete(asset.asset_id, asset.name || asset.filename, e)}
                    className="flex items-center gap-1"
                  >
                    <Trash2 className="w-4 h-4" />
                    Delete
                  </Button>
                </div>

                {/* Asset type badge */}
                {asset.reference_asset_type && (
                  <div className="absolute top-2 left-2">
                    <span className="px-2 py-1 text-xs font-semibold rounded bg-primary/90 text-primary-foreground">
                      {asset.reference_asset_type}
                    </span>
                  </div>
                )}

                {/* Logo badge */}
                {asset.is_logo && (
                  <div className="absolute top-2 right-2">
                    <span className="px-2 py-1 text-xs font-semibold rounded bg-blue-600 text-white">
                      Logo
                    </span>
                  </div>
                )}

                {/* AI Analyzed indicator */}
                {asset.analysis && (
                  <div className="absolute top-2 right-2" style={{ top: asset.is_logo ? '2.5rem' : '0.5rem' }}>
                    <span className="px-2 py-1 text-xs font-semibold rounded bg-green-600 text-white">
                      ✓ AI
                    </span>
                  </div>
                )}

                {/* Primary object on hover */}
                {asset.primary_object && (
                  <div className="absolute inset-0 bg-black/80 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center p-4 pointer-events-none">
                    <p className="text-sm text-white text-center line-clamp-3">
                      {asset.primary_object}
                    </p>
                  </div>
                )}

                {/* Asset name */}
                <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/80 to-transparent p-3">
                  <p className="text-sm font-medium text-white truncate">
                    {asset.name || asset.filename}
                  </p>
                </div>
              </div>
            ))}
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="mt-8 flex items-center justify-center gap-2">
              <Button
                variant="outline"
                onClick={() => setPage((p) => Math.max(0, p - 1))}
                disabled={page === 0}
              >
                Previous
              </Button>
              <span className="text-sm text-muted-foreground">
                Page {page + 1} of {totalPages} ({total} total)
              </span>
              <Button
                variant="outline"
                onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
                disabled={page >= totalPages - 1}
              >
                Next
              </Button>
            </div>
          )}
        </>
      )}

      {/* Empty state */}
      {!isLoading && assets.length === 0 && (
        <div className="text-center py-16">
          <Image className="w-16 h-16 mx-auto text-muted-foreground mb-4" />
          <p className="text-lg font-semibold text-foreground mb-2">
            No assets yet
          </p>
          <p className="text-muted-foreground mb-6">
            {filterType || filterLogo !== null
              ? 'No assets match your filters. Try adjusting your filters.'
              : 'Upload your first reference asset to get started'}
          </p>
          {(!filterType && filterLogo === null) && (
            <p className="text-sm text-muted-foreground">
              Use the upload zone above to add your first reference asset
            </p>
          )}
        </div>
      )}

      {/* Upload Modal (kept for backward compatibility, but UploadZone is primary) */}
      <UploadAssetModal
        isOpen={isUploadModalOpen}
        onClose={() => setIsUploadModalOpen(false)}
        onSuccess={handleUploadSuccess}
      />

      {/* Detail Modal */}
      {selectedAsset && (
        <AssetDetailModal
          isOpen={isDetailModalOpen}
          onClose={handleCloseDetailModal}
          assetId={selectedAsset.asset_id}
        />
      )}

      {/* Delete Confirmation Dialog */}
      <Dialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete Asset</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete "{assetToDelete?.name}"? This action cannot be undone and will permanently delete the asset and all associated files.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={cancelDelete}
              disabled={isDeleting}
            >
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={confirmDelete}
              disabled={isDeleting}
            >
              {isDeleting ? 'Deleting...' : 'Delete'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

