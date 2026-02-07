import { Link } from "react-router-dom";

import type { TownConfig } from "../types";

interface LandingPageProps {
  towns: TownConfig[];
}

export function LandingPage({ towns }: LandingPageProps) {
  return (
    <main className="mx-auto flex w-full max-w-5xl flex-col gap-8 px-4 py-10 md:px-8">
      <section className="rounded-3xl border border-white/60 bg-white/70 p-8 shadow-glass backdrop-blur">
        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-teal-700">Town Collection Calendar</p>
        <h1 className="mt-3 font-heading text-4xl text-slate-800 md:text-5xl">Subscribe to collection schedules in minutes</h1>
        <p className="mt-4 max-w-3xl text-base text-slate-700">
          Pick your town, generate your personalized calendar URL, and subscribe once in Google Calendar,
          Apple Calendar, Outlook, or Home Assistant.
        </p>
      </section>

      <section>
        <h2 className="font-heading text-2xl text-slate-800">Available towns</h2>
        <div className="mt-4 grid gap-4 md:grid-cols-2">
          {towns.map((town) => (
            <Link
              key={town.id}
              to={`/towns/${town.slug}`}
              className="group rounded-3xl border border-white/60 bg-white/75 p-6 shadow-glass transition hover:-translate-y-0.5 hover:border-teal-200"
            >
              <p className="text-xs font-semibold uppercase tracking-wide text-teal-700">{town.ui.badge}</p>
              <h3 className="mt-2 font-heading text-3xl text-slate-800">{town.name}</h3>
              <p className="mt-2 text-sm text-slate-600">{town.ui.heroSubtitle}</p>
              <p className="mt-4 text-sm font-medium text-teal-700 group-hover:text-teal-800">Open town page</p>
            </Link>
          ))}
        </div>
      </section>
    </main>
  );
}
