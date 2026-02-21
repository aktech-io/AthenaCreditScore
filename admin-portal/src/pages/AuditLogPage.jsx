import { useState } from 'react';
import { Shield, User, ExternalLink, Download } from 'lucide-react';

const MOCK_LOGS = [
    { id: 1, ts: '2026-02-20 16:52:01', partner: 'EQU_BANK', customer: 101, action: 'CREDIT_SCORE_REQUEST', outcome: 'APPROVED', ip: '41.90.x.x' },
    { id: 2, ts: '2026-02-20 16:49:38', partner: 'ATHENA_ADMIN', customer: 102, action: 'PROFILE_UPDATED', outcome: 'OK', ip: '10.0.0.5' },
    { id: 3, ts: '2026-02-20 16:45:12', partner: 'EQU_BANK', customer: 103, action: 'CREDIT_SCORE_REQUEST', outcome: 'DENIED_NO_CONSENT', ip: '41.90.x.x' },
    { id: 4, ts: '2026-02-20 16:40:00', partner: 'KCB_PARTNER', customer: 104, action: 'CREDIT_SCORE_REQUEST', outcome: 'APPROVED', ip: '196.12.x.x' },
    { id: 5, ts: '2026-02-20 16:30:55', partner: 'ATHENA_ADMIN', customer: 101, action: 'DISPUTE_FILED', outcome: 'OK', ip: '10.0.0.5' },
    { id: 6, ts: '2026-02-20 16:20:10', partner: 'EQU_BANK', customer: 105, action: 'CONSENT_REVOKED', outcome: 'OK', ip: '41.90.x.x' },
];

const OUTCOME_CLS = {
    APPROVED: 'badge-green',
    OK: 'badge-blue',
    DENIED_NO_CONSENT: 'badge-red',
    DENIED: 'badge-red',
};

export default function AuditLogPage() {
    const [logs] = useState(MOCK_LOGS);
    const [filter, setFilter] = useState('');

    const visible = filter
        ? logs.filter(l => l.action.includes(filter) || l.outcome.includes(filter) || l.partner.includes(filter))
        : logs;

    return (
        <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 24 }}>
                <div>
                    <h1 style={{ fontSize: '1.5rem' }}>Audit Log</h1>
                    <p style={{ marginTop: 4 }}>All partner data access events — tamper-evident append-only record</p>
                </div>
                <button className="btn btn-ghost btn-sm">
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
                            {visible.map(log => (
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
        </div>
    );
}
