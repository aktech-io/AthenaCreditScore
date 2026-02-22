const BASE = '/api';

async function request(path, options = {}, token = null) {
    const headers = { 'Content-Type': 'application/json', ...options.headers };
    if (token) headers['Authorization'] = `Bearer ${token}`;
    const res = await fetch(`${BASE}${path}`, { ...options, headers });
    if (!res.ok) {
        const err = await res.json().catch(() => ({ message: res.statusText }));
        throw new Error(err.message || `HTTP ${res.status}`);
    }
    return res.json();
}

export const api = {
    // Auth
    login: (username, password) =>
        request('/auth/admin/login', {
            method: 'POST',
            body: JSON.stringify({ username, password }),
        }),

    // Dashboard stats — aggregate from scoring engine and Java service
    getDashboardStats: (token) => request('/v1/dashboard/stats', {}, token),

    // Customers
    searchCustomers: (query, token) =>
        request(`/v1/customers/search?q=${encodeURIComponent(query)}`, {}, token),
    getCustomer: (id, token) =>
        request(`/v1/customers/${id}`, {}, token),
    getCreditScore: (id, token) =>
        request(`/v1/credit/score/${id}`, {}, token),
    getFullReport: (id, token) =>
        request(`/v1/credit/report/${id}`, {}, token),
    triggerRescore: (id, token) =>
        request(`/v1/credit/score/${id}/trigger`, { method: 'POST' }, token),

    // Disputes
    listDisputes: (token, status = '') =>
        request(`/v1/disputes${status ? `?status=${status}` : ''}`, {}, token),
    updateDispute: (id, body, token) =>
        request(`/v1/disputes/${id}`, { method: 'PUT', body: JSON.stringify(body) }, token),

    // Champion-Challenger
    getRoutingConfig: (token) => request('/v1/crb/routing-config', {}, token),
    setRoutingConfig: (pct, token) =>
        request(`/v1/crb/routing-config?challengerPct=${pct}`, { method: 'PUT' }, token),

    // Champion comparison
    compareModels: (token) =>
        request('/v1/models/compare', {}, token),

    // Promote challenger to champion
    promoteChallenger: (token) =>
        request('/v1/models/promote', { method: 'PUT' }, token),

    // Score history
    getCreditScoreHistory: (id, token) =>
        request(`/v1/credit/score/${id}/history`, {}, token),

    // Audit log
    getAuditLog: (token, page = 0) =>
        request(`/v1/audit?page=${page}&size=50`, {}, token),
};
