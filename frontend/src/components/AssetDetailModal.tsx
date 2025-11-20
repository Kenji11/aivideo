import { useState, useEffect } from 'react';
import { api, AssetDetail } from '../lib/api';
import { X, Edit2, Save, Trash2, Image as ImageIcon } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { toast } from '@/hooks/use-toast';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';

const REFERENCE_ASSET_TYPES = [
  { value: 'product', label: 'Product' },
  { value: 'logo', label: 'Logo' },
  { value: 'person', label: 'Person' },
  { value: 'environment', label: 'Environment' },
  { value: 'texture', label: 'Texture' },
  { value: 'prop', label: 'Prop' },
];

const LOGO_POSITIONS = [
  { value: 'bottom-right', label: 'Bottom Right' },
  { value: 'bottom-left', label: 'Bottom Left' },
  { value: 'top-right', label: 'Top Right' },
  { value: 'top-left', label: 'Top Left' },
  { value: 'center', label: 'Center' },
];

interface AssetDetailModalProps {
  isOpen: boolean;
  onClose: () => void;
  assetId: string;
}

export function AssetDetailModal({ isOpen, onClose, assetId }: AssetDetailModalProps) {
  const [asset, setAsset] = useState<AssetDetail | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isEditing, setIsEditing] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  
  // Editable fields
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [referenceAssetType, setReferenceAssetType] = useState('');
  const [logoPositionPreference, setLogoPositionPreference] = useState('');

  useEffect(() => {
    if (isOpen && assetId) {
      fetchAsset();
    }
  }, [isOpen, assetId]);

  const fetchAsset = async () => {
    setIsLoading(true);
    try {
      const assetData = await api.getAsset(assetId);
      setAsset(assetData);
      setName(assetData.name || assetData.filename || '');
      setDescription(assetData.description || '');
      setReferenceAssetType(assetData.reference_asset_type || '');
      setLogoPositionPreference(assetData.logo_position_preference || '');
    } catch (error) {
      console.error('Failed to fetch asset:', error);
      toast({
        variant: 'destructive',
        title: 'Error',
        description: error instanceof Error ? error.message : 'Failed to load asset',
      });
      onClose();
    } finally {
      setIsLoading(false);
    }
  };

  const handleSave = async () => {
    if (!asset) return;

    setIsSaving(true);
    try {
      const updated = await api.updateAsset(assetId, {
        name: name.trim(),
        description: description.trim() || undefined,
        reference_asset_type: referenceAssetType || undefined,
        logo_position_preference: logoPositionPreference || undefined,
      });
      setAsset(updated);
      setIsEditing(false);
      toast({
        title: 'Success',
        description: 'Asset updated successfully',
      });
    } catch (error) {
      console.error('Failed to update asset:', error);
      toast({
        variant: 'destructive',
        title: 'Error',
        description: error instanceof Error ? error.message : 'Failed to update asset',
      });
    } finally {
      setIsSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!asset) return;
    if (!confirm('Are you sure you want to delete this asset? This action cannot be undone.')) {
      return;
    }

    setIsDeleting(true);
    try {
      await api.deleteAsset(assetId);
      toast({
        title: 'Success',
        description: 'Asset deleted successfully',
      });
      onClose();
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

  if (isLoading) {
    return (
      <Dialog open={isOpen} onOpenChange={onClose}>
        <DialogContent>
          <div className="flex items-center justify-center py-8">
            <div className="w-8 h-8 border-4 border-primary border-t-transparent rounded-full animate-spin" />
          </div>
        </DialogContent>
      </Dialog>
    );
  }

  if (!asset) {
    return null;
  }

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center justify-between">
            <span>Asset Details</span>
            <div className="flex items-center gap-2">
              {!isEditing ? (
                <>
                  <Button variant="outline" size="sm" onClick={() => setIsEditing(true)}>
                    <Edit2 className="w-4 h-4 mr-2" />
                    Edit
                  </Button>
                  <Button
                    variant="destructive"
                    size="sm"
                    onClick={handleDelete}
                    disabled={isDeleting}
                  >
                    <Trash2 className="w-4 h-4 mr-2" />
                    {isDeleting ? 'Deleting...' : 'Delete'}
                  </Button>
                </>
              ) : (
                <>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => {
                      setIsEditing(false);
                      // Reset to original values
                      setName(asset.name || asset.filename || '');
                      setDescription(asset.description || '');
                      setReferenceAssetType(asset.reference_asset_type || '');
                      setLogoPositionPreference(asset.logo_position_preference || '');
                    }}
                    disabled={isSaving}
                  >
                    Cancel
                  </Button>
                  <Button size="sm" onClick={handleSave} disabled={isSaving}>
                    <Save className="w-4 h-4 mr-2" />
                    {isSaving ? 'Saving...' : 'Save'}
                  </Button>
                </>
              )}
            </div>
          </DialogTitle>
          <DialogDescription>View and edit asset metadata</DialogDescription>
        </DialogHeader>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Image preview */}
          <div className="space-y-4">
            <div className="aspect-square bg-muted rounded-lg overflow-hidden">
              <img
                src={asset.thumbnail_url || asset.s3_url}
                alt={asset.name || asset.filename}
                className="w-full h-full object-contain"
                onError={(e) => {
                  e.currentTarget.src = 'https://via.placeholder.com/400x400?text=Asset';
                }}
              />
            </div>
            {asset.width && asset.height && (
              <p className="text-sm text-muted-foreground text-center">
                {asset.width} × {asset.height} pixels
              </p>
            )}
          </div>

          {/* Metadata */}
          <div className="space-y-4">
            {/* Editable fields */}
            <div>
              <label className="block text-sm font-medium text-foreground mb-2">
                Name
              </label>
              {isEditing ? (
                <input
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg border border-border bg-background text-foreground"
                />
              ) : (
                <p className="text-foreground">{name || asset.filename}</p>
              )}
            </div>

            <div>
              <label className="block text-sm font-medium text-foreground mb-2">
                Description
              </label>
              {isEditing ? (
                <textarea
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  rows={3}
                  className="w-full px-3 py-2 rounded-lg border border-border bg-background text-foreground resize-none"
                />
              ) : (
                <p className="text-foreground">{description || 'No description'}</p>
              )}
            </div>

            <div>
              <label className="block text-sm font-medium text-foreground mb-2">
                Asset Type
              </label>
              {isEditing ? (
                <select
                  value={referenceAssetType}
                  onChange={(e) => setReferenceAssetType(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg border border-border bg-background text-foreground"
                >
                  <option value="">Select type</option>
                  {REFERENCE_ASSET_TYPES.map((type) => (
                    <option key={type.value} value={type.value}>
                      {type.label}
                    </option>
                  ))}
                </select>
              ) : (
                <p className="text-foreground">
                  {asset.reference_asset_type || 'Not set'}
                </p>
              )}
            </div>

            {/* Logo position (only if logo) */}
            {asset.is_logo && (
              <div>
                <label className="block text-sm font-medium text-foreground mb-2">
                  Logo Position Preference
                </label>
                {isEditing ? (
                  <select
                    value={logoPositionPreference}
                    onChange={(e) => setLogoPositionPreference(e.target.value)}
                    className="w-full px-3 py-2 rounded-lg border border-border bg-background text-foreground"
                  >
                    <option value="">Select position</option>
                    {LOGO_POSITIONS.map((pos) => (
                      <option key={pos.value} value={pos.value}>
                        {pos.label}
                      </option>
                    ))}
                  </select>
                ) : (
                  <p className="text-foreground">
                    {asset.logo_position_preference || 'Not set'}
                  </p>
                )}
              </div>
            )}

            {/* Read-only fields */}
            <div className="pt-4 border-t border-border space-y-3">
              <div>
                <label className="block text-sm font-medium text-muted-foreground mb-1">
                  Filename
                </label>
                <p className="text-sm text-foreground">{asset.filename}</p>
              </div>
              <div>
                <label className="block text-sm font-medium text-muted-foreground mb-1">
                  File Size
                </label>
                <p className="text-sm text-foreground">
                  {(asset.file_size_bytes / (1024 * 1024)).toFixed(2)} MB
                </p>
              </div>
              {asset.has_transparency && (
                <div>
                  <label className="block text-sm font-medium text-muted-foreground mb-1">
                    Transparency
                  </label>
                  <p className="text-sm text-foreground">Has alpha channel</p>
                </div>
              )}
              {asset.is_logo && (
                <div>
                  <span className="inline-block px-2 py-1 text-xs font-semibold rounded bg-blue-600 text-white">
                    Logo Detected
                  </span>
                </div>
              )}
              {asset.primary_object && (
                <div>
                  <label className="block text-sm font-medium text-muted-foreground mb-1">
                    Primary Object
                  </label>
                  <p className="text-sm text-foreground">{asset.primary_object}</p>
                </div>
              )}
              {asset.colors && asset.colors.length > 0 && (
                <div>
                  <label className="block text-sm font-medium text-muted-foreground mb-2">
                    Colors
                  </label>
                  <div className="flex flex-wrap gap-2">
                    {asset.colors.map((color, i) => (
                      <span
                        key={i}
                        className="px-2 py-1 text-xs rounded bg-muted text-foreground"
                      >
                        {color}
                      </span>
                    ))}
                  </div>
                </div>
              )}
              {asset.style_tags && asset.style_tags.length > 0 && (
                <div>
                  <label className="block text-sm font-medium text-muted-foreground mb-2">
                    Style Tags
                  </label>
                  <div className="flex flex-wrap gap-2">
                    {asset.style_tags.map((tag, i) => (
                      <span
                        key={i}
                        className="px-2 py-1 text-xs rounded bg-primary/20 text-primary"
                      >
                        {tag}
                      </span>
                    ))}
                  </div>
                </div>
              )}
              <div>
                <label className="block text-sm font-medium text-muted-foreground mb-1">
                  Usage Count
                </label>
                <p className="text-sm text-foreground">{asset.usage_count || 0} times</p>
              </div>
              <div>
                <label className="block text-sm font-medium text-muted-foreground mb-1">
                  Created
                </label>
                <p className="text-sm text-foreground">
                  {asset.created_at ? new Date(asset.created_at).toLocaleString() : 'Unknown'}
                </p>
              </div>
            </div>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}

