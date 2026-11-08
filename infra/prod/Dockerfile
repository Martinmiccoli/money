# Immagine unica del progetto (M9): motore Rust, binding money_py, CLI Python, webapp.
# Multi-architettura: gira sia su Mac (arm64) sia sulla VM Oracle Ampere (arm64) o su x86.

# ── 1. motore Rust ─────────────────────────────────────────────────────────────
FROM rust:1-slim-bookworm AS engine
WORKDIR /src/engine
COPY engine/ ./
COPY config/ /src/config/
RUN cargo build --release -p money-engine

# ── 2. ambiente Python con money_py (serve Rust per compilare il binding) ─────
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS python
RUN apt-get update && apt-get install -y --no-install-recommends curl build-essential ca-certificates \
    && curl -sSf https://sh.rustup.rs | sh -s -- -y --profile minimal && rm -rf /var/lib/apt/lists/*
ENV PATH="/root/.cargo/bin:$PATH" UV_LINK_MODE=copy UV_COMPILE_BYTECODE=1
WORKDIR /app
COPY engine/ engine/
COPY config/ config/
COPY research/pyproject.toml research/uv.lock research/
RUN cd research && uv sync --frozen --no-dev --no-install-project
COPY research/ research/
RUN cd research && uv sync --frozen --no-dev

# ── 3. webapp ─────────────────────────────────────────────────────────────────
FROM node:22-bookworm-slim AS web
WORKDIR /app/web
COPY web/package.json web/package-lock.json ./
RUN npm ci
COPY web/ ./
RUN npm run build

# ── 4. runtime ────────────────────────────────────────────────────────────────
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim
RUN apt-get update && apt-get install -y --no-install-recommends nodejs npm tzdata ca-certificates \
    && rm -rf /var/lib/apt/lists/*
ENV TZ=Europe/Rome MONEY_REPO=/app
WORKDIR /app
COPY . .
COPY --from=python /app/research/.venv research/.venv
COPY --from=engine /src/engine/target/release/money-engine engine/target/release/money-engine
COPY --from=web /app/web/node_modules web/node_modules
COPY --from=web /app/web/dist web/dist
# Nessun segreto nell'immagine: .env viene montato a runtime (G-14).
CMD ["bash", "-lc", "cd web && exec npx tsx server/index.ts"]
