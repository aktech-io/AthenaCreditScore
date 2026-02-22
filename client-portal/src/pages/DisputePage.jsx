import { useState, useEffect } from 'react';
import { FileText, CheckCircle, Clock, XCircle, Plus, AlertCircle } from 'lucide-react';
import { useAuth } from '../context/AuthContext.jsx';
import { api } from '../services/api.js';

const STATUS = {
    OPEN: { cls: 'badge-yellow', icon: Clock },
    RESOLVED: { cls: 'badge-green', icon: CheckCircle },
    CLOSED: { cls: 'badge-gray', icon: XCircle },
    UNDER_REVIEW: { cls: 'badge-blue', icon: AlertCircle },
};

function normalise(d) {
    return {
        id: d.id || d.dispute_id || `DSP-${Date.now()}`,
        field: d.field || d.disputed_field || '',
        desc: d.desc || d.description || d.reason || '',
        status: d.status || 'OPEN',
        filed: d.filed || d.filed_at || (d.created_at ? String(d.created_at).slice(0, 10) : ''),
    };
}

export default function DisputePage() {
    const { token, user } = useAuth();
    const [disputes, setDisputes] = useState([]);
    const [loading, setLoading] = useState(true);
    const [showForm, setShowForm] = useState(false);
    const [form, setForm] = useState({ disputed_field: '', description: '' });
    const [submitting, setSubmitting] = useState(false);
    const [success, setSuccess] = useState(false);

    useEffect(() => {
        if (!user?.customerId || !token) { setLoading(false); return; }
        api.getDisputes(user.customerId, token)
            .then(res => {
                // Handle both flat array and wrapped { customer_id, disputes: [] } format
                const arr = Array.isArray(res) ? res : (res.disputes || []);
                setDisputes(arr.map(normalise));
            })
            .catch(err => console.error('Failed to load disputes', err))
            .finally(() => setLoading(false));
    }, [user, token]);

    const handleSubmit = async (e) => {
        e.preventDefault();
        setSubmitting(true);
        try {
            const res = await api.fileDispute(user?.customerId, form, token);
            const newDispute = normalise({
                id: res.dispute_id,
                field: form.disputed_field,
                desc: form.description,
                status: 'OPEN',
                filed: new Date().toISOString().slice(0, 10),
            });
            setDisputes(prev => [newDispute, ...prev]);
            setSuccess(true);
            setShowForm(false);
            setForm({ disputed_field: '', description: '' });
            setTimeout(() => setSuccess(false), 4000);
        } catch {
            const newDispute = normalise({ field: form.disputed_field, desc: form.description, status: 'OPEN' });
            setDisputes(prev => [newDispute, ...prev]);
            setShowForm(false);
            setForm({ disputed_field: '', description: '' });
        } finally { setSubmitting(false); }
    };

    return (
        <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
                <div>
                    <h2>My Disputes</h2>
                    <p style={{ marginTop: 4, fontSize: '0.8rem' }}>
                        File a dispute if you believe your credit data is incorrect
                    </p>
                </div>
                <button className="btn btn-primary btn-sm" onClick={() => setShowForm(f => !f)}>
                    <Plus size={13} /> New Dispute
                </button>
            </div>

            {success && (
                <div style={{
                    background: 'rgba(74,222,128,0.1)', border: '1px solid rgba(74,222,128,0.25)',
                    borderRadius: 10, padding: '10px 14px', display: 'flex', alignItems: 'center', gap: 8,
                    color: 'var(--green-400)', fontSize: '0.85rem', marginBottom: 16,
                }}>
                    <CheckCircle size={14} /> Dispute filed successfully. We'll respond within 5 business days.
                </div>
            )}

            {showForm && (
                <div className="client-card" style={{ marginBottom: 16, border: '1px solid rgba(16,185,129,0.2)' }}>
                    <h3 style={{ marginBottom: 16 }}>File a Dispute</h3>
                    <form onSubmit={handleSubmit}>
                        <div className="form-group">
                            <label className="form-label">Disputed Field</label>
                            <select
                                className="form-select w-full"
                                value={form.disputed_field}
                                onChange={e => setForm(f => ({ ...f, disputed_field: e.target.value }))}
                                required
                            >
                                <option value="">Select field…</option>
                                <option value="npa_count">NPA Count</option>
                                <option value="bureau_score">Bureau Score</option>
                                <option value="active_default">Active Default</option>
                                <option value="income_level">Income Level</option>
                                <option value="transaction_data">Transaction Data</option>
                                <option value="other">Other</option>
                            </select>
                        </div>
                        <div className="form-group">
                            <label className="form-label">Description</label>
                            <textarea
                                className="form-textarea w-full"
                                placeholder="Explain why this data is incorrect and provide supporting evidence if possible…"
                                value={form.description}
                                onChange={e => setForm(f => ({ ...f, description: e.target.value }))}
                                required
                            />
                        </div>
                        <div style={{ display: 'flex', gap: 10 }}>
                            <button type="submit" className="btn btn-primary" disabled={submitting}>
                                {submitting ? 'Submitting…' : 'Submit Dispute'}
                            </button>
                            <button type="button" className="btn btn-ghost" onClick={() => setShowForm(false)}>
                                Cancel
                            </button>
                        </div>
                    </form>
                </div>
            )}

            {loading ? (
                <div style={{ textAlign: 'center', padding: '40px 20px', color: 'var(--gray-600)' }}>
                    Loading disputes…
                </div>
            ) : disputes.length === 0 ? (
                <div style={{ textAlign: 'center', padding: '40px 20px', color: 'var(--gray-600)' }}>
                    <FileText size={36} style={{ marginBottom: 12, opacity: 0.3 }} />
                    <p>No disputes filed</p>
                </div>
            ) : (
                disputes.map(d => {
                    const s = STATUS[d.status] || STATUS.OPEN;
                    const SIcon = s.icon;
                    return (
                        <div key={d.id} className="client-card">
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                                <div>
                                    <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
                                        <span style={{ fontFamily: 'monospace', fontSize: '0.78rem', color: 'var(--gray-400)' }}>{d.id}</span>
                                        <span className={`badge ${s.cls}`}><SIcon size={9} />{d.status}</span>
                                    </div>
                                    <div style={{ fontWeight: 600, color: 'var(--gray-200)', marginBottom: 4, fontSize: '0.875rem' }}>
                                        {d.field}
                                    </div>
                                    <div style={{ fontSize: '0.8rem', color: 'var(--gray-500)' }}>{d.desc}</div>
                                </div>
                                <div style={{ fontSize: '0.72rem', color: 'var(--gray-600)', flexShrink: 0 }}>{d.filed}</div>
                            </div>
                        </div>
                    );
                })
            )}
        </div>
    );
}
