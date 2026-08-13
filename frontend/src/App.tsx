import { BrowserRouter, Link, Route, Routes } from 'react-router-dom'
import Report from './pages/Report'
import Dashboard from './pages/Dashboard'
import Track from './pages/Track'
import Login from './pages/Login'
import MapView from './pages/MapView'
import { AuthProvider, useAuth } from './auth/AuthContext'

function Nav() {
  const { user, logout } = useAuth()
  return (
    <nav className="flex justify-center gap-4 border-b border-gray-200 py-3 text-sm">
      <Link to="/" className="text-gray-600 hover:text-gray-900">
        Report an issue
      </Link>
      <Link to="/track" className="text-gray-600 hover:text-gray-900">
        My reports
      </Link>
      <Link to="/map" className="text-gray-600 hover:text-gray-900">
        Map
      </Link>
      <Link to="/dashboard" className="text-gray-600 hover:text-gray-900">
        Authority dashboard
      </Link>
      {user ? (
        <button onClick={logout} className="text-gray-600 hover:text-gray-900">
          Log out ({user.name})
        </button>
      ) : (
        <Link to="/login" className="text-gray-600 hover:text-gray-900">
          Log in
        </Link>
      )}
    </nav>
  )
}

function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Nav />
        <Routes>
          <Route path="/" element={<Report />} />
          <Route path="/track" element={<Track />} />
          <Route path="/map" element={<MapView />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/login" element={<Login />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  )
}

export default App
