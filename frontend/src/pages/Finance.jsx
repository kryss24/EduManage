// Page Finance — squelette SCRUM-6 (thème sombre comme dans les maquettes)

const transactions = [
  { activity: 'Noel', reason: 'Fête de fin d\'année', user: 'Admin John', type: 'entree', amount: '+20 000' },
  { activity: 'Transport', reason: 'Frais transport', user: 'Admin Sarah', type: 'sortie', amount: '-50 000' },
  { activity: 'Salaire', reason: 'Paie mensuelle', user: 'Admin Mike', type: 'entree', amount: '+10 000' },
]

function Finance() {
  return (
    <div className="min-h-full bg-slate-900 -m-6 p-6 text-white">
      {/* En-tête */}
      <div className="mb-8">
        <h1 className="text-4xl font-bold text-white/80">Financial Control Center</h1>
        <p className="text-slate-400 mt-1">Welcome, Manage your finance in real time</p>
      </div>

      {/* Cartes balances */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
        {/* Balance */}
        <div className="bg-slate-800 rounded-xl p-5">
          <p className="text-slate-400 text-sm mb-2">Balances</p>
          <p className="text-3xl font-bold text-white">274 000 F.CFA</p>
          <p className="text-green-400 text-xs mt-2">↗ 8.4% this month</p>
          <div className="flex items-end gap-1 h-12 mt-3">
            {[20, 30, 25, 40, 45, 55, 60].map((h, i) => (
              <div key={i} className="flex-1 bg-blue-500 rounded-sm opacity-70" style={{ height: `${h}%` }} />
            ))}
          </div>
        </div>

        {/* Entrées du jour */}
        <div className="bg-slate-800 rounded-xl p-5">
          <div className="flex justify-between items-start mb-2">
            <p className="text-slate-400 text-sm">Entrées du jour</p>
            <span className="bg-green-500 text-white text-xs px-2 py-1 rounded">↗</span>
          </div>
          <p className="text-3xl font-bold text-green-400">274 000 F.CFA</p>
          <div className="flex items-end gap-1 h-12 mt-3">
            {[15, 25, 20, 35, 40, 50, 55].map((h, i) => (
              <div key={i} className="flex-1 bg-green-500 rounded-sm" style={{ height: `${h}%` }} />
            ))}
          </div>
          <p className="text-slate-400 text-xs mt-2">Total entries for the month : 30.000 FCFA</p>
        </div>

        {/* Sorties */}
        <div className="bg-slate-800 rounded-xl p-5">
          <div className="flex justify-between items-start mb-2">
            <p className="text-slate-400 text-sm">Balances</p>
            <span className="bg-red-500 text-white text-xs px-2 py-1 rounded">↘</span>
          </div>
          <p className="text-3xl font-bold text-red-400">274 000 F.CFA</p>
          <div className="flex items-end gap-1 h-12 mt-3">
            {[40, 30, 35, 25, 20, 15, 10].map((h, i) => (
              <div key={i} className="flex-1 bg-red-500 rounded-sm" style={{ height: `${h}%` }} />
            ))}
          </div>
          <p className="text-slate-400 text-xs mt-2">Total entries for the month: 65.000 FCFA</p>
        </div>
      </div>

      {/* Historique transactions */}
      <div className="bg-slate-800 rounded-xl p-5">
        <div className="flex items-center justify-between mb-4">
          <h2 className="font-semibold text-white">Historique des Transactions</h2>
          <div className="flex gap-2">
            {['Sorties', 'Entrées', 'Sorties'].map((btn, i) => (
              <button key={i} className={`px-3 py-1 rounded-full text-xs border ${i === 1 ? 'border-green-500 text-green-400' : 'border-slate-600 text-slate-400'}`}>
                {btn}
              </button>
            ))}
          </div>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-slate-400 border-b border-slate-700">
                <th className="pb-2 text-left font-medium">Activities</th>
                <th className="pb-2 text-left font-medium">Reason</th>
                <th className="pb-2 text-left font-medium">User</th>
                <th className="pb-2 text-left font-medium">Type</th>
                <th className="pb-2 text-left font-medium">Amount</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-700">
              {transactions.map((t, i) => (
                <tr key={i}>
                  <td className="py-3 text-white">{t.activity}</td>
                  <td className="py-3 text-slate-400">{t.reason}</td>
                  <td className="py-3 text-slate-400">{t.user}</td>
                  <td className="py-3">
                    <span className={`text-xs font-medium ${t.type === 'entree' ? 'text-green-400' : 'text-red-400'}`}>
                      ↗ {t.type}
                    </span>
                  </td>
                  <td className={`py-3 font-semibold ${t.type === 'entree' ? 'text-green-400' : 'text-red-400'}`}>
                    {t.amount}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="flex justify-end gap-1 mt-4">
          <button className="px-3 py-1 text-xs border border-slate-600 text-slate-400 rounded hover:bg-slate-700">Previous</button>
          <button className="px-3 py-1 text-xs bg-green-600 text-white rounded">1</button>
          <button className="px-3 py-1 text-xs border border-slate-600 text-slate-400 rounded hover:bg-slate-700">2</button>
          <button className="px-3 py-1 text-xs border border-slate-600 text-slate-400 rounded hover:bg-slate-700">Next</button>
        </div>
      </div>
    </div>
  )
}

export default Finance
