// API service layer — replaces mock data with real API calls

const TOKEN_KEY = "athena_token";
const CUSTOMER_ID_KEY = "athena_customer_id";

// ── helpers ──────────────────────────────────────────────────────────

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string) {
  localStorage.setItem(TOKEN_KEY, token);
}

export function getCustomerId(): number | null {
  const v = localStorage.getItem(CUSTOMER_ID_KEY);
  return v ? Number(v) : null;
}

export function setCustomerId(id: number) {
  localStorage.setItem(CUSTOMER_ID_KEY, String(id));
}

export function clearAuth() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(CUSTOMER_ID_KEY);
}

async function apiFetch<T>(url: string, init?: RequestInit): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(init?.headers as Record<string, string> | undefined),
  };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  const res = await fetch(url, { ...init, headers });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(text || `HTTP ${res.status}`);
  }
  // handle 204 / empty body
  const ct = res.headers.get("content-type") || "";
  if (res.status === 204 || !ct.includes("application/json")) {
    return {} as T;
  }
  return res.json() as Promise<T>;
}

// ── Auth ─────────────────────────────────────────────────────────────

export interface AdminLoginResponse {
  token: string;
  roles: string[];
}

export async function adminLogin(username: string, password: string): Promise<AdminLoginResponse> {
  return apiFetch<AdminLoginResponse>("/api/auth/admin/login", {
    method: "POST",
    body: JSON.stringify({ username, password }),
  });
}

export async function requestOtp(phone: string): Promise<{ message: string }> {
  return apiFetch("/api/auth/customer/request-otp?phone=" + encodeURIComponent(phone), {
    method: "POST",
  });
}

export interface OtpVerifyResponse {
  token: string;
  customerId: number;
}

export async function verifyOtp(phone: string, otp: string): Promise<OtpVerifyResponse> {
  return apiFetch<OtpVerifyResponse>(
    `/api/auth/customer/verify-otp?phone=${encodeURIComponent(phone)}&otp=${encodeURIComponent(otp)}`,
    { method: "POST" },
  );
}

// ── Dashboard ────────────────────────────────────────────────────────

export interface DashboardStats {
  totalScored: number;
  avgScore: number;
  approvalRate: number;
  defaultRate: number;
  openDisputes: number;
  ksStatistic: number;
  psiValue: number;
  [key: string]: unknown;
}

export async function fetchDashboardStats(): Promise<DashboardStats> {
  return apiFetch<DashboardStats>("/api/v1/dashboard/stats");
}

// ── Customers ────────────────────────────────────────────────────────

export interface CustomerPage {
  content: CustomerRecord[];
  totalElements: number;
  totalPages: number;
}

export interface CustomerRecord {
  id: number;
  first_name?: string;
  last_name?: string;
  firstName?: string;
  lastName?: string;
  name?: string;
  phone?: string;
  mobile_number?: string;
  email?: string;
  national_id?: string;
  nationalId?: string;
  score?: number;
  credit_score?: number;
  score_band?: string;
  scoreBand?: string;
  pd?: number;
  status?: string;
  county?: string;
  date_of_birth?: string;
  gender?: string;
  [key: string]: unknown;
}

export async function fetchCustomers(page = 0, size = 20): Promise<CustomerPage> {
  return apiFetch<CustomerPage>(`/api/v1/customers?page=${page}&size=${size}`);
}

export async function searchCustomers(q: string): Promise<CustomerRecord[]> {
  return apiFetch<CustomerRecord[]>(`/api/v1/customers/search?q=${encodeURIComponent(q)}`);
}

export async function fetchCustomer(id: number): Promise<CustomerRecord> {
  return apiFetch<CustomerRecord>(`/api/v1/customers/${id}`);
}

// ── Credit / Scoring ─────────────────────────────────────────────────

export interface CreditScoreResponse {
  final_score: number;
  score_band: string;
  pd_probability: number;
  base_score: number;
  crb_contribution: number;
  llm_adjustment: number;
  score_breakdown?: {
    income_stability_score?: number;
    income_level_score?: number;
    savings_rate_score?: number;
    low_balance_score?: number;
    transaction_diversity?: number;
  };
  [key: string]: unknown;
}

export async function fetchCreditScore(customerId: number): Promise<CreditScoreResponse> {
  return apiFetch<CreditScoreResponse>(`/api/v1/credit/score/${customerId}`);
}

export interface CreditReportResponse {
  final_score: number;
  score_band: string;
  pd_probability: number;
  customer_name: string;
  llm_reasoning: string;
  crb_bureau_score: number;
  crb_npa_count: number;
  crb_active_default: boolean;
  delinquency_rate_90d: number;
  base_score?: number;
  crb_contribution?: number;
  llm_adjustment?: number;
  score_breakdown?: {
    income_stability_score?: number;
    income_level_score?: number;
    savings_rate_score?: number;
    low_balance_score?: number;
    transaction_diversity?: number;
  };
  [key: string]: unknown;
}

export async function fetchCreditReport(customerId: number): Promise<CreditReportResponse> {
  return apiFetch<CreditReportResponse>(`/api/v1/credit/report/${customerId}`);
}

export async function triggerScoring(customerId: number): Promise<{ status: string }> {
  return apiFetch<{ status: string }>(`/api/v1/credit/score/${customerId}/trigger`, {
    method: "POST",
  });
}

export interface ScoreHistoryEntry {
  final_score: number;
  score_band: string;
  scored_at: string;
  [key: string]: unknown;
}

export async function fetchScoreHistory(customerId: number, months = 12): Promise<{ data: ScoreHistoryEntry[] }> {
  return apiFetch<{ data: ScoreHistoryEntry[] }>(`/api/v1/credit/score/${customerId}/history?months=${months}`);
}

// ── Disputes ─────────────────────────────────────────────────────────

export interface DisputeRecord {
  id: number | string;
  customerId?: number;
  customer_id?: number;
  customer?: string;
  field?: string;
  desc?: string;
  description?: string;
  status: string;
  filed?: string;
  created_at?: string;
  reason?: string;
  [key: string]: unknown;
}

export async function fetchAllDisputes(status?: string): Promise<DisputeRecord[]> {
  const qs = status ? `?status=${encodeURIComponent(status)}` : "";
  return apiFetch<DisputeRecord[]>(`/api/v1/disputes${qs}`);
}

export async function updateDisputeStatus(id: number | string, status: string): Promise<void> {
  await apiFetch(`/api/v1/disputes/${id}`, {
    method: "PUT",
    body: JSON.stringify({ status }),
  });
}

export async function fetchCustomerDisputes(customerId: number): Promise<{ customer_id: number; disputes: DisputeRecord[] }> {
  return apiFetch<{ customer_id: number; disputes: DisputeRecord[] }>(`/api/v1/customers/${customerId}/disputes`);
}

export async function fileDispute(customerId: number, body: { field?: string; reason?: string; description?: string }): Promise<void> {
  await apiFetch(`/api/v1/customers/${customerId}/disputes`, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

// ── Consents ─────────────────────────────────────────────────────────

export interface ConsentRecord {
  id: number | string;
  name?: string;
  scope?: string;
  granted?: boolean;
  institution?: string;
  purpose?: string;
  grantedDate?: string;
  expiryDate?: string;
  status?: string;
  expires_at?: string;
  revoked_at?: string;
  [key: string]: unknown;
}

export async function fetchConsents(customerId: number): Promise<ConsentRecord[]> {
  return apiFetch<ConsentRecord[]>(`/api/v1/customers/${customerId}/consents`);
}

export async function grantConsent(customerId: number, body: Record<string, unknown>): Promise<void> {
  await apiFetch(`/api/v1/customers/${customerId}/consent`, {
    method: "PUT",
    body: JSON.stringify(body),
  });
}

export async function revokeConsent(customerId: number, consentId: number | string): Promise<void> {
  await apiFetch(`/api/v1/customers/${customerId}/consents/${consentId}`, {
    method: "DELETE",
  });
}

// ── Models ───────────────────────────────────────────────────────────

export interface ModelCompareResponse {
  champion: Record<string, unknown>;
  challenger: Record<string, unknown>;
  recommendation?: string;
  [key: string]: unknown;
}

export async function fetchModelCompare(): Promise<ModelCompareResponse> {
  return apiFetch<ModelCompareResponse>("/api/v1/models/compare");
}

export async function promoteModel(): Promise<void> {
  await apiFetch("/api/v1/models/promote", { method: "PUT" });
}

export interface RoutingConfig {
  challenger_traffic_pct: number;
  champion_traffic_pct: number;
}

export async function fetchRoutingConfig(): Promise<RoutingConfig> {
  return apiFetch<RoutingConfig>("/api/v1/crb/routing-config");
}

export async function updateRoutingConfig(challengerPct: number): Promise<void> {
  await apiFetch(`/api/v1/crb/routing-config?challengerPct=${challengerPct}`, {
    method: "PUT",
  });
}

// ── Audit ────────────────────────────────────────────────────────────

export interface AuditEntry {
  id: number | string;
  ts?: string;
  timestamp?: string;
  partner?: string;
  customer?: string;
  action?: string;
  outcome?: string;
  ip?: string;
  userName?: string;
  details?: string;
  resource?: string;
  [key: string]: unknown;
}

export async function fetchAuditLogs(page = 0, size = 50): Promise<AuditEntry[]> {
  // API may return paginated or array
  const res = await apiFetch<AuditEntry[] | { content: AuditEntry[] }>(`/api/v1/audit?page=${page}&size=${size}`);
  return Array.isArray(res) ? res : (res as { content: AuditEntry[] }).content || [];
}

// ── User Management ──────────────────────────────────────────────────

export interface AdminUser {
  id: number | string;
  username?: string;
  name?: string;
  email?: string;
  roles?: string[];
  groups?: string[];
  status?: string;
  lastLogin?: string;
  department?: string;
  [key: string]: unknown;
}

export async function fetchAdminUsers(): Promise<AdminUser[]> {
  return apiFetch<AdminUser[]>("/api/v1/admin/users");
}

export async function createAdminUser(body: Record<string, unknown>): Promise<void> {
  await apiFetch("/api/v1/admin/users", { method: "POST", body: JSON.stringify(body) });
}

export async function inviteUser(body: Record<string, unknown>): Promise<void> {
  await apiFetch("/api/v1/admin/users/invite", { method: "POST", body: JSON.stringify(body) });
}

export async function deleteAdminUser(id: number | string): Promise<void> {
  await apiFetch(`/api/v1/admin/users/${id}`, { method: "DELETE" });
}

export async function fetchRoles(): Promise<{ id: number; name: string }[]> {
  return apiFetch("/api/v1/admin/roles");
}

export async function fetchGroups(): Promise<{ id: number; name: string }[]> {
  return apiFetch("/api/v1/admin/groups");
}

// ── Notifications ────────────────────────────────────────────────────

export interface NotificationConfig {
  type?: string;
  provider?: string;
  host?: string;
  port?: number;
  enabled?: boolean;
  [key: string]: unknown;
}

export async function fetchNotificationConfig(type: string): Promise<NotificationConfig> {
  return apiFetch<NotificationConfig>(`/api/v1/notifications/config/${type}`);
}

export async function updateNotificationConfig(body: Record<string, unknown>): Promise<void> {
  await apiFetch("/api/v1/notifications/config", { method: "POST", body: JSON.stringify(body) });
}

export async function sendNotification(body: Record<string, unknown>): Promise<void> {
  await apiFetch("/api/v1/notifications/send", { method: "POST", body: JSON.stringify(body) });
}
