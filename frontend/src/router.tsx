import { Navigate, Outlet, Route, Routes, useLocation } from 'react-router-dom';
import { useAuth } from '@/auth/AuthContext';
import DashboardPage from '@/pages/DashboardPage';
import ExpenseFormPage from '@/pages/ExpenseFormPage';
import ExpenseListPage from '@/pages/ExpenseListPage';
import GroupDetailPage from '@/pages/GroupDetailPage';
import SignInPage from '@/pages/SignInPage';

function ProtectedRoute() {
  const { isAuthenticated, isLoading } = useAuth();
  const location = useLocation();

  if (isLoading) return <div>Loading…</div>;
  if (!isAuthenticated) {
    return <Navigate to="/signin" state={{ from: location }} replace />;
  }
  return <Outlet />;
}

export default function AppRouter() {
  return (
    <Routes>
      <Route path="/signin" element={<SignInPage />} />
      <Route element={<ProtectedRoute />}>
        <Route path="/dashboard" element={<DashboardPage />} />
        <Route path="/groups/:id" element={<GroupDetailPage />} />
        <Route path="/groups/:id/expenses" element={<ExpenseListPage />} />
        <Route path="/groups/:id/expenses/new" element={<ExpenseFormPage />} />
      </Route>
      <Route path="/" element={<Navigate to="/dashboard" replace />} />
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  );
}
