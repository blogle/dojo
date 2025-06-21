# syntax=docker/dockerfile:1.7
###############################################################################
# Dojo – multi-stage, multi-DAG build
#   • dev-runtime  : incremental debug build + Bacon hot-reload
#   • runtime      : slim release image for prod / staging
###############################################################################

############################
# 1. Rust tool-chain base
############################
FROM rust:1.87-slim-bookworm AS rust-base

# System libraries + pre-built sccache binary
RUN apt-get update -qq && apt-get install -y --no-install-recommends \
      pkg-config libssl-dev libpq-dev clang cmake sccache && \
    rm -rf /var/lib/apt/lists/*

# Only cargo-chef needs to be compiled now
RUN cargo install --locked cargo-chef

ENV RUSTC_WRAPPER=sccache \
    SCCACHE_DIR=/sccache \
    SCCACHE_CACHE_SIZE=2G \
    CARGO_REGISTRIES_CRATES_IO_PROTOCOL=sparse

############################
# 2. Dependency planner
############################
FROM rust-base AS planner
WORKDIR /app
COPY backend ./backend

WORKDIR /app/backend
RUN cargo chef prepare --recipe-path recipe.json

###############################################################################
# === DEBUG / TEST DAG ========================================================
###############################################################################
FROM rust-base AS builder-dev
WORKDIR /app
COPY --from=planner /app/backend/recipe.json .

RUN --mount=type=cache,target=/cargo/registry \
    --mount=type=cache,target=/cargo/git \
    --mount=type=cache,target=/rust-target \
    --mount=type=cache,target=/sccache \
    cargo chef cook --profile dev --recipe-path recipe.json

COPY backend ./backend
RUN --mount=type=cache,target=/cargo/registry \
    --mount=type=cache,target=/cargo/git \
    --mount=type=cache,target=/rust-target \
    --mount=type=cache,target=/sccache \
    cargo test --workspace --all-targets --no-run

##########################
# 3. Dev runtime (Bacon)
##########################
FROM builder-dev AS dev-runtime
WORKDIR /app
RUN cargo install --locked bacon
COPY ./backend/bacon.toml ./bacon.toml
VOLUME ["/app/backend", "/sccache"]            # bind-mount source + sccache
ENV RUST_LOG=debug
CMD ["bacon"]

###############################################################################
# === RELEASE DAG =============================================================
###############################################################################
FROM rust-base AS builder-release
WORKDIR /app
COPY --from=planner /app/backend/recipe.json .

RUN --mount=type=cache,target=/cargo/registry \
    --mount=type=cache,target=/cargo/git \
    --mount=type=cache,target=/rust-target \
    --mount=type=cache,target=/sccache \
    cargo chef cook --profile release --recipe-path recipe.json

COPY backend ./backend
WORKDIR /app/backend
RUN --mount=type=cache,target=/cargo/registry \
    --mount=type=cache,target=/cargo/git \
    --mount=type=cache,target=/rust-target \
    --mount=type=cache,target=/sccache \
    cargo build --release --bin dojo

############################
# 4. Node / PNPM pipeline
############################
FROM node:20-alpine AS node-base
RUN corepack enable
ENV PNPM_CACHE_DIR=/pnpm/store

FROM node-base AS web-deps
WORKDIR /web
COPY frontend/pnpm-lock.yaml frontend/package.json ./
RUN --mount=type=cache,target=$PNPM_CACHE_DIR,id=pnpm \
    pnpm install --frozen-lockfile --ignore-scripts

FROM node-base AS web-builder
WORKDIR /web
COPY --from=web-deps /web/node_modules ./node_modules
COPY frontend .
RUN pnpm run build        # ⇒ /web/dist

############################
# 5. Production runtime
############################
FROM gcr.io/distroless/cc-debian12 AS runtime
WORKDIR /app
COPY --from=builder-release /app/backend/target/release/dojo ./dojo
COPY --from=builder-release /app/backend/migrations ./migrations
COPY --from=web-builder     /web/dist                     ./public
USER 1001
EXPOSE 8080
ENTRYPOINT ["./dojo"]
