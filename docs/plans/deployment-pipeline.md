# Deployment Pipeline & Kubernetes Manifests

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

Reference: [.agent/PLANS.md](../.agent/PLANS.md) - This document must be maintained in accordance with PLANS.md.

## Purpose / Big Picture

This plan implements a reproducible deployment pipeline for the `dojo` application. It enables:
1.  **Automated Builds:** Using Nix to create minimal, secure container images containing the Python application and its dependencies.
2.  **Continuous Integration:** A GitHub Actions workflow to run tests and publish images to the GitHub Container Registry (GHCR) on every push to `master` or version tags.
3.  **Kubernetes Deployment:** A Kustomize-based manifest structure to deploy the application safely (handling the single-writer DuckDB constraint) across different environments (dev, staging, production).

After this work is complete, a developer can push a tag like `v0.1.0` to GitHub, which will automatically build and publish a container image. This image can then be deployed to a Kubernetes cluster using the generated manifests, ensuring consistent behavior from development to production.

## Progress

Use a list with checkboxes to summarize granular steps. Every stopping point must be documented here, even if it requires splitting a partially completed task into two (“done” vs. “remaining”). This section must always reflect the actual current state of the work.

- [x] **Milestone 1: Nix Container Build**
    - [x] Define `docker` output in `flake.nix` using `dockerTools.buildLayeredImage`.
    - [x] Verify local build with `nix build .#docker`.
    - [x] Verify image loads into Docker and runs `uvicorn`.
- [x] **Milestone 2: Kubernetes Manifests**
    - [x] Create `deploy/k8s/base` (Deployment, Service, Kustomization; storage supplied by consumers).
    - [x] Document that environment overlays live in infra repos consuming the base.
    - [x] Validate manifests with `kubectl kustomize`.
- [x] **Milestone 3: CI/CD Pipeline**
    - [x] Create `.github/workflows/ci.yml` for testing.
    - [x] Add build-and-push job for `master` and tags.
    - [x] Configure GHCR authentication and permissions.

## Surprises & Discoveries

- Observation: `multitasking` and `peewee` packages (transitive dependencies) failed to build with Nix because they depend on `setuptools` but do not declare it in their build system requirements.
  Evidence: `ModuleNotFoundError: No module named 'setuptools'` during `nix build`.
  Resolution: Added a `dependencyOverlay` in `flake.nix` to inject `setuptools` into `nativeBuildInputs` for these packages.

## Decision Log

- Decision: Use `dockerTools.buildLayeredImage` in Nix.
  Rationale: Produces optimized, multi-layered images that share common layers (like glibc or python) between builds, significantly reducing push/pull times compared to monolithic tarballs.
  Date: 2025-11-26

- Decision: Use `Recreate` deployment strategy.
  Rationale: `DuckDB` is a single-file database that does not support concurrent writers. We must ensure the old pod is fully terminated before the new one starts to prevent corruption.
  Date: 2025-11-26

## Context and Orientation

- **`flake.nix`**: The root Nix configuration file. We will add a new output package named `docker`.
- **`deploy/k8s/`**: A new directory to hold all Kubernetes manifests.
- **`.github/workflows/ci.yml`**: The definition for the CI/CD pipeline.

The application runs a standard `uvicorn` server. The critical state is stored in `ledger.duckdb`, which is expected to be at `/data/ledger.duckdb` inside the container.

## Plan of Work

### 1. Update `flake.nix` for Container Image

We will modify `flake.nix` to add a `docker` package. This package will use `pkgs.dockerTools.buildLayeredImage`.
- **Base Image**: Minimal (e.g., `busybox` or empty with just needed shared libs).
- **Contents**: Python interpreter, the virtual environment (built via `uv2nix` or similar existing logic in flake), and the `src` directory.
- **Config**:
    - `Cmd`: `["python", "-m", "uvicorn", "dojo.core.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]`
    - `Env`: `["DOJO_DB_PATH=/data/ledger.duckdb", "DOJO_ENV=production"]`
    - `ExposedPorts`: `{"8000/tcp": {}}`
    - `User`: "1000" (non-root).

### 2. Create Kubernetes Manifests

We will implement the Kustomize structure described in the architecture doc.

**`deploy/k8s/base`**:
- `deployment.yaml`: One replica, `strategy: Recreate`. Mounts `/data` and expects a PVC named `dojo-data` supplied by the consumer.
- `service.yaml`: ClusterIP service exposing port 80 -> 8000.
- `kustomization.yaml`: Aggregates the above.

Environment overlays (namespaces, PVC definitions, ingress, image tags) are provided by downstream infrastructure repos that reference `deploy/k8s/base` via Kustomize Git URLs.

### 3. Create GitHub Actions Workflow

We will create `.github/workflows/ci.yml`.
- **Triggers**: `push` (master, tags), `pull_request`.
- **Jobs**:
    - `test`: Runs `nix develop . --command pytest`.
    - `build-and-push`: Runs `nix build .#docker`, loads it, tags it, and pushes to `ghcr.io`.

## Concrete Steps

1.  **Modify `flake.nix`**:
    Edit `flake.nix` to add the `docker` output.
    ```bash
    # (Edit flake.nix)
    nix build .#docker
    ls -l result
    ```

2.  **Scaffold K8s**:
    ```bash
    mkdir -p deploy/k8s/base
    ```
    Create the YAML files in this directory; downstream infra repos will layer their own overlays.

3.  **Validate K8s**:
    ```bash
    kubectl kustomize deploy/k8s/base
    ```
    Expect to see the rendered YAML with the correct deployment/service skeleton.

4.  **Create Workflow**:
    Create `.github/workflows/ci.yml` with the content specified.

## Validation and Acceptance

1.  **Local Build**:
    Run `nix build .#docker`. It should succeed and produce a symlink `result`.
    Run `docker load < result`.
    Run `docker run --rm -it dojo:latest`. (You might need to override entrypoint to `sh` to inspect if it fails immediately due to missing `/data`).
    
2.  **CI Pipeline**:
    Push a commit to a branch. Verify the 'test' job runs in GitHub Actions.
    (Note: We cannot fully test the "push" step without proper secrets/permissions, but we can verify the configuration syntax).

3.  **Manifest Generation**:
    Run `kubectl kustomize deploy/k8s/base`.
    Verify output contains a Deployment with `replicas: 1` and `strategy: Recreate`.

## Idempotence and Recovery

- `nix build` is pure and idempotent.
- `kubectl kustomize` is a dry-run operation.
- The K8s manifests are declarative; re-applying them enforces the desired state.

## Artifacts and Notes

N/A

## Interfaces and Dependencies

- **Nix**: Required for building the image.
- **Docker**: Required for loading/running the image locally.
- **Kubernetes**: Target platform.
- **GHCR**: Target registry.
