export type Weekday = "Monday" | "Tuesday" | "Wednesday" | "Thursday" | "Friday";

export type RecyclingColor = "BLUE" | "GREEN";

export type CollectionType = "trash" | "recycling";

export interface TownApiConfig {
  baseUrl: string;
  icsPath: string;
  resolvePath: string;
  debugPath: string;
  versionPath: string;
  streetsPath: string;
}

export interface TownTheme {
  from: string;
  via: string;
  to: string;
}

export interface TownUiConfig {
  badge: string;
  heroTitle: string;
  heroSubtitle: string;
  theme: TownTheme;
  officialRoutesDoc: string;
}

export interface TownCapabilities {
  explicitBypass: {
    enabled: boolean;
    weekdayValues: Weekday[];
    colorValues: RecyclingColor[];
    typeValues: CollectionType[];
  };
  addressResolution: {
    enabled: boolean;
    supportsAddressField: boolean;
    supportsStreetNumberFields: boolean;
    usesSuggestions: boolean;
  };
}

export interface TownConfig {
  id: string;
  name: string;
  slug: string;
  api: TownApiConfig;
  ui: TownUiConfig;
  capabilities: TownCapabilities;
}

export interface TownRegistry {
  towns: TownConfig[];
}

export interface ResolveRoute {
  weekday?: Weekday;
  recycling_color?: RecyclingColor;
}

export interface ResolveSuccess {
  mode: "address";
  route: ResolveRoute;
}

export interface ResolveError {
  error: string;
  suggestions?: string[];
  requires_number?: boolean;
}

export interface DebugEvent {
  date: string;
  types: CollectionType[];
}

export interface DebugSuccess {
  mode: "bypass" | "address";
  days: number;
  types: CollectionType[];
  events: DebugEvent[];
}

export interface VersionResponse {
  service_version?: string;
  schema_version: number;
  meta?: {
    generated_at?: string;
    town_id?: string;
  };
}

export interface ModeBSelection {
  weekday: Weekday;
  color: RecyclingColor;
  types: CollectionType[];
  days?: number;
}
