// Extended mock data for additional credit bureau features

export interface Dispute {
  id: string;
  clientId: string;
  clientName: string;
  accountRef: string;
  institution: string;
  type: "incorrect_balance" | "identity_theft" | "duplicate_entry" | "closed_not_updated" | "wrong_status" | "other";
  description: string;
  status: "open" | "investigating" | "resolved" | "rejected";
  filedDate: string;
  resolvedDate?: string;
  assignedTo?: string;
}

export interface AuditLog {
  id: string;
  userId: string;
  userName: string;
  action: string;
  resource: string;
  details: string;
  ipAddress: string;
  timestamp: string;
}

export interface CreditAlert {
  id: string;
  clientId: string;
  type: "score_change" | "new_inquiry" | "new_account" | "delinquency" | "identity_alert" | "fraud_alert";
  title: string;
  message: string;
  severity: "info" | "warning" | "critical";
  read: boolean;
  createdAt: string;
}

export interface ModelConfig {
  id: string;
  name: string;
  version: string;
  status: "champion" | "challenger" | "retired";
  accuracy: number;
  giniCoefficient: number;
  ksStatistic: number;
  lastTrained: string;
  features: number;
  description: string;
}

export interface ConsentRecord {
  id: string;
  institution: string;
  purpose: string;
  grantedDate: string;
  expiryDate: string;
  status: "active" | "expired" | "revoked";
}

export interface SimulatorScenario {
  action: string;
  description: string;
  impact: number;
  timeframe: string;
}

// New interfaces for PRD features
export interface AdminUser {
  id: string;
  name: string;
  email: string;
  role: "super_admin" | "admin" | "analyst" | "auditor" | "viewer";
  department: string;
  status: "active" | "inactive" | "locked";
  lastLogin: string;
  createdAt: string;
  permissions: string[];
}

export interface SystemNotification {
  id: string;
  title: string;
  message: string;
  type: "system" | "alert" | "report" | "compliance" | "model";
  channel: "email" | "sms" | "in_app" | "all";
  targetAudience: "all_clients" | "all_admins" | "specific" | "segment";
  status: "sent" | "scheduled" | "draft" | "failed";
  sentAt?: string;
  scheduledAt?: string;
  recipients: number;
  openRate?: number;
}

export interface SystemConfig {
  category: string;
  settings: { key: string; label: string; value: string | number | boolean; type: "text" | "number" | "toggle" | "select"; options?: string[]; description: string }[];
}

export interface NPLSummary {
  totalNPLs: number;
  nplRatio: number;
  totalExposure: number;
  provisionRequired: number;
  byCategory: { category: string; count: number; amount: number; percentage: number }[];
  bySector: { sector: string; count: number; amount: number; nplRate: number }[];
  trend: { month: string; nplRatio: number; count: number }[];
  ageing: { bucket: string; count: number; amount: number }[];
}

export interface BureauScore {
  bureau: string;
  score: number;
  grade: string;
  baseScore: number;
  aiInsight: number;
  lastUpdated: string;
  factors: { factor: string; impact: "positive" | "negative" | "neutral"; points: number; description: string }[];
}

export interface LoanPortfolio {
  totalLoans: number;
  activeLoans: number;
  totalDisbursed: number;
  totalRepaid: number;
  defaultRate: number;
  avgLoanSize: number;
  byStatus: { status: string; count: number; amount: number }[];
  byScoreBand: { band: string; approved: number; defaulted: number; defaultRate: number }[];
  monthlyDisbursements: { month: string; count: number; amount: number; defaults: number }[];
}

// Mock Data

export const mockAdminUsers: AdminUser[] = [
  { id: "USR-001", name: "Sarah Kimani", email: "sarah.k@athena.co.ke", role: "super_admin", department: "IT", status: "active", lastLogin: "2025-03-12T14:30:00Z", createdAt: "2023-01-15", permissions: ["all"] },
  { id: "USR-002", name: "James Mwangi", email: "james.m@athena.co.ke", role: "admin", department: "Operations", status: "active", lastLogin: "2025-03-12T10:15:00Z", createdAt: "2023-03-20", permissions: ["manage_disputes", "view_reports", "manage_clients"] },
  { id: "USR-003", name: "Lucy Akinyi", email: "lucy.a@athena.co.ke", role: "analyst", department: "Data Science", status: "active", lastLogin: "2025-03-11T16:45:00Z", createdAt: "2023-06-10", permissions: ["view_reports", "manage_models", "view_analytics"] },
  { id: "USR-004", name: "Daniel Otieno", email: "daniel.o@athena.co.ke", role: "auditor", department: "Compliance", status: "active", lastLogin: "2025-03-10T09:00:00Z", createdAt: "2024-01-05", permissions: ["view_reports", "view_audit_logs", "export_data"] },
  { id: "USR-005", name: "Grace Wambui", email: "grace.w@athena.co.ke", role: "viewer", department: "Customer Support", status: "inactive", lastLogin: "2025-02-28T11:30:00Z", createdAt: "2024-06-15", permissions: ["view_reports"] },
  { id: "USR-006", name: "Michael Njoroge", email: "michael.n@athena.co.ke", role: "admin", department: "Risk", status: "locked", lastLogin: "2025-03-05T08:20:00Z", createdAt: "2023-09-01", permissions: ["manage_disputes", "view_reports", "view_analytics"] },
];

export const mockSystemNotifications: SystemNotification[] = [
  { id: "NTF-001", title: "Monthly Credit Report Available", message: "Your March 2025 credit report is now available for download.", type: "report", channel: "all", targetAudience: "all_clients", status: "sent", sentAt: "2025-03-12T08:00:00Z", recipients: 12450, openRate: 67.3 },
  { id: "NTF-002", title: "System Maintenance Scheduled", message: "Planned maintenance on March 15th from 2:00 AM - 4:00 AM EAT.", type: "system", channel: "email", targetAudience: "all_admins", status: "scheduled", scheduledAt: "2025-03-14T20:00:00Z", recipients: 24 },
  { id: "NTF-003", title: "New Scoring Model Deployed", message: "Athena Score v3.1 has been deployed as challenger model.", type: "model", channel: "in_app", targetAudience: "all_admins", status: "sent", sentAt: "2025-03-01T10:00:00Z", recipients: 24, openRate: 91.7 },
  { id: "NTF-004", title: "Regulatory Compliance Deadline", message: "Q1 2025 compliance reports due by March 31st.", type: "compliance", channel: "email", targetAudience: "specific", status: "sent", sentAt: "2025-03-10T09:00:00Z", recipients: 6, openRate: 100 },
  { id: "NTF-005", title: "Fraud Alert: Unusual Activity", message: "Multiple suspicious applications detected from Mombasa region.", type: "alert", channel: "all", targetAudience: "all_admins", status: "sent", sentAt: "2025-03-11T06:30:00Z", recipients: 24, openRate: 95.8 },
  { id: "NTF-006", title: "Score Improvement Tips", message: "Personalized tips based on your latest credit report.", type: "report", channel: "sms", targetAudience: "segment", status: "draft", recipients: 3200 },
];

export const mockSystemConfigs: SystemConfig[] = [
  {
    category: "Scoring Engine",
    settings: [
      { key: "base_score_weight", label: "Base Score Weight (%)", value: 70, type: "number", description: "Weight of the quantitative base score in final calculation" },
      { key: "ai_insight_weight", label: "AI Insight Weight (%)", value: 30, type: "number", description: "Weight of the AI qualitative insight" },
      { key: "ai_insight_min", label: "Min AI Insight", value: -50, type: "number", description: "Minimum points the AI can adjust" },
      { key: "ai_insight_max", label: "Max AI Insight", value: 50, type: "number", description: "Maximum points the AI can adjust" },
      { key: "score_floor", label: "Score Floor", value: 300, type: "number", description: "Minimum possible credit score" },
      { key: "score_ceiling", label: "Score Ceiling", value: 850, type: "number", description: "Maximum possible credit score" },
    ],
  },
  {
    category: "Risk Thresholds",
    settings: [
      { key: "auto_approve_threshold", label: "Auto-Approve Score", value: 700, type: "number", description: "Score above which loans are auto-approved" },
      { key: "auto_reject_threshold", label: "Auto-Reject Score", value: 350, type: "number", description: "Score below which loans are auto-rejected" },
      { key: "manual_review_enabled", label: "Manual Review Zone", value: true, type: "toggle", description: "Enable manual review for scores between auto-approve and auto-reject" },
      { key: "npl_days_threshold", label: "NPL Days Threshold", value: 90, type: "number", description: "Days in arrears before marking as non-performing" },
      { key: "betting_penalty_threshold", label: "Betting Spend Penalty (%)", value: 5, type: "number", description: "% of income spent on betting that triggers score penalty" },
    ],
  },
  {
    category: "Data & Privacy",
    settings: [
      { key: "data_retention_years", label: "Data Retention (Years)", value: 7, type: "number", description: "Years to retain transaction data" },
      { key: "decision_retention_years", label: "Decision Retention (Years)", value: 10, type: "number", description: "Years to retain credit decisions for audit" },
      { key: "data_encryption", label: "Data Encryption at Rest", value: true, type: "toggle", description: "Encrypt all PII fields in the database" },
      { key: "consent_required", label: "Consent Required", value: true, type: "toggle", description: "Require explicit consent before scoring" },
      { key: "data_sovereignty", label: "Data Sovereignty Mode", value: "local", type: "select", options: ["local", "regional", "global"], description: "Where data can be processed and stored" },
    ],
  },
  {
    category: "Notifications",
    settings: [
      { key: "score_change_alert", label: "Score Change Alerts", value: true, type: "toggle", description: "Notify clients when their score changes" },
      { key: "score_change_threshold", label: "Score Change Threshold", value: 10, type: "number", description: "Minimum point change to trigger alert" },
      { key: "inquiry_alerts", label: "Credit Inquiry Alerts", value: true, type: "toggle", description: "Notify when a new inquiry is made" },
      { key: "monthly_report_reminder", label: "Monthly Report Reminder", value: true, type: "toggle", description: "Send monthly credit report availability notice" },
    ],
  },
];

export const mockNPLSummary: NPLSummary = {
  totalNPLs: 1034,
  nplRatio: 8.3,
  totalExposure: 2450000000,
  provisionRequired: 735000000,
  byCategory: [
    { category: "Substandard (91-180 days)", count: 456, amount: 890000000, percentage: 44.1 },
    { category: "Doubtful (181-360 days)", count: 312, amount: 780000000, percentage: 30.2 },
    { category: "Loss (360+ days)", count: 266, amount: 780000000, percentage: 25.7 },
  ],
  bySector: [
    { sector: "Personal Banking", count: 412, amount: 680000000, nplRate: 6.8 },
    { sector: "SME Lending", count: 289, amount: 750000000, nplRate: 11.2 },
    { sector: "Sacco", count: 178, amount: 420000000, nplRate: 9.5 },
    { sector: "Microfinance", count: 98, amount: 350000000, nplRate: 14.3 },
    { sector: "Mobile Lending", count: 57, amount: 250000000, nplRate: 5.1 },
  ],
  trend: [
    { month: "Oct", nplRatio: 9.1, count: 1120 },
    { month: "Nov", nplRatio: 8.9, count: 1095 },
    { month: "Dec", nplRatio: 8.7, count: 1070 },
    { month: "Jan", nplRatio: 8.5, count: 1052 },
    { month: "Feb", nplRatio: 8.4, count: 1043 },
    { month: "Mar", nplRatio: 8.3, count: 1034 },
  ],
  ageing: [
    { bucket: "91-120 days", count: 234, amount: 380000000 },
    { bucket: "121-180 days", count: 222, amount: 510000000 },
    { bucket: "181-270 days", count: 189, amount: 470000000 },
    { bucket: "271-360 days", count: 123, amount: 310000000 },
    { bucket: "360+ days", count: 266, amount: 780000000 },
  ],
};

export const mockBureauScores: BureauScore[] = [
  {
    bureau: "Athena",
    score: 698,
    grade: "Satisfactory",
    baseScore: 672,
    aiInsight: 26,
    lastUpdated: "2025-03-12",
    factors: [
      { factor: "Income Stability", impact: "positive", points: 15, description: "Consistent monthly income with low variance" },
      { factor: "Savings Pattern", impact: "positive", points: 15, description: "Regular savings deposits detected" },
      { factor: "Payment History", impact: "negative", points: -10, description: "1 account with 365 days in arrears" },
      { factor: "Credit Utilization", impact: "positive", points: 10, description: "Low credit utilization at 12%" },
      { factor: "Educational Spending", impact: "positive", points: 8, description: "AI detected regular educational institution payments" },
      { factor: "Business Investment", impact: "positive", points: 12, description: "AI detected consistent business supply purchases" },
      { factor: "Cash Cycling Risk", impact: "negative", points: -6, description: "AI flagged occasional deposit-withdrawal patterns" },
    ],
  },
  {
    bureau: "TransUnion",
    score: 677,
    grade: "Satisfactory",
    baseScore: 677,
    aiInsight: 0,
    lastUpdated: "2025-03-10",
    factors: [
      { factor: "Payment History", impact: "negative", points: -15, description: "Late payments on 2 accounts" },
      { factor: "Credit Age", impact: "positive", points: 12, description: "84 months of credit history" },
      { factor: "Credit Mix", impact: "positive", points: 8, description: "Good diversity of credit types" },
      { factor: "Outstanding Debt", impact: "neutral", points: 0, description: "Moderate outstanding balance" },
    ],
  },
  {
    bureau: "Metropol",
    score: 685,
    grade: "Satisfactory",
    baseScore: 685,
    aiInsight: 0,
    lastUpdated: "2025-03-08",
    factors: [
      { factor: "Repayment Conduct", impact: "negative", points: -12, description: "Non-performing account detected" },
      { factor: "Account Standing", impact: "positive", points: 10, description: "Majority of accounts in good standing" },
      { factor: "Inquiry Volume", impact: "positive", points: 5, description: "No recent hard inquiries" },
      { factor: "Debt Ratio", impact: "neutral", points: 2, description: "Acceptable debt-to-income ratio" },
    ],
  },
];

export const mockLoanPortfolio: LoanPortfolio = {
  totalLoans: 18650,
  activeLoans: 12340,
  totalDisbursed: 45200000000,
  totalRepaid: 32800000000,
  defaultRate: 4.8,
  avgLoanSize: 2420000,
  byStatus: [
    { status: "Active", count: 12340, amount: 29800000000 },
    { status: "Repaid", count: 4876, amount: 11200000000 },
    { status: "Defaulted", count: 894, amount: 3100000000 },
    { status: "Restructured", count: 540, amount: 1100000000 },
  ],
  byScoreBand: [
    { band: "300-400", approved: 320, defaulted: 96, defaultRate: 30.0 },
    { band: "401-500", approved: 1240, defaulted: 248, defaultRate: 20.0 },
    { band: "501-600", approved: 4560, defaulted: 365, defaultRate: 8.0 },
    { band: "601-700", approved: 7890, defaulted: 158, defaultRate: 2.0 },
    { band: "701-850", approved: 4640, defaulted: 27, defaultRate: 0.6 },
  ],
  monthlyDisbursements: [
    { month: "Oct", count: 1450, amount: 3510000000, defaults: 42 },
    { month: "Nov", count: 1620, amount: 3920000000, defaults: 38 },
    { month: "Dec", count: 1280, amount: 3100000000, defaults: 51 },
    { month: "Jan", count: 1780, amount: 4310000000, defaults: 35 },
    { month: "Feb", count: 1890, amount: 4570000000, defaults: 29 },
    { month: "Mar", count: 1950, amount: 4720000000, defaults: 24 },
  ],
};

export const mockDisputes: Dispute[] = [
  { id: "DSP-001", clientId: "CLI-001", clientName: "Denis Muhando Adira", accountRef: "ILA_85200", institution: "Maisha Bora Sacco Ltd", type: "incorrect_balance", description: "Balance shows KES 1,668 but I paid off this loan in full on Feb 2024. Receipts attached.", status: "investigating", filedDate: "2025-03-01", assignedTo: "Sarah K." },
  { id: "DSP-002", clientId: "CLI-002", clientName: "Jane Wanjiku Kamau", accountRef: "440006635679", institution: "NCBA Bank Kenya PLC", type: "closed_not_updated", description: "Account was closed and settled in March 2022 but still showing as active with arrears.", status: "open", filedDate: "2025-03-10" },
  { id: "DSP-003", clientId: "CLI-003", clientName: "Peter Otieno Odhiambo", accountRef: "3000080330", institution: "Stanbic Bank Ltd", type: "identity_theft", description: "I never opened a credit card with Stanbic Bank. This is a fraudulent account.", status: "investigating", filedDate: "2025-02-20", assignedTo: "James M." },
  { id: "DSP-004", clientId: "CLI-004", clientName: "Mary Njeri Mwangi", accountRef: "0100010700048", institution: "Stanbic Bank Ltd", type: "duplicate_entry", description: "Same loan appears twice under different reference numbers.", status: "resolved", filedDate: "2025-01-15", resolvedDate: "2025-02-10", assignedTo: "Sarah K." },
  { id: "DSP-005", clientId: "CLI-005", clientName: "James Kiprop Kosgei", accountRef: "25471636015520241127", institution: "NCBA Bank Kenya PLC", type: "wrong_status", description: "Overdraft shows non-performing but payments are current.", status: "rejected", filedDate: "2025-02-01", resolvedDate: "2025-02-15", assignedTo: "James M." },
];

export const mockAuditLogs: AuditLog[] = [
  { id: "AUD-001", userId: "ADM-001", userName: "Admin Sarah", action: "VIEW_REPORT", resource: "CLI-001", details: "Viewed credit report for Denis Muhando Adira", ipAddress: "192.168.1.45", timestamp: "2025-03-12T14:30:00Z" },
  { id: "AUD-002", userId: "ADM-002", userName: "Admin James", action: "RESCORE", resource: "CLI-003", details: "Initiated rescore for Peter Otieno Odhiambo", ipAddress: "192.168.1.52", timestamp: "2025-03-12T13:15:00Z" },
  { id: "AUD-003", userId: "ADM-001", userName: "Admin Sarah", action: "RESOLVE_DISPUTE", resource: "DSP-004", details: "Resolved dispute DSP-004 - duplicate entry removed", ipAddress: "192.168.1.45", timestamp: "2025-03-11T16:45:00Z" },
  { id: "AUD-004", userId: "ADM-003", userName: "Admin Lucy", action: "UPDATE_MODEL", resource: "MDL-002", details: "Deployed challenger model v2.1 to staging", ipAddress: "192.168.1.60", timestamp: "2025-03-11T10:00:00Z" },
  { id: "AUD-005", userId: "CLI-001", userName: "Denis Adira", action: "FILE_DISPUTE", resource: "DSP-001", details: "Filed dispute for account ILA_85200", ipAddress: "41.89.12.100", timestamp: "2025-03-01T09:30:00Z" },
  { id: "AUD-006", userId: "ADM-001", userName: "Admin Sarah", action: "EXPORT_DATA", resource: "REPORTS", details: "Exported monthly compliance report", ipAddress: "192.168.1.45", timestamp: "2025-03-10T11:20:00Z" },
  { id: "AUD-007", userId: "ADM-002", userName: "Admin James", action: "FREEZE_ACCOUNT", resource: "CLI-003", details: "Froze credit file for Peter Otieno due to identity theft investigation", ipAddress: "192.168.1.52", timestamp: "2025-03-09T08:00:00Z" },
  { id: "AUD-008", userId: "CLI-002", userName: "Jane Kamau", action: "DOWNLOAD_REPORT", resource: "RPT-002", details: "Downloaded personal credit report", ipAddress: "41.89.22.55", timestamp: "2025-03-08T15:10:00Z" },
];

export const mockAlerts: CreditAlert[] = [
  { id: "ALT-001", clientId: "CLI-001", type: "score_change", title: "Credit Score Increased", message: "Your credit score increased by 21 points from 677 to 698.", severity: "info", read: false, createdAt: "2025-03-12T10:00:00Z" },
  { id: "ALT-002", clientId: "CLI-001", type: "new_inquiry", title: "New Credit Inquiry", message: "NCBA Bank Kenya PLC made a hard inquiry on your credit file.", severity: "warning", read: false, createdAt: "2025-03-10T14:30:00Z" },
  { id: "ALT-003", clientId: "CLI-001", type: "delinquency", title: "Account In Arrears", message: "Maisha Bora Sacco account ILA_85200 is 365 days in arrears.", severity: "critical", read: true, createdAt: "2025-03-01T08:00:00Z" },
  { id: "ALT-004", clientId: "CLI-001", type: "new_account", title: "New Account Reported", message: "A new overdraft account was reported by NCBA Bank Kenya PLC.", severity: "info", read: true, createdAt: "2025-02-15T12:00:00Z" },
  { id: "ALT-005", clientId: "CLI-001", type: "fraud_alert", title: "Potential Fraud Detected", message: "Unusual activity detected - 3 credit applications in 24 hours from different locations.", severity: "critical", read: false, createdAt: "2025-03-11T06:00:00Z" },
];

export const mockModels: ModelConfig[] = [
  { id: "MDL-001", name: "Athena Score v3.0", version: "3.0.2", status: "champion", accuracy: 92.4, giniCoefficient: 0.78, ksStatistic: 0.65, lastTrained: "2025-02-15", features: 156, description: "Production LightGBM model with enhanced feature engineering" },
  { id: "MDL-002", name: "Athena Score v3.1", version: "3.1.0-beta", status: "challenger", accuracy: 93.1, giniCoefficient: 0.81, ksStatistic: 0.68, lastTrained: "2025-03-01", features: 172, description: "Challenger model with additional mobile money features" },
  { id: "MDL-003", name: "Athena Score v2.5", version: "2.5.8", status: "retired", accuracy: 89.7, giniCoefficient: 0.72, ksStatistic: 0.59, lastTrained: "2024-08-10", features: 134, description: "Previous production model - retired Feb 2025" },
];

export const mockConsents: ConsentRecord[] = [
  { id: "CON-001", institution: "NCBA Bank Kenya PLC", purpose: "Loan application assessment", grantedDate: "2025-01-15", expiryDate: "2025-07-15", status: "active" },
  { id: "CON-002", institution: "Stanbic Bank Ltd", purpose: "Credit card limit review", grantedDate: "2024-06-01", expiryDate: "2025-06-01", status: "active" },
  { id: "CON-003", institution: "Maisha Bora Sacco Ltd", purpose: "Loan restructuring assessment", grantedDate: "2024-03-10", expiryDate: "2024-09-10", status: "expired" },
  { id: "CON-004", institution: "Safaricom PLC", purpose: "Fuliza limit assessment", grantedDate: "2025-02-01", expiryDate: "2025-08-01", status: "active" },
];

export const simulatorScenarios: SimulatorScenario[] = [
  { action: "Pay off delinquent account", description: "Clear the KES 1,668 arrears on Maisha Bora Sacco loan", impact: 45, timeframe: "2-3 months" },
  { action: "Reduce credit utilization to 30%", description: "Pay down balances to use only 30% of available credit", impact: 30, timeframe: "1-2 months" },
  { action: "Remove incorrect negative item", description: "Successfully dispute and remove erroneous default record", impact: 55, timeframe: "30-45 days" },
  { action: "Open new credit account", description: "Apply for a new personal loan or credit card", impact: -15, timeframe: "Immediate" },
  { action: "Make 6 consecutive on-time payments", description: "Maintain perfect payment record for 6 months", impact: 35, timeframe: "6 months" },
  { action: "Close oldest credit account", description: "Close your longest-standing credit line", impact: -20, timeframe: "1-2 months" },
];

export const educationTopics = [
  { id: "EDU-001", title: "Understanding Your Credit Score", category: "Basics", readTime: "5 min", description: "Learn what makes up your credit score and how bureaus calculate it.", icon: "GraduationCap" },
  { id: "EDU-002", title: "How to Improve Your Score", category: "Tips", readTime: "8 min", description: "Proven strategies to boost your credit score over time.", icon: "TrendingUp" },
  { id: "EDU-003", title: "Reading Your Credit Report", category: "Basics", readTime: "6 min", description: "A guide to understanding each section of your credit report.", icon: "FileText" },
  { id: "EDU-004", title: "Disputing Errors on Your Report", category: "Actions", readTime: "7 min", description: "Step-by-step guide to filing and resolving credit report disputes.", icon: "AlertTriangle" },
  { id: "EDU-005", title: "Credit Freeze vs. Fraud Alert", category: "Security", readTime: "4 min", description: "When and how to use credit freezes and fraud alerts to protect yourself.", icon: "Shield" },
  { id: "EDU-006", title: "Types of Credit Inquiries", category: "Basics", readTime: "3 min", description: "Understand the difference between hard and soft credit inquiries.", icon: "Search" },
  { id: "EDU-007", title: "Managing Debt Effectively", category: "Tips", readTime: "10 min", description: "Strategies for debt repayment including snowball and avalanche methods.", icon: "Wallet" },
  { id: "EDU-008", title: "Credit Score Myths Debunked", category: "Basics", readTime: "5 min", description: "Common misconceptions about credit scores and the truth behind them.", icon: "HelpCircle" },
];

export function getDisputeTypeLabel(type: Dispute["type"]): string {
  const labels: Record<Dispute["type"], string> = {
    incorrect_balance: "Incorrect Balance",
    identity_theft: "Identity Theft",
    duplicate_entry: "Duplicate Entry",
    closed_not_updated: "Closed Not Updated",
    wrong_status: "Wrong Status",
    other: "Other",
  };
  return labels[type];
}

export function getDisputeStatusColor(status: Dispute["status"]): string {
  switch (status) {
    case "open": return "bg-blue-500/10 text-blue-600 border-blue-500/20";
    case "investigating": return "bg-amber-500/10 text-amber-600 border-amber-500/20";
    case "resolved": return "bg-emerald-500/10 text-emerald-600 border-emerald-500/20";
    case "rejected": return "bg-red-500/10 text-red-600 border-red-500/20";
    default: return "bg-muted text-muted-foreground border-border";
  }
}

export function getAlertSeverityColor(severity: CreditAlert["severity"]): string {
  switch (severity) {
    case "info": return "border-blue-500/30 bg-blue-500/5";
    case "warning": return "border-amber-500/30 bg-amber-500/5";
    case "critical": return "border-red-500/30 bg-red-500/5";
    default: return "border-border bg-card";
  }
}

export function getRoleColor(role: AdminUser["role"]): string {
  switch (role) {
    case "super_admin": return "bg-purple-500/10 text-purple-600 border-purple-500/20";
    case "admin": return "bg-blue-500/10 text-blue-600 border-blue-500/20";
    case "analyst": return "bg-cyan-500/10 text-cyan-600 border-cyan-500/20";
    case "auditor": return "bg-amber-500/10 text-amber-600 border-amber-500/20";
    case "viewer": return "bg-muted text-muted-foreground border-border";
    default: return "bg-muted text-muted-foreground border-border";
  }
}

export function formatLargeNumber(num: number): string {
  if (num >= 1000000000) return `${(num / 1000000000).toFixed(1)}B`;
  if (num >= 1000000) return `${(num / 1000000).toFixed(1)}M`;
  if (num >= 1000) return `${(num / 1000).toFixed(1)}K`;
  return num.toString();
}
