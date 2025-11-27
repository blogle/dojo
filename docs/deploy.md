# Dojo Deployment & CI/CD Architecture

This document describes how to build, package, and deploy the `dojo` application using Nix-built container images and Kubernetes manifests managed by Kustomize. It is intended to be self-contained and consumable by any standard Kubernetes cluster.

The overall goals are:

- Simple and reproducible deployment for a small number of users.
- Safe handling of the DuckDB database file (no corruption, no concurrent writers).
- Minimal but useful debug tooling inside the container (e.g., busybox shell).
- A straightforward CI pipeline that runs tests, builds an image, and publishes to GitHub Container Registry (GHCR).

---

## 1. Containerization with Nix

### 1.1. Overview

The `dojo` application is packaged as an OCI container image built using Nix (e.g. `dockerTools.buildLayeredImage`). Instead of a `Dockerfile`, the Nix flake defines a `docker` package output that:

- Uses a minimal base image (with `busybox` for debugging).
- Includes:
  - A Python interpreter.
  - Application dependencies resolved from `pyproject.toml` (via `uv2nix` or equivalent).
  - The `dojo` application code.
- Runs as a non-root user by default.
- Exposes a single HTTP port for the API.

This gives reproducible, cacheable container builds with a small attack surface while still allowing basic in-container debugging via `kubectl exec`.

### 1.2. Image Layout and Entrypoint

The Nix flake should define a `docker` output that builds an image with roughly the following layout:

- Base:
  - Minimal root filesystem with `busybox` installed for debugging.
- Runtime:
  - Python interpreter.
  - Virtual environment or site-packages corresponding to the dependencies specified in `pyproject.toml`.
- Application:
  - `dojo` source code copied into `/app`.

Container configuration:

- Working directory: `/app`.
- Default environment variables:
  - `DOJO_DB_PATH=/data/ledger.duckdb`
  - `DOJO_ENV=production` (can be overridden in Kubernetes).
- Entrypoint:
  - The container entrypoint runs `uvicorn` in factory mode:
    - Command conceptually equivalent to:

          python -m uvicorn dojo.core.app:create_app \
            --factory \
            --host 0.0.0.0 \
            --port 8000

  - This can be configured in the Nix build via the container `config.Entrypoint` field.
- Exposed port:
  - Container listens on `8000/tcp`.

### 1.3. Security and Debugging Trade-offs

Security-related defaults:

- The container runs as a non-root user (e.g. UID/GID `1000`).
- The root filesystem should be read-only in Kubernetes; `/data` is the only writable path.

Debugging trade-offs:

- `busybox` is included in the image so that `kubectl exec` can be used to:
  - Inspect the filesystem.
  - Confirm the presence and permissions of `/data/ledger.duckdb`.
  - Perform simple network checks (e.g. `wget` or `nc`).
- There is no package manager or compiler in the image; any heavy diagnostics should be done locally with Nix or with a separate debug-oriented image if needed.

### 1.4. Build Command

The image is built from the repository root using Nix:

    nix build .#docker

This produces a `result` tarball that can be loaded into Docker:

    docker load < result

When used in CI, the tarball is loaded and then re-tagged according to branch or tag naming conventions (see CI/CD section).

---

## 2. Kubernetes Deployment (Kustomize)

### 2.1. Directory Structure

Kubernetes manifests live under `deploy/k8s` in the `dojo` repository:

    deploy/k8s/
    ├── base/
    │   ├── deployment.yaml
    │   ├── service.yaml
    │   ├── pvc.yaml
    │   └── kustomization.yaml
    └── overlays/
        ├── dev/
        │   └── kustomization.yaml
        ├── staging/
        │   └── kustomization.yaml
        └── production/
            └── kustomization.yaml

- `base/` holds the canonical deployment definition.
- `overlays/` apply environment-specific overrides.
- A separate infrastructure repository is expected to reference the overlays via Kustomize and Git URLs.

### 2.2. Base: Deployment

The base `Deployment` defines the core runtime behavior.

Key properties:

- Name: `dojo`.
- Replicas: `1`.
- Update strategy: `Recreate` (not rolling).
- Image: defaults to `ghcr.io/blogle/dojo:edge` (overridden in overlays or external infra repo).
- Pod spec:
  - Container name: `dojo`.
  - Container port: `8000`.
  - Env vars:
    - `DOJO_DB_PATH=/data/ledger.duckdb`
    - `DOJO_ENV` set via overlay or ConfigMap (defaults to `production`).
  - Volume mounts:
    - Mount a volume named `data` at `/data`.

Rationale:

- `DuckDB` uses a single file (`/data/ledger.duckdb`) and is not safe for concurrent writers.
- To prevent file lock contention and corruption:
  - The deployment always runs exactly one replica.
  - `strategy.type` is set to `Recreate` so that the old pod is fully terminated (and releases the file lock) before the new pod starts.

### 2.3. Base: PersistentVolumeClaim

The base defines a PVC named `dojo-data`:

- Access mode: `ReadWriteOnce`.
- Storage: cluster default storage class.
- Size: e.g. `5Gi` (adjustable).
- Mount path in the pod: `/data`.

Notes:

- This ensures the DuckDB database file persists across pod restarts.
- On multi-node clusters, the `ReadWriteOnce` PVC may restrict the pod to a single node; the scheduler and storage class handle that detail.
- The `Recreate` deployment strategy ensures that there is never more than one pod attempting to use the PVC concurrently.

### 2.4. Base: Service

The base `Service` exposes the HTTP API inside the cluster:

- Type: `ClusterIP`.
- Port:
  - `port: 80` externally.
  - `targetPort: 8000` (container port).
- Selector:
  - Matches the labels on the `dojo` pod (e.g. `app: dojo`).

External access (e.g. via Ingress or load balancer) is provided by the consuming environment (staging/production overlay or an external infra repo).

### 2.5. Base: Probes, Resources, and SecurityContext

The base deployment should define:

- Readiness probe:
  - HTTP GET on `/healthz` at port `8000`.
  - Reasonable initial delay (e.g. 5–10 seconds).
  - Period (e.g. every 10 seconds).
- Liveness probe:
  - HTTP GET on `/healthz` at port `8000`.
  - Longer initial delay (e.g. 30 seconds).
  - Period (e.g. every 30 seconds).
- Resource requests/limits:
  - `requests.cpu`: small baseline (e.g. `100m`).
  - `requests.memory`: e.g. `256Mi`.
  - `limits.cpu`: e.g. `1`.
  - `limits.memory`: e.g. `1Gi`.
- Security context (pod-level or container-level), for example:
  - `runAsNonRoot: true`.
  - `runAsUser: 1000`.
  - `runAsGroup: 1000`.
  - `fsGroup: 1000`.
  - `readOnlyRootFilesystem: true`.

The application is expected to expose a simple `/healthz` endpoint that returns HTTP 200 when the application is ready and healthy.

### 2.6. Base: Config and Secrets

Non-sensitive configuration:

- Injected via environment variables or a ConfigMap.
- Examples:
  - `DOJO_ENV` (e.g. `dev`, `staging`, `production`).
  - Logging level (e.g. `DOJO_LOG_LEVEL`).
  - Feature flags.

Sensitive configuration:

- Injected via Kubernetes Secrets.
- Examples (if needed in the future):
  - Session signing keys.
  - API keys for external services.

Base manifests may define ConfigMap and Secret references but should not contain actual secret values. Environment-specific manifests or external infrastructure repositories provide concrete values.

---

## 3. Environment Overlays

The overlays under `deploy/k8s/overlays` provide environment-specific configuration mounted on top of the `base` manifests via Kustomize.

### 3.1. Dev Overlay

The `dev` overlay is intended for local or experimental use. Typical characteristics:

- Uses `imagePullPolicy: IfNotPresent` or `Never` for local clusters.
- May use an `emptyDir` volume instead of a PVC for `/data` so state is ephemeral.
- Sets `DOJO_ENV=dev` and `DOJO_LOG_LEVEL=debug`.
- May disable resource limits or set very low values for convenience.

This overlay is optional and primarily for local development or ad hoc testing.

### 3.2. Staging Overlay

The `staging` overlay is used for testing changes before promoting them to production:

- References the base manifests.
- Overrides:
  - Namespace (e.g. `dojo-staging`).
  - Image tag (e.g. `ghcr.io/blogle/dojo:edge` or a specific SHA tag).
  - Ingress/host configuration (e.g. `staging-dojo.example.com`).
- Uses a PVC for `/data` for persistence across staging deployments.
- Configuration is generally similar to production but may have reduced resource limits.

Staging can track:

- The `edge` image (latest from `main`).
- Or specific commit-based tags (e.g. `sha-<commit>`), depending on desired safety.

### 3.3. Production Overlay

The `production` overlay is intended for stable, pinned releases:

- References the base manifests.
- Overrides:
  - Namespace (e.g. `dojo-prod`).
  - Image tag: pinned to a specific version, e.g. `ghcr.io/blogle/dojo:v0.1.0`.
  - Ingress/host configuration (e.g. `dojo.example.com`).
- Uses a PVC for `/data` with appropriate storage class and size.
- May set stricter resource limits and any production-specific environment variables.

The production overlay should not track `edge`. It should be updated only when promoting a verified release.

---

## 4. GitOps Integration Example

A recommended pattern is to manage actual environment deployments from a separate infrastructure repository. That repository can reference the overlays from the `dojo` repo via Kustomize’s Git URL support.

Example `kustomization.yaml` in an infrastructure repo for a production environment:

    apiVersion: kustomize.config.k8s.io/v1beta1
    kind: Kustomization

    namespace: dojo-prod

    resources:
      - github.com/blogle/dojo//deploy/k8s/overlays/production?ref=v0.1.0

    images:
      - name: ghcr.io/blogle/dojo
        newTag: v0.1.0

    patchesJson6902:
      - target:
          group: networking.k8s.io
          version: v1
          kind: Ingress
          name: dojo
        patch: |-
          - op: replace
            path: /spec/rules/0/host
            value: dojo.example.com

Key points:

- `resources` references the production overlay at a specific Git tag (`ref=v0.1.0`).
- `images` ensures the `image:` tag inside the manifests is pinned to `v0.1.0`.
- `patchesJson6902` customizes the Ingress host (and any other fields as needed).

This pattern allows each environment (e.g. `staging`, `prod`) to be fully defined and promoted via Git changes in the infrastructure repo.

---

## 5. CI/CD Pipeline (GitHub Actions)

CI/CD is handled via a single workflow file, e.g. `.github/workflows/ci.yml`.

### 5.1. Triggers

The workflow is triggered on:

- `push` to `master`:
  - Run tests.
  - Build and publish an `edge` image.
- `push` of tags matching `v*`:
  - Run tests.
  - Build and publish a versioned image.
- `pull_request` targeting `master`:
  - Run tests only (no image publish).

### 5.2. Jobs Overview

The workflow contains two main jobs:

1. `test`:
   - Runs on PRs, `master`, and tags.
   - Steps:
     - Check out the repository.
     - Install Nix.
     - Enter the development environment and run tests, e.g.:

           nix develop . --command pytest

     - Fails the job if tests fail.

2. `build-and-push`:
   - Runs only on `push` to `master` and on tags `v*`.
   - Depends on `test` (won’t run if tests fail).
   - Steps:
     - Check out the repository.
     - Install Nix.
     - Build the container tarball:

           nix build .#docker

     - Install Docker (if needed) on the CI runner.
     - Authenticate to GHCR using the built-in `GITHUB_TOKEN`:
       - `permissions` in the workflow must include:

             permissions:
               contents: read
               packages: write

       - Login command conceptually:

             echo "${GITHUB_TOKEN}" \
               | docker login ghcr.io -u "${GITHUB_ACTOR}" --password-stdin

     - Load the tarball into Docker:

           docker load < result

     - Determine tags based on the Git ref:
       - For `master`:
         - `ghcr.io/blogle/dojo:edge`
         - `ghcr.io/blogle/dojo:sha-<short-commit>`
       - For a tag `vX.Y.Z`:
         - `ghcr.io/blogle/dojo:vX.Y.Z`
         - `ghcr.io/blogle/dojo:latest` (optional convenience tag).
     - Tag the image appropriately and push to GHCR.

The first push will implicitly create the `ghcr.io/blogle/dojo` package in GitHub.

### 5.3. Nix Caching (Optional)

To speed up CI builds, a Nix cache (e.g. via Cachix or GitHub Actions cache) can be configured. This is optional for a small project but recommended as the dependency set grows.

Caching strategy:

- Key on the Nix store inputs, especially the lockfile(s).
- Cache the `/nix/store` or relevant portions to avoid re-building Python dependencies on each run.

---

## 6. Release and Promotion Workflow

### 6.1. Cutting a Release

To cut a new release:

1. Ensure `master` is in a good state and all tests are passing.
2. Create an annotated tag:

       git tag -a v0.1.0 -m "Release v0.1.0"

3. Push the tag:

       git push origin v0.1.0

4. CI will:
   - Run tests.
   - Build the container image.
   - Push:
     - `ghcr.io/blogle/dojo:v0.1.0`
     - Optionally `ghcr.io/blogle/dojo:latest`.

### 6.2. Promoting to Staging

Staging can be configured in the infra repo to track:

- `edge` (continuous deployment from `master`), or
- Specific SHA tags (e.g. `sha-<commit>`) for more controlled promotion.

Promotion to staging is a Git change in the staging `kustomization.yaml`:

- Update the `images` section to point at a new tag (e.g. `ghcr.io/blogle/dojo:v0.1.0` or `sha-<commit>`).
- Optionally update the overlay `ref` if staging should track a different Git tag for manifests.

### 6.3. Promoting to Production

Production promotion is also driven by Git:

1. In the production `kustomization.yaml` (in the infra repo):
   - Update the `resources` reference to point to the new Git tag:

         resources:
           - github.com/blogle/dojo//deploy/k8s/overlays/production?ref=v0.1.0

   - Update the image tag to match:

         images:
           - name: ghcr.io/blogle/dojo
             newTag: v0.1.0

2. Commit and push the change.
3. The GitOps controller (e.g. ArgoCD or Flux) or a manual `kubectl apply -k ...` will apply the changes.

This aligns:

- Git tag `v0.1.0` for manifests.
- Container image tag `v0.1.0`.
- Kubernetes resources in production.

### 6.4. Rollback

Rollback is also done via Git:

1. In the production infra repo, revert the `kustomization.yaml` changes back to a previous version (e.g. `v0.0.9`).
2. Commit and push.
3. Apply via the GitOps controller or `kubectl apply -k`.

Data safety considerations:

- Rolling back the application is only safe if the DuckDB schema has not changed in a backward-incompatible way.
- As schema evolves, a simple mechanism should be used to track schema version and apply migrations in a forward-only manner.

Suggested approach:

- Maintain a small migrations system (e.g. SQL files with version numbers).
- On startup, `dojo`:
  - Reads the current schema version from a metadata table.
  - Applies forward migrations if needed.
  - Refuses to start if a downgrade would be required.

For small deployments, migrations can also be applied manually via a separate job or script, as long as forward-only migrations and backups are respected.

---

## 7. Data Safety and Backups

The DuckDB database file lives at `/data/ledger.duckdb`, backed by the `ReadWriteOnce` PVC.

Key practices for data safety:

- Always use `Recreate` strategy and a single replica.
- Do not run multiple `dojo` pods concurrently against the same PVC.
- Ensure the PVC’s underlying storage has durability guarantees appropriate for production (e.g. networked block storage or durable local SSD with backups).
- Periodically back up the DuckDB file by:
  - Snapshotting the PVC via the storage provider, or
  - Copying `/data/ledger.duckdb` to an external backup location using a Kubernetes `Job` or an out-of-band process.

---

## 8. Summary

This deployment and CI/CD design aims to:

- Use Nix to produce reproducible container images with minimal runtime dependencies and a small but useful debug surface (`busybox`).
- Deploy via Kubernetes with:
  - A single replica of `dojo`.
  - A `Recreate` deployment strategy to keep DuckDB safe.
  - A `ReadWriteOnce` PVC for durable storage.
  - Health probes, resource limits, and a non-root security context.
- Provide environment overlays (dev, staging, production) that can be referenced by an external infra repo using Kustomize and Git URLs.
- Implement a simple but robust GitHub Actions pipeline that:
  - Runs tests on every change.
  - Builds and pushes images to GHCR for `main` and version tags.
  - Supports straightforward promotion and rollback via Git changes.

This setup is intentionally streamlined for a small-scale deployment while leaving room for future enhancements (more environments, more advanced observability, richer configuration, etc.) without requiring a redesign.
