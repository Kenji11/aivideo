import { Sparkles, Play } from 'lucide-react';

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

const categoryColors: Record<Template['category'], string> = {
  marketing: 'bg-purple-100 text-purple-700',
  education: 'bg-blue-100 text-blue-700',
  entertainment: 'bg-pink-100 text-pink-700',
  social: 'bg-orange-100 text-orange-700',
  corporate: 'bg-green-100 text-green-700',
};

export function TemplateGallery({ templates, onSelect, isLoading = false }: TemplateGalleryProps) {
  if (isLoading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {[...Array(6)].map((_, i) => (
          <div key={i} className="card overflow-hidden animate-pulse">
            <div className="aspect-video bg-slate-200" />
            <div className="p-4 space-y-3">
              <div className="h-4 bg-slate-200 rounded w-2/3" />
              <div className="h-3 bg-slate-200 rounded w-full" />
              <div className="h-2 bg-slate-200 rounded w-1/2" />
            </div>
          </div>
        ))}
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      {templates.map((template) => (
        <button
          key={template.id}
          onClick={() => onSelect(template)}
          className="card overflow-hidden group hover:shadow-lg transition-all duration-300 text-left"
        >
          <div className="aspect-video bg-gradient-to-br from-slate-300 to-slate-400 flex items-center justify-center relative overflow-hidden">
            {template.is_featured && (
              <div className="absolute top-2 right-2 flex items-center space-x-1 bg-yellow-400 text-yellow-900 px-2 py-1 rounded-full text-xs font-semibold">
                <Sparkles className="w-3 h-3" />
                Featured
              </div>
            )}
            <div className="absolute inset-0 bg-black/0 group-hover:bg-black/30 transition-colors flex items-center justify-center">
              <Play className="w-12 h-12 text-white opacity-0 group-hover:opacity-100 transition-opacity fill-current" />
            </div>
          </div>
          <div className="p-4 space-y-3">
            <div>
              <h3 className="font-semibold text-slate-900 group-hover:text-blue-600 transition-colors">
                {template.name}
              </h3>
              {template.description && (
                <p className="text-sm text-slate-600 line-clamp-2 mt-1">
                  {template.description}
                </p>
              )}
            </div>
            <span className={`inline-block px-2.5 py-1 rounded-full text-xs font-medium ${categoryColors[template.category]}`}>
              {categoryLabels[template.category]}
            </span>
          </div>
        </button>
      ))}
    </div>
  );
}
