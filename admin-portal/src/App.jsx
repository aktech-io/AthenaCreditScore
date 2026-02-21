import { Routes, Route, Navigate } from 'react-router-dom';
import { useAuth } from './context/AuthContext.jsx';
import Layout from './components/Layout.jsx';
import LoginPage from './pages/LoginPage.jsx';
import DashboardPage from './pages/DashboardPage.jsx';
import CustomerSearchPage from './pages/CustomerSearchPage.jsx';
import DisputesPage from './pages/DisputesPage.jsx';
import ModelConfigPage from './pages/ModelConfigPage.jsx';
import AuditLogPage from './pages/AuditLogPage.jsx';

function ProtectedRoute({ children }) {
    const { isAuthenticated } = useAuth();
    return isAuthenticated ? children : <Navigate to="/login" replace />;
}

export default function App() {
    const { isAuthenticated } = useAuth();

    return (
        <Routes>
            <Route path="/login" element={
                isAuthenticated ? <Navigate to="/" replace /> : <LoginPage />
            } />
            <Route path="/" element={
                <ProtectedRoute><Layout /></ProtectedRoute>
            }>
                <Route index element={<DashboardPage />} />
                <Route path="customers" element={<CustomerSearchPage />} />
                <Route path="disputes" element={<DisputesPage />} />
                <Route path="model" element={<ModelConfigPage />} />
                <Route path="audit" element={<AuditLogPage />} />
            </Route>
            <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
    );
}
