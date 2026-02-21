import { NavLink, Outlet, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext.jsx';
import { BarChart2, FileText, AlertCircle, Shield, LogOut } from 'lucide-react';

const NAV = [
    { to: '/', icon: BarChart2, label: 'My Score', end: true },
    { to: '/report', icon: FileText, label: 'Full Report' },
    { to: '/disputes', icon: AlertCircle, label: 'Disputes' },
    { to: '/consent', icon: Shield, label: 'Consent' },
];

export default function ClientShell() {
    const { user, logout } = useAuth();
    const navigate = useNavigate();

    const handleLogout = () => { logout(); navigate('/login'); };

    return (
        <div className="client-shell">
            <nav className="client-navbar">
                <div className="client-nav-logo">
                    <div className="client-nav-logo-icon">✦</div>
                    My Athena Score
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
                    <span style={{ fontSize: '0.8rem', color: 'var(--gray-500)' }}>
                        {user?.phone || 'Customer'}
                    </span>
                    <button
                        className="btn btn-ghost btn-sm"
                        onClick={handleLogout}
                        style={{ padding: '5px 10px' }}
                    >
                        <LogOut size={14} />
                    </button>
                </div>
            </nav>

            {/* Tab bar navigation */}
            <div className="tab-bar" style={{ marginBottom: 24 }}>
                {NAV.map(({ to, icon: Icon, label, end }) => (
                    <NavLink
                        key={to}
                        to={to}
                        end={end}
                        style={{ textDecoration: 'none' }}
                        className={({ isActive }) => `tab${isActive ? ' active' : ''}`}
                    >
                        <Icon size={13} style={{ marginRight: 4, verticalAlign: 'middle' }} />
                        {label}
                    </NavLink>
                ))}
            </div>

            <main className="page animate-in">
                <Outlet />
            </main>
        </div>
    );
}
