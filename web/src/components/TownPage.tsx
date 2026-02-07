import { FormEvent, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";

import { ApiClientError, fetchDebugPreview, fetchVersion, resolveRoute } from "../lib/api";
import { buildDebugUrl, buildSubscriptionUrl } from "../lib/ics";
import type { CollectionType, ModeBSelection, RecyclingColor, TownConfig, Weekday } from "../types";
import { InstructionsTabs } from "./InstructionsTabs";

interface TownPageProps {
  town: TownConfig;
}

const ALL_TYPES: CollectionType[] = ["trash", "recycling"];
const MIN_DAYS_AHEAD = 1;
const MAX_DAYS_AHEAD = 365;

function parseDaysAhead(raw: string): { days?: number; error?: string } {
  const trimmed = raw.trim();
  if (!trimmed) {
    return {};
  }
  if (!/^\d+$/.test(trimmed)) {
    return {
      error: `Days ahead must be a whole number between ${MIN_DAYS_AHEAD} and ${MAX_DAYS_AHEAD}.`,
    };
  }
  const days = Number(trimmed);
  if (days < MIN_DAYS_AHEAD || days > MAX_DAYS_AHEAD) {
    return {
      error: `Days ahead must be between ${MIN_DAYS_AHEAD} and ${MAX_DAYS_AHEAD}.`,
    };
  }
  return { days };
}

export function TownPage({ town }: TownPageProps) {
  const heroIllustration = "/illustrations/bins-wave.svg";
  const [weekday, setWeekday] = useState<Weekday>(town.capabilities.explicitBypass.weekdayValues[0]);
  const [color, setColor] = useState<RecyclingColor>(town.capabilities.explicitBypass.colorValues[0]);
  const [selectedTypes, setSelectedTypes] = useState<CollectionType[]>([...ALL_TYPES]);
  const [daysInput, setDaysInput] = useState("");
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [showDebugLink, setShowDebugLink] = useState(false);

  const [address, setAddress] = useState("");
  const [street, setStreet] = useState("");
  const [number, setNumber] = useState("");
  const [suggestions, setSuggestions] = useState<string[]>([]);

  const [icsUrl, setIcsUrl] = useState("");
  const [debugUrl, setDebugUrl] = useState("");
  const [events, setEvents] = useState<Array<{ date: string; types: CollectionType[] }>>([]);
  const [resolvedSummary, setResolvedSummary] = useState<string>("");

  const [version, setVersion] = useState<string>("");
  const [error, setError] = useState<string>("");
  const [loading, setLoading] = useState(false);
  const [copyState, setCopyState] = useState<"idle" | "done">("idle");

  const daysValidation = useMemo(() => parseDaysAhead(daysInput), [daysInput]);

  useEffect(() => {
    void (async () => {
      try {
        const data = await fetchVersion(town);
        const generatedAt = data.meta?.generated_at ? new Date(data.meta.generated_at).toLocaleString() : "unknown";
        setVersion(`service ${data.service_version ?? "n/a"} · schema ${data.schema_version} · generated ${generatedAt}`);
      } catch {
        setVersion("version unavailable");
      }
    })();
  }, [town]);

  const modeBSelection = useMemo<ModeBSelection>(() => {
    return {
      weekday,
      color,
      types: selectedTypes.length ? selectedTypes : ALL_TYPES,
      days: daysValidation.days,
    };
  }, [color, daysValidation.days, selectedTypes, weekday]);

  async function runPreview(selection: ModeBSelection, summary?: string) {
    setLoading(true);
    setError("");
    setSuggestions([]);
    try {
      const response = await fetchDebugPreview(town, selection);
      setEvents(response.events.slice(0, 12));
      setIcsUrl(buildSubscriptionUrl(town, selection));
      setDebugUrl(buildDebugUrl(town, selection));
      if (summary) {
        setResolvedSummary(summary);
      }
    } catch (err) {
      if (err instanceof ApiClientError) {
        setError(err.message);
      } else {
        setError("Unable to generate preview right now.");
      }
    } finally {
      setLoading(false);
    }
  }

  async function handleKnownSubmit(event: FormEvent) {
    event.preventDefault();
    if (daysValidation.error) {
      setError(daysValidation.error);
      return;
    }
    setResolvedSummary("");
    await runPreview(modeBSelection);
  }

  async function handleResolveSubmit(event: FormEvent) {
    event.preventDefault();
    await performResolve({
      address,
      street,
      number,
    });
  }

  async function performResolve(input: { address?: string; street?: string; number?: string }) {
    if (daysValidation.error) {
      setError(daysValidation.error);
      return;
    }
    setLoading(true);
    setError("");
    setSuggestions([]);

    try {
      const resolved = await resolveRoute(town, input);
      const nextWeekday = resolved.route.weekday;
      const nextColor = resolved.route.recycling_color;

      if (!nextWeekday || !nextColor) {
        setError("Resolved route is missing weekday/color. Please try the direct mode.");
        return;
      }

      setWeekday(nextWeekday);
      setColor(nextColor);

      const summary = `Resolved to ${nextWeekday} + ${nextColor}`;
      setResolvedSummary(summary);
      await runPreview(
        {
          ...modeBSelection,
          weekday: nextWeekday,
          color: nextColor,
        },
        summary,
      );
    } catch (err) {
      if (err instanceof ApiClientError) {
        setError(err.message);
        setSuggestions(err.suggestions);
        if (err.requiresNumber) {
          setError("This street needs a house number to find the right route.");
        }
      } else {
        setError("Unable to resolve this address right now.");
      }
    } finally {
      setLoading(false);
    }
  }

  async function handleSuggestionClick(value: string) {
    setStreet(value);
    setAddress("");
    await performResolve({
      street: value,
      number,
    });
  }

  async function copyUrl() {
    if (!icsUrl) {
      return;
    }
    try {
      await navigator.clipboard.writeText(icsUrl);
      setCopyState("done");
      window.setTimeout(() => setCopyState("idle"), 1400);
    } catch {
      setError("Could not copy automatically. Please copy the URL manually.");
    }
  }

  function toggleType(value: CollectionType) {
    setSelectedTypes((prev) => {
      const exists = prev.includes(value);
      if (exists) {
        const next = prev.filter((item) => item !== value);
        return next.length ? next : prev;
      }
      return [...prev, value];
    });
  }

  return (
    <main className="mx-auto w-full max-w-6xl px-4 py-8 md:px-8">
      <Link to="/" className="text-sm font-medium text-teal-800 hover:text-teal-950">
        Back to towns
      </Link>

      <section
        className="mt-4 rounded-3xl border border-white/60 p-8 shadow-glass"
        style={{
          background: `linear-gradient(135deg, ${town.ui.theme.from}, ${town.ui.theme.via}, ${town.ui.theme.to})`,
        }}
      >
        <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <div>
            <p className="inline-flex rounded-full bg-white/70 px-3 py-1 text-xs font-semibold uppercase tracking-wide text-teal-800">
              {town.ui.badge}
            </p>
            <h1 className="mt-3 font-heading text-4xl text-slate-900">{town.ui.heroTitle}</h1>
            <p className="mt-3 max-w-2xl text-sm text-slate-700">{town.ui.heroSubtitle}</p>
          </div>

          <img
            src={heroIllustration}
            className="h-24 w-24 shrink-0"
            alt="Cartoon-style trash and recycling bins"
          />
        </div>

        <p className="mt-4 text-xs text-slate-600">{version}</p>
      </section>

      <section className="mt-6 grid gap-6 lg:grid-cols-2">
        <form onSubmit={handleKnownSubmit} className="rounded-3xl border border-white/50 bg-white/75 p-6 shadow-glass backdrop-blur">
          <h2 className="font-heading text-2xl text-slate-800">I know my pickup day and bin color</h2>
          <p className="mt-2 text-sm text-slate-600">
            Generate a subscription URL directly from known route details.
          </p>

          <div className="mt-4 grid gap-4 md:grid-cols-2">
            <label className="text-sm text-slate-700">
              Weekday
              <select
                className="mt-1 w-full rounded-xl border border-slate-200 bg-white px-3 py-2"
                value={weekday}
                onChange={(event) => setWeekday(event.target.value as Weekday)}
              >
                {town.capabilities.explicitBypass.weekdayValues.map((value) => (
                  <option key={value} value={value}>
                    {value}
                  </option>
                ))}
              </select>
            </label>

            <label className="text-sm text-slate-700">
              Recycling color
              <select
                className="mt-1 w-full rounded-xl border border-slate-200 bg-white px-3 py-2"
                value={color}
                onChange={(event) => setColor(event.target.value as RecyclingColor)}
              >
                {town.capabilities.explicitBypass.colorValues.map((value) => (
                  <option key={value} value={value}>
                    {value}
                  </option>
                ))}
              </select>
            </label>
          </div>

          <button
            type="button"
            className="mt-4 block w-fit text-sm font-medium text-teal-800 underline decoration-dotted underline-offset-4"
            onClick={() => setShowAdvanced((prev) => !prev)}
          >
            {showAdvanced ? "Hide" : "Show"} advanced options
          </button>

          {showAdvanced && (
            <div className="mt-4 rounded-2xl border border-slate-200 bg-slate-50/70 p-4">
              <p className="text-sm font-medium text-slate-700">Types</p>
              <div className="mt-2 flex flex-wrap gap-2">
                {ALL_TYPES.map((type) => {
                  const active = selectedTypes.includes(type);
                  return (
                    <button
                      type="button"
                      key={type}
                      onClick={() => toggleType(type)}
                      className={`rounded-full px-3 py-1 text-sm ${
                        active
                          ? "bg-teal-700 text-white"
                          : "bg-white text-slate-700 ring-1 ring-slate-200"
                      }`}
                    >
                      {type}
                    </button>
                  );
                })}
              </div>

              <label className="mt-4 block text-sm text-slate-700">
                Days ahead (optional)
                <input
                  type="number"
                  min={MIN_DAYS_AHEAD}
                  max={MAX_DAYS_AHEAD}
                  step={1}
                  inputMode="numeric"
                  aria-invalid={Boolean(daysValidation.error)}
                  value={daysInput}
                  onChange={(event) => setDaysInput(event.target.value)}
                  placeholder="Use backend default"
                  className="mt-1 w-full rounded-xl border border-slate-200 bg-white px-3 py-2"
                />
              </label>
              {daysValidation.error && (
                <p className="mt-2 text-xs text-rose-700">{daysValidation.error}</p>
              )}

              <label className="mt-4 inline-flex items-center gap-2 text-sm text-slate-700">
                <input
                  type="checkbox"
                  checked={showDebugLink}
                  onChange={(event) => setShowDebugLink(event.target.checked)}
                />
                Show troubleshooting debug link
              </label>
            </div>
          )}

          <button
            type="submit"
            className="mt-5 rounded-xl bg-teal-800 px-4 py-2 text-sm font-semibold text-white hover:bg-teal-900"
          >
            {loading ? "Generating..." : "Generate preview and URL"}
          </button>
        </form>

        <form onSubmit={handleResolveSubmit} className="rounded-3xl border border-white/50 bg-white/75 p-6 shadow-glass backdrop-blur">
          <h2 className="font-heading text-2xl text-slate-800">I do not know my pickup info</h2>
          <p className="mt-2 text-sm text-slate-600">Resolve your route from address.</p>

          <label className="mt-4 block text-sm text-slate-700">
            Full address (optional)
            <input
              type="text"
              value={address}
              onChange={(event) => setAddress(event.target.value)}
              placeholder="65 Boston Road, Westford, MA 01886"
              className="mt-1 w-full rounded-xl border border-slate-200 bg-white px-3 py-2"
            />
          </label>

          <p className="mt-3 text-center text-xs uppercase tracking-wide text-slate-500">or</p>

          <div className="mt-3 grid gap-3 md:grid-cols-[1fr_140px]">
            <label className="text-sm text-slate-700">
              Street
              <input
                type="text"
                value={street}
                onChange={(event) => setStreet(event.target.value)}
                placeholder="Boston Road"
                className="mt-1 w-full rounded-xl border border-slate-200 bg-white px-3 py-2"
              />
            </label>

            <label className="text-sm text-slate-700">
              Number
              <input
                type="text"
                value={number}
                onChange={(event) => setNumber(event.target.value)}
                placeholder="65"
                className="mt-1 w-full rounded-xl border border-slate-200 bg-white px-3 py-2"
              />
            </label>
          </div>

          <button
            type="submit"
            className="mt-5 rounded-xl bg-sky-700 px-4 py-2 text-sm font-semibold text-white hover:bg-sky-800"
          >
            {loading ? "Resolving..." : "Resolve and generate"}
          </button>

          {!!suggestions.length && (
            <div className="mt-4 rounded-2xl border border-slate-200 bg-slate-50 p-3">
              <p className="text-sm font-medium text-slate-700">Did you mean:</p>
              <div className="mt-2 flex flex-wrap gap-2">
                {suggestions.map((item) => (
                  <button
                    key={item}
                    type="button"
                    onClick={() => void handleSuggestionClick(item)}
                    className="rounded-full bg-white px-3 py-1 text-sm text-slate-700 ring-1 ring-slate-300"
                  >
                    {item}
                  </button>
                ))}
              </div>
            </div>
          )}

          <p className="mt-4 text-xs text-slate-600">
            Need official route references? <a href={town.ui.officialRoutesDoc} className="text-teal-800 underline">Open town document</a>
          </p>
        </form>
      </section>

      {(error || icsUrl) && (
        <section className="mt-6 rounded-3xl border border-white/50 bg-white/75 p-6 shadow-glass backdrop-blur">
          {error && <p className="rounded-xl bg-rose-50 px-3 py-2 text-sm text-rose-700">{error}</p>}

          {icsUrl && (
            <>
              <h3 className="mt-2 font-heading text-2xl text-slate-800">Your subscription URL</h3>
              {resolvedSummary && <p className="mt-1 text-sm text-slate-600">{resolvedSummary}</p>}
              <p className="mt-3 break-all rounded-xl bg-slate-100 p-3 font-mono text-xs text-slate-700">{icsUrl}</p>

              <div className="mt-4 flex flex-wrap gap-3">
                <a
                  className="pressable rounded-xl bg-teal-800 px-4 py-2 text-sm font-semibold text-white hover:bg-teal-900"
                  href={icsUrl}
                  target="_blank"
                  rel="noreferrer"
                >
                  Open subscription URL
                </a>
                <button
                  type="button"
                  onClick={() => void copyUrl()}
                  className="rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700"
                >
                  {copyState === "done" ? "Copied" : "Copy URL"}
                </button>
                {showAdvanced && showDebugLink && debugUrl && (
                  <a
                    className="pressable rounded-xl border border-slate-300 bg-slate-50 px-4 py-2 text-sm font-semibold text-slate-700"
                    href={debugUrl}
                    target="_blank"
                    rel="noreferrer"
                  >
                    Open debug link
                  </a>
                )}
              </div>

              {!!events.length && (
                <div className="mt-4">
                  <p className="text-sm font-medium text-slate-700">Upcoming preview</p>
                  <ul className="mt-2 grid gap-2 sm:grid-cols-2">
                    {events.map((event) => (
                      <li key={`${event.date}-${event.types.join("-")}`} className="rounded-xl bg-white px-3 py-2 text-sm text-slate-700 ring-1 ring-slate-200">
                        <span className="font-medium">{event.date}</span>
                        <span className="ml-2 text-xs uppercase tracking-wide text-slate-500">{event.types.join(" + ")}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </>
          )}
        </section>
      )}

      {icsUrl && <div className="mt-6"><InstructionsTabs icsUrl={icsUrl} /></div>}
    </main>
  );
}
