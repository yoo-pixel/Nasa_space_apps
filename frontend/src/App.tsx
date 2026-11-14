import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Navigate, Route, Routes } from "react-router-dom";
import Layout from "./components/Layout";
import Dashboard from "./pages/Dashboard";
import Crew from "./pages/Crew";
import Profile from "./pages/Profile";
import Checkin from "./pages/Checkin";
import Analytics from "./pages/Analytics";
import Alerts from "./pages/Alerts";
import Review from "./pages/Review";
import DataSources from "./pages/DataSources";
import Settings from "./pages/Settings";
import PersonalizedLearning from "./pages/PersonalizedLearning";
import BoneHealth from "./pages/BoneHealth";
import RadiationMonitoring from "./pages/RadiationMonitoring";
import HealthDomains from "./pages/HealthDomains";
import { CrewSelectionProvider } from "./state/CrewSelection";

const queryClient = new QueryClient({ defaultOptions: { queries: { retry: 1, staleTime: 15000, refetchOnWindowFocus: false } } });

export default function App() {
  return <QueryClientProvider client={queryClient}><CrewSelectionProvider><Routes><Route element={<Layout />}>
    <Route path="/" element={<Dashboard />} />
    <Route path="/crew" element={<Crew />} />
    <Route path="/crew/:id" element={<Profile />} />
    <Route path="/check-in" element={<Checkin />} />
    <Route path="/personalized-learning" element={<PersonalizedLearning />} />
    <Route path="/bone-health" element={<BoneHealth />} />
    <Route path="/radiation" element={<RadiationMonitoring />} />
    <Route path="/health-domains" element={<HealthDomains />} />
    <Route path="/analytics" element={<Analytics />} />
    <Route path="/alerts" element={<Alerts />} />
    <Route path="/review" element={<Review />} />
    <Route path="/data-sources" element={<DataSources />} />
    <Route path="/settings" element={<Settings />} />
    <Route path="*" element={<Navigate to="/" replace />} />
  </Route></Routes></CrewSelectionProvider></QueryClientProvider>;
}
