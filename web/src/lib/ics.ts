import type { CollectionType, ModeBSelection, TownConfig } from "../types";

function uniqueTypes(input: CollectionType[]): CollectionType[] {
  const set = new Set(input);
  const ordered: CollectionType[] = [];
  if (set.has("trash")) {
    ordered.push("trash");
  }
  if (set.has("recycling")) {
    ordered.push("recycling");
  }
  return ordered.length ? ordered : ["trash", "recycling"];
}

function isDefaultTypes(types: CollectionType[]): boolean {
  return types.length === 2 && types[0] === "trash" && types[1] === "recycling";
}

function parseDays(days?: number): number | undefined {
  if (!days || Number.isNaN(days) || days < 1) {
    return undefined;
  }
  return Math.floor(days);
}

function apiBase(town: TownConfig): string {
  const fromEnv = import.meta.env.VITE_API_BASE_URL?.trim();
  const fromTown = town.api.baseUrl?.trim();
  if (fromEnv) {
    return fromEnv;
  }
  if (fromTown) {
    return fromTown;
  }
  if (typeof window !== "undefined") {
    return window.location.origin;
  }
  return "http://localhost";
}

function buildModeBUrl(path: string, town: TownConfig, selection: ModeBSelection): string {
  const url = new URL(path, apiBase(town));
  const types = uniqueTypes(selection.types);
  const days = parseDays(selection.days);

  url.searchParams.set("weekday", selection.weekday);
  url.searchParams.set("color", selection.color);
  if (!isDefaultTypes(types)) {
    url.searchParams.set("types", types.join(","));
  }
  if (days) {
    url.searchParams.set("days", String(days));
  }

  return url.toString();
}

export function buildSubscriptionUrl(town: TownConfig, selection: ModeBSelection): string {
  return buildModeBUrl(town.api.icsPath, town, selection);
}

export function buildDebugUrl(town: TownConfig, selection: ModeBSelection): string {
  return buildModeBUrl(town.api.debugPath, town, selection);
}

export function toWebcal(url: string): string {
  if (url.startsWith("https://")) {
    return `webcal://${url.slice("https://".length)}`;
  }
  if (url.startsWith("http://")) {
    return `webcal://${url.slice("http://".length)}`;
  }
  return url;
}
