import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext.jsx';
import { api } from '../services/api.js';
import { Lock, User, AlertCircle } from 'lucide-react';

export default function LoginPage() {
    const [form, setForm] = useState({ username: '', password: '' });
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');
    const { login } = useAuth();
    const navigate = useNavigate();

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError(''); setLoading(true);
        try {
            const res = await api.login(form.username, form.password);
            login(res.token, { username: form.username, roles: res.roles });
            navigate('/');
        } catch (err) {
            setError(err.message || 'Invalid credentials');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="login-screen">
            <div className="login-card">
                <div className="login-header">
                    <div className="login-brand-icon">⚡</div>
                    <h2>Athena Admin Portal</h2>
                    <p style={{ marginTop: 8, fontSize: '0.875rem' }}>
                        Credit risk management &amp; model monitoring
                    </p>
                </div>

                {error && (
                    <div style={{
                        background: 'rgba(239,68,68,0.1)',
                        border: '1px solid rgba(239,68,68,0.25)',
                        borderRadius: 'var(--radius-md)',
                        padding: '10px 14px',
                        display: 'flex', alignItems: 'center', gap: 8,
                        color: 'var(--red-400)', fontSize: '0.85rem', marginBottom: 16,
                    }}>
                        <AlertCircle size={15} /> {error}
                    </div>
                )}

                <form className="login-form" onSubmit={handleSubmit}>
                    <div className="form-group">
                        <label className="form-label">Username</label>
                        <div style={{ position: 'relative' }}>
                            <User size={15} style={{
                                position: 'absolute', left: 12, top: '50%',
                                transform: 'translateY(-50%)', color: 'var(--gray-500)',
                            }} />
                            <input
                                id="username"
                                className="form-input w-full"
                                style={{ paddingLeft: 36 }}
                                placeholder="admin"
                                value={form.username}
                                onChange={e => setForm(f => ({ ...f, username: e.target.value }))}
                                required autoFocus
                            />
                        </div>
                    </div>

                    <div className="form-group">
                        <label className="form-label">Password</label>
                        <div style={{ position: 'relative' }}>
                            <Lock size={15} style={{
                                position: 'absolute', left: 12, top: '50%',
                                transform: 'translateY(-50%)', color: 'var(--gray-500)',
                            }} />
                            <input
                                id="password"
                                type="password"
                                className="form-input w-full"
                                style={{ paddingLeft: 36 }}
                                placeholder="••••••••"
                                value={form.password}
                                onChange={e => setForm(f => ({ ...f, password: e.target.value }))}
                                required
                            />
                        </div>
                    </div>

                    <button
                        type="submit"
                        className="btn btn-primary w-full"
                        disabled={loading}
                        style={{ justifyContent: 'center', marginTop: 8 }}
                    >
                        {loading ? 'Signing in…' : 'Sign In'}
                    </button>
                </form>

                <p style={{ textAlign: 'center', marginTop: 20, fontSize: '0.75rem', color: 'var(--gray-600)' }}>
                    Athena Credit Initiative · Secured by JWT + TLS
                </p>
            </div>
        </div>
    );
}
