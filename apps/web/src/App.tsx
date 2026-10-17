import { Route, Routes } from "react-router-dom";
import { AppShell } from "./components/AppShell";
import {
  AboutPage,
  HomePage,
  NotFoundPage,
  ProtectPage,
  VerifyPage,
} from "./pages/Pages";

export function App() {
  return (
    <Routes>
      <Route element={<AppShell />}>
        <Route index element={<HomePage />} />
        <Route path="protect" element={<ProtectPage />} />
        <Route path="verify" element={<VerifyPage />} />
        <Route path="about" element={<AboutPage />} />
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  );
}
