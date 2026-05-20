#!/bin/bash
# setup.sh — Instalação do Pi Recon no Raspberry Pi Zero 2W
# Uso: chmod +x setup.sh && sudo ./setup.sh

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log()  { echo -e "${GREEN}[+]${NC} $1"; }
warn() { echo -e "${YELLOW}[!]${NC} $1"; }
err()  { echo -e "${RED}[✗]${NC} $1"; }

echo ""
echo "════════════════════════════════════"
echo "   PI RECON — Setup & Instalação"
echo "════════════════════════════════════"
echo ""

# ── Sistema ───────────────────────────────────────────────────────────────────
log "Atualizando sistema..."
apt-get update -qq

log "Instalando ferramentas de segurança..."
apt-get install -y -qq \
    nmap \
    nikto \
    gobuster \
    bettercap \
    aircrack-ng \
    wordlists \
    python3-pip \
    python3-venv \
    git \
    fonts-dejavu

# ── Wordlists ──────────────────────────────────────────────────────────────
if [ -f /usr/share/wordlists/rockyou.txt.gz ]; then
    log "Descomprimindo rockyou..."
    gunzip -f /usr/share/wordlists/rockyou.txt.gz || true
fi

# ── Python ────────────────────────────────────────────────────────────────────
log "Criando ambiente virtual Python..."
python3 -m venv /opt/pi_recon_env

log "Instalando dependências Python..."
/opt/pi_recon_env/bin/pip install --upgrade pip -q
/opt/pi_recon_env/bin/pip install \
    google-genai \
    Pillow \
    RPi.GPIO \
    spidev -q

# ── Driver e-paper Waveshare ──────────────────────────────────────────────────
log "Instalando driver Waveshare e-paper..."
if [ ! -d "/tmp/e-Paper" ]; then
    git clone --depth=1 https://github.com/waveshare/e-Paper.git /tmp/e-Paper -q
fi
/opt/pi_recon_env/bin/pip install /tmp/e-Paper/RaspberryPi_JetsonNano/python/ -q

# ── Copia arquivos ────────────────────────────────────────────────────────────
log "Instalando Pi Recon em /opt/pi_recon..."
mkdir -p /opt/pi_recon/logs
cp scanner.py /opt/pi_recon/
cp epaper_display.py /opt/pi_recon/

# ── Wrapper de execução ───────────────────────────────────────────────────────
cat > /usr/local/bin/pirecon << 'EOF'
#!/bin/bash
cd /opt/pi_recon
source /opt/pi_recon_env/bin/activate
exec python3 scanner.py "$@"
EOF
chmod +x /usr/local/bin/pirecon

# ── Serviço systemd (exibe tela de boot no e-paper) ──────────────────────────
cat > /etc/systemd/system/pirecon-boot.service << 'EOF'
[Unit]
Description=Pi Recon Boot Screen
After=network.target

[Service]
Type=oneshot
WorkingDirectory=/opt/pi_recon
ExecStart=/opt/pi_recon_env/bin/python3 -c "import epaper_display; epaper_display.show_boot_screen()"
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable pirecon-boot.service 2>/dev/null || true

# ── Instruções finais ─────────────────────────────────────────────────────────
echo ""
echo "════════════════════════════════════"
echo "   ✓ Instalação concluída!"
echo "════════════════════════════════════"
echo ""
echo "Configure sua API Key (Antigravity/Google AI Studio):"
echo ""
echo "  1. Adicione ao ~/.bashrc (persistente):"
echo "     echo 'export GEMINI_API_KEY=\"sua_chave\"' >> ~/.bashrc"
echo "     source ~/.bashrc"
echo ""
echo "  2. Obtenha sua chave gratuita em:"
echo "     https://aistudio.google.com/app/apikey"
echo ""
echo "Para iniciar:"
echo "  pirecon"
echo "  (ou: sudo pirecon   para bettercap/wireless)"
echo ""
warn "Antigravity 2.0 pronto. Use com responsabilidade."
echo ""
