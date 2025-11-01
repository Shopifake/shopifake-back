## GitHub Actions Workflow Structure

This guide lays out the GitHub Actions pipelines we will add to `shopifake-back` to implement the CI/CD flow described in `overview.md`.

### 1. Workflow `ci-dev-pr.yml`

- **Triggers**: `pull_request` targeting `staging` from `dev` (plus manual `workflow_dispatch`).
- **Goals**:
  - Bring up the full stack with docker compose and run integration + system tests.
  - Generate the lock file (`locks/<pr-number>.yml`).
  - Publish the lock as an artefact and PR comment.
- **Key jobs**:
  1. `system-tests`: spins up the stack via `compose/system-tests.compose.yml`, then executes `scripts/tests/run-integration-tests.sh` and `scripts/tests/run-system-tests.sh`.
  2. `generate-lock`: runs `scripts/lock/generate_lock.py` to capture submodule SHAs + image tags.
  3. `publish-lock`: uploads the lock artefact and posts a PR comment with its contents.

### 2. Workflow `ci-staging-post-merge.yml`

- **Triggers**: `push` on `staging` and `workflow_dispatch` (manual rerun).
- **Goals**:
  - Retrieve the lock committed when the PR merged.
  - Check the health of the Staging cluster.
  - Deploy automatically to Staging using the lock.
  - Run the E2E suite against the real environment.
  - Create the `staging` → `main` PR when successful.
- **Key jobs**:
  1. `prepare`: checkout + lock parsing.
  2. `staging-healthcheck`: `scripts/cluster/healthcheck.sh --env staging`.
  3. `deploy-staging`: apply manifests/Helm/ArgoCD with the lock images.
  4. `e2e-staging`: functional and system tests covering inter-service interactions (stack spun up with the lock images).
  5. `create-promotion-pr`: open the `staging` → `main` PR carrying the unchanged lock.

### 3. Workflow `ci-prod-post-merge.yml`

- **Triggers**: `push` on `main` and `workflow_dispatch`.
- **Goals**:
  - Read the lock promoted from `staging`.
  - Validate Production health.
  - Deploy to Production with the pinned images.
  - Execute smoke tests.
  - Tag the release and archive the lock.
- **Key jobs**:
  1. `prepare`: checkout + lock load.
  2. `prod-healthcheck`: `scripts/cluster/healthcheck.sh --env prod`.
  3. `deploy-prod`: deployment mirroring Staging.
  4. `smoke-tests`: quick post-deploy verification.
  5. `release-tag`: Git tag + long-term lock artefact.

### 4. Scripts and dependencies

- Shell/Python helpers stored under `scripts/` (e.g., `scripts/lock/generate.py`).
- Required secrets:
  - GitHub token to comment/create PRs.
  - Staging/Production kubeconfigs.
  - Registry credentials (pull private images).
- Minimal permissions:
  - `contents: write` to commit the lock on `staging`.
  - `pull-requests: write` to comment and open promotion PRs.

### 5. Artefacts produced

- `lock`: YAML file + checksum.
- `reports`: test results (JUnit, coverage, lint) – produced by downstream jobs when relevant.
- `deployment-logs`: Staging/Prod deployment logs for auditing.

### 6. Manual control points

- Staging and Prod workflows expose `workflow_dispatch` for manual reruns.
- The `staging` → `main` PR still requires four human approvals.

### 7. Next steps

1. Draft the YAML skeletons of the three workflows.
2. Implement `generate_lock.py`, `healthcheck.sh`, `deploy.sh`.
3. Configure GitHub Actions secrets/permissions.
4. Add user-facing docs (orchestrator README, trigger guides).

