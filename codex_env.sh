#!/usr/bin/env bash
set -euo pipefail

##
##  Dojo dev-environment bootstrap
##

echo ">>> 0. Rust components (rustfmt, clippy)"
if command -v rustup >/dev/null 2>&1; then
  rustup update stable                      # keep the toolchain fresh
  rustup component add rustfmt clippy       # install missing components
else
  echo "[warn] rustup not found – skipping rust components installation" >&2
fi

echo ">>> 1. System packages"
sudo apt-get update -y
sudo apt-get install -y --no-install-recommends \
  postgresql postgresql-contrib libpq-dev \
  build-essential pkg-config libssl-dev curl jq

echo ">>> 2. Postgres 15 init"
sudo service postgresql start
sudo -u postgres psql -qc "CREATE ROLE dojo WITH LOGIN SUPERUSER PASSWORD 'dojo';" || true
createdb -U dojo dojo_dev || true

echo ">>> 3. Node toolchain (pnpm)"
if ! command -v pnpm >/dev/null 2>&1; then
  curl -fsSL https://get.pnpm.io/install.sh | sh -
  export PATH="$HOME/.local/share/pnpm:$PATH"
fi
node -v && pnpm -v

echo ">>> 4. SQLx CLI"
if ! command -v sqlx >/dev/null 2>&1; then
  cargo install sqlx-cli --no-default-features --features rustls,postgres
fi

echo ">>> 5. Repo dependencies"
# JS deps (frontend) ────────────────────────────────────────────────────────────
pnpm --filter ./frontend install

# Rust deps (backend) ───────────────────────────────────────────────────────────
cargo fetch --manifest-path ./backend/Cargo.toml

echo ">>> 6. Database migrations"
export DATABASE_URL="postgres://dojo:dojo@localhost/dojo_dev"
# (run `sqlx migrate run` or equivalent here when the migrations directory exists)

