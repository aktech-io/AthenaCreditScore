import { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext.jsx';
import { api } from '../services/api.js';
import { Shield, ShieldAlert, Key, Globe } from 'lucide-react';

export default function ConsentPage() {
    const { token, user } = useAuth();
    const [partners, setPartners] = useState([]);
    const [loading, setLoading] = useState(true);
    const [savingId, setSavingId] = useState(null);

    useEffect(() => {
        if (!user?.customerId || !token) { setLoading(false); return; }
        api.getConsents(user.customerId, token)
            .then(data => setPartners(Array.isArray(data) ? data : []))
            .catch(err => console.error('Failed to load consents', err))
            .finally(() => setLoading(false));
    }, [user, token]);

    const revokeConsent = async (consentId) => {
        setSavingId(consentId);
        try {
            await api.revokeConsent(user.customerId, consentId, token);
            setPartners(prev => prev.filter(p => p.id !== consentId));
        } catch (err) {
            console.error('Failed to revoke consent', err);
        } finally { setSavingId(null); }
    };

    return (
        <div>
            <div style={{ textAlign: 'center', padding: '20px 0 32px' }}>
                <div style={{
                    width: 56, height: 56, margin: '0 auto 16px', background: 'var(--gray-800)',
                    border: '1px solid rgba(16,185,129,0.3)', borderRadius: '50%',
                    display: 'flex', alignItems: 'center', justifyContent: 'center'
                }}>
                    <Shield size={24} color="var(--brand-400)" />
                </div>
                <h2>Data Privacy &amp; Consent</h2>
                <p style={{ marginTop: 8, fontSize: '0.85rem', maxWidth: 300, margin: '8px auto 0' }}>
                    Control which partners can access your credit score and reports.
                </p>
            </div>

            <div style={{
                background: 'rgba(59,130,246,0.08)', border: '1px solid rgba(59,130,246,0.2)',
                borderRadius: 12, padding: 16, display: 'flex', gap: 12, marginBottom: 24,
            }}>
                <Globe size={18} color="var(--blue-400)" style={{ flexShrink: 0, marginTop: 2 }} />
                <div>
                    <h4 style={{ fontSize: '0.875rem', color: 'var(--blue-400)' }}>Open Finance Ready</h4>
                    <p style={{ fontSize: '0.75rem', marginTop: 4, color: 'var(--gray-300)' }}>
                        Athena uses secure, tokenized API access. Partners never see your raw financial data
                        unless you explicitly grant "Full Report" access.
                    </p>
                </div>
            </div>

            <h3 style={{ fontSize: '1rem', marginBottom: 12 }}>Active Consents</h3>

            {loading ? (
                <div style={{ textAlign: 'center', padding: '30px', color: 'var(--gray-500)', background: 'var(--gray-800)', borderRadius: 12 }}>
                    <p style={{ fontSize: '0.85rem' }}>Loading consents…</p>
                </div>
            ) : partners.length === 0 ? (
                <div style={{ textAlign: 'center', padding: '30px', color: 'var(--gray-500)', background: 'var(--gray-800)', borderRadius: 12 }}>
                    <Key size={24} style={{ opacity: 0.4, marginBottom: 8 }} />
                    <p style={{ fontSize: '0.85rem' }}>No active partners</p>
                </div>
            ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                    {partners.map(p => (
                        <div key={p.id} className="client-card" style={{ padding: 16 }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                <div>
                                    <div style={{ fontWeight: 600, fontSize: '0.9rem' }}>{p.name}</div>
                                    <div style={{ fontSize: '0.72rem', color: 'var(--gray-500)', marginTop: 2 }}>
                                        Granted: {p.granted}
                                    </div>
                                </div>
                                <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                                    <span className={`badge ${p.scope === 'FULL_REPORT' ? 'badge-yellow' : 'badge-blue'}`}>
                                        {p.scope === 'FULL_REPORT' ? 'Full Report' : 'Score Only'}
                                    </span>
                                    <button
                                        className="toggle on"
                                        onClick={() => revokeConsent(p.id)}
                                        disabled={savingId === p.id}
                                        title="Revoke access"
                                    />
                                </div>
                            </div>
                        </div>
                    ))}
                </div>
            )}

            <div style={{ marginTop: 24, fontSize: '0.75rem', color: 'var(--gray-500)', textAlign: 'center' }}>
                <ShieldAlert size={12} style={{ marginRight: 6, verticalAlign: 'middle' }} />
                Revoking access prevents future data sharing, but does not delete data already retrieved by the partner.
            </div>
        </div>
    );
}
