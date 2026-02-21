import { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext.jsx';
import { api } from '../services/api.js';
import { Download, AlertCircle, TrendingDown, HelpCircle, Loader2 } from 'lucide-react';

const Section = ({ title, children }) => (
    <div className="client-card" style={{ marginBottom: 16 }}>
        <h3 style={{ marginBottom: 16, fontSize: '1rem', color: 'white' }}>{title}</h3>
        {children}
    </div>
);

const Row = ({ label, value, highlight }) => (
    <div className="breakdown-row">
        <span className="breakdown-label">{label}</span>
        <span className="breakdown-pts" style={{ color: highlight ? 'var(--brand-400)' : 'white' }}>
            {value}
        </span>
    </div>
);

export default function ReportPage() {
    const { user, token } = useAuth();
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');

    useEffect(() => {
        async function loadReport() {
            try {
                if (user?.customerId && token) {
                    const res = await api.getReport(user.customerId, token);
                    setData(res);
                }
            } catch (err) {
                setError('Failed to load credit report: ' + err.message);
            } finally {
                setLoading(false);
            }
        }
        loadReport();
    }, [user, token]);

    if (loading) return (
        <div style={{ display: 'flex', justifyContent: 'center', padding: '100px 0' }}>
            <Loader2 className="animate-spin" size={32} color="var(--brand-500)" />
        </div>
    );

    if (error) return <div style={{ color: 'var(--red-400)', textAlign: 'center', marginTop: 40 }}>{error}</div>;
    if (!data) return <div style={{ textAlign: 'center', marginTop: 40 }}>No report found.</div>;

    const scoredDate = data.scored_at ? new Date(data.scored_at).toLocaleDateString() : 'N/A';

    return (
        <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 20 }}>
                <div>
                    <h2>Full Credit Report</h2>
                    <p style={{ marginTop: 4, fontSize: '0.8rem' }}>
                        Detailed breakdown of your credit file as of {scoredDate}
                    </p>
                </div>
                <button className="btn btn-ghost btn-sm" style={{ padding: '8px' }}>
                    <Download size={16} />
                </button>
            </div>

            <Section title="Application Context">
                <Row label="Customer ID" value={data.customer_id} />
                <Row label="Phone Number" value={data.phone || 'Unknown'} />
                <Row label="Business Sector" value={data.sector || 'Missing'} />
                <Row label="Capital Growth Ratio" value={`${((data.capital_growth_ratio || 0) * 100).toFixed(1)}%`} />
                <Row label="Est. Revenue / Employee" value={`KES ${(data.revenue_per_employee || 0).toLocaleString()}`} />
                <Row label="Est. Profit Margin" value={`${((data.profit_margin || 0) * 100).toFixed(1)}%`} highlight />
            </Section>

            <Section title="Repayment History (Internal)">
                <Row label="90-Day Delinquency Rate" value={`${((data.delinquency_rate_90d || 0) * 100).toFixed(1)}%`} />
                <Row label="Max Consecutive Late Payments" value={data.max_delinquency_streak || 0} />
                {(data.delinquency_rate_90d > 0 || data.max_delinquency_streak > 0) && (
                    <div style={{
                        display: 'flex', gap: 8, marginTop: 12, padding: 12,
                        background: 'rgba(244,63,94,0.1)', borderRadius: 8, color: 'var(--red-400)', fontSize: '0.8rem'
                    }}>
                        <TrendingDown size={14} style={{ flexShrink: 0, marginTop: 2 }} />
                        Late payments severely impact your score. Consistent on-time payments will gradually improve this metric.
                    </div>
                )}
            </Section>

            <Section title="Credit Reference Bureau (CRB)">
                <Row label="Bureau Score Override" value={data.crb_bureau_score || 'Not Found'} />
                <Row label="Non-Performing Accounts (NPA)" value={data.crb_npa_count || 0} />
                <Row label="Active Default Status" value={data.crb_active_default ? 'YES ⚠' : 'CLEAR'} />
                {data.crb_active_default && (
                    <div style={{
                        display: 'flex', gap: 8, marginTop: 12, padding: 12,
                        background: 'rgba(251,191,36,0.1)', borderRadius: 8, color: 'var(--yellow-400)', fontSize: '0.8rem'
                    }}>
                        <AlertCircle size={14} style={{ flexShrink: 0, marginTop: 2 }} />
                        An active default restricts access to near-prime credit bands. Clear outstanding defaults to improve eligibility.
                    </div>
                )}
            </Section>

            <Section title="AI Analyst Synopsis">
                <div style={{
                    padding: 16, background: 'rgba(16,185,129,0.06)', border: '1px solid rgba(16,185,129,0.2)',
                    borderRadius: 'var(--radius-md)', fontSize: '0.9rem', color: 'var(--gray-300)', fontStyle: 'italic', lineHeight: 1.6
                }}>
                    {data.llm_reasoning ? `"${data.llm_reasoning}"` : "AI synopsis is currently generating or unavailable."}
                </div>
            </Section>

            <div style={{ textAlign: 'center', marginTop: 32, marginBottom: 16 }}>
                <p style={{ fontSize: '0.8rem', color: 'var(--gray-500)', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6 }}>
                    <HelpCircle size={14} /> Notice missing or incorrect data?
                </p>
                <button className="btn btn-ghost btn-sm" style={{ marginTop: 8 }} onClick={() => window.location.href = '/disputes'}>
                    File a Dispute
                </button>
            </div>
        </div>
    );
}
