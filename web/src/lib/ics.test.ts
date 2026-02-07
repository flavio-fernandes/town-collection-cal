import { describe, expect, it } from "vitest";

import { buildSubscriptionUrl } from "./ics";
import type { TownConfig } from "../types";

const town: TownConfig = {
  id: "westford_ma",
  name: "Westford, MA",
  slug: "westford-ma",
  api: {
    baseUrl: "https://trash.example.com",
    icsPath: "/town.ics",
    resolvePath: "/resolve",
    debugPath: "/debug",
    versionPath: "/version",
    streetsPath: "/streets",
  },
  ui: {
    badge: "Westford",
    heroTitle: "Title",
    heroSubtitle: "Subtitle",
    theme: {
      from: "#fff",
      via: "#fff",
      to: "#fff",
    },
    officialRoutesDoc: "https://example.com",
  },
  capabilities: {
    explicitBypass: {
      enabled: true,
      weekdayValues: ["Thursday"],
      colorValues: ["BLUE"],
      typeValues: ["trash", "recycling"],
    },
    addressResolution: {
      enabled: true,
      supportsAddressField: true,
      supportsStreetNumberFields: true,
      usesSuggestions: true,
    },
  },
};

describe("buildSubscriptionUrl", () => {
  it("omits types for default trash+recycling selection", () => {
    const url = buildSubscriptionUrl(town, {
      weekday: "Thursday",
      color: "BLUE",
      types: ["trash", "recycling"],
      days: 120,
    });

    expect(url).toBe("https://trash.example.com/town.ics?weekday=Thursday&color=BLUE&days=120");
  });

  it("includes types when user selects non-default types", () => {
    const url = buildSubscriptionUrl(town, {
      weekday: "Thursday",
      color: "BLUE",
      types: ["trash"],
      days: 120,
    });

    expect(url).toBe("https://trash.example.com/town.ics?weekday=Thursday&color=BLUE&types=trash&days=120");
  });

  it("never includes address fields", () => {
    const url = buildSubscriptionUrl(town, {
      weekday: "Thursday",
      color: "BLUE",
      types: ["trash"],
    });

    expect(url).not.toContain("address=");
    expect(url).not.toContain("street=");
    expect(url).not.toContain("number=");
  });
});
