#!/bin/bash

# Configuration
VPS_USER="su617375"
VPS_HOST="access-5018867175.webspace-host.com"
DEPLOY_PATH="~/ai-shift-agent"

echo "🚀 Avvio deploy su $VPS_HOST..."

# 1. Check for Docker and create remote directory
echo "📁 Verifica ambiente e preparazione cartella..."
ssh -4 $VPS_USER@$VPS_HOST "docker --version && mkdir -p $DEPLOY_PATH" || {
    echo "❌ Errore: Docker non sembra essere disponibile sulla VPS o problemi di permessi."
    echo "Attenzione: Se questa è un'istanza 'Webspace' (Shared Hosting), Docker potrebbe non essere supportato."
    exit 1
}

# 2. Sync files
echo "📦 Sincronizzazione file..."
# Added -4 for IPv4 only to avoid potential IPv6 timeouts seen in logs
rsync -avz -e "ssh -4" --exclude '.git' \
          --exclude '.venv' \
          --exclude '__pycache__' \
          --exclude 'logs/*' \
          --exclude '.env' \
          ./ $VPS_USER@$VPS_HOST:$DEPLOY_PATH

if [ $? -ne 0 ]; then
    echo "❌ Errore durante la sincronizzazione rsync. Verifica la connessione."
    exit 1
fi

# 3. Upload .env separately if not present
ssh -4 $VPS_USER@$VPS_HOST "test -f $DEPLOY_PATH/.env" || {
    echo "⚠️ .env non trovato sulla VPS. Caricamento versione locale..."
    scp -4 .env $VPS_USER@$VPS_HOST:$DEPLOY_PATH/.env
}

# 4. Pull latest images and restart containers
echo "🔄 Riavvio container sulla VPS..."
ssh -4 $VPS_USER@$VPS_HOST "cd $DEPLOY_PATH && docker compose -f docker-compose.prod.yml up -d --build"

echo "✅ Deploy completato con successo!"
