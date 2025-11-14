import { ArrowLeft, TrendingUp, Video, Clock, Users } from 'lucide-react';
import { LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

interface AnalyticsProps {
  onBack: () => void;
}

const chartData = [
  { date: 'Mon', videos: 2, views: 400 },
  { date: 'Tue', videos: 3, views: 720 },
  { date: 'Wed', videos: 1, views: 200 },
  { date: 'Thu', videos: 4, views: 1000 },
  { date: 'Fri', videos: 5, views: 1200 },
  { date: 'Sat', videos: 2, views: 600 },
  { date: 'Sun', videos: 3, views: 800 },
];

export function Analytics({ onBack }: AnalyticsProps) {
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
        <h1 className="text-3xl font-bold text-slate-900 dark:text-slate-100">Analytics</h1>
        <p className="text-slate-600 dark:text-slate-400 mt-1">Track your video creation activity and performance</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <div className="card p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-slate-600 dark:text-slate-400">Videos Created</p>
              <p className="text-3xl font-bold text-slate-900 dark:text-slate-100 mt-1">24</p>
              <p className="text-xs text-green-600 mt-2">+3 this week</p>
            </div>
            <div className="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center">
              <Video className="w-6 h-6 text-blue-600" />
            </div>
          </div>
        </div>

        <div className="card p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-slate-600 dark:text-slate-400">Total Views</p>
              <p className="text-3xl font-bold text-slate-900 dark:text-slate-100 mt-1">4.2K</p>
              <p className="text-xs text-green-600 mt-2">+12% this month</p>
            </div>
            <div className="w-12 h-12 bg-purple-100 rounded-lg flex items-center justify-center">
              <Users className="w-6 h-6 text-purple-600" />
            </div>
          </div>
        </div>

        <div className="card p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-slate-600 dark:text-slate-400">Total Duration</p>
              <p className="text-3xl font-bold text-slate-900 dark:text-slate-100 mt-1">8h 24m</p>
              <p className="text-xs text-slate-500 dark:text-slate-400 mt-2">Average 21m per video</p>
            </div>
            <div className="w-12 h-12 bg-green-100 rounded-lg flex items-center justify-center">
              <Clock className="w-6 h-6 text-green-600" />
            </div>
          </div>
        </div>

        <div className="card p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-slate-600 dark:text-slate-400">Growth Rate</p>
              <p className="text-3xl font-bold text-slate-900 dark:text-slate-100 mt-1">18%</p>
              <p className="text-xs text-green-600 mt-2">Month over month</p>
            </div>
            <div className="w-12 h-12 bg-orange-100 rounded-lg flex items-center justify-center">
              <TrendingUp className="w-6 h-6 text-orange-600" />
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        <div className="card p-6">
          <h3 className="font-semibold text-slate-900 dark:text-slate-100 mb-4">Videos Created (This Week)</h3>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis dataKey="date" stroke="#94a3b8" />
              <YAxis stroke="#94a3b8" />
              <Tooltip
                contentStyle={{
                  backgroundColor: '#f1f5f9',
                  border: '1px solid #cbd5e1',
                  borderRadius: '8px'
                }}
              />
              <Bar dataKey="videos" fill="#3b82f6" radius={[8, 8, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="card p-6">
          <h3 className="font-semibold text-slate-900 dark:text-slate-100 mb-4">Views Trend</h3>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis dataKey="date" stroke="#94a3b8" />
              <YAxis stroke="#94a3b8" />
              <Tooltip
                contentStyle={{
                  backgroundColor: '#f1f5f9',
                  border: '1px solid #cbd5e1',
                  borderRadius: '8px'
                }}
              />
              <Line
                type="monotone"
                dataKey="views"
                stroke="#8b5cf6"
                strokeWidth={2}
                dot={{ fill: '#8b5cf6', r: 4 }}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="card p-6">
        <h3 className="font-semibold text-slate-900 dark:text-slate-100 mb-4">Top Videos</h3>
        <div className="space-y-3">
          {[
            { title: 'Summer Travel Guide', views: 1240, date: '2 days ago' },
            { title: 'Product Launch Teaser', views: 980, date: '5 days ago' },
            { title: 'Tutorial Series Ep.1', views: 756, date: '1 week ago' },
          ].map((video, idx) => (
            <div
              key={idx}
              className="flex items-center justify-between p-4 bg-slate-50 dark:bg-slate-700/50 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-700 dark:bg-slate-700 transition-colors"
            >
              <div>
                <p className="font-medium text-slate-900 dark:text-slate-100">{video.title}</p>
                <p className="text-sm text-slate-500 dark:text-slate-400">{video.date}</p>
              </div>
              <p className="text-lg font-semibold text-slate-900 dark:text-slate-100">{video.views}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
