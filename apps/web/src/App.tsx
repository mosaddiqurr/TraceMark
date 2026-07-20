import { Navigate, Route, Routes, useLocation } from "react-router-dom";
import { useAuth } from "./auth/AuthContext";
import { AppShell } from "./components/AppShell";
import { FullPageLoader } from "./components/States";
import {
  AssetDetailPage, AssetsPage, AuthPage, BenchmarksPage, CollectionsPage, DashboardPage,
  DistributionsPage, JobsPage, LandingPage, MethodologyPage, NotFoundPage, ProtectPage,
  ReportsPage, ScannerPage, SettingsPage, TracePage, VerifyPage,
} from "./pages/Pages";

function ProtectedLayout() {
  const { user, loading } = useAuth();
  const location = useLocation();
  if (loading) return <FullPageLoader label="Checking your secure session" />;
  if (!user) return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  return <AppShell />;
}

export function App() {
  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />
      <Route path="/login" element={<AuthPage mode="login" />} />
      <Route path="/register" element={<AuthPage mode="register" />} />
      <Route path="/app" element={<ProtectedLayout />}>
        <Route index element={<DashboardPage />} />
        <Route path="protect" element={<ProtectPage />} />
        <Route path="assets" element={<AssetsPage />} />
        <Route path="assets/:assetId" element={<AssetDetailPage />} />
        <Route path="distributions" element={<DistributionsPage />} />
        <Route path="verify" element={<VerifyPage />} />
        <Route path="trace" element={<TracePage />} />
        <Route path="collections" element={<CollectionsPage />} />
        <Route path="scans" element={<ScannerPage />} />
        <Route path="lab" element={<BenchmarksPage />} />
        <Route path="reports" element={<ReportsPage />} />
        <Route path="jobs" element={<JobsPage />} />
        <Route path="settings" element={<SettingsPage />} />
        <Route path="methodology" element={<MethodologyPage />} />
      </Route>
      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  );
}
