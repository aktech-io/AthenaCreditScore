import { Outlet, NavLink, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext.jsx';
import {
    LayoutDashboard, Users, AlertCircle,
    Sliders, FileText, LogOut, Activity
} from 'lucide-react';

const navItems = [
    { to: '/', icon: LayoutDashboard, label: 'Dashboard', end: true },
    { to: '/customers', icon: Users, label: 'Customers' },
    { to: '/disputes', icon: AlertCircle, label: 'Disputes' },
    { to: '/model', icon: Sliders, label: 'Model Config' },
    { to: '/audit', icon: FileText, label: 'Audit Log' },
];

export default function Layout() {
    const { user, logout } = useAuth();
    const navigate = useNavigate();

    const handleLogout = () => { logout(); navigate('/login'); };

    return (
        <div className="app-shell">
            {/* Sidebar */}
            <aside className="sidebar">
                <div className="sidebar-logo">
                    <div className="sidebar-logo-icon">⚡</div>
                    <div>
                        <div className="sidebar-logo-text">Athena Admin</div>
                        <div style={{ fontSize: '0.65rem', color: 'var(--gray-600)', marginTop: 2 }}>
                            Credit Initiative
                        </div>
                    </div>
                </div>

                <nav className="sidebar-nav">
                    <div className="nav-section-title">Navigation</div>
                    {navItems.map(({ to, icon: Icon, label, end }) => (
                        <NavLink
                            key={to}
                            to={to}
                            end={end}
                            className={({ isActive }) => `nav-item${isActive ? ' active' : ''}`}
                        >
                            <Icon className="nav-icon" size={18} />
                            {label}
                        </NavLink>
                    ))}
                </nav>

                {/* Bottom user area */}
                <div style={{
                    padding: '16px 12px',
                    borderTop: '1px solid rgba(255,255,255,0.06)',
                }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 12 }}>
                        <div className="avatar">{user?.username?.[0]?.toUpperCase() || 'A'}</div>
                        <div>
                            <div style={{ fontSize: '0.82rem', fontWeight: 600, color: 'var(--gray-200)' }}>
                                {user?.username || 'Admin'}
                            </div>
                            <div style={{ fontSize: '0.7rem', color: 'var(--gray-600)' }}>
                                {user?.roles?.[0] || 'ADMIN'}
                            </div>
                        </div>
                    </div>
                    <button className="nav-item w-full" onClick={handleLogout}>
                        <LogOut size={16} />
                        Sign Out
                    </button>
                </div>
            </aside>

            {/* Main */}
            <div className="main-content">
                <header className="topbar">
                    <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                        <Activity size={16} style={{ color: 'var(--green-500)' }} />
                        <span className="topbar-title">Athena Credit Control</span>
                    </div>
                    <div className="topbar-right">
                        <span style={{ fontSize: '0.78rem', color: 'var(--gray-500)' }}>
                            {new Date().toLocaleDateString('en-KE', { weekday: 'short', month: 'short', day: 'numeric' })}
                        </span>
                        <div className="avatar">{user?.username?.[0]?.toUpperCase() || 'A'}</div>
                    </div>
                </header>
                <main className="page-content animate-in">
                    <Outlet />
                </main>
            </div>
        </div>
    );
}
