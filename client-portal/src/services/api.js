const BASE = '/api';

async function req(path, opts = {}, token = null) {
    const headers = { 'Content-Type': 'application/json', ...opts.headers };
    if (token) headers['Authorization'] = `Bearer ${token}`;
    const res = await fetch(`${BASE}${path}`, { ...opts, headers });
    if (!res.ok) {
        const e = await res.json().catch(() => ({ message: res.statusText }));
        throw new Error(e.message || `HTTP ${res.status}`);
    }
    return res.json();
}

export const api = {
    demoToken: (customerId) => req(`/auth/customer/demo-token?customerId=${customerId}`, { method: 'POST' }),
    requestOtp: (phone) => req('/auth/customer/request-otp', { method: 'POST', body: JSON.stringify({ phone }) }),
    verifyOtp: (phone, otp) => req('/auth/customer/verify-otp', { method: 'POST', body: JSON.stringify({ phone, otp }) }),
    getScore: (id, token) => req(`/v1/credit/score/${id}`, {}, token),
    getReport: (id, token) => req(`/v1/credit/report/${id}`, {}, token),
    getDisputes: (id, token) => req(`/v1/customers/${id}/disputes`, {}, token),
    fileDispute: (id, body, token) => req(`/v1/customers/${id}/disputes`, { method: 'POST', body: JSON.stringify(body) }, token),
    grantConsent: (id, body, token) => req(`/v1/customers/${id}/consent`, { method: 'PUT', body: JSON.stringify(body) }, token),
};
