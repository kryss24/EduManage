// Page Classes — squelette SCRUM-6

const classes = [
  { id: 1, name: 'CM2', capacity: 35, totalSubjects: 20 },
  { id: 2, name: 'CE1', capacity: 30, totalSubjects: 19 },
  { id: 3, name: 'CLASS 6', capacity: 79, totalSubjects: 30 },
  { id: 4, name: 'CE2', capacity: 32, totalSubjects: 20 },
]

function Classes() {
  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">Class Management</h1>
          <p className="text-sm text-gray-500 mt-1">Welcome, Mr SOM</p>
        </div>
        <button className="flex items-center gap-2 bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors">
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
          </svg>
          Add Classes
        </button>
      </div>

      {/* Barre recherche */}
      <div className="bg-white rounded-xl border border-gray-200 p-4 mb-6 flex gap-3 items-center">
        <div className="relative flex-1">
          <svg className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
          <input type="text" placeholder="Find class..." className="w-full pl-9 pr-4 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-green-500" />
        </div>
        <span className="text-sm text-gray-400">{classes.length} Results</span>
      </div>

      {/* Grille de cartes */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-2 xl:grid-cols-3 gap-4">
        {classes.map((cls) => (
          <div key={cls.id} className="bg-white rounded-xl border border-gray-200 overflow-hidden">
            {/* Image header */}
            <div className="h-32 bg-sky-300 flex items-center justify-center">
              <div className="text-center">
                <div className="w-12 h-12 bg-green-600 rounded-full mx-auto flex items-center justify-center mb-1">
                  <svg className="w-7 h-7 text-white" fill="currentColor" viewBox="0 0 24 24">
                    <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" />
                  </svg>
                </div>
                <span className="text-green-700 font-bold text-sm">EduManage</span>
              </div>
            </div>
            {/* Infos + actions */}
            <div className="p-4 flex items-center justify-between">
              <div className="text-sm">
                <p className="font-semibold text-gray-800">CLASS : {cls.name}</p>
                <p className="text-gray-500">CAPACITY : {cls.capacity}</p>
                <p className="text-gray-500">TOTAL SUBJECTS: {cls.totalSubjects}</p>
              </div>
              <div className="flex gap-2">
                <button className="p-1 text-gray-400 hover:text-blue-600" title="Modifier">
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" /></svg>
                </button>
                <button className="p-1 text-gray-400 hover:text-red-600" title="Supprimer">
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" /></svg>
                </button>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

export default Classes
