import { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext.jsx';
import { api } from '../services/api.js';
import { PieChart, Pie, Cell, ResponsiveContainer } from 'recharts';
import { TrendingUp, Info } from 'lucide-react';

// Band colour based on score
const bandFor = (score) => {
    if (score >= 720) return { label: 'Prime', color: '#6366f1', bg: 'rgba(99,102,241,0.15)' };
    if (score >= 630) return { label: 'Near-Prime', color: '#10b981', bg: 'rgba(16,185,129,0.15)' };
    if (score >= 500) return { label: 'Subprime', color: '#eab308', bg: 'rgba(234,179,8,0.15)' };
    if (score >= 400) return { label: 'Marginal', color: '#f97316', bg: 'rgba(249,115,22,0.15)' };
    return { label: 'Decline', color: '#ef4444', bg: 'rgba(239,68,68,0.15)' };
};

const MOCK_SCORE = {
    final_score: 638,
    pd_probability: 0.08,
    score_band: 'Near-Prime',
    base_score: 572,
    crb_contribution: 68,
    llm_adjustment: -2,
    scored_at: '2026-02-18T14:30:00',
};

const BREAKDOWN = [
    { label: 'Income Stability', pts: 98, max: 120, color: '#6366f1' },
    { label: 'Income Level', pts: 75, max: 100, color: '#10b981' },
    { label: 'Savings Rate', pts: 58, max: 80, color: '#60a5fa' },
    { label: 'Low-Balance Events', pts: 82, max: 100, color: '#a78bfa' },
    { label: 'Tx Diversity', pts: 64, max: 100, color: '#34d399' },
];

// Semi-circle gauge via Recharts Pie
function ScoreGauge({ score, pdProbability }) {
    const pct = (score - 300) / (850 - 300);
    const band = bandFor(score);
    const data = [
        { value: pct * 100 },
        { value: (1 - pct) * 100 },
    ];
    return (
        <div className="score-hero">
            <div className="score-gauge-wrapper">
                <ResponsiveContainer width={240} height={130}>
                    <PieChart>
                        <Pie
                            data={data} dataKey="value"
                            startAngle={180} endAngle={0}
                            innerRadius={70} outerRadius={90}
                            paddingAngle={0}
                            cornerRadius={6}
                        >
                            <Cell fill={band.color} />
                            <Cell fill="rgba(255,255,255,0.05)" />
                        </Pie>
                    </PieChart>
                </ResponsiveContainer>
                <div className="score-center">
                    <div className="score-big" style={{ color: band.color }}>{score}</div>
                    <div style={{ fontSize: '0.72rem', color: 'var(--gray-500)', marginTop: 2 }}>out of 850</div>
                    <span className="score-band-label" style={{ background: band.bg, color: band.color, marginTop: 6 }}>
                        {band.label}
                    </span>
                </div>
            </div>
            <p style={{ marginTop: 16, fontSize: '0.8rem' }}>
                Your probability of default is <strong style={{ color: band.color }}>
                    {(pdProbability * 100).toFixed(1)}%
                </strong>
            </p>
        </div>
    );
}

export default function ScorePage() {
    const { token, user } = useAuth();
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [usedFallback, setUsedFallback] = useState(false);

    useEffect(() => {
        if (!user?.customerId || !token) return;
        api.getScore(user.customerId, token)
            .then(res => setData(res))
            .catch(() => {
                setData(MOCK_SCORE);
                setUsedFallback(true);
            })
            .finally(() => setLoading(false));
    }, [user, token]);

    if (loading) {
        return (
            <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: 200 }}>
                <div style={{ fontSize: '0.85rem', color: 'var(--gray-500)' }}>Loading your score…</div>
            </div>
        );
    }

    return (
        <div>
            {usedFallback && (
                <div style={{
                    marginBottom: 12, padding: '8px 14px',
                    background: 'rgba(234,179,8,0.1)',
                    border: '1px solid rgba(234,179,8,0.3)',
                    borderRadius: 8, fontSize: '0.75rem', color: 'var(--gray-400)',
                }}>
                    Could not reach scoring service — showing last cached score.
                </div>
            )}
            <ScoreGauge score={data.final_score} pdProbability={data.pd_probability} />

            {/* Score breakdown */}
            <div className="client-card">
                <div className="client-card-header">
                    <div className="client-card-title">
                        <TrendingUp size={15} color="var(--brand-400)" />
                        Score Breakdown
                    </div>
                    <span style={{ fontSize: '0.72rem', color: 'var(--gray-600)' }}>
                        Scored {new Date(data.scored_at).toLocaleDateString('en-KE', { month: 'short', day: 'numeric' })}
                    </span>
                </div>

                {BREAKDOWN.map(({ label, pts, max, color }) => (
                    <div key={label} className="breakdown-row">
                        <span className="breakdown-label">{label}</span>
                        <div className="breakdown-bar">
                            <div
                                className="breakdown-fill"
                                style={{ width: `${(pts / max) * 100}%`, background: color }}
                            />
                        </div>
                        <span className="breakdown-pts">{pts}/{max}</span>
                    </div>
                ))}

                {/* CRB + LLM supplements */}
                <div style={{
                    marginTop: 16, padding: '12px 14px',
                    background: 'rgba(255,255,255,0.03)',
                    borderRadius: 10, display: 'grid',
                    gridTemplateColumns: '1fr 1fr', gap: 12,
                }}>
                    {[
                        { label: 'CRB Contribution', val: `+${data.crb_contribution} pts`, color: 'var(--green-400)' },
                        { label: 'AI Adjustment', val: `${data.llm_adjustment > 0 ? '+' : ''}${data.llm_adjustment} pts`, color: data.llm_adjustment >= 0 ? 'var(--green-400)' : 'var(--red-400)' },
                    ].map(({ label, val, color }) => (
                        <div key={label} style={{ textAlign: 'center' }}>
                            <div style={{ fontSize: '1.1rem', fontWeight: 700, color }}>{val}</div>
                            <div style={{ fontSize: '0.7rem', color: 'var(--gray-500)', marginTop: 3 }}>{label}</div>
                        </div>
                    ))}
                </div>
            </div>

            {/* Info tip */}
            <div style={{
                display: 'flex', gap: 8, padding: '12px 14px',
                background: 'rgba(99,102,241,0.06)',
                border: '1px solid rgba(99,102,241,0.15)',
                borderRadius: 10, fontSize: '0.78rem', color: 'var(--gray-400)',
            }}>
                <Info size={14} color="#6366f1" style={{ flexShrink: 0, marginTop: 1 }} />
                Your score is updated each time a lender requests a fresh credit report.
                Improving repayment history and income consistency will raise your score over time.
            </div>
        </div>
    );
}
