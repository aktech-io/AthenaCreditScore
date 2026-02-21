import { Routes, Route, Navigate } from 'react-router-dom';
import { useAuth } from './context/AuthContext.jsx';
import ClientShell from './components/ClientShell.jsx';
import LoginPage from './pages/LoginPage.jsx';
import ScorePage from './pages/ScorePage.jsx';
import ReportPage from './pages/ReportPage.jsx';
import DisputePage from './pages/DisputePage.jsx';
import ConsentPage from './pages/ConsentPage.jsx';

function Protected({ children }) {
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
            <Route path="/" element={<Protected><ClientShell /></Protected>}>
                <Route index element={<ScorePage />} />
                <Route path="report" element={<ReportPage />} />
                <Route path="disputes" element={<DisputePage />} />
                <Route path="consent" element={<ConsentPage />} />
            </Route>
            <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
    );
}
