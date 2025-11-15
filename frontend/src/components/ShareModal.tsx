import { X, Mail, Copy, Check } from 'lucide-react';
import { useState } from 'react';

interface ShareModalProps {
  projectId: string;
  projectTitle: string;
  onClose: () => void;
}

export function ShareModal({ projectId, onClose }: ShareModalProps) {
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

  // const permissionLabels = { // Unused for now
  //   view: 'Can view',
  //   comment: 'Can comment',
  //   edit: 'Can edit',
  // };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl shadow-xl max-w-md w-full animate-fade-in">
        <div className="flex items-center justify-between p-6 border-b border-slate-200 dark:border-slate-700">
          <h2 className="text-xl font-bold text-slate-900 dark:text-slate-100">Share Project</h2>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-slate-600 dark:text-slate-400 transition-colors"
          >
            <X className="w-6 h-6" />
          </button>
        </div>

        <div className="p-6 space-y-6">
          <div>
            <p className="text-sm font-medium text-slate-700 dark:text-slate-300 mb-3">Share via Link</p>
            <div className="flex items-center space-x-2">
              <input
                type="text"
                value={shareLink}
                readOnly
                className="flex-1 px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg bg-slate-50 dark:bg-slate-700/50 text-sm text-slate-600 dark:text-slate-400"
              />
              <button
                onClick={handleCopyLink}
                className="p-2 text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:text-slate-100 hover:bg-slate-100 dark:hover:bg-slate-700 dark:bg-slate-700 rounded-lg transition-colors"
              >
                {copied ? (
                  <Check className="w-5 h-5 text-green-600" />
                ) : (
                  <Copy className="w-5 h-5" />
                )}
              </button>
            </div>
          </div>

          <div className="border-t border-slate-200 dark:border-slate-700 pt-6">
            <p className="text-sm font-medium text-slate-700 dark:text-slate-300 mb-3">Share with Collaborators</p>
            <form onSubmit={handleAddEmail} className="space-y-3">
              <div className="flex items-center space-x-2">
                <div className="flex-1 relative">
                  <Mail className="absolute left-3 top-2.5 w-5 h-5 text-slate-400" />
                  <input
                    type="email"
                    value={newEmail}
                    onChange={(e) => setNewEmail(e.target.value)}
                    placeholder="Enter email"
                    className="input-field pl-10"
                  />
                </div>
                <select
                  value={permission}
                  onChange={(e) => setPermission(e.target.value as 'view' | 'comment' | 'edit')}
                  className="px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg focus:ring-2 focus:ring-blue-500"
                >
                  <option value="view">View</option>
                  <option value="comment">Comment</option>
                  <option value="edit">Edit</option>
                </select>
                <button
                  type="submit"
                  disabled={!newEmail}
                  className="px-3 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-slate-300 disabled:cursor-not-allowed transition-colors"
                >
                  Add
                </button>
              </div>
            </form>

            {sharedEmails.length > 0 && (
              <div className="mt-4 space-y-2">
                {sharedEmails.map((email) => (
                  <div
                    key={email}
                    className="flex items-center justify-between p-3 bg-slate-50 dark:bg-slate-700/50 rounded-lg"
                  >
                    <span className="text-sm text-slate-700 dark:text-slate-300">{email}</span>
                    <button
                      onClick={() =>
                        setSharedEmails(sharedEmails.filter((e) => e !== email))
                      }
                      className="text-slate-400 hover:text-slate-600 dark:text-slate-400"
                    >
                      <X className="w-4 h-4" />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        <div className="flex space-x-3 p-6 border-t border-slate-200 dark:border-slate-700">
          <button
            onClick={onClose}
            className="flex-1 btn-secondary"
          >
            Done
          </button>
        </div>
      </div>
    </div>
  );
}
