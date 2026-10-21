// Dashboard Admin — squelette SCRUM-6
// Les données sont fictives (placeholder) en attendant l'API Django

const stats = [
  { label: 'Total Students', value: '1 000', icon: '👨‍🎓' },
  { label: 'Total Teachers', value: '15', icon: '👨‍🏫' },
  { label: 'Total Classes', value: '26', icon: '🏫' },
  { label: 'School Average Grade', value: '89%', icon: '📊' },
]

const recentActivities = [
  { action: 'Student added', user: 'Admin John', date: '16 Feb 2026' },
  { action: 'Grades submitted', user: 'Teacher Sarah', date: '15 Feb 2026' },
  { action: 'Class created', user: 'Admin John', date: '14 Feb 2026' },
  { action: 'Teacher updated', user: 'Admin Mike', date: '13 Feb 2026' },
]

function Dashboard() {
  return (
    <div>
      {/* En-tête */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">Admin Dashboard</h1>
          <p className="text-sm text-gray-500 mt-1">
            Overview of school performance and metrics for Term 2, 2024.
          </p>
        </div>
        <button className="flex items-center gap-2 px-4 py-2 border border-gray-300 rounded-lg text-sm text-gray-600 hover:bg-gray-50 transition-colors">
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
              d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
          Refresh
        </button>
      </div>

      {/* Cartes stats */}
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4 mb-8">
        {stats.map((stat) => (
          <div
            key={stat.label}
            className="bg-white rounded-xl border border-gray-200 p-5 flex items-center gap-4"
          >
            <span className="text-3xl">{stat.icon}</span>
            <div>
              <p className="text-xs text-gray-500">{stat.label}</p>
              <p className="text-2xl font-bold text-gray-800">{stat.value}</p>
            </div>
          </div>
        ))}
      </div>

      {/* Graphe + Activités récentes */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Graphe placeholder */}
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <h2 className="text-sm font-semibold text-gray-700 mb-4">Performance Overview</h2>
          <div className="flex items-end gap-2 h-32">
            {[30, 45, 40, 60, 55, 75, 65, 80].map((h, i) => (
              <div key={i} className="flex-1 flex flex-col items-center gap-1">
                <div
                  className={`w-full rounded-t ${i % 2 === 0 ? 'bg-green-600' : 'bg-green-200'}`}
                  style={{ height: `${h}%` }}
                />
              </div>
            ))}
          </div>
        </div>

        {/* Activités récentes */}
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <h2 className="text-sm font-semibold text-gray-700 mb-4">Recent Activities</h2>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-gray-400 border-b">
                  <th className="pb-2 font-medium">Action</th>
                  <th className="pb-2 font-medium">User</th>
                  <th className="pb-2 font-medium">Date</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {recentActivities.map((item, i) => (
                  <tr key={i}>
                    <td className="py-2 text-gray-700">{item.action}</td>
                    <td className="py-2 text-gray-500">{item.user}</td>
                    <td className="py-2 text-gray-400">{item.date}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  )
}

export default Dashboard
