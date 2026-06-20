#!/usr/bin/env bash
# =============================================================
# RAG Evaluation Framework Deployment Script — Ubuntu 22.04 LTS
# No Docker. Uses systemd + Nginx.
#
# Usage:
#   sudo bash deploy/setup.sh
#
# This script installs system dependencies, sets up PostgreSQL,
# Redis, Python virtual environment, builds the Next.js dashboard,
# and configures systemd + Nginx.
# =============================================================
set -euo pipefail

# ── Configuration ───────────────────────────────────────────
RAG_EVALUATION_FRAMEWORK_DIR="/opt/rag-evaluation-framework"
RAG_EVALUATION_FRAMEWORK_USER="rag-evaluation-framework"
RAG_EVALUATION_FRAMEWORK_DB="rag_evaluation_framework_db"
RAG_EVALUATION_FRAMEWORK_DB_USER="rag_evaluation_framework_user"
RAG_EVALUATION_FRAMEWORK_DB_PASS="$(openssl rand -hex 16)"
SECRET_KEY="$(openssl rand -hex 32)"
REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() { echo -e "${GREEN}[✓]${NC} $1"; }
warn() { echo -e "${YELLOW}[!]${NC} $1"; }
error() { echo -e "${RED}[✗]${NC} $1"; exit 1; }

# ── Check root ─────────────────────────────────────────────
if [ "$EUID" -ne 0 ]; then
    error "Please run as root (sudo bash deploy/setup.sh)"
fi

log "Starting RAG Evaluation Framework deployment..."

# ── 1. System Dependencies ─────────────────────────────────
log "Installing system dependencies..."
apt-get update -qq
apt-get install -y -qq \
    python3.11 python3.11-venv python3.11-dev \
    postgresql postgresql-contrib redis-server nginx \
    nodejs npm build-essential libpq-dev libffi-dev \
    curl git

# Ensure Python 3.11 is default
update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1

log "System dependencies installed."

# ── 2. PostgreSQL Setup ────────────────────────────────────
log "Setting up PostgreSQL..."
systemctl start postgresql
systemctl enable postgresql

# Create user and database
su - postgres -c "psql -c \"CREATE USER ${RAG_EVALUATION_FRAMEWORK_DB_USER} WITH PASSWORD '${RAG_EVALUATION_FRAMEWORK_DB_PASS}';\" 2>/dev/null" || warn "User may already exist"
su - postgres -c "psql -c \"CREATE DATABASE ${RAG_EVALUATION_FRAMEWORK_DB} OWNER ${RAG_EVALUATION_FRAMEWORK_DB_USER};\" 2>/dev/null" || warn "Database may already exist"
su - postgres -c "psql -c \"GRANT ALL PRIVILEGES ON DATABASE ${RAG_EVALUATION_FRAMEWORK_DB} TO ${RAG_EVALUATION_FRAMEWORK_DB_USER};\""

# Enable pgvector
su - postgres -c "psql -d ${RAG_EVALUATION_FRAMEWORK_DB} -c \"CREATE EXTENSION IF NOT EXISTS vector;\"" || warn "pgvector extension may not be available"

log "PostgreSQL setup complete."

# ── 3. Redis Setup ─────────────────────────────────────────
log "Configuring Redis..."
if [ -f /etc/redis/redis.conf ]; then
    sed -i 's/^# maxmemory <bytes>/maxmemory 512mb/' /etc/redis/redis.conf
    sed -i 's/^# maxmemory-policy noeviction/maxmemory-policy allkeys-lru/' /etc/redis/redis.conf
fi
systemctl enable redis-server
systemctl start redis-server
log "Redis configured."

# ── 4. Application Setup ───────────────────────────────────
log "Setting up RAG Evaluation Framework application..."

# Create rag-evaluation-framework user
id -u ${RAG_EVALUATION_FRAMEWORK_USER} &>/dev/null || useradd -m -s /bin/bash ${RAG_EVALUATION_FRAMEWORK_USER}

# Create application directory
mkdir -p ${RAG_EVALUATION_FRAMEWORK_DIR}
cp -r ${REPO_DIR}/* ${RAG_EVALUATION_FRAMEWORK_DIR}/
chown -R ${RAG_EVALUATION_FRAMEWORK_USER}:${RAG_EVALUATION_FRAMEWORK_USER} ${RAG_EVALUATION_FRAMEWORK_DIR}

# Python virtual environment
python3.11 -m venv ${RAG_EVALUATION_FRAMEWORK_DIR}/venv
source ${RAG_EVALUATION_FRAMEWORK_DIR}/venv/bin/activate
pip install --upgrade pip setuptools wheel
pip install -r ${RAG_EVALUATION_FRAMEWORK_DIR}/requirements.txt
pip install -r ${RAG_EVALUATION_FRAMEWORK_DIR}/requirements-dev.txt

log "Python environment set up."

# ── 5. Environment File ────────────────────────────────────
log "Creating environment file..."

cat > ${RAG_EVALUATION_FRAMEWORK_DIR}/.env << EOF
DATABASE_URL=postgresql+asyncpg://${RAG_EVALUATION_FRAMEWORK_DB_USER}:${RAG_EVALUATION_FRAMEWORK_DB_PASS}@localhost/${RAG_EVALUATION_FRAMEWORK_DB}
REDIS_URL=redis://localhost:6379/0
SECRET_KEY=${SECRET_KEY}
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
ALLOWED_ORIGINS=http://localhost:3000
DEBUG=false
LOG_LEVEL=INFO
EOF

chown ${RAG_EVALUATION_FRAMEWORK_USER}:${RAG_EVALUATION_FRAMEWORK_USER} ${RAG_EVALUATION_FRAMEWORK_DIR}/.env
chmod 600 ${RAG_EVALUATION_FRAMEWORK_DIR}/.env

log "Environment file created at ${RAG_EVALUATION_FRAMEWORK_DIR}/.env"

# ── 6. Run Migrations ──────────────────────────────────────
log "Running database migrations..."
cd ${RAG_EVALUATION_FRAMEWORK_DIR}
source venv/bin/activate
alembic upgrade head 2>/dev/null || warn "Migrations may have failed (DB may not be ready yet)"
log "Migrations applied."

# ── 7. Systemd Units ───────────────────────────────────────
log "Creating systemd units..."

# API service
cat > /etc/systemd/system/rag-evaluation-framework-api.service << 'EOF'
[Unit]
Description=RAG Evaluation Framework FastAPI Service
After=network.target postgresql.service redis.service
Wants=postgresql.service redis.service

[Service]
Type=exec
User=rag-evaluation-framework
WorkingDirectory=/opt/rag-evaluation-framework
EnvironmentFile=/opt/rag-evaluation-framework/.env
ExecStart=/opt/rag-evaluation-framework/venv/bin/uvicorn api.main:app --host 127.0.0.1 --port 8000 --workers 4
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# Worker service
cat > /etc/systemd/system/rag-evaluation-framework-worker.service << 'EOF'
[Unit]
Description=RAG Evaluation Framework Celery Worker
After=network.target redis.service
Wants=redis.service

[Service]
Type=exec
User=rag-evaluation-framework
WorkingDirectory=/opt/rag-evaluation-framework
EnvironmentFile=/opt/rag-evaluation-framework/.env
ExecStart=/opt/rag-evaluation-framework/venv/bin/celery -A api.tasks worker --loglevel=info --concurrency=4
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable rag-evaluation-framework-api rag-evaluation-framework-worker
systemctl start rag-evaluation-framework-api rag-evaluation-framework-worker || warn "Services may need manual start"

log "Systemd units created and enabled."

# ── 8. Next.js Dashboard ───────────────────────────────────
log "Building Next.js dashboard..."
cd ${RAG_EVALUATION_FRAMEWORK_DIR}/dashboard

if [ -f "package.json" ]; then
    npm install
    npm run build

    # Create dashboard systemd service
    cat > /etc/systemd/system/rag-evaluation-framework-dashboard.service << 'EOF'
[Unit]
Description=RAG Evaluation Framework Next.js Dashboard
After=network.target

[Service]
Type=exec
User=rag-evaluation-framework
WorkingDirectory=/opt/rag-evaluation-framework/dashboard
ExecStart=/usr/bin/node /opt/rag-evaluation-framework/dashboard/.next/standalone/server.js
Restart=always
RestartSec=5
Environment=PORT=3000
Environment=HOSTNAME=127.0.0.1

[Install]
WantedBy=multi-user.target
EOF

    systemctl daemon-reload
    systemctl enable rag-evaluation-framework-dashboard
    systemctl start rag-evaluation-framework-dashboard || warn "Dashboard may need manual start"
    log "Next.js dashboard built and deployed."
else
    warn "Dashboard source not found. Skipping Next.js build."
    warn "To build later: cd ${RAG_EVALUATION_FRAMEWORK_DIR}/dashboard && npm install && npm run build"
fi

# ── 9. Nginx Config ────────────────────────────────────────
log "Configuring Nginx..."

cat > /etc/nginx/sites-available/rag-evaluation-framework << 'EOF'
server {
    listen 80;
    server_name _;

    # API proxy
    location /api/ {
        proxy_pass http://127.0.0.1:8000/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 120s;
        proxy_connect_timeout 10s;
    }

    # Dashboard proxy
    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 120s;
        proxy_connect_timeout 10s;
    }
}
EOF

# Enable site
ln -sf /etc/nginx/sites-available/rag-evaluation-framework /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default

nginx -t && systemctl reload nginx

log "Nginx configured."

# ── SSL via Certbot ────────────────────────────────────────
warn "To add SSL, run: certbot --nginx -d yourdomain.com"

# ── Summary ────────────────────────────────────────────────
echo ""
echo -e "${GREEN}================================================${NC}"
echo -e "${GREEN}  RAG Evaluation Framework Deployment Complete!${NC}"
echo -e "${GREEN}================================================${NC}"
echo ""
echo "  API:          http://localhost:8000"
echo "  Dashboard:    http://localhost:3000"
echo "  API Docs:     http://localhost:8000/docs"
echo ""
echo "  Database:     ${RAG_EVALUATION_FRAMEWORK_DB} (user: ${RAG_EVALUATION_FRAMEWORK_DB_USER})"
echo "  DB Password:  ${RAG_EVALUATION_FRAMEWORK_DB_PASS}"
echo "  Secret Key:   ${SECRET_KEY}"
echo ""
echo "  Systemd Services:"
echo "    rag-evaluation-framework-api        - FastAPI"
echo "    rag-evaluation-framework-worker     - Celery"
echo "    rag-evaluation-framework-dashboard  - Next.js"
echo ""
echo -e "${YELLOW}  Next steps:${NC}"
echo "  1. Configure API keys in /opt/rag-evaluation-framework/.env"
echo "  2. Restart services: systemctl restart rag-evaluation-framework-api"
echo "  3. Add SSL: certbot --nginx -d yourdomain.com"
echo ""
echo -e "${GREEN}  The .env file is at /opt/rag-evaluation-framework/.env (chmod 600)${NC}"
echo ""

exit 0
