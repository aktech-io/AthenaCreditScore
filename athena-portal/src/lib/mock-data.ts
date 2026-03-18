// Mock data for credit bureau system

export interface Client {
  id: string;
  name: string;
  nationalId: string;
  email: string;
  phone: string;
  dateOfBirth: string;
  gender: string;
  nationality: string;
  creditScore: number;
  scoreGrade: string;
  status: "active" | "suspended" | "pending";
  lastReportDate: string;
  totalAccounts: number;
  openAccounts: number;
  totalOutstanding: number;
}

export interface CreditAccount {
  id: string;
  accountRef: string;
  institution: string;
  sector: string;
  accountType: string;
  principalAmount: number;
  balanceAmount: number;
  status: "active" | "closed" | "settled";
  performanceStatus: "performing" | "non-performing" | "default-history";
  listingDate: string;
  lastPayment: string;
  daysInArrears: number;
  worstArrear: number;
  arrearsAmount: number;
  repaymentHistory: { month: string; days: number }[];
}

export interface CreditReport {
  id: string;
  clientId: string;
  clientName: string;
  reportDate: string;
  bureauScore: number;
  scoreGrade: string;
  ppiScore: string;
  source: "TransUnion" | "Metropol" | "Athena";
  summary: {
    totalAccounts: number;
    nonPerformingAccounts: number;
    performingWithDefault: number;
    performingAccounts: number;
    totalOutstanding: number;
    totalOverdue: number;
    creditHistoryMonths: number;
    enquiriesLast30Days: number;
    bouncedCheques: number;
  };
  accounts: CreditAccount[];
  scoreTrend: { month: string; score: number }[];
}

export const mockClients: Client[] = [
  {
    id: "CLI-001",
    name: "Denis Muhando Adira",
    nationalId: "27005899",
    email: "dennisadira@gmail.com",
    phone: "0716360155",
    dateOfBirth: "1989-07-09",
    gender: "Male",
    nationality: "KE",
    creditScore: 698,
    scoreGrade: "Satisfactory",
    status: "active",
    lastReportDate: "2025-03-12",
    totalAccounts: 43,
    openAccounts: 5,
    totalOutstanding: 197961.94,
  },
  {
    id: "CLI-002",
    name: "Jane Wanjiku Kamau",
    nationalId: "31245678",
    email: "jane.kamau@email.com",
    phone: "0722456789",
    dateOfBirth: "1985-03-15",
    gender: "Female",
    nationality: "KE",
    creditScore: 782,
    scoreGrade: "Good",
    status: "active",
    lastReportDate: "2025-03-10",
    totalAccounts: 12,
    openAccounts: 3,
    totalOutstanding: 450000,
  },
  {
    id: "CLI-003",
    name: "Peter Otieno Odhiambo",
    nationalId: "28765432",
    email: "peter.otieno@email.com",
    phone: "0733567890",
    dateOfBirth: "1990-11-22",
    gender: "Male",
    nationality: "KE",
    creditScore: 345,
    scoreGrade: "Poor",
    status: "active",
    lastReportDate: "2025-03-08",
    totalAccounts: 8,
    openAccounts: 4,
    totalOutstanding: 1250000,
  },
  {
    id: "CLI-004",
    name: "Mary Njeri Mwangi",
    nationalId: "29876543",
    email: "mary.njeri@email.com",
    phone: "0711678901",
    dateOfBirth: "1992-06-30",
    gender: "Female",
    nationality: "KE",
    creditScore: 580,
    scoreGrade: "Fair",
    status: "pending",
    lastReportDate: "2025-02-28",
    totalAccounts: 15,
    openAccounts: 6,
    totalOutstanding: 890000,
  },
  {
    id: "CLI-005",
    name: "James Kiprop Kosgei",
    nationalId: "33456789",
    email: "james.kiprop@email.com",
    phone: "0744789012",
    dateOfBirth: "1988-01-18",
    gender: "Male",
    nationality: "KE",
    creditScore: 820,
    scoreGrade: "Excellent",
    status: "active",
    lastReportDate: "2025-03-11",
    totalAccounts: 6,
    openAccounts: 2,
    totalOutstanding: 2100000,
  },
];

export const mockAccounts: CreditAccount[] = [
  {
    id: "ACC-001",
    accountRef: "ILA_85200",
    institution: "Maisha Bora Sacco Ltd",
    sector: "Sacco",
    accountType: "Personal Loan",
    principalAmount: 35000,
    balanceAmount: 1668.05,
    status: "active",
    performanceStatus: "non-performing",
    listingDate: "2025-01-09",
    lastPayment: "2024-02-28",
    daysInArrears: 365,
    worstArrear: 365,
    arrearsAmount: 1668.05,
    repaymentHistory: [
      { month: "Mar-25", days: 365 }, { month: "Feb-25", days: 335 },
      { month: "Jan-25", days: 304 }, { month: "Dec-24", days: 274 },
      { month: "Nov-24", days: 243 }, { month: "Oct-24", days: 213 },
      { month: "Sep-24", days: 182 }, { month: "Aug-24", days: 152 },
      { month: "Jul-24", days: 121 }, { month: "Jun-24", days: 91 },
      { month: "May-24", days: 60 }, { month: "Apr-24", days: 30 },
    ],
  },
  {
    id: "ACC-002",
    accountRef: "0100010700048",
    institution: "Stanbic Bank Ltd",
    sector: "Bank",
    accountType: "Business Working",
    principalAmount: 150000,
    balanceAmount: 0,
    status: "closed",
    performanceStatus: "default-history",
    listingDate: "2022-12-10",
    lastPayment: "2023-04-28",
    daysInArrears: 0,
    worstArrear: 96,
    arrearsAmount: 0,
    repaymentHistory: [
      { month: "Apr-23", days: 0 }, { month: "Mar-23", days: 0 },
      { month: "Feb-23", days: 0 }, { month: "Jan-23", days: 30 },
      { month: "Dec-22", days: 60 }, { month: "Nov-22", days: 90 },
      { month: "Oct-22", days: 96 }, { month: "Sep-22", days: 66 },
      { month: "Aug-22", days: 35 }, { month: "Jul-22", days: 0 },
      { month: "Jun-22", days: 0 }, { month: "May-22", days: 0 },
    ],
  },
  {
    id: "ACC-003",
    accountRef: "440006635679",
    institution: "NCBA Bank Kenya PLC",
    sector: "Bank",
    accountType: "Personal Loan",
    principalAmount: 80000,
    balanceAmount: 0,
    status: "closed",
    performanceStatus: "default-history",
    listingDate: "2021-01-09",
    lastPayment: "2022-03-08",
    daysInArrears: 0,
    worstArrear: 335,
    arrearsAmount: 0,
    repaymentHistory: [
      { month: "Mar-22", days: 0 }, { month: "Feb-22", days: 335 },
      { month: "Jan-22", days: 307 }, { month: "Dec-21", days: 279 },
      { month: "Nov-21", days: 246 }, { month: "Oct-21", days: 243 },
      { month: "Sep-21", days: 181 }, { month: "Aug-21", days: 181 },
      { month: "Jul-21", days: 189 }, { month: "Jun-21", days: 159 },
      { month: "May-21", days: 121 }, { month: "Apr-21", days: 90 },
    ],
  },
  {
    id: "ACC-004",
    accountRef: "3000080330",
    institution: "Stanbic Bank Ltd",
    sector: "Bank",
    accountType: "Credit Card",
    principalAmount: 170000,
    balanceAmount: 0,
    status: "closed",
    performanceStatus: "performing",
    listingDate: "2018-08-09",
    lastPayment: "2021-04-29",
    daysInArrears: 0,
    worstArrear: 128,
    arrearsAmount: 0,
    repaymentHistory: [
      { month: "Apr-21", days: 0 }, { month: "Mar-21", days: 0 },
      { month: "Feb-21", days: 0 }, { month: "Jan-21", days: 0 },
      { month: "Dec-20", days: 0 }, { month: "Nov-20", days: 0 },
      { month: "Oct-20", days: 0 }, { month: "Sep-20", days: 0 },
      { month: "Aug-20", days: 0 }, { month: "Jul-20", days: 0 },
      { month: "Jun-20", days: 0 }, { month: "May-20", days: 0 },
    ],
  },
  {
    id: "ACC-005",
    accountRef: "25471636015520241127",
    institution: "NCBA Bank Kenya PLC",
    sector: "Bank",
    accountType: "Overdraft",
    principalAmount: 6061.06,
    balanceAmount: 0,
    status: "closed",
    performanceStatus: "performing",
    listingDate: "2024-12-02",
    lastPayment: "2024-11-29",
    daysInArrears: 0,
    worstArrear: 0,
    arrearsAmount: 0,
    repaymentHistory: [
      { month: "Dec-24", days: 0 }, { month: "Nov-24", days: 0 },
      { month: "Oct-24", days: 0 }, { month: "Sep-24", days: 0 },
      { month: "Aug-24", days: 0 }, { month: "Jul-24", days: 0 },
      { month: "Jun-24", days: 0 }, { month: "May-24", days: 0 },
      { month: "Apr-24", days: 0 }, { month: "Mar-24", days: 0 },
      { month: "Feb-24", days: 0 }, { month: "Jan-24", days: 0 },
    ],
  },
];

export const mockReport: CreditReport = {
  id: "RPT-001",
  clientId: "CLI-001",
  clientName: "Denis Muhando Adira",
  reportDate: "2025-03-12",
  bureauScore: 698,
  scoreGrade: "Satisfactory",
  ppiScore: "M3",
  source: "Athena",
  summary: {
    totalAccounts: 43,
    nonPerformingAccounts: 2,
    performingWithDefault: 6,
    performingAccounts: 37,
    totalOutstanding: 197961.94,
    totalOverdue: 15917.65,
    creditHistoryMonths: 84,
    enquiriesLast30Days: 0,
    bouncedCheques: 0,
  },
  accounts: mockAccounts,
  scoreTrend: [
    { month: "Sep", score: 200 }, { month: "Oct", score: 300 },
    { month: "Nov", score: 400 }, { month: "Dec", score: 500 },
    { month: "Jan", score: 600 }, { month: "Feb", score: 677 },
    { month: "Mar", score: 692 }, { month: "Apr", score: 698 },
  ],
};

export const adminStats = {
  totalClients: 12450,
  activeReports: 3287,
  pendingRequests: 156,
  reportsThisMonth: 892,
  revenueThisMonth: 4560000,
  avgCreditScore: 612,
  npaRate: 8.3,
  growthRate: 12.5,
};

export function getScoreColor(score: number): string {
  if (score >= 750) return "text-emerald-500";
  if (score >= 650) return "text-green-500";
  if (score >= 500) return "text-amber-500";
  if (score >= 350) return "text-orange-500";
  return "text-red-500";
}

export function getScoreBgColor(score: number): string {
  if (score >= 750) return "bg-emerald-500/10 border-emerald-500/20";
  if (score >= 650) return "bg-green-500/10 border-green-500/20";
  if (score >= 500) return "bg-amber-500/10 border-amber-500/20";
  if (score >= 350) return "bg-orange-500/10 border-orange-500/20";
  return "bg-red-500/10 border-red-500/20";
}

export function getScoreLabel(score: number): string {
  if (score >= 750) return "Excellent";
  if (score >= 650) return "Good";
  if (score >= 500) return "Satisfactory";
  if (score >= 350) return "Fair";
  return "Poor";
}

export function formatCurrency(amount: number): string {
  return `KES ${amount.toLocaleString("en-KE", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

export function getStatusColor(status: string): string {
  switch (status) {
    case "active": return "bg-emerald-500/10 text-emerald-600 border-emerald-500/20";
    case "closed": return "bg-muted text-muted-foreground border-border";
    case "settled": return "bg-blue-500/10 text-blue-600 border-blue-500/20";
    case "pending": return "bg-amber-500/10 text-amber-600 border-amber-500/20";
    case "suspended": return "bg-red-500/10 text-red-600 border-red-500/20";
    default: return "bg-muted text-muted-foreground border-border";
  }
}
