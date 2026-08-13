import { BrowserRouter, Link, Route, Routes } from 'react-router-dom'
import Report from './pages/Report'
import Dashboard from './pages/Dashboard'

function Nav() {
  return (
    <nav className="flex justify-center gap-4 border-b border-gray-200 py-3 text-sm">
      <Link to="/" className="text-gray-600 hover:text-gray-900">
        Report an issue
      </Link>
      <Link to="/dashboard" className="text-gray-600 hover:text-gray-900">
        Authority dashboard
      </Link>
    </nav>
  )
}

function App() {
  return (
    <BrowserRouter>
      <Nav />
      <Routes>
        <Route path="/" element={<Report />} />
        <Route path="/dashboard" element={<Dashboard />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App
