## Goal

Document the shared artefacts, responsibilities, and steps for the new CI/CD orchestration flow driven from `shopifake-back`.

## Overview

- `dev`, `staging`, and `main` are the source-of-truth branches.
- Every microservice publishes Docker images tagged with the commit SHA on `main`.
- Promotions from `dev` to `staging` start with a manually created pull request; the pipeline automatically generates the lock associated with that PR.
- Once merged into `staging`, both Staging and Production deployments consume this shared **lock**, ensuring full parity.

## Shared Artefacts

| Artefact | Contents | Owner | Storage |
| --- | --- | --- | --- |
| Batch lock | For each microservice: Git SHA, image tag (SHA), OCI digest, timestamp | PR CI workflow | CI artefact + committed to `staging` on merge |
| Scripts | `scripts/generate_lock.py` and orchestration helpers | central repo | versioned |
| QA reports | Lint/Test/E2E results | GitHub Actions | CI artefacts + PR comments |

## Local Preparation (manual)

- Developers update the desired submodules manually, run local tests, then push their changes to `dev`.
- No central automation here: this is a local workshop before opening the `dev` → `staging` PR.

## Promotion dev → staging (manual PR + auto lock)

1. Developers open the `dev` → `staging` PR containing only submodule bumps and related changes.
2. On PR open, CI spins up the full stack (via docker compose) and runs integration + system tests, then automatically generates the lock (Git SHAs + tags + digests), publishing it as an artefact and/or PR comment.
3. The PR is merged manually once all checks pass; no auto-merge.
4. During merge, the workflow commits the lock to the `staging` branch so it becomes the deployment reference.

## Post-merge to staging

1. A workflow triggers on `staging` after the merge.
2. Steps:
   - Retrieve the lock committed during the merge (versioned file in `staging`).
   - Run Staging cluster health checks (API reachability, nodes, quotas, critical dependencies). Abort if unhealthy.
   - Deploy using the lock (pinned images) automatically after the checks, while keeping a `workflow_dispatch` entry point for manual reruns if needed.
   - Execute the same E2E/system suite against real Staging (including spinning up/building every service required) to confirm cross-service interactions.
   - If successful, open the `staging` → `main` PR carrying the unchanged lock.
   - On failure, do not open the PR; fix issues and rerun the manual deployment entry point.

## PR staging → main and Production

1. **`staging` → `main` PR**
   - Requires validation by the four designated reviewers.
   - Reviewers verify the functionality on the live Staging environment deployed with the lock.
2. **Post-merge workflow on `main`**
   - Run Production health checks (blocking).
   - Deploy to Production from the same lock automatically after merge, while exposing a `workflow_dispatch` trigger for manual reruns when necessary.
   - Execute post-deploy smoke tests.
   - Tag the release and archive the lock (enables fast rollback).

## Microservice prerequisites

- Keep the existing build strategy: per-repo CI, Docker images tagged by SHA.
- Expose required metadata (digest, version, API spec) as CI outputs so the central lock generator can consume them.
- Ensure submodules can be bumped cleanly (no lingering local commits).

## Next steps

1. Finalise the lock format (`locks/schema.json`, YAML template).
2. Draft the shared scripts/libraries required to generate and consume the lock.
3. Describe the GitHub Actions workflows: job structure, permissions, secrets, automatic triggers plus optional manual reruns.
4. Publish user-facing documentation (orchestrator README, trigger guide).

