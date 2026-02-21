import { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext.jsx';
import {
    RadialBarChart, RadialBar, PieChart, Pie, Cell,
    AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid,
} from 'recharts';
import { TrendingUp, TrendingDown, Users, AlertTriangle, Activity, Zap } from 'lucide-react';
import { api } from '../services/api.js';

// --- Mock data (replaced by api.getDashboardStats when backend is live) ---
const MOCK_STATS = {
    totalScored: 2847,
    approvalRate: 0.62,
    defaultRate: 0.087,
    ksStatistic: 0.41,
    psiValue: 0.09,
    openDisputes: 14,
    avgScore: 538,
    championVersion: 'v3',
    challengerVersion: 'v4',
    challengerPct: 0.15,
};

const SCORE_DIST = [
    { band: '300-399', count: 120, color: '#ef4444' },
    { band: '400-499', count: 340, color: '#f97316' },
    { band: '500-629', count: 980, color: '#eab308' },
    { band: '630-719', count: 890, color: '#22c55e' },
    { band: '720-850', count: 517, color: '#6366f1' },
];

const TREND_DATA = [
    { month: 'Sep', scored: 310, defaults: 28 },
    { month: 'Oct', scored: 420, defaults: 35 },
    { month: 'Nov', scored: 390, defaults: 30 },
    { month: 'Dec', scored: 510, defaults: 41 },
    { month: 'Jan', scored: 580, defaults: 48 },
    { month: 'Feb', scored: 647, defaults: 51 },
];

function StatCard({ title, value, sub, accent, icon: Icon, trend }) {
    return (
        <div className="stat-card" style={{ '--accent': accent }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <div>
                    <div className="card-title">{title}</div>
                    <div className="card-value" style={{ color: 'white', fontSize: '1.75rem', marginTop: 4 }}>{value}</div>
                    {sub && <div className="card-sub">{sub}</div>}
                </div>
                <div style={{
                    width: 40, height: 40,
                    background: `${accent}20`,
                    borderRadius: 'var(--radius-md)',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                }}>
                    <Icon size={20} color={accent} />
                </div>
            </div>
            {trend !== undefined && (
                <div style={{
                    marginTop: 12, display: 'flex', alignItems: 'center', gap: 4,
                    fontSize: '0.75rem', color: trend >= 0 ? 'var(--green-400)' : 'var(--red-400)',
                }}>
                    {trend >= 0 ? <TrendingUp size={13} /> : <TrendingDown size={13} />}
                    {Math.abs(trend)}% vs last month
                </div>
            )}
        </div>
    );
}

export default function DashboardPage() {
    const { token } = useAuth();
    const [stats, setStats] = useState(MOCK_STATS);

    useEffect(() => {
        async function loadStats() {
            try {
                const data = await api.getDashboardStats(token);
                setStats(data);
            } catch (err) {
                console.error("Failed to load dashboard stats", err);
            }
        }
        loadStats();
    }, [token]);

    const psiColor = stats.psiValue > 0.2 ? '#ef4444' : stats.psiValue > 0.1 ? '#eab308' : '#22c55e';
    const ksColor = stats.ksStatistic < 0.2 ? '#ef4444' : stats.ksStatistic < 0.3 ? '#eab308' : '#22c55e';

    return (
        <div>
            <div style={{ marginBottom: 24 }}>
                <h1 style={{ fontSize: '1.5rem' }}>Dashboard</h1>
                <p style={{ marginTop: 4, fontSize: '0.875rem' }}>
                    {new Date().toLocaleDateString('en-KE', { weekday: 'long', month: 'long', day: 'numeric', year: 'numeric' })}
                </p>
            </div>

            {/* Stat cards */}
            <div className="stats-grid">
                <StatCard title="Scored This Month" value={stats.totalScored.toLocaleString()}
                    sub="Total applications" accent="#6366f1" icon={Zap} trend={4.2} />
                <StatCard title="Approval Rate" value={`${(stats.approvalRate * 100).toFixed(1)}%`}
                    sub="30-day rolling" accent="#22c55e" icon={TrendingUp} trend={1.8} />
                <StatCard title="Default Rate" value={`${(stats.defaultRate * 100).toFixed(1)}%`}
                    sub="30-day rolling" accent="#ef4444" icon={TrendingDown} trend={-0.4} />
                <StatCard title="Open Disputes" value={stats.openDisputes}
                    sub="Pending review" accent="#f97316" icon={AlertTriangle} />
                <StatCard title="Avg Credit Score" value={stats.avgScore}
                    sub="All scored customers" accent="#60a5fa" icon={Activity} trend={2.1} />
                <StatCard title="Active Users" value="1,249"
                    sub="Registered customers" accent="#a78bfa" icon={Users} />
            </div>

            {/* Model health + score distribution */}
            <div className="grid-2" style={{ marginBottom: 24 }}>
                {/* Model health gauges */}
                <div className="chart-card">
                    <div className="chart-title">Model Health</div>
                    <div style={{ display: 'flex', justifyContent: 'space-around', alignItems: 'center', padding: '8px 0' }}>
                        {[
                            { label: 'KS Statistic', value: stats.ksStatistic, color: ksColor, max: 0.6 },
                            { label: 'PSI', value: stats.psiValue, color: psiColor, max: 0.5 },
                        ].map(({ label, value, color, max }) => (
                            <div key={label} style={{ textAlign: 'center' }}>
                                <ResponsiveContainer width={120} height={120}>
                                    <RadialBarChart
                                        innerRadius="60%" outerRadius="90%"
                                        startAngle={180} endAngle={0}
                                        data={[{ value: value / max * 100 }]}
                                    >
                                        <RadialBar dataKey="value" fill={color} background={{ fill: 'rgba(255,255,255,0.04)' }} cornerRadius={6} />
                                    </RadialBarChart>
                                </ResponsiveContainer>
                                <div style={{ fontWeight: 700, fontSize: '1.2rem', color }}>{value.toFixed(3)}</div>
                                <div style={{ fontSize: '0.72rem', color: 'var(--gray-500)', marginTop: 2 }}>{label}</div>
                            </div>
                        ))}
                        <div style={{ textAlign: 'center' }}>
                            <div style={{ fontSize: '1.4rem', fontWeight: 800, color: '#6366f1' }}>{stats.avgScore}</div>
                            <div style={{ fontSize: '0.72rem', color: 'var(--gray-500)', marginTop: 4 }}>Avg Score</div>
                            <div style={{
                                marginTop: 16, padding: '6px 12px',
                                background: 'rgba(99,102,241,0.1)',
                                borderRadius: 'var(--radius-md)',
                                fontSize: '0.75rem', color: 'var(--brand-400)',
                            }}>
                                Champion: {stats.championVersion}<br />
                                Challenger: {stats.challengerVersion} ({(stats.challengerPct * 100).toFixed(0)}%)
                            </div>
                        </div>
                    </div>
                </div>

                {/* Score distribution pie */}
                <div className="chart-card">
                    <div className="chart-title">Score Band Distribution</div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 20 }}>
                        <ResponsiveContainer width={160} height={160}>
                            <PieChart>
                                <Pie data={SCORE_DIST} dataKey="count" innerRadius={45} outerRadius={70} paddingAngle={3}>
                                    {SCORE_DIST.map((entry, i) => <Cell key={i} fill={entry.color} />)}
                                </Pie>
                            </PieChart>
                        </ResponsiveContainer>
                        <div style={{ flex: 1 }}>
                            {SCORE_DIST.map(({ band, count, color }) => (
                                <div key={band} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                                    <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                                        <div style={{ width: 8, height: 8, borderRadius: 2, background: color }} />
                                        <span style={{ fontSize: '0.78rem', color: 'var(--gray-400)' }}>{band}</span>
                                    </div>
                                    <span style={{ fontSize: '0.8rem', fontWeight: 600, color: 'white' }}>{count}</span>
                                </div>
                            ))}
                        </div>
                    </div>
                </div>
            </div>

            {/* Scoring trend chart */}
            <div className="chart-card">
                <div className="chart-title">Monthly Scoring Volume &amp; Defaults</div>
                <ResponsiveContainer width="100%" height={220}>
                    <AreaChart data={TREND_DATA} margin={{ top: 10, right: 10, bottom: 0, left: -10 }}>
                        <defs>
                            <linearGradient id="gradScored" x1="0" y1="0" x2="0" y2="1">
                                <stop offset="5%" stopColor="#6366f1" stopOpacity={0.3} />
                                <stop offset="95%" stopColor="#6366f1" stopOpacity={0} />
                            </linearGradient>
                            <linearGradient id="gradDefaults" x1="0" y1="0" x2="0" y2="1">
                                <stop offset="5%" stopColor="#ef4444" stopOpacity={0.3} />
                                <stop offset="95%" stopColor="#ef4444" stopOpacity={0} />
                            </linearGradient>
                        </defs>
                        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
                        <XAxis dataKey="month" tick={{ fontSize: 11, fill: '#64748b' }} axisLine={false} tickLine={false} />
                        <YAxis tick={{ fontSize: 11, fill: '#64748b' }} axisLine={false} tickLine={false} />
                        <Tooltip
                            contentStyle={{ background: '#1e293b', border: '1px solid rgba(255,255,255,0.08)', borderRadius: 8, fontSize: 12 }}
                            itemStyle={{ color: '#cbd5e1' }}
                        />
                        <Area type="monotone" dataKey="scored" name="Scored" stroke="#6366f1" fill="url(#gradScored)" strokeWidth={2} />
                        <Area type="monotone" dataKey="defaults" name="Defaults" stroke="#ef4444" fill="url(#gradDefaults)" strokeWidth={2} />
                    </AreaChart>
                </ResponsiveContainer>
            </div>
        </div>
    );
}
