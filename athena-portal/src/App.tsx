import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider, useAuth } from "@/lib/auth";
import Landing from "./pages/Landing";
import Login from "./pages/Login";
import AdminLogin from "./pages/AdminLogin";
import NotFound from "./pages/NotFound";
import AdminLayout from "./components/layouts/AdminLayout";
import AdminDashboard from "./pages/admin/AdminDashboard";
import CustomerSearch from "./pages/admin/CustomerSearch";
import AdminReports from "./pages/admin/AdminReports";
import AdminDisputes from "./pages/admin/AdminDisputes";
import ModelConfig from "./pages/admin/ModelConfig";
import AdminAnalytics from "./pages/admin/AdminAnalytics";
import AuditLogs from "./pages/admin/AuditLogs";
import NPLAnalytics from "./pages/admin/NPLAnalytics";
import UserManagement from "./pages/admin/UserManagement";
import NotificationManagement from "./pages/admin/NotificationManagement";
import SystemConfiguration from "./pages/admin/SystemConfiguration";
import ClientLayout from "./components/layouts/ClientLayout";
import ClientDashboard from "./pages/client/ClientDashboard";
import CreditReport from "./pages/client/CreditReport";
import ClientDisputes from "./pages/client/ClientDisputes";
import ClientAlerts from "./pages/client/ClientAlerts";
import ScoreSimulator from "./pages/client/ScoreSimulator";
import CreditFreeze from "./pages/client/CreditFreeze";
import ConsentManagement from "./pages/client/ConsentManagement";
import CreditEducation from "./pages/client/CreditEducation";
import ClientSettings from "./pages/client/ClientSettings";
import BureauComparison from "./pages/client/BureauComparison";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
      staleTime: 30_000,
    },
  },
});

function AdminGuard({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isAdmin } = useAuth();
  if (!isAuthenticated || !isAdmin) return <Navigate to="/admin-login" replace />;
  return <>{children}</>;
}

function ClientGuard({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isCustomer } = useAuth();
  if (!isAuthenticated || !isCustomer) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

const App = () => (
  <QueryClientProvider client={queryClient}>
    <AuthProvider>
      <TooltipProvider>
        <Toaster />
        <Sonner />
        <BrowserRouter>
          <Routes>
            <Route path="/" element={<Landing />} />
            <Route path="/login" element={<Login />} />
            <Route path="/admin-login" element={<AdminLogin />} />

            {/* Admin Portal */}
            <Route path="/admin" element={<AdminGuard><AdminLayout /></AdminGuard>}>
              <Route index element={<AdminDashboard />} />
              <Route path="customers" element={<CustomerSearch />} />
              <Route path="reports" element={<AdminReports />} />
              <Route path="disputes" element={<AdminDisputes />} />
              <Route path="models" element={<ModelConfig />} />
              <Route path="analytics" element={<AdminAnalytics />} />
              <Route path="audit" element={<AuditLogs />} />
              <Route path="npl" element={<NPLAnalytics />} />
              <Route path="users" element={<UserManagement />} />
              <Route path="notifications" element={<NotificationManagement />} />
              <Route path="config" element={<SystemConfiguration />} />
            </Route>

            {/* Client Portal */}
            <Route path="/client" element={<ClientGuard><ClientLayout /></ClientGuard>}>
              <Route index element={<ClientDashboard />} />
              <Route path="report" element={<CreditReport />} />
              <Route path="bureau" element={<BureauComparison />} />
              <Route path="disputes" element={<ClientDisputes />} />
              <Route path="alerts" element={<ClientAlerts />} />
              <Route path="simulator" element={<ScoreSimulator />} />
              <Route path="freeze" element={<CreditFreeze />} />
              <Route path="consent" element={<ConsentManagement />} />
              <Route path="education" element={<CreditEducation />} />
              <Route path="settings" element={<ClientSettings />} />
            </Route>

            <Route path="*" element={<NotFound />} />
          </Routes>
        </BrowserRouter>
      </TooltipProvider>
    </AuthProvider>
  </QueryClientProvider>
);

export default App;
