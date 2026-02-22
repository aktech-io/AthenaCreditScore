import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { CheckCircle, Clock, AlertCircle } from 'lucide-react';
import { useAuth } from '../context/AuthContext.jsx';
import { api } from '../services/api.js';

const STATUS_META = {
    OPEN: { cls: 'badge-yellow', icon: Clock },
    RESOLVED: { cls: 'badge-green', icon: CheckCircle },
    CLOSED: { cls: 'badge-gray', icon: AlertCircle },
};

export default function DisputesPage() {
    const { token } = useAuth();
    const navigate = useNavigate();
    const [disputes, setDisputes] = useState([]);
    const [filter, setFilter] = useState('ALL');
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        async function loadDisputes() {
            try {
                const data = await api.listDisputes(token, filter === 'ALL' ? '' : filter);
                setDisputes(Array.isArray(data) ? data : []);
            } catch (err) {
                console.error('Failed to load disputes', err);
            } finally {
                setLoading(false);
            }
        }
        loadDisputes();
    }, [token, filter]);

    const visible = disputes;

    const markResolved = async (id) => {
        try {
            await api.updateDispute(id, { status: 'RESOLVED' }, token);
            setDisputes(prev => prev.map(d => d.id === id ? { ...d, status: 'RESOLVED' } : d));
        } catch (err) {
            console.error('Failed to update dispute', err);
        }
    };

    const viewCustomer = (dispute) => {
        const q = dispute.customer || dispute.customerId || '';
        navigate(`/customers?q=${encodeURIComponent(q)}`);
    };

    return (
        <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 24 }}>
                <div>
                    <h1 style={{ fontSize: '1.5rem' }}>Dispute Management</h1>
                    <p style={{ marginTop: 4 }}>Review and resolve customer credit report disputes</p>
                </div>
                <div style={{ display: 'flex', gap: 8 }}>
                    {['ALL', 'OPEN', 'RESOLVED', 'CLOSED'].map(s => (
                        <button
                            key={s}
                            className={`btn btn-sm ${filter === s ? 'btn-primary' : 'btn-ghost'}`}
                            onClick={() => setFilter(s)}
                        >
                            {s}
                        </button>
                    ))}
                </div>
            </div>

            {/* Summary row */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3,1fr)', gap: 12, marginBottom: 20 }}>
                {[
                    { label: 'Open', count: disputes.filter(d => d.status === 'OPEN').length, color: '#eab308' },
                    { label: 'Resolved', count: disputes.filter(d => d.status === 'RESOLVED').length, color: '#22c55e' },
                    { label: 'Closed', count: disputes.filter(d => d.status === 'CLOSED').length, color: '#64748b' },
                ].map(({ label, count, color }) => (
                    <div key={label} className="card" style={{ textAlign: 'center', padding: '16px 12px' }}>
                        <div style={{ fontSize: '1.75rem', fontWeight: 800, color }}>{count}</div>
                        <div style={{ fontSize: '0.78rem', color: 'var(--gray-500)', marginTop: 4 }}>{label}</div>
                    </div>
                ))}
            </div>

            {/* Disputes list */}
            {loading ? (
                <div style={{ textAlign: 'center', padding: '40px', color: 'var(--gray-500)' }}>Loading disputes…</div>
            ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                    {visible.map(d => {
                        const meta = STATUS_META[d.status] || STATUS_META.CLOSED;
                        const Icon = meta.icon;
                        return (
                            <div key={d.id} className="card" style={{ padding: '18px 20px' }}>
                                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: 10 }}>
                                    <div style={{ flex: 1 }}>
                                        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 6 }}>
                                            <span style={{ fontWeight: 700, color: 'white', fontSize: '0.875rem' }}>{d.id}</span>
                                            <span className={`badge ${meta.cls}`}><Icon size={10} />{d.status}</span>
                                            <span className="badge badge-gray" style={{ fontSize: '0.65rem' }}>{d.field || 'Credit Report'}</span>
                                        </div>
                                        <div style={{ fontWeight: 600, color: 'var(--gray-200)', fontSize: '0.875rem', marginBottom: 4 }}>
                                            {d.customer}
                                        </div>
                                        <div style={{ fontSize: '0.82rem', color: 'var(--gray-400)' }}>{d.desc}</div>
                                        <div style={{ fontSize: '0.72rem', color: 'var(--gray-600)', marginTop: 6 }}>
                                            Filed: {d.filed}
                                        </div>
                                    </div>
                                    <div style={{ display: 'flex', gap: 8, flexShrink: 0 }}>
                                        {d.status === 'OPEN' && (
                                            <button
                                                className="btn btn-sm btn-primary"
                                                onClick={() => markResolved(d.id)}
                                            >
                                                <CheckCircle size={13} /> Mark Resolved
                                            </button>
                                        )}
                                        <button className="btn btn-sm btn-ghost" onClick={() => viewCustomer(d)}>
                                            View Customer
                                        </button>
                                    </div>
                                </div>
                            </div>
                        );
                    })}
                    {visible.length === 0 && (
                        <div className="empty-state">
                            <CheckCircle size={40} className="empty-icon" />
                            <p>No {filter.toLowerCase()} disputes</p>
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}
