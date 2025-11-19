import { Mail, Copy, Check, X } from 'lucide-react';
import { useState } from 'react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Label } from '@/components/ui/label';

interface ShareModalProps {
  projectId: string;
  projectTitle: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function ShareModal({ projectId, open, onOpenChange }: ShareModalProps) {
  const [sharedEmails, setSharedEmails] = useState<string[]>([]);
  const [newEmail, setNewEmail] = useState('');
  const [permission, setPermission] = useState<'view' | 'comment' | 'edit'>('view');
  const [copied, setCopied] = useState(false);

  const shareLink = `${window.location.origin}/shared/${projectId}`;

  const handleAddEmail = (e: React.FormEvent) => {
    e.preventDefault();
    if (newEmail && !sharedEmails.includes(newEmail)) {
      setSharedEmails([...sharedEmails, newEmail]);
      setNewEmail('');
    }
  };

  const handleCopyLink = () => {
    navigator.clipboard.writeText(shareLink);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Share Project</DialogTitle>
        </DialogHeader>

        <div className="space-y-6 py-4">
          <div className="space-y-3">
            <Label>Share via Link</Label>
            <div className="flex items-center space-x-2">
              <Input
                type="text"
                value={shareLink}
                readOnly
                className="flex-1 bg-muted"
              />
              <Button
                onClick={handleCopyLink}
                variant="outline"
                size="icon"
              >
                {copied ? (
                  <Check className="h-4 w-4 text-green-600" />
                ) : (
                  <Copy className="h-4 w-4" />
                )}
              </Button>
            </div>
          </div>

          <div className="space-y-3 border-t pt-6">
            <Label>Share with Collaborators</Label>
            <form onSubmit={handleAddEmail} className="space-y-3">
              <div className="flex items-center space-x-2">
                <div className="flex-1 relative">
                  <Mail className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
                  <Input
                    type="email"
                    value={newEmail}
                    onChange={(e) => setNewEmail(e.target.value)}
                    placeholder="Enter email"
                    className="pl-10"
                  />
                </div>
                <Select value={permission} onValueChange={(value) => setPermission(value as 'view' | 'comment' | 'edit')}>
                  <SelectTrigger className="w-[120px]">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="view">View</SelectItem>
                    <SelectItem value="comment">Comment</SelectItem>
                    <SelectItem value="edit">Edit</SelectItem>
                  </SelectContent>
                </Select>
                <Button
                  type="submit"
                  disabled={!newEmail}
                >
                  Add
                </Button>
              </div>
            </form>

            {sharedEmails.length > 0 && (
              <div className="mt-4 space-y-2">
                {sharedEmails.map((email) => (
                  <div
                    key={email}
                    className="flex items-center justify-between p-3 bg-muted rounded-lg"
                  >
                    <span className="text-sm">{email}</span>
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() =>
                        setSharedEmails(sharedEmails.filter((e) => e !== email))
                      }
                    >
                      <X className="h-4 w-4" />
                    </Button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        <DialogFooter>
          <Button onClick={() => onOpenChange(false)} variant="secondary">
            Done
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
