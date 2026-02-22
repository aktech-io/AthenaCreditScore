import { useState, useEffect } from 'react';
import { Shield, User, Download } from 'lucide-react';
import { useAuth } from '../context/AuthContext.jsx';
import { api } from '../services/api.js';

const OUTCOME_CLS = {
    APPROVED: 'badge-green',
    OK: 'badge-blue',
    DENIED_NO_CONSENT: 'badge-red',
    DENIED: 'badge-red',
};

export default function AuditLogPage() {
    const { token } = useAuth();
    const [logs, setLogs] = useState([]);
    const [filter, setFilter] = useState('');
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        async function loadAuditLog() {
            try {
                const data = await api.getAuditLog(token);
                setLogs(Array.isArray(data) ? data : []);
            } catch (err) {
                console.error('Failed to load audit log', err);
            } finally {
                setLoading(false);
            }
        }
        loadAuditLog();
    }, [token]);

    const visible = filter
        ? logs.filter(l =>
            (l.action || '').toUpperCase().includes(filter) ||
            (l.outcome || '').toUpperCase().includes(filter) ||
            (l.partner || '').toUpperCase().includes(filter))
        : logs;

    const handleExportCsv = () => {
        if (logs.length === 0) return;
        const headers = ['id', 'ts', 'partner', 'customer', 'action', 'outcome', 'ip'];
        const rows = logs.map(l =>
            headers.map(h => JSON.stringify(l[h] ?? '')).join(',')
        );
        const csv = [headers.join(','), ...rows].join('\n');
        const blob = new Blob([csv], { type: 'text/csv' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `audit-log-${new Date().toISOString().slice(0, 10)}.csv`;
        a.click();
        URL.revokeObjectURL(url);
    };

    return (
        <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 24 }}>
                <div>
                    <h1 style={{ fontSize: '1.5rem' }}>Audit Log</h1>
                    <p style={{ marginTop: 4 }}>All partner data access events — tamper-evident append-only record</p>
                </div>
                <button className="btn btn-ghost btn-sm" onClick={handleExportCsv} disabled={logs.length === 0}>
                    <Download size={14} /> Export CSV
                </button>
            </div>

            <div style={{ display: 'flex', gap: 10, marginBottom: 16 }}>
                <input
                    className="form-input"
                    style={{ maxWidth: 280 }}
                    placeholder="Filter by action, partner, outcome…"
                    value={filter}
                    onChange={e => setFilter(e.target.value.toUpperCase())}
                />
                <span style={{ fontSize: '0.78rem', color: 'var(--gray-500)', alignSelf: 'center' }}>
                    {visible.length} events
                </span>
            </div>

            {loading ? (
                <div style={{ textAlign: 'center', padding: '40px', color: 'var(--gray-500)' }}>Loading audit log…</div>
            ) : (
                <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
                    <div className="table-wrapper">
                        <table>
                            <thead>
                                <tr>
                                    <th>Timestamp</th>
                                    <th>Partner</th>
                                    <th>Customer</th>
                                    <th>Action</th>
                                    <th>Outcome</th>
                                    <th>IP</th>
                                </tr>
                            </thead>
                            <tbody>
                                {visible.length === 0 ? (
                                    <tr>
                                        <td colSpan={6} style={{ textAlign: 'center', color: 'var(--gray-500)', padding: 32 }}>
                                            No audit events found
                                        </td>
                                    </tr>
                                ) : visible.map(log => (
                                    <tr key={log.id}>
                                        <td style={{ fontFamily: 'monospace', fontSize: '0.78rem', color: 'var(--gray-400)' }}>
                                            {log.ts}
                                        </td>
                                        <td>
                                            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                                                <Shield size={12} color="var(--gray-500)" />
                                                <span style={{ fontSize: '0.82rem', fontWeight: 500 }}>{log.partner}</span>
                                            </div>
                                        </td>
                                        <td>
                                            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                                                <User size={12} color="var(--gray-500)" />
                                                <span>{log.customer}</span>
                                            </div>
                                        </td>
                                        <td>
                                            <span style={{ fontFamily: 'monospace', fontSize: '0.75rem', color: 'var(--gray-300)' }}>
                                                {log.action}
                                            </span>
                                        </td>
                                        <td>
                                            <span className={`badge ${OUTCOME_CLS[log.outcome] || 'badge-gray'}`}>
                                                {log.outcome}
                                            </span>
                                        </td>
                                        <td style={{ fontFamily: 'monospace', fontSize: '0.75rem', color: 'var(--gray-600)' }}>
                                            {log.ip}
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>
            )}
        </div>
    );
}
