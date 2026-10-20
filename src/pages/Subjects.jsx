// Page Subjects — squelette SCRUM-6

const subjects = [
  { id: 1, name: 'Mathematique', coefficient: 3 },
  { id: 2, name: 'Algorithme', coefficient: 3 },
  { id: 3, name: 'Sciences', coefficient: 3 },
  { id: 4, name: 'English', coefficient: 3 },
  { id: 5, name: 'History', coefficient: 2 },
  { id: 6, name: 'Education', coefficient: 2 },
]

function Subjects() {
  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-800">Subjects Management</h1>
        <button className="flex items-center gap-2 bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors">
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
          </svg>
          Add Subjects
        </button>
      </div>

      {/* Filtres */}
      <div className="bg-white rounded-xl border border-gray-200 p-4 mb-4 flex gap-3 items-center">
        <div className="relative flex-1">
          <svg className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
          <input type="text" placeholder="Search subject..." className="w-full pl-9 pr-4 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-green-500" />
        </div>
        <select className="border border-gray-300 rounded-lg px-3 py-2 text-sm text-gray-600 focus:outline-none focus:ring-2 focus:ring-green-500">
          <option>CLASS</option><option>CM2</option><option>CE1</option><option>CE2</option>
        </select>
        <span className="text-sm text-gray-400">{subjects.length} Results</span>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-b border-gray-200">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">Subject Name</th>
              <th className="px-6 py-3 text-center text-xs font-semibold text-gray-500 uppercase tracking-wide">Coefficient</th>
              <th className="px-6 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {subjects.map((s) => (
              <tr key={s.id} className="hover:bg-gray-50 transition-colors">
                <td className="px-6 py-4 font-medium text-gray-800">{s.name}</td>
                <td className="px-6 py-4 text-center">
                  <span className="bg-gray-100 text-gray-700 px-3 py-1 rounded-lg text-sm font-medium">{s.coefficient}</span>
                </td>
                <td className="px-6 py-4">
                  <div className="flex gap-2">
                    <button className="p-1 text-gray-400 hover:text-blue-600" title="Modifier">
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" /></svg>
                    </button>
                    <button className="p-1 text-gray-400 hover:text-red-600" title="Supprimer">
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" /></svg>
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

export default Subjects
