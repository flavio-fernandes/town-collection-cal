"""Run inside the production container to verify packaging and address support."""

import importlib.metadata
import importlib.util
import os
from collections import Counter
from pathlib import Path

from town_collection_cal.common import address

assert os.getuid() != 0, "Production must run as a non-root user"
for module in ("pip", "setuptools", "wheel", "ensurepip", "pytest"):
    assert importlib.util.find_spec(module) is None, f"Unexpected runtime build tool: {module}"

# Check both locations: isolated app dependencies and the base Python installation.
for location in ("/opt/venv/lib/python3.11/site-packages",
                 "/usr/local/lib/python3.11/site-packages"):
    distributions = list(importlib.metadata.distributions(path=[location]))
    names = [d.metadata["Name"].lower().replace("_", "-") for d in distributions]
    assert all(n == 1 for n in Counter(names).values()), "Duplicate distribution metadata"
    assert not {"pip", "setuptools", "wheel"}.intersection(names), location
    assert not list(Path(location).rglob("*jaraco*context*")), "Bundled build tool remains"

assert address.usaddress is not None, "Optional trained address parser silently fell back"
parsed = address.parse_address("65 Boston Road, Westford, MA 01886")
assert (parsed.house_number, parsed.street_name) == ("65", "Boston Road"), parsed
print("Runtime checks passed: non-root, no build tools or duplicate metadata, address model works")
