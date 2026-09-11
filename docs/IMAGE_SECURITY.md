# Container security and release checks

The production image uses Python 3.11 on Debian Bookworm. Its base is pinned to a
multi-platform digest, and available Debian package updates are applied in a
shared base stage before building the application and runtime. Updating packages
only in a discarded compiler stage does not patch the final image.

Application dependencies are constrained in `requirements/runtime.txt`. The
initial constraints preserve the runtime versions verified in v0.2.4, including
the optional trained address parser. Update these constraints deliberately when
fixes become available and run the same regression checks.

The application is installed into a clean `/opt/venv`, which is copied into the
runtime instead of overlaying the base image's `/usr/local`. Production excludes
pip, setuptools, wheel, ensurepip, compilers, and test tooling. This removes
unused bundled dependencies and avoids conflicting package metadata. Application
files are owned by root and read by the non-root service user. Use the existing
read-only filesystem and capability restrictions when deploying.

The development image retains packaging and compilation tools for development;
it is not the production deployment image.

## Local verification

From the repository root:

```bash
docker build --pull --target test -t town-collection-cal:test .
docker build -t town-collection-cal:candidate .
docker run --rm --network none --read-only \
  -v "$PWD/scripts/check_runtime_image.py:/check_runtime_image.py:ro" \
  town-collection-cal:candidate python /check_runtime_image.py
docker scout cves local://town-collection-cal:candidate
docker scout cves --only-fixed --only-severity critical,high --exit-code \
  local://town-collection-cal:candidate
```

The test target runs the existing suite against the installed production package
as the non-root user, with test tooling added only to that target. The runtime
check verifies packaging-tool removal, absence of duplicate distribution
metadata, and that the trained address parser works without silently falling
back. The normal default image does not contain the test target's files.

Also rebuild the DB from the live town PDFs and compare routes, calendar policy,
holiday policy, and all pickup dates with the previous release. Generated
timestamps and build commit metadata are expected to differ. Check API and ICS
output using the same non-root/read-only deployment options as production.

## CI and publishing

CI runs the container tests and runtime check, rejects fixable high/critical OS
or library vulnerabilities using Trivy, and exercises a live-PDF DB build and
hardened service startup. A release must pass CI before its version tag is pushed.
The publishing workflow attaches an SBOM and maximum-level provenance to images
for both supported architectures. Build arguments must contain public build
metadata only; credentials belong in secret mounts, never build arguments.

After publishing, scan the actual tagged image for each architecture, confirm
its SBOM/provenance, and compare it with the previous release before deployment.
Scanner databases evolve: record the scan date, platform, and image digest when
assessing a release. A successful application health check is not a vulnerability
scan.

## Remaining findings

A zero count of fixable high/critical findings is not a claim of zero
vulnerabilities. Retain the full scan report and review findings without an
available distribution fix for applicability, exposure, and future remediation.
Do not suppress findings merely to improve the score. Copyleft licensing policy
and missing build attestations are separate from exploitable application flaws.

References:

- [Docker SBOM and provenance attestations](https://docs.docker.com/build/ci/github-actions/attestations/)
- [Debian security tracker](https://security-tracker.debian.org/tracker/)
