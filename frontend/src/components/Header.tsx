import { Film, LogOut, Menu, Sparkles } from 'lucide-react';
import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from '@/components/ui/sheet';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Button } from '@/components/ui/button';

interface HeaderProps {
  userName?: string;
  onLogout?: () => void;
}

export function Header({ userName, onLogout }: HeaderProps) {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const navigate = useNavigate();

  return (
    <nav className="bg-background/95 backdrop-blur-sm bg-gradient-to-br from-background via-background/98 to-background/95 border-b border-border sticky top-0 z-50 transition-colors shadow-sm">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          <div className="flex items-center space-x-2 cursor-pointer group" onClick={() => navigate('/')}>
            <div className="relative">
              <Film className="w-8 h-8 text-primary group-hover:scale-110 transition-transform" />
              <div className="absolute inset-0 bg-primary/20 rounded-lg blur-md group-hover:blur-lg transition-all" />
            </div>
            <div>
              <span className="text-xl font-bold gradient-text">VideoAI</span>
              <span className="text-xs text-muted-foreground block">Studio</span>
            </div>
          </div>

          <div className="hidden md:flex items-center space-x-4">
            <Button asChild>
              <Link to="/" className="flex items-center space-x-2">
                <Sparkles className="w-4 h-4" />
                <span>Generate Video</span>
              </Link>
            </Button>
            <Button variant="ghost" asChild>
              <Link to="/projects">My Projects</Link>
            </Button>
            <Button variant="ghost" asChild>
              <Link to="/asset-library">Asset Library</Link>
            </Button>
            {userName && (
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="ghost" className="flex items-center space-x-3 pl-4 border-l">
                    <div className="text-right">
                      <p className="text-sm font-medium">{userName}</p>
                      <p className="text-xs text-muted-foreground">Creator</p>
                    </div>
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end">
                  <DropdownMenuLabel>
                    <div>
                      <p className="font-medium">{userName}</p>
                      <p className="text-xs text-muted-foreground">Creator</p>
                    </div>
                  </DropdownMenuLabel>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem onClick={onLogout}>
                    <LogOut className="w-4 h-4 mr-2" />
                    Logout
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            )}
          </div>

          <Sheet open={mobileMenuOpen} onOpenChange={setMobileMenuOpen}>
            <SheetTrigger asChild>
              <Button variant="ghost" size="icon" className="md:hidden">
                <Menu className="w-6 h-6" />
              </Button>
            </SheetTrigger>
            <SheetContent side="right">
              <SheetHeader>
                <SheetTitle>Menu</SheetTitle>
              </SheetHeader>
              <div className="mt-6 space-y-2">
                <Button asChild className="w-full justify-start" onClick={() => setMobileMenuOpen(false)}>
                  <Link to="/" className="flex items-center space-x-2">
                    <Sparkles className="w-4 h-4" />
                    <span>Generate Video</span>
                  </Link>
                </Button>
                <Button variant="ghost" asChild className="w-full justify-start" onClick={() => setMobileMenuOpen(false)}>
                  <Link to="/projects">My Projects</Link>
                </Button>
                <Button variant="ghost" asChild className="w-full justify-start" onClick={() => setMobileMenuOpen(false)}>
                  <Link to="/asset-library">Asset Library</Link>
                </Button>
                {userName && (
                  <>
                    <div className="pt-4 border-t">
                      <p className="px-2 py-1 text-sm font-medium">{userName}</p>
                      <p className="px-2 text-xs text-muted-foreground">Creator</p>
                    </div>
                    <Button
                      variant="ghost"
                      className="w-full justify-start"
                      onClick={() => {
                        onLogout?.();
                        setMobileMenuOpen(false);
                      }}
                    >
                      <LogOut className="w-4 h-4 mr-2" />
                      Logout
                    </Button>
                  </>
                )}
              </div>
            </SheetContent>
          </Sheet>
        </div>
      </div>
    </nav>
  );
}
