import { Film, LogOut, Menu, X } from 'lucide-react';
import { useState } from 'react';

interface HeaderProps {
  userName?: string;
  onLogout?: () => void;
  onProjectsClick?: () => void;
}

export function Header({ userName, onLogout, onProjectsClick }: HeaderProps) {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  return (
    <nav className="bg-white border-b border-slate-200 sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          <div className="flex items-center space-x-2 cursor-pointer group" onClick={onProjectsClick}>
            <div className="relative">
              <Film className="w-8 h-8 text-blue-600 group-hover:scale-110 transition-transform" />
              <div className="absolute inset-0 bg-blue-600/20 rounded-lg blur-md group-hover:blur-lg transition-all" />
            </div>
            <div>
              <span className="text-xl font-bold gradient-text">VideoAI</span>
              <span className="text-xs text-slate-500 block">Studio</span>
            </div>
          </div>

          <div className="hidden md:flex items-center space-x-4">
            <button
              onClick={onProjectsClick}
              className="text-sm font-medium text-slate-700 hover:text-slate-900 px-4 py-2 rounded-lg hover:bg-slate-100 transition-colors"
            >
              My Projects
            </button>
            {userName && (
              <div className="flex items-center space-x-3 pl-4 border-l border-slate-200">
                <div className="text-right">
                  <p className="text-sm font-medium text-slate-900">
                    {userName}
                  </p>
                  <p className="text-xs text-slate-500">Creator</p>
                </div>
                <button
                  onClick={onLogout}
                  className="p-2 text-slate-600 hover:text-slate-900 hover:bg-slate-100 rounded-lg transition-colors"
                  title="Logout"
                >
                  <LogOut className="w-5 h-5" />
                </button>
              </div>
            )}
          </div>

          <button
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            className="md:hidden p-2 text-slate-600 hover:bg-slate-100 rounded-lg"
          >
            {mobileMenuOpen ? (
              <X className="w-6 h-6" />
            ) : (
              <Menu className="w-6 h-6" />
            )}
          </button>
        </div>

        {mobileMenuOpen && (
          <div className="md:hidden pb-4 space-y-2 border-t border-slate-200 pt-4 animate-slide-in">
            <button
              onClick={onProjectsClick}
              className="w-full text-left text-sm font-medium text-slate-700 px-4 py-2 rounded-lg hover:bg-slate-100 transition-colors"
            >
              My Projects
            </button>
            {userName && (
              <>
                <div className="px-4 py-2 text-sm">
                  <p className="font-medium text-slate-900">{userName}</p>
                  <p className="text-xs text-slate-500">Creator</p>
                </div>
                <button
                  onClick={onLogout}
                  className="w-full text-left text-sm font-medium text-slate-700 px-4 py-2 rounded-lg hover:bg-slate-100 transition-colors flex items-center space-x-2"
                >
                  <LogOut className="w-4 h-4" />
                  <span>Logout</span>
                </button>
              </>
            )}
          </div>
        )}
      </div>
    </nav>
  );
}
