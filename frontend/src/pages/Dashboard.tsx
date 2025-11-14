import { ArrowLeft, Plus, Activity, Zap, Users, TrendingUp } from 'lucide-react';
import { useState } from 'react';

interface DashboardProps {
  onBack: () => void;
}

const recentActivity = [
  { id: 1, action: 'Created project', item: 'Summer Travel Guide', time: '2 hours ago', icon: Zap },
  { id: 2, action: 'Shared with', item: 'team@example.com', time: '5 hours ago', icon: Users },
  { id: 3, action: 'Downloaded video', item: 'Product Launch', time: '1 day ago', icon: TrendingUp },
];

export function Dashboard({ onBack }: DashboardProps) {
  const [showNewTeam, setShowNewTeam] = useState(false);

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
        <h1 className="text-3xl font-bold text-slate-900">Dashboard</h1>
        <p className="text-slate-600 mt-1">Welcome back! Here's what's happening with your account</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
        <div className="card p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-slate-600">Videos This Month</p>
              <p className="text-3xl font-bold text-slate-900 mt-1">8</p>
            </div>
            <div className="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center">
              <Zap className="w-6 h-6 text-blue-600" />
            </div>
          </div>
        </div>

        <div className="card p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-slate-600">Total Views</p>
              <p className="text-3xl font-bold text-slate-900 mt-1">1.2K</p>
            </div>
            <div className="w-12 h-12 bg-purple-100 rounded-lg flex items-center justify-center">
              <TrendingUp className="w-6 h-6 text-purple-600" />
            </div>
          </div>
        </div>

        <div className="card p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-slate-600">Collaborators</p>
              <p className="text-3xl font-bold text-slate-900 mt-1">3</p>
            </div>
            <div className="w-12 h-12 bg-green-100 rounded-lg flex items-center justify-center">
              <Users className="w-6 h-6 text-green-600" />
            </div>
          </div>
        </div>

        <div className="card p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-slate-600">Storage Used</p>
              <p className="text-3xl font-bold text-slate-900 mt-1">24GB</p>
              <p className="text-xs text-slate-500 mt-1">of 100GB</p>
            </div>
            <div className="w-12 h-12 bg-orange-100 rounded-lg flex items-center justify-center">
              <Activity className="w-6 h-6 text-orange-600" />
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 card p-6">
          <h3 className="font-semibold text-slate-900 mb-4 flex items-center space-x-2">
            <Activity className="w-5 h-5 text-blue-600" />
            <span>Recent Activity</span>
          </h3>
          <div className="space-y-4">
            {recentActivity.map((activity) => (
              <div
                key={activity.id}
                className="flex items-center justify-between p-4 bg-slate-50 rounded-lg hover:bg-slate-100 transition-colors"
              >
                <div className="flex items-center space-x-4">
                  <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center">
                    <activity.icon className="w-5 h-5 text-blue-600" />
                  </div>
                  <div>
                    <p className="font-medium text-slate-900">{activity.action}</p>
                    <p className="text-sm text-slate-500">{activity.item}</p>
                  </div>
                </div>
                <p className="text-xs text-slate-500">{activity.time}</p>
              </div>
            ))}
          </div>
        </div>

        <div className="card p-6 space-y-4">
          <h3 className="font-semibold text-slate-900">Teams</h3>
          <div className="space-y-2">
            <button className="w-full p-3 bg-slate-50 rounded-lg hover:bg-slate-100 transition-colors text-left">
              <p className="font-medium text-slate-900">Personal Workspace</p>
              <p className="text-xs text-slate-500 mt-1">1 member</p>
            </button>
            <button className="w-full p-3 bg-slate-50 rounded-lg hover:bg-slate-100 transition-colors text-left">
              <p className="font-medium text-slate-900">Marketing Team</p>
              <p className="text-xs text-slate-500 mt-1">4 members</p>
            </button>
          </div>
          <button
            onClick={() => setShowNewTeam(true)}
            className="w-full flex items-center justify-center space-x-2 mt-4 p-3 border-2 border-dashed border-slate-300 rounded-lg hover:border-blue-400 hover:bg-blue-50 transition-colors text-slate-700"
          >
            <Plus className="w-5 h-5" />
            <span className="text-sm font-medium">New Team</span>
          </button>
        </div>
      </div>
    </div>
  );
}
