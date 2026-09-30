import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import Sidebar from './components/Sidebar'
import Dashboard from './pages/Dashboard'
import Upload from './pages/Upload'
import Documents from './pages/Documents'
import InvoiceDetails from './pages/InvoiceDetails'
import Review from './pages/Review'

function App() {
  return (
    <Router>
      <div className="min-h-screen bg-gray-50">
        <Sidebar />
        <main className="lg:ml-64 p-4 lg:p-8 transition-all duration-300">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/upload" element={<Upload />} />
            <Route path="/documents" element={<Documents />} />
            <Route path="/invoice/:documentId" element={<InvoiceDetails />} />
            <Route path="/review/:documentId" element={<Review />} />
          </Routes>
        </main>
      </div>
    </Router>
  )
}

export default App
