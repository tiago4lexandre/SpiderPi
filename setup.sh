#!/bin/bash
# setup.sh — Instalação do Pi Recon no Raspberry Pi Zero 2W
# Uso: chmod +x setup.sh && sudo ./setup.sh

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'

log()   { echo -e "${GREEN}[+]${NC} $1"; }
warn()  { echo -e "${YELLOW}[!]${NC} $1"; }
err()   { echo -e "${RED}[✗]${NC} $1"; }
step()  { echo -e "\n${CYAN}━━━ $1 ━━━${NC}"; }

# ── Verifica root ─────────────────────────────────────────────────────────────
if [ "$EUID" -ne 0 ]; then
    err "Execute como root: sudo ./setup.sh"
    exit 1
fi

echo ""
echo "════════════════════════════════════════"
echo "   PI RECON — Setup & Instalação"
echo "   Raspberry Pi Zero 2W"
echo "════════════════════════════════════════"
echo ""

# ════════════════════════════════════════════════════════
# 1. SWAP — configura antes de qualquer instalação
# ════════════════════════════════════════════════════════
step "Configurando SWAP"

SWAP_SIZE=512
SWAP_FILE=/etc/dphys-swapfile

# Lê valor atual
CURRENT_SWAP=$(grep "^CONF_SWAPSIZE=" $SWAP_FILE 2>/dev/null | cut -d= -f2 || echo "0")

if [ "$CURRENT_SWAP" -lt "$SWAP_SIZE" ] 2>/dev/null; then
    log "Swap atual: ${CURRENT_SWAP}MB → aumentando para ${SWAP_SIZE}MB..."
    dphys-swapfile swapoff 2>/dev/null || true
    sed -i "s/^CONF_SWAPSIZE=.*/CONF_SWAPSIZE=${SWAP_SIZE}/" $SWAP_FILE
    dphys-swapfile setup
    dphys-swapfile swapon
    log "Swap configurado: $(free -h | grep Swap | awk '{print $2}')"
else
    log "Swap já está em ${CURRENT_SWAP}MB, sem alterações."
fi

# ════════════════════════════════════════════════════════
# 2. SISTEMA — atualização e ferramentas de segurança
# ════════════════════════════════════════════════════════
step "Atualizando sistema"
apt-get update -qq
log "Sistema atualizado."

step "Instalando ferramentas de segurança"

# Instala uma por vez para facilitar diagnóstico de erros
APT_PACKAGES=(
    "nmap"
    "nikto"
    "gobuster"
    "bettercap"
    "aircrack-ng"
    "wordlists"
    "python3-pip"
    "python3-venv"
    "python3-dev"
    "libjpeg-dev"
    "zlib1g-dev"
    "libfreetype6-dev"
    "git"
    "fonts-dejavu"
)

for pkg in "${APT_PACKAGES[@]}"; do
    if dpkg -s "$pkg" &>/dev/null; then
        log "$pkg já instalado, pulando."
    else
        log "Instalando $pkg..."
        apt-get install -y -qq "$pkg" || warn "Falha ao instalar $pkg — continuando."
    fi
done

# ── Wordlists ─────────────────────────────────────────────────────────────────
if [ -f /usr/share/wordlists/rockyou.txt.gz ]; then
    log "Descomprimindo rockyou.txt..."
    gunzip -f /usr/share/wordlists/rockyou.txt.gz || true
fi

# ════════════════════════════════════════════════════════
# 3. PYTHON — ambiente virtual + dependências uma a uma
# ════════════════════════════════════════════════════════
step "Criando ambiente virtual Python"

if [ ! -d "/opt/pi_recon_env" ]; then
    python3 -m venv /opt/pi_recon_env
    log "Ambiente virtual criado em /opt/pi_recon_env"
else
    log "Ambiente virtual já existe, reutilizando."
fi

PIP="/opt/pi_recon_env/bin/pip"

log "Atualizando pip..."
$PIP install --upgrade pip -q

# Função auxiliar: instala pacote pip com retry e feedback
pip_install() {
    local pkg="$1"
    local extra_flags="${2:-}"
    log "Instalando Python: $pkg ..."

    # Tenta wheel binária primeiro (mais rápido, menos RAM)
    if $PIP install "$pkg" --only-binary=:all: $extra_flags -q 2>/dev/null; then
        log "$pkg instalado via wheel binária."
        return 0
    fi

    # Fallback: compila do fonte
    warn "$pkg sem wheel disponível, compilando do fonte (pode demorar)..."
    if $PIP install "$pkg" $extra_flags -q; then
        log "$pkg compilado e instalado."
        return 0
    fi

    warn "Falha ao instalar $pkg — verifique manualmente depois."
    return 1
}

# Instala cada dependência separadamente
pip_install "google-genai"
pip_install "Pillow"
pip_install "RPi.GPIO"
pip_install "spidev"

# ════════════════════════════════════════════════════════
# 4. DRIVER WAVESHARE E-PAPER
# ════════════════════════════════════════════════════════
step "Instalando driver Waveshare e-paper"

EPAPER_DIR="/tmp/e-Paper"

if [ ! -d "$EPAPER_DIR" ]; then
    log "Clonando repositório Waveshare..."
    git clone --depth=1 https://github.com/waveshare/e-Paper.git "$EPAPER_DIR" -q
else
    log "Repositório já existe, reutilizando."
fi

EPAPER_LIB="$EPAPER_DIR/RaspberryPi_JetsonNano/python"

if [ -d "$EPAPER_LIB" ]; then
    log "Instalando biblioteca e-paper..."
    $PIP install "$EPAPER_LIB" -q || warn "Falha no driver e-paper — display pode não funcionar."
else
    warn "Diretório da biblioteca e-paper não encontrado em $EPAPER_LIB"
fi

# ════════════════════════════════════════════════════════
# 5. ARQUIVOS DO PI RECON
# ════════════════════════════════════════════════════════
step "Instalando Pi Recon"

mkdir -p /opt/pi_recon/logs

for f in scanner.py epaper_display.py; do
    if [ -f "./$f" ]; then
        cp "./$f" /opt/pi_recon/
        log "$f copiado."
    else
        warn "$f não encontrado no diretório atual — copie manualmente para /opt/pi_recon/"
    fi
done

# ── Comando global pirecon ────────────────────────────────────────────────────
cat > /usr/local/bin/pirecon << 'EOF'
#!/bin/bash
cd /opt/pi_recon
source /opt/pi_recon_env/bin/activate
exec python3 scanner.py "$@"
EOF
chmod +x /usr/local/bin/pirecon
log "Comando 'pirecon' criado em /usr/local/bin/"

# ── Serviço systemd (boot screen no e-paper) ─────────────────────────────────
cat > /etc/systemd/system/pirecon-boot.service << 'EOF'
[Unit]
Description=Pi Recon Boot Screen (e-paper)
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
log "Serviço de boot screen configurado."

# ════════════════════════════════════════════════════════
# 6. RESUMO FINAL
# ════════════════════════════════════════════════════════
echo ""
echo "════════════════════════════════════════"
echo "   ✓ Instalação concluída!"
echo "════════════════════════════════════════"
echo ""
echo "  Swap ativo : $(free -h | grep Swap | awk '{print $2}')"
echo "  Python venv: /opt/pi_recon_env"
echo "  Arquivos   : /opt/pi_recon/"
echo "  Logs       : /opt/pi_recon/logs/"
echo ""
echo "Próximo passo — configure sua API Key:"
echo ""
echo "  echo 'export GEMINI_API_KEY=\"sua_chave\"' >> ~/.bashrc"
echo "  source ~/.bashrc"
echo ""
echo "  Obtenha sua chave gratuita em:"
echo "  https://aistudio.google.com/app/apikey"
echo ""
echo "Para iniciar:"
echo "  pirecon              # ferramentas normais"
echo "  sudo pirecon         # bettercap / wireless"
echo ""
warn "Use apenas em redes com autorização explícita."
echo ""