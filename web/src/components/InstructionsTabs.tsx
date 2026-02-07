import { useMemo, useState } from "react";

import { toWebcal } from "../lib/ics";

interface InstructionsTabsProps {
  icsUrl: string;
}

type Platform = "google" | "apple" | "outlook" | "ha";

export function InstructionsTabs({ icsUrl }: InstructionsTabsProps) {
  const [platform, setPlatform] = useState<Platform>("google");
  const webcalUrl = useMemo(() => toWebcal(icsUrl), [icsUrl]);

  return (
    <section className="rounded-3xl border border-white/50 bg-white/70 p-6 shadow-glass backdrop-blur">
      <h3 className="font-heading text-2xl text-slate-800">How to subscribe</h3>
      <p className="mt-2 text-sm text-slate-600">
        Use this URL as a subscription source so updates flow automatically.
      </p>

      <div className="mt-4 flex flex-wrap gap-2">
        <TabButton label="Google" active={platform === "google"} onClick={() => setPlatform("google")} />
        <TabButton label="Apple" active={platform === "apple"} onClick={() => setPlatform("apple")} />
        <TabButton label="Outlook" active={platform === "outlook"} onClick={() => setPlatform("outlook")} />
        <TabButton label="Home Assistant" active={platform === "ha"} onClick={() => setPlatform("ha")} />
      </div>

      <div className="mt-4 rounded-2xl border border-slate-200 bg-white p-4 text-sm text-slate-700">
        {platform === "google" && (
          <ol className="list-decimal space-y-2 pl-5">
            <li>Open Google Calendar in a browser.</li>
            <li>Go to Other calendars, then choose Add by URL.</li>
            <li>Paste this URL and confirm: <Code>{icsUrl}</Code>.</li>
          </ol>
        )}

        {platform === "apple" && (
          <ol className="list-decimal space-y-2 pl-5">
            <li>In Calendar, choose File then New Calendar Subscription.</li>
            <li>Paste one of these URLs and continue.</li>
            <li><Code>{icsUrl}</Code></li>
            <li><Code>{webcalUrl}</Code></li>
          </ol>
        )}

        {platform === "outlook" && (
          <ol className="list-decimal space-y-2 pl-5">
            <li>Open Outlook on the web.</li>
            <li>Go to Add calendar, then Subscribe from web.</li>
            <li>Paste this URL and save: <Code>{icsUrl}</Code>.</li>
          </ol>
        )}

        {platform === "ha" && (
          <ol className="list-decimal space-y-2 pl-5">
            <li>Open Home Assistant calendar integration settings.</li>
            <li>Add a URL-based calendar source.</li>
            <li>Use this URL: <Code>{icsUrl}</Code>.</li>
          </ol>
        )}
      </div>
    </section>
  );
}

function TabButton({
  label,
  active,
  onClick,
}: {
  label: string;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`rounded-full px-4 py-2 text-sm font-medium transition ${
        active
          ? "bg-teal-700 text-white"
          : "bg-white text-slate-700 ring-1 ring-slate-200 hover:ring-slate-300"
      }`}
    >
      {label}
    </button>
  );
}

function Code({ children }: { children: string }) {
  return <code className="rounded bg-slate-100 px-1.5 py-0.5 text-xs text-slate-900">{children}</code>;
}
