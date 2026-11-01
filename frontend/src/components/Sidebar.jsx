import { Link, useLocation } from 'react-router-dom';
import { useState } from 'react';
import { LayoutDashboard, Upload, FileText, BookOpen, Cog, CheckCircle2, ScanLine, Menu, X, User } from 'lucide-react';

const navigation = [
  { name: 'Dashboard', href: '/', icon: LayoutDashboard },
  { name: 'Upload', href: '/upload', icon: Upload },
  { name: 'Documents', href: '/documents', icon: FileText },
  { name: 'Accounting', href: '/accounting-records', icon: BookOpen },
  //{ name: 'Processing', href: '/', icon: Cog },
  //{ name: 'Results', href: '/', icon: CheckCircle2 },
];

function Brand() {
  return (
    <div className="flex items-center gap-3">
      <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-gradient-to-br from-primary-500 to-primary-700 shadow-sm">
        <ScanLine className="h-5 w-5 text-white" />
      </div>
      <div className="leading-tight">
        <h1 className="text-sm font-semibold text-slate-900">Document AI</h1>
        <p className="text-xs text-slate-500">Intelligent Processing</p>
      </div>
    </div>
  );
}

function Sidebar() {
  const location = useLocation();
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

  return (
    <>
      {/* Mobile top bar */}
      {/*Display a button to open and close the menu */}
      <div className="lg:hidden sticky top-0 z-30 flex h-14 items-center justify-between border-b border-slate-200 bg-white/90 px-4 backdrop-blur">
        <Brand />
        <button
          onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)} //toggles ON and OFF
          aria-label={isMobileMenuOpen ? 'Close menu' : 'Open menu'}
          className="rounded-lg p-2 text-slate-600 hover:bg-slate-100"
        >
          {isMobileMenuOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}  {/* if Menu Open -> show option to close it. if Menu closed -> show option to open it*/}
        </button>
      </div>

      {/*Mobile Overlay */}
      {/*When Menu is Open, an overlay appears behind the Menu*/}
      {/*When clicked on the overlay the menu disappears */}
      {isMobileMenuOpen && (
        <div
          className="lg:hidden fixed inset-0 bg-slate-900/40 backdrop-blur-sm z-40"
          onClick={() => setIsMobileMenuOpen(false)}
        />
      )}

      {/* Sidebar */}
      {/*If Menu Open, side bar remains in its normal position (visible) */}
      {/*If Menu Close, side bar moves off screen */}
      <div className={`fixed left-0 top-0 h-full bg-white border-r border-slate-200 flex flex-col z-50 transition-transform duration-300 ease-in-out ${
        isMobileMenuOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'
      } w-64`}>
        {/* Logo */}
        <div className="flex h-16 items-center px-5 border-b border-slate-100">
          <Brand />
        </div>

        {/* Navigation */}
        <nav className="flex-1 px-3 py-4 space-y-1">
          <p className="px-3 pb-2 text-xs font-semibold uppercase tracking-wider text-slate-400">Menu</p>
          {navigation.map((item) => {
            const isActive = location.pathname === item.href;
            const Icon = item.icon;
            return (
              <Link
                key={item.name}
                to={item.href}
                onClick={() => setIsMobileMenuOpen(false)}
                className={`group relative flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                  isActive
                    ? 'bg-primary-50 text-primary-700'
                    : 'text-slate-600 hover:bg-slate-50 hover:text-slate-900'
                }`}
              >
                {isActive && <span className="absolute left-0 top-1.5 bottom-1.5 w-1 rounded-r-full bg-primary-600" />}
                <Icon className={`h-5 w-5 ${isActive ? 'text-primary-600' : 'text-slate-400 group-hover:text-slate-600'}`} />
                <span>{item.name}</span>
              </Link>
            );
          })}
        </nav>

        {/* User Profile */}
        <div className="p-4 border-t border-slate-100">
          <div className="flex items-center gap-3 rounded-lg px-2 py-1.5">
            <div className="flex h-8 w-8 items-center justify-center rounded-full bg-slate-100">
              <User className="h-4 w-4 text-slate-500" />
            </div>
            <div className="flex-1">
              <p className="text-sm font-medium text-slate-900">User</p>
              <p className="text-xs text-slate-500">Admin</p>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}

export default Sidebar;
