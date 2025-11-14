import { ArrowLeft, Search, Tag, Play, Download, Trash2 } from 'lucide-react';
import { useState } from 'react';

interface LibraryVideo {
  id: string;
  title: string;
  thumbnail?: string;
  duration: number;
  tags: string[];
  category: string;
  isPublic: boolean;
  createdAt: string;
}

interface VideoLibraryProps {
  onBack: () => void;
}

const mockVideos: LibraryVideo[] = [
  {
    id: '1',
    title: 'Sunset Transition',
    duration: 5,
    tags: ['transition', 'nature', 'sunset'],
    category: 'transitions',
    isPublic: true,
    createdAt: '2024-11-10',
  },
  {
    id: '2',
    title: 'Corporate Intro',
    duration: 8,
    tags: ['intro', 'corporate', 'professional'],
    category: 'intros',
    isPublic: true,
    createdAt: '2024-11-08',
  },
  {
    id: '3',
    title: 'Music Background',
    duration: 30,
    tags: ['music', 'background', 'royalty-free'],
    category: 'audio',
    isPublic: false,
    createdAt: '2024-11-05',
  },
];

export function VideoLibrary({ onBack }: VideoLibraryProps) {
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);

  const categories = ['All', 'Transitions', 'Intros', 'Outros', 'Audio', 'Effects'];

  const filteredVideos = mockVideos.filter((video) => {
    const matchesSearch = video.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      video.tags.some(tag => tag.toLowerCase().includes(searchQuery.toLowerCase()));
    const matchesCategory = !selectedCategory || selectedCategory === 'All' ||
      video.category.toLowerCase() === selectedCategory.toLowerCase();
    return matchesSearch && matchesCategory;
  });

  return (
    <div className="max-w-6xl mx-auto animate-fade-in">
      <button
        onClick={onBack}
        className="flex items-center space-x-2 text-slate-600 hover:text-slate-900 mb-6 transition-colors"
      >
        <ArrowLeft className="w-5 h-5" />
        <span>Back</span>
      </button>

      <div className="mb-8">
        <h1 className="text-3xl font-bold text-slate-900">Video Library</h1>
        <p className="text-slate-600 mt-1">Manage and organize your reusable video clips</p>
      </div>

      <div className="card p-6 mb-8">
        <div className="space-y-4">
          <div className="relative">
            <Search className="absolute left-3 top-3 w-5 h-5 text-slate-400" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search by title or tags..."
              className="input-field pl-10"
            />
          </div>

          <div className="flex flex-wrap gap-2">
            {categories.map((cat) => (
              <button
                key={cat}
                onClick={() => setSelectedCategory(cat === 'All' ? null : cat)}
                className={`px-4 py-2 rounded-full text-sm font-medium transition-all ${
                  (cat === 'All' && !selectedCategory) || selectedCategory === cat
                    ? 'bg-blue-600 text-white'
                    : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
                }`}
              >
                {cat}
              </button>
            ))}
          </div>
        </div>
      </div>

      {filteredVideos.length === 0 ? (
        <div className="card p-16 text-center">
          <p className="text-slate-500">No videos found matching your criteria</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredVideos.map((video) => (
            <div key={video.id} className="card overflow-hidden group hover:shadow-lg transition-all">
              <div className="aspect-video bg-gradient-to-br from-slate-300 to-slate-400 flex items-center justify-center relative overflow-hidden">
                <Play className="w-12 h-12 text-white/50 group-hover:scale-110 transition-transform" />
                <div className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity bg-black/40 flex items-center justify-center space-x-2">
                  <button className="p-2 bg-white rounded-full hover:bg-slate-100 transition-colors">
                    <Play className="w-5 h-5 text-blue-600 fill-current" />
                  </button>
                  <button className="p-2 bg-white rounded-full hover:bg-slate-100 transition-colors">
                    <Download className="w-5 h-5 text-blue-600" />
                  </button>
                </div>
                <div className="absolute top-2 right-2 bg-blue-600 text-white px-2 py-1 rounded text-xs font-medium">
                  {video.duration}s
                </div>
              </div>

              <div className="p-4 space-y-3">
                <div>
                  <h3 className="font-semibold text-slate-900 line-clamp-2">{video.title}</h3>
                  <p className="text-xs text-slate-500 mt-1">{video.createdAt}</p>
                </div>

                {video.tags.length > 0 && (
                  <div className="flex flex-wrap gap-1">
                    {video.tags.slice(0, 3).map((tag) => (
                      <span
                        key={tag}
                        className="inline-flex items-center space-x-1 px-2 py-1 bg-slate-100 rounded text-xs text-slate-600"
                      >
                        <Tag className="w-3 h-3" />
                        <span>{tag}</span>
                      </span>
                    ))}
                    {video.tags.length > 3 && (
                      <span className="text-xs text-slate-500 px-2 py-1">+{video.tags.length - 3}</span>
                    )}
                  </div>
                )}

                <div className="flex items-center justify-between pt-2 border-t border-slate-200">
                  <span className="text-xs font-medium text-slate-600">
                    {video.isPublic ? 'Public' : 'Private'}
                  </span>
                  <button className="text-slate-400 hover:text-red-600 transition-colors">
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
