# ── Frontend: Wind Forecast Dashboard ────────────────────────────────────────
# Stage 1 — Build
# Node 20 LTS builds the Vite/React production bundle.
FROM node:20-slim AS builder

WORKDIR /app

# Install dependencies first (cached layer).
COPY package.json package-lock.json* ./
RUN npm ci

# Copy source and build.
COPY . .
RUN npm run build
# Vite outputs to /app/dist by default.

# ── Stage 2 — Serve ──────────────────────────────────────────────────────────
# Nginx serves the static bundle and proxies /api requests to the backend.
FROM nginx:1.27-alpine AS runner

# Remove the default Nginx config.
RUN rm /etc/nginx/conf.d/default.conf

# Copy our custom config.
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy the Vite build output from stage 1.
COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
