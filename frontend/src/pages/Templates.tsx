import { ArrowLeft, Search } from 'lucide-react';
import { useState } from 'react';
import { TemplateGallery, Template } from '../components/TemplateGallery';

interface TemplatesProps {
  onBack: () => void;
  onSelectTemplate: (template: Template) => void;
}

const mockTemplates: Template[] = [
  {
    id: '1',
    name: 'Product Launch',
    description: 'Professional product launch video template',
    category: 'marketing',
    is_featured: true,
  },
  {
    id: '2',
    name: 'Social Media Teaser',
    description: 'Perfect for Instagram and TikTok',
    category: 'social',
    is_featured: true,
  },
  {
    id: '3',
    name: 'Educational Explainer',
    description: 'Make complex topics easy to understand',
    category: 'education',
    is_featured: false,
  },
  {
    id: '4',
    name: 'Brand Story',
    description: 'Tell your brand story with impact',
    category: 'corporate',
    is_featured: false,
  },
  {
    id: '5',
    name: 'Comedy Sketch',
    description: 'Entertaining short-form video',
    category: 'entertainment',
    is_featured: false,
  },
  {
    id: '6',
    name: 'Event Highlights',
    description: 'Capture the best moments',
    category: 'social',
    is_featured: true,
  },
];

export function Templates({ onBack, onSelectTemplate }: TemplatesProps) {
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);

  const categories = [
    { id: 'all', name: 'All' },
    { id: 'marketing', name: 'Marketing' },
    { id: 'education', name: 'Education' },
    { id: 'entertainment', name: 'Entertainment' },
    { id: 'social', name: 'Social Media' },
    { id: 'corporate', name: 'Corporate' },
  ];

  const filteredTemplates = mockTemplates.filter((template) => {
    const matchesSearch = template.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      template.description?.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesCategory = !selectedCategory || selectedCategory === 'all' || template.category === selectedCategory;
    return matchesSearch && matchesCategory;
  });

  return (
    <div className="max-w-6xl mx-auto animate-fade-in">
      <button
        onClick={onBack}
        className="flex items-center space-x-2 text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:text-slate-100 mb-6 transition-colors"
      >
        <ArrowLeft className="w-5 h-5" />
        <span>Back</span>
      </button>

      <div className="mb-8">
        <h1 className="text-3xl font-bold text-slate-900 dark:text-slate-100">Templates</h1>
        <p className="text-slate-600 dark:text-slate-400 mt-1">Choose from professionally designed templates to jumpstart your video</p>
      </div>

      <div className="card p-6 mb-8">
        <div className="flex flex-col gap-4">
          <div className="relative">
            <Search className="absolute left-3 top-3 w-5 h-5 text-slate-400" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search templates..."
              className="input-field pl-10"
            />
          </div>

          <div className="flex flex-wrap gap-2">
            {categories.map((cat) => (
              <button
                key={cat.id}
                onClick={() => setSelectedCategory(cat.id === 'all' ? null : cat.id)}
                className={`px-4 py-2 rounded-full text-sm font-medium transition-all ${
                  (cat.id === 'all' && !selectedCategory) || selectedCategory === cat.id
                    ? 'bg-blue-600 text-white'
                    : 'bg-slate-100 dark:bg-slate-700 text-slate-700 dark:text-slate-300 hover:bg-slate-200'
                }`}
              >
                {cat.name}
              </button>
            ))}
          </div>
        </div>
      </div>

      <TemplateGallery
        templates={filteredTemplates}
        onSelect={onSelectTemplate}
      />

      {filteredTemplates.length === 0 && (
        <div className="card p-16 text-center">
          <p className="text-slate-500 dark:text-slate-400">No templates found matching your criteria</p>
        </div>
      )}
    </div>
  );
}
