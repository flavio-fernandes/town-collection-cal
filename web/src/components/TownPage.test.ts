import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { createElement } from "react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { TownPage } from "./TownPage";
import { ApiClientError, fetchDebugPreview, fetchVersion, resolveRoute } from "../lib/api";
import type { TownConfig } from "../types";

vi.mock("../lib/api", () => {
  class ApiClientError extends Error {
    readonly status?: number;
    readonly suggestions: string[];
    readonly requiresNumber: boolean;

    constructor(message: string, options?: { status?: number; suggestions?: string[]; requiresNumber?: boolean }) {
      super(message);
      this.name = "ApiClientError";
      this.status = options?.status;
      this.suggestions = options?.suggestions ?? [];
      this.requiresNumber = options?.requiresNumber ?? false;
    }
  }

  return {
    ApiClientError,
    fetchDebugPreview: vi.fn(),
    fetchVersion: vi.fn(),
    resolveRoute: vi.fn(),
  };
});

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
    heroTitle: "Trash and Recycling Calendar",
    heroSubtitle: "Subscribe once and keep your collection schedule current.",
    theme: {
      from: "#d0efe8",
      via: "#d8edf7",
      to: "#f3ebd8",
    },
    officialRoutesDoc: "https://example.com/routes",
  },
  capabilities: {
    explicitBypass: {
      enabled: true,
      weekdayValues: ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
      colorValues: ["BLUE", "GREEN"],
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

const mockedFetchDebugPreview = vi.mocked(fetchDebugPreview);
const mockedFetchVersion = vi.mocked(fetchVersion);
const mockedResolveRoute = vi.mocked(resolveRoute);

describe("TownPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockedFetchVersion.mockResolvedValue({
      service_version: "0.1.0",
      schema_version: 1,
      meta: {
        generated_at: "2026-02-01T00:00:00Z",
      },
    });
  });

  it("clears stale subscription output when resolve returns no-pickup error", async () => {
    mockedFetchDebugPreview.mockResolvedValue({
      mode: "bypass",
      days: 365,
      types: ["trash", "recycling"],
      events: [
        { date: "2026-02-10", types: ["trash"] },
      ],
    });
    mockedResolveRoute.mockRejectedValue(new ApiClientError("No municipal collection for this address"));

    render(createElement(MemoryRouter, undefined, createElement(TownPage, { town })));

    fireEvent.click(screen.getByRole("button", { name: "Generate preview and URL" }));
    await screen.findByText("Your subscription URL");
    expect(screen.getByRole("link", { name: "Open subscription URL" })).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Street"), {
      target: { value: "No pickup road" },
    });
    fireEvent.change(screen.getByLabelText("Number"), {
      target: { value: "1" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Resolve and generate" }));

    await screen.findByText("No municipal collection for this address");
    await waitFor(() => {
      expect(screen.queryByText("Your subscription URL")).not.toBeInTheDocument();
      expect(screen.queryByRole("link", { name: "Open subscription URL" })).not.toBeInTheDocument();
    });
  });
});
