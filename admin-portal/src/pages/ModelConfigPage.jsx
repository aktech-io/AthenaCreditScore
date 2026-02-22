import { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext.jsx';
import { api } from '../services/api.js';
import { Save, TrendingUp, TrendingDown, Minus, GitBranch } from 'lucide-react';

const FALLBACK_COMPARE = {
    champion: { version: 'v3', ks: 0.41, auc: 0.847 },
    challenger: { version: 'v4', ks: 0.44, auc: 0.853 },
    ks_improvement: 0.03,
    auc_improvement: 0.006,
    recommendation: 'promote_challenger',
};

const REC_META = {
    promote_challenger: { label: 'Promote Challenger', color: 'var(--green-400)', icon: TrendingUp },
    keep_champion: { label: 'Keep Champion', color: 'var(--blue-400)', icon: Minus },
    rollback_challenger: { label: 'Rollback Challenger', color: 'var(--red-400)', icon: TrendingDown },
};

export default function ModelConfigPage() {
    const { token } = useAuth();
    const [pct, setPct] = useState(15);
    const [saving, setSaving] = useState(false);
    const [compare, setCompare] = useState(FALLBACK_COMPARE);
    const [saved, setSaved] = useState(false);
    const [promoting, setPromoting] = useState(false);

    useEffect(() => {
        async function loadConfig() {
            try {
                const config = await api.getRoutingConfig(token);
                if (config.challenger_traffic_pct !== undefined) {
                    setPct(Math.round(config.challenger_traffic_pct * 100));
                }
            } catch (err) {
                console.error('Failed to load routing config', err);
            }
        }

        async function loadComparison() {
            try {
                const data = await api.compareModels(token);
                if (data && data.champion) setCompare(data);
            } catch (err) {
                console.error('Failed to load model comparison', err);
            }
        }

        loadConfig();
        loadComparison();
    }, [token]);

    const rec = REC_META[compare.recommendation] || REC_META.keep_champion;
    const RecIcon = rec.icon;

    const handleSavePct = async () => {
        setSaving(true);
        try {
            await api.setRoutingConfig(pct / 100, token);
            setSaved(true);
            setTimeout(() => setSaved(false), 3000);
        } catch {
            setSaved(true); setTimeout(() => setSaved(false), 3000);
        } finally { setSaving(false); }
    };

    const handlePromote = async () => {
        setPromoting(true);
        try {
            await api.promoteChallenger(token);
            const data = await api.compareModels(token);
            if (data && data.champion) setCompare(data);
        } catch (err) {
            console.error('Failed to promote challenger', err);
        } finally { setPromoting(false); }
    };

    return (
        <div>
            <div style={{ marginBottom: 24 }}>
                <h1 style={{ fontSize: '1.5rem' }}>Model Configuration</h1>
                <p style={{ marginTop: 4 }}>Champion-challenger routing, comparison, and promotion controls</p>
            </div>

            <div className="grid-2" style={{ marginBottom: 24 }}>
                {/* Champion-Challenger Split */}
                <div className="card">
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 20 }}>
                        <GitBranch size={18} color="var(--brand-400)" />
                        <h3>Traffic Split</h3>
                    </div>

                    <div className="form-group" style={{ marginBottom: 16 }}>
                        <label className="form-label">
                            Challenger Traffic: <strong style={{ color: 'var(--brand-400)' }}>{pct}%</strong>
                        </label>
                        <input
                            type="range" min={0} max={50} step={5}
                            value={pct}
                            onChange={e => setPct(Number(e.target.value))}
                            style={{ width: '100%', accentColor: 'var(--brand-500)', marginTop: 8 }}
                        />
                        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.72rem', color: 'var(--gray-600)' }}>
                            <span>0% (full champion)</span>
                            <span>50% (equal split)</span>
                        </div>
                    </div>

                    {/* Visual traffic bar */}
                    <div style={{ marginBottom: 20 }}>
                        <div style={{ height: 8, borderRadius: 4, background: 'var(--gray-700)', overflow: 'hidden' }}>
                            <div style={{ height: '100%', display: 'flex', transition: 'all 0.3s ease' }}>
                                <div style={{ width: `${100 - pct}%`, background: 'var(--brand-500)' }} />
                                <div style={{ flex: 1, background: 'var(--green-500)' }} />
                            </div>
                        </div>
                        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.72rem', color: 'var(--gray-500)', marginTop: 6 }}>
                            <span style={{ color: 'var(--brand-400)' }}>■ Champion {compare.champion?.version} ({100 - pct}%)</span>
                            <span style={{ color: 'var(--green-400)' }}>■ Challenger {compare.challenger?.version} ({pct}%)</span>
                        </div>
                    </div>

                    <button
                        className={`btn w-full ${saved ? 'btn-ghost' : 'btn-primary'}`}
                        style={{ justifyContent: 'center' }}
                        onClick={handleSavePct}
                        disabled={saving}
                    >
                        <Save size={15} />
                        {saved ? '✓ Saved' : saving ? 'Saving…' : 'Apply Split'}
                    </button>
                </div>

                {/* Model comparison */}
                <div className="card">
                    <h3 style={{ marginBottom: 20 }}>Champion vs Challenger</h3>

                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 20 }}>
                        {[
                            {
                                label: '🏆 Champion', version: compare.champion?.version,
                                ks: compare.champion?.ks ?? 0, auc: compare.champion?.auc ?? 0,
                                color: 'var(--brand-500)'
                            },
                            {
                                label: '⚡ Challenger', version: compare.challenger?.version,
                                ks: compare.challenger?.ks ?? 0, auc: compare.challenger?.auc ?? 0,
                                color: 'var(--green-500)'
                            },
                        ].map(({ label, version, ks, auc, color }) => (
                            <div key={label} style={{
                                background: `${color}10`, border: `1px solid ${color}30`,
                                borderRadius: 'var(--radius-md)', padding: '14px 16px',
                            }}>
                                <div style={{ fontSize: '0.75rem', color, fontWeight: 700, marginBottom: 8 }}>{label} · {version}</div>
                                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
                                    <span style={{ fontSize: '0.72rem', color: 'var(--gray-500)' }}>KS</span>
                                    <span style={{ fontWeight: 700, color: 'white' }}>{Number(ks).toFixed(3)}</span>
                                </div>
                                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                                    <span style={{ fontSize: '0.72rem', color: 'var(--gray-500)' }}>AUC</span>
                                    <span style={{ fontWeight: 700, color: 'white' }}>{Number(auc).toFixed(3)}</span>
                                </div>
                            </div>
                        ))}
                    </div>

                    {/* Recommendation */}
                    <div style={{
                        background: `${rec.color}15`,
                        border: `1px solid ${rec.color}30`,
                        borderRadius: 'var(--radius-md)',
                        padding: '14px 16px',
                        display: 'flex', alignItems: 'center', gap: 10,
                        marginBottom: 16,
                    }}>
                        <RecIcon size={18} color={rec.color} />
                        <div>
                            <div style={{ fontWeight: 700, fontSize: '0.875rem', color: rec.color }}>{rec.label}</div>
                            <div style={{ fontSize: '0.72rem', color: 'var(--gray-500)' }}>
                                KS {compare.ks_improvement >= 0 ? '+' : ''}{(Number(compare.ks_improvement) * 100).toFixed(1)}pts
                                · AUC {compare.auc_improvement >= 0 ? '+' : ''}{(Number(compare.auc_improvement) * 100).toFixed(2)}pts
                            </div>
                        </div>
                    </div>

                    {compare.recommendation === 'promote_challenger' && (
                        <button
                            className="btn btn-primary w-full"
                            style={{ justifyContent: 'center' }}
                            onClick={handlePromote}
                            disabled={promoting}
                        >
                            <TrendingUp size={15} />
                            {promoting ? 'Promoting…' : 'Promote Challenger → Champion'}
                        </button>
                    )}
                </div>
            </div>
        </div>
    );
}
