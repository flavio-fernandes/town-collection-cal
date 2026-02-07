import { Navigate, Route, Routes, useParams } from "react-router-dom";

import { LandingPage } from "./components/LandingPage";
import { TownPage } from "./components/TownPage";
import { findTownBySlug, listTowns } from "./lib/towns";

function TownPageRoute() {
  const { townSlug } = useParams();
  if (!townSlug) {
    return <Navigate to="/" replace />;
  }

  const town = findTownBySlug(townSlug);
  if (!town) {
    return (
      <main className="mx-auto max-w-3xl px-4 py-12">
        <h1 className="font-heading text-4xl text-slate-800">Town not found</h1>
        <p className="mt-4 text-slate-700">The requested town page is not configured yet.</p>
      </main>
    );
  }

  return <TownPage town={town} />;
}

export default function App() {
  const towns = listTowns();

  return (
    <Routes>
      <Route path="/" element={<LandingPage towns={towns} />} />
      <Route path="/towns/:townSlug" element={<TownPageRoute />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
