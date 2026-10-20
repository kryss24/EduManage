import { useState } from 'react'
import { Link } from 'react-router-dom'

function Navbar({ onToggleSidebar }) {
  const [dropdownOpen, setDropdownOpen] = useState(false)

  return (
    <header className="bg-white border-b border-gray-200 h-16 flex items-center justify-between px-6 z-50 relative">
      {/* Gauche : logo */}
      <div className="flex items-center gap-3">
        <button
          onClick={onToggleSidebar}
          className="p-2 rounded hover:bg-gray-100 transition-colors lg:hidden"
          aria-label="Menu"
        >
          <svg className="w-5 h-5 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
          </svg>
        </button>
        <Link to="/dashboard" className="flex items-center gap-2">
          <div className="w-9 h-9 bg-green-600 rounded-full flex items-center justify-center">
            <svg className="w-5 h-5 text-white" fill="currentColor" viewBox="0 0 24 24">
              <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" />
            </svg>
          </div>
          <span className="text-green-600 font-bold text-xl">EduManage</span>
        </Link>
      </div>

      {/* Droite : utilisateur */}
      <div className="relative">
        <button
          onClick={() => setDropdownOpen(!dropdownOpen)}
          className="flex items-center gap-2 px-3 py-1.5 rounded-lg hover:bg-gray-100 transition-colors"
        >
          <div className="text-right hidden sm:block">
            <p className="text-sm font-medium text-gray-700">Administrator</p>
            <p className="text-xs text-gray-400">ADMIN</p>
          </div>
          <div className="w-9 h-9 bg-green-100 text-green-700 rounded-full flex items-center justify-center font-bold text-sm">
            A
          </div>
        </button>

        {dropdownOpen && (
          <div className="absolute right-0 mt-1 w-48 bg-white border border-gray-200 rounded-lg shadow-lg z-50">
            <div className="px-4 py-2 border-b text-xs text-gray-500">Administrator · ADMIN</div>
            <Link
              to="/settings"
              className="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-50"
              onClick={() => setDropdownOpen(false)}
            >
              Paramètres
            </Link>
            <Link
              to="/login"
              className="block px-4 py-2 text-sm text-red-600 hover:bg-gray-50"
              onClick={() => setDropdownOpen(false)}
            >
              Se déconnecter
            </Link>
          </div>
        )}
      </div>
    </header>
  )
}

export default Navbar
