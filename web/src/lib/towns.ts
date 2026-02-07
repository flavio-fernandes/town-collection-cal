import registry from "../../config/towns.json";
import type { TownConfig, TownRegistry } from "../types";

const typedRegistry = registry as TownRegistry;

export function listTowns(): TownConfig[] {
  return typedRegistry.towns;
}

export function findTownBySlug(slug: string): TownConfig | undefined {
  return typedRegistry.towns.find((town) => town.slug === slug);
}
