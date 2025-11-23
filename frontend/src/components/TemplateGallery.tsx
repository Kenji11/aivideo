import { Sparkles, Play } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';

export interface Template {
  id: string;
  name: string;
  description: string;
  category: 'marketing' | 'education' | 'entertainment' | 'social' | 'corporate';
  thumbnail_url?: string;
  is_featured: boolean;
}

interface TemplateGalleryProps {
  templates: Template[];
  onSelect: (template: Template) => void;
  isLoading?: boolean;
}

const categoryLabels: Record<Template['category'], string> = {
  marketing: 'Marketing',
  education: 'Education',
  entertainment: 'Entertainment',
  social: 'Social Media',
  corporate: 'Corporate',
};

const categoryVariants: Record<Template['category'], 'default' | 'secondary' | 'outline'> = {
  marketing: 'default',
  education: 'default',
  entertainment: 'default',
  social: 'default',
  corporate: 'default',
};

export function TemplateGallery({ templates, onSelect, isLoading = false }: TemplateGalleryProps) {
  if (isLoading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {[...Array(6)].map((_, i) => (
          <Card key={i} className="overflow-hidden">
            <Skeleton className="aspect-video w-full" />
            <CardContent className="p-4 space-y-3">
              <Skeleton className="h-4 w-2/3" />
              <Skeleton className="h-3 w-full" />
              <Skeleton className="h-2 w-1/2" />
            </CardContent>
          </Card>
        ))}
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      {templates.map((template) => (
        <Card
          key={template.id}
          className="overflow-hidden group hover:shadow-lg transition-all duration-300 cursor-pointer"
          onClick={() => onSelect(template)}
        >
          <div className="aspect-video bg-gradient-to-br from-slate-300 to-slate-400 flex items-center justify-center relative overflow-hidden">
            {template.is_featured && (
              <Badge className="absolute top-2 right-2 bg-yellow-400 text-yellow-900">
                <Sparkles className="w-3 h-3 mr-1" />
                Featured
              </Badge>
            )}
            <div className="absolute inset-0 bg-black/0 group-hover:bg-black/30 transition-colors flex items-center justify-center">
              <Play className="w-12 h-12 text-white opacity-0 group-hover:opacity-100 transition-opacity fill-current" />
            </div>
          </div>
          <CardContent className="p-4 space-y-3">
            <div>
              <h3 className="font-semibold text-slate-900 dark:text-slate-100 group-hover:text-blue-600 transition-colors">
                {template.name}
              </h3>
              {template.description && (
                <p className="text-sm text-muted-foreground line-clamp-2 mt-1">
                  {template.description}
                </p>
              )}
            </div>
            <Badge variant={categoryVariants[template.category]}>
              {categoryLabels[template.category]}
            </Badge>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
