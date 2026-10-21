// Page Settings — squelette SCRUM-6

import { useState } from 'react'

const tabs = ['Profile', 'Security', 'Notification', 'Users', 'General']

function Settings() {
  const [activeTab, setActiveTab] = useState('Profile')

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">Paramètres</h1>
          <p className="text-sm text-gray-500 mt-1">Manage your Account, your security and your preferences</p>
        </div>
        <button className="flex items-center gap-2 bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors">
          ✓ Save
        </button>
      </div>

      <div className="flex gap-6">
        {/* Sidebar tabs */}
        <div className="w-48 shrink-0">
          <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
            {tabs.map((tab) => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={`w-full text-left px-4 py-3 text-sm font-medium transition-colors border-b last:border-b-0 border-gray-100 ${
                  activeTab === tab ? 'bg-green-600 text-white' : 'text-gray-600 hover:bg-gray-50'
                }`}
              >
                {tab}
              </button>
            ))}
            <button className="w-full text-left px-4 py-3 text-sm font-medium text-red-500 hover:bg-gray-50">
              Dangerous area
            </button>
          </div>
        </div>

        {/* Contenu */}
        <div className="flex-1 bg-white rounded-xl border border-gray-200 p-6">
          {activeTab === 'Profile' && (
            <div>
              <h2 className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-4">Personal Information</h2>
              <div className="flex items-center gap-4 mb-6">
                <div className="w-14 h-14 bg-green-500 rounded-full flex items-center justify-center text-white font-bold text-xl">A</div>
                <div>
                  <p className="font-semibold text-gray-800">Administrator</p>
                  <button className="text-xs text-green-600 hover:underline mt-1">Change the photo</button>
                </div>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {[
                  { label: 'First Name', value: 'Admin' },
                  { label: 'Last Name', value: 'Astro' },
                  { label: 'Email', value: 'astroadmin@gmail.com' },
                  { label: 'Phone', value: '+237 26857945' },
                ].map((field) => (
                  <div key={field.label}>
                    <label className="block text-xs text-gray-500 mb-1">{field.label}</label>
                    <input
                      defaultValue={field.value}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-green-500"
                    />
                  </div>
                ))}
              </div>
            </div>
          )}
          {activeTab === 'Security' && (
            <div>
              <h2 className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-4">Security of Account</h2>
              <div className="space-y-4 max-w-md">
                <div>
                  <label className="block text-xs text-gray-500 mb-1">Current password</label>
                  <input type="password" defaultValue="••••••••" className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-green-500" />
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-xs text-gray-500 mb-1">New Password</label>
                    <input type="password" className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-green-500" />
                  </div>
                  <div>
                    <label className="block text-xs text-gray-500 mb-1">Confirm</label>
                    <input type="password" className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-green-500" />
                  </div>
                </div>
              </div>
            </div>
          )}
          {!['Profile', 'Security'].includes(activeTab) && (
            <div className="text-center py-12 text-gray-400">
              <p className="text-4xl mb-3">⚙️</p>
              <p className="text-sm">{activeTab} — à implémenter dans les prochaines tâches</p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default Settings
