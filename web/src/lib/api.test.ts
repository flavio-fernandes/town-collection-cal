import { describe, expect, it } from "vitest";

import { normalizeSuggestions } from "./api";

describe("normalizeSuggestions", () => {
  it("returns string suggestions unchanged", () => {
    expect(normalizeSuggestions(["Boston Road", "Main Street"])).toEqual([
      "Boston Road",
      "Main Street",
    ]);
  });

  it("supports object suggestions with street field for future-proofing", () => {
    expect(
      normalizeSuggestions([
        { street: "Boston Road", score: 99 },
        { street: "Main Street" },
        { label: "Ignore" },
      ]),
    ).toEqual(["Boston Road", "Main Street"]);
  });

  it("returns empty list for invalid payloads", () => {
    expect(normalizeSuggestions(undefined)).toEqual([]);
    expect(normalizeSuggestions("x")).toEqual([]);
  });
});
