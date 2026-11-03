import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import Sidebar from './components/Sidebar'
import Dashboard from './pages/Dashboard'
import Upload from './pages/Upload'
import Documents from './pages/Documents'
import InvoiceDetails from './pages/InvoiceDetails'
import Review from './pages/Review'
import AccountingRecords from './pages/AccountingRecords'
import { useInvoiceEvents } from './hooks/useInvoices'

function App() {
  useInvoiceEvents();

  return (
    <Router>
      <div className="min-h-screen bg-slate-50">
        <Sidebar />
        <main className="lg:ml-64 px-4 py-6 sm:px-6 lg:px-10 lg:py-10 transition-all duration-300">
          <div className="mx-auto max-w-7xl">
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/upload" element={<Upload />} />
              <Route path="/documents" element={<Documents />} />
              <Route path="/invoice/:documentId" element={<InvoiceDetails />} />
              <Route path="/review/:documentId" element={<Review />} />
              <Route path="/accounting-records" element={<AccountingRecords />} />
            </Routes>
          </div>
        </main>
      </div>
    </Router>
  )
}

export default App
