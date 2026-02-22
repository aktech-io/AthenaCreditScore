import { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext.jsx';
import { api } from '../services/api.js';
import { Search, RefreshCw, ChevronRight } from 'lucide-react';
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';

const SCORE_BAND = (score) => {
    if (score >= 720) return { label: 'Prime', cls: 'badge-blue' };
    if (score >= 630) return { label: 'Near-Prime', cls: 'badge-green' };
    if (score >= 500) return { label: 'Subprime', cls: 'badge-yellow' };
    if (score >= 400) return { label: 'Marginal', cls: 'badge-red' };
    return { label: 'Decline', cls: 'badge-gray' };
};

// Mock customers as fallback
const MOCK = [
    { id: 101, name: 'Jane Wanjiru', phone: '+254711223344', score: 672, pd: 0.09, sector: 'Retail' },
    { id: 102, name: 'Peter Otieno', phone: '+254722334455', score: 498, pd: 0.31, sector: 'Agriculture' },
    { id: 103, name: 'Amina Khalid', phone: '+254733445566', score: 735, pd: 0.05, sector: 'Healthcare' },
    { id: 104, name: 'Brian Kiptoo', phone: '+254744556677', score: 381, pd: 0.67, sector: 'Transport' },
    { id: 105, name: 'Grace Muthoni', phone: '+254755667788', score: 551, pd: 0.22, sector: 'Food & Hospitality' },
];

export default function CustomerSearchPage() {
    const { token } = useAuth();
    const [query, setQuery] = useState('');
    const [results, setResults] = useState(MOCK);
    const [selected, setSelected] = useState(null);
    const [reportData, setReportData] = useState(null);
    const [scoreHistory, setScoreHistory] = useState([]);
    const [loadingReport, setLoadingReport] = useState(false);
    const [rescoring, setRescoring] = useState(false);
    const [loading, setLoading] = useState(false);

    useEffect(() => {
        if (!selected) {
            setReportData(null);
            setScoreHistory([]);
            return;
        }
        const customerId = selected.id || selected.customer_id;
        async function loadDetails() {
            setLoadingReport(true);
            try {
                const [report, history] = await Promise.all([
                    api.getFullReport(customerId, token),
                    api.getCreditScoreHistory(customerId, token).catch(() => ({ data: [] })),
                ]);
                setReportData(report);
                const histData = history?.data || [];
                setScoreHistory(histData.slice(0, 6).reverse());
            } catch (err) {
                console.error('Failed to load report', err);
            } finally {
                setLoadingReport(false);
            }
        }
        loadDetails();
    }, [selected, token]);

    useEffect(() => {
        async function loadInitial() {
            setLoading(true);
            try {
                const data = await api.searchCustomers('', token);
                setResults(data);
            } catch (err) {
                console.error('Failed to load initial customers', err);
            } finally {
                setLoading(false);
            }
        }
        loadInitial();
    }, [token]);

    const handleSearch = async (e) => {
        e.preventDefault();
        setLoading(true);
        try {
            const data = await api.searchCustomers(query, token);
            setResults(data);
        } catch {
            console.error('Failed to search customers');
        } finally { setLoading(false); }
    };

    const handleRescore = async (id) => {
        setRescoring(true);
        try {
            await api.triggerRescore(id, token);
            alert('Scoring run triggered. Results will be available shortly.');
        } catch (err) {
            alert('Re-score triggered (mock): ' + err.message);
        } finally { setRescoring(false); }
    };

    return (
        <div>
            <div style={{ marginBottom: 24 }}>
                <h1 style={{ fontSize: '1.5rem' }}>Customer Search</h1>
                <p style={{ marginTop: 4 }}>Search customers, view credit scores and full reports</p>
            </div>

            {/* Search bar */}
            <form onSubmit={handleSearch} style={{ display: 'flex', gap: 10, marginBottom: 20 }}>
                <div style={{ position: 'relative', flex: 1 }}>
                    <Search size={16} style={{
                        position: 'absolute', left: 12, top: '50%',
                        transform: 'translateY(-50%)', color: 'var(--gray-500)',
                    }} />
                    <input
                        id="customer-search"
                        className="form-input w-full"
                        style={{ paddingLeft: 38 }}
                        placeholder="Search by name, phone, or ID…"
                        value={query}
                        onChange={e => setQuery(e.target.value)}
                    />
                </div>
                <button type="submit" className="btn btn-primary" disabled={loading}>
                    {loading ? 'Searching…' : 'Search'}
                </button>
            </form>

            {/* Results table */}
            <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
                <div className="table-wrapper">
                    <table>
                        <thead>
                            <tr>
                                <th>Customer</th>
                                <th>Sector</th>
                                <th>Credit Score</th>
                                <th>PD</th>
                                <th>Band</th>
                                <th></th>
                            </tr>
                        </thead>
                        <tbody>
                            {results.map(c => {
                                const band = SCORE_BAND(c.score);
                                return (
                                    <tr key={c.id} style={{ cursor: 'pointer' }} onClick={() => setSelected(c)}>
                                        <td>
                                            <div style={{ fontWeight: 600, color: 'white', fontSize: '0.875rem' }}>{c.name}</div>
                                            <div style={{ fontSize: '0.72rem', color: 'var(--gray-500)' }}>{c.phone} · ID {c.id}</div>
                                        </td>
                                        <td>{c.sector}</td>
                                        <td>
                                            <span style={{ fontWeight: 700, fontSize: '1rem', color: 'white' }}>{c.score}</span>
                                        </td>
                                        <td>
                                            <span style={{ color: c.pd > 0.3 ? 'var(--red-400)' : c.pd > 0.15 ? 'var(--yellow-400)' : 'var(--green-400)' }}>
                                                {(c.pd * 100).toFixed(1)}%
                                            </span>
                                        </td>
                                        <td><span className={`badge ${band.cls}`}>{band.label}</span></td>
                                        <td><ChevronRight size={15} color="var(--gray-600)" /></td>
                                    </tr>
                                );
                            })}
                        </tbody>
                    </table>
                </div>
            </div>

            {/* Customer detail slide-in */}
            {selected && (
                <div style={{
                    position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.6)',
                    backdropFilter: 'blur(4px)', zIndex: 200, display: 'flex',
                    justifyContent: 'flex-end',
                }} onClick={() => setSelected(null)}>
                    <div style={{
                        width: 420, height: '100%',
                        background: 'var(--gray-800)', padding: 28,
                        overflow: 'auto', animation: 'fadeIn 0.2s ease',
                        borderLeft: '1px solid rgba(255,255,255,0.08)',
                    }} onClick={e => e.stopPropagation()}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
                            <h3>{selected.name}</h3>
                            <button className="btn btn-ghost btn-sm" onClick={() => setSelected(null)}>✕</button>
                        </div>

                        <div style={{ textAlign: 'center', marginBottom: 24 }}>
                            <div style={{
                                fontSize: '3rem', fontWeight: 800,
                                background: 'linear-gradient(135deg, #6366f1, #a78bfa)',
                                WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent',
                            }}>
                                {selected.score}
                            </div>
                            <div style={{ fontSize: '0.8rem', color: 'var(--gray-500)', marginTop: 4 }}>Credit Score</div>
                            <span className={`badge ${SCORE_BAND(selected.score).cls}`} style={{ marginTop: 8 }}>
                                {SCORE_BAND(selected.score).label}
                            </span>
                        </div>

                        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 20 }}>
                            {[
                                { label: 'Customer ID', value: selected.id },
                                { label: 'Phone', value: selected.phone },
                                { label: 'Sector', value: selected.sector },
                                { label: 'PD', value: `${(selected.pd * 100).toFixed(1)}%` },
                            ].map(({ label, value }) => (
                                <div key={label} style={{
                                    background: 'rgba(255,255,255,0.03)', borderRadius: 'var(--radius-md)',
                                    padding: '12px 14px', border: '1px solid rgba(255,255,255,0.06)',
                                }}>
                                    <div style={{ fontSize: '0.7rem', color: 'var(--gray-500)', marginBottom: 4 }}>{label}</div>
                                    <div style={{ fontSize: '0.875rem', fontWeight: 600, color: 'white' }}>{value}</div>
                                </div>
                            ))}
                        </div>

                        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                            <button
                                className="btn btn-primary w-full"
                                style={{ justifyContent: 'center' }}
                                disabled={rescoring}
                                onClick={() => handleRescore(selected.id)}
                            >
                                <RefreshCw size={15} />
                                {rescoring ? 'Triggering…' : 'Trigger Re-score'}
                            </button>
                        </div>

                        {loadingReport && <div style={{ textAlign: 'center', marginTop: 30, color: 'var(--gray-500)' }}>Loading full credit history...</div>}

                        {reportData && !loadingReport && (
                            <div style={{ marginTop: 32, borderTop: '1px solid rgba(255,255,255,0.08)', paddingTop: 24, animation: 'fadeIn 0.3s ease' }}>
                                <h4 style={{ marginBottom: 16 }}>Detailed Credit History</h4>

                                {/* Score history chart */}
                                {scoreHistory.length > 1 && (
                                    <div style={{ marginBottom: 20 }}>
                                        <div style={{ fontSize: '0.75rem', color: 'var(--gray-500)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 8 }}>Score Trend</div>
                                        <ResponsiveContainer width="100%" height={100}>
                                            <AreaChart data={scoreHistory} margin={{ top: 4, right: 4, bottom: 0, left: -20 }}>
                                                <defs>
                                                    <linearGradient id="scoreGrad" x1="0" y1="0" x2="0" y2="1">
                                                        <stop offset="5%" stopColor="#6366f1" stopOpacity={0.3} />
                                                        <stop offset="95%" stopColor="#6366f1" stopOpacity={0} />
                                                    </linearGradient>
                                                </defs>
                                                <XAxis
                                                    dataKey="scored_at"
                                                    tickFormatter={v => v ? new Date(v).toLocaleDateString('en-KE', { month: 'short', day: 'numeric' }) : ''}
                                                    tick={{ fontSize: 9, fill: 'var(--gray-600)' }}
                                                />
                                                <YAxis domain={[300, 850]} tick={{ fontSize: 9, fill: 'var(--gray-600)' }} />
                                                <Tooltip
                                                    contentStyle={{ background: 'var(--gray-800)', border: '1px solid rgba(255,255,255,0.1)', fontSize: '0.75rem' }}
                                                    formatter={v => [v, 'Score']}
                                                    labelFormatter={v => v ? new Date(v).toLocaleDateString() : ''}
                                                />
                                                <Area type="monotone" dataKey="final_score" stroke="#6366f1" fill="url(#scoreGrad)" strokeWidth={2} dot={false} />
                                            </AreaChart>
                                        </ResponsiveContainer>
                                    </div>
                                )}

                                <div style={{ marginBottom: 20 }}>
                                    <div style={{ fontSize: '0.75rem', color: 'var(--gray-500)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 8 }}>Application Ratios</div>
                                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                                        <div style={{ background: 'rgba(0,0,0,0.2)', padding: 10, borderRadius: 8 }}>
                                            <div style={{ fontSize: '0.7rem', color: 'var(--gray-400)' }}>Cap Growth</div>
                                            <div style={{ fontWeight: 600 }}>{((reportData.capital_growth_ratio || 0) * 100).toFixed(1)}%</div>
                                        </div>
                                        <div style={{ background: 'rgba(0,0,0,0.2)', padding: 10, borderRadius: 8 }}>
                                            <div style={{ fontSize: '0.7rem', color: 'var(--gray-400)' }}>Profit Margin</div>
                                            <div style={{ fontWeight: 600, color: 'var(--brand-400)' }}>{((reportData.profit_margin || 0) * 100).toFixed(1)}%</div>
                                        </div>
                                    </div>
                                </div>

                                <div style={{ marginBottom: 20 }}>
                                    <div style={{ fontSize: '0.75rem', color: 'var(--gray-500)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 8 }}>Internal Repayment</div>
                                    <div style={{ background: 'rgba(0,0,0,0.2)', padding: 12, borderRadius: 8 }}>
                                        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
                                            <span style={{ fontSize: '0.8rem', color: 'var(--gray-400)' }}>90-Day Delinquency</span>
                                            <span style={{ fontWeight: 600, color: reportData.delinquency_rate_90d > 0.1 ? 'var(--red-400)' : 'white' }}>{((reportData.delinquency_rate_90d || 0) * 100).toFixed(1)}%</span>
                                        </div>
                                        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                                            <span style={{ fontSize: '0.8rem', color: 'var(--gray-400)' }}>Max Consecutive Missed</span>
                                            <span style={{ fontWeight: 600 }}>{reportData.max_delinquency_streak || 0}</span>
                                        </div>
                                    </div>
                                </div>

                                <div style={{ marginBottom: 20 }}>
                                    <div style={{ fontSize: '0.75rem', color: 'var(--gray-500)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 8 }}>CRB Data</div>
                                    <div style={{ background: 'rgba(0,0,0,0.2)', padding: 12, borderRadius: 8 }}>
                                        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
                                            <span style={{ fontSize: '0.8rem', color: 'var(--gray-400)' }}>Bureau Score</span>
                                            <span style={{ fontWeight: 600 }}>{reportData.crb_bureau_score || 'N/A'}</span>
                                        </div>
                                        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                                            <span style={{ fontSize: '0.8rem', color: 'var(--gray-400)' }}>Active Defaults</span>
                                            <span style={{ fontWeight: 600, color: reportData.crb_active_default ? 'var(--orange-500)' : 'var(--green-400)' }}>
                                                {reportData.crb_active_default ? 'YES' : 'NONE'}
                                            </span>
                                        </div>
                                    </div>
                                </div>

                                <div>
                                    <div style={{ fontSize: '0.75rem', color: 'var(--gray-500)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 8 }}>AI Analyst Synopsis</div>
                                    <div style={{ padding: 12, background: 'rgba(99,102,241,0.08)', borderLeft: '3px solid var(--brand-500)', borderRadius: '0 8px 8px 0', fontSize: '0.8rem', color: 'var(--gray-300)', fontStyle: 'italic', lineHeight: 1.5 }}>
                                        "{reportData.llm_reasoning || 'No analysis available.'}"
                                    </div>
                                </div>
                            </div>
                        )}
                    </div>
                </div>
            )}
        </div>
    );
}
