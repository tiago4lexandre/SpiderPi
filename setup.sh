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
step "Limpeza e Atualização do Sistema"

log "Limpando diretório temporário (/tmp)..."
rm -rf /tmp/* || true

log "Limpando cache e corrigindo listas do APT..."
rm -rf /var/lib/apt/lists/*
apt-get clean
apt-get update -qq

log "Sistema limpo e atualizado."

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

# 1. Detecta o modelo do display configurado em epaper_display.py
DISPLAY_MODEL=$(grep "^DISPLAY_MODEL =" epaper_display.py | cut -d'"' -f2 || echo "epd2in13_V4")
if [ -z "$DISPLAY_MODEL" ]; then
    DISPLAY_MODEL="epd2in13_V4"
    warn "Modelo não detectado em epaper_display.py, usando padrão: $DISPLAY_MODEL"
else
    log "Modelo de display detectado em epaper_display.py: $DISPLAY_MODEL"
fi

# 2. Cria a estrutura da biblioteca waveshare_epd no diretório de instalação
TARGET_LIB_DIR="/opt/pi_recon/waveshare_epd"
mkdir -p "$TARGET_LIB_DIR"

BASE_URL="https://raw.githubusercontent.com/waveshareteam/e-Paper/master/RaspberryPi_JetsonNano/python/lib/waveshare_epd"

log "Instalando drivers específicos para $DISPLAY_MODEL..."

# Baixa apenas os arquivos necessários da Waveshare via curl
if curl -s -f "$BASE_URL/__init__.py" -o "$TARGET_LIB_DIR/__init__.py" && \
   curl -s -f "$BASE_URL/epdconfig.py" -o "$TARGET_LIB_DIR/epdconfig.py" && \
   curl -s -f "$BASE_URL/${DISPLAY_MODEL}.py" -o "$TARGET_LIB_DIR/${DISPLAY_MODEL}.py"; then
    log "Drivers do e-paper instalados com sucesso em $TARGET_LIB_DIR (~10KB baixados)."
else
    warn "Falha ao baixar drivers específicos via curl. Tentando fallback com clone esparso..."
    
    EPAPER_DIR="/opt/e-paper-temp"
    rm -rf "$EPAPER_DIR"
    mkdir -p "$EPAPER_DIR"
    git init "$EPAPER_DIR" -q
    cd "$EPAPER_DIR"
    git remote add origin https://github.com/waveshare/e-Paper.git
    git config core.sparseCheckout true
    echo "RaspberryPi_JetsonNano/python/lib/waveshare_epd/__init__.py" >> .git/info/sparse-checkout
    echo "RaspberryPi_JetsonNano/python/lib/waveshare_epd/epdconfig.py" >> .git/info/sparse-checkout
    echo "RaspberryPi_JetsonNano/python/lib/waveshare_epd/${DISPLAY_MODEL}.py" >> .git/info/sparse-checkout
    
    if git pull --depth=1 origin master -q || git pull --depth=1 origin main -q; then
        cp -r RaspberryPi_JetsonNano/python/lib/waveshare_epd/* "$TARGET_LIB_DIR/"
        log "Drivers instalados via clone esparso de fallback."
    else
        warn "Falha crítica ao obter drivers do e-paper — display pode não funcionar."
    fi
    cd - > /dev/null
    rm -rf "$EPAPER_DIR"
fi

# ════════════════════════════════════════════════════════
# 5. ARQUIVOS DO PI RECON
# ════════════════════════════════════════════════════════
step "Instalando Pi Recon"

mkdir -p /opt/pi_recon/logs
chmod 777 /opt/pi_recon/logs
chmod 755 /opt/pi_recon

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
echo "  No Zsh (padrão no Kali):"
echo "    echo 'export GEMINI_API_KEY=\"sua_chave\"' >> ~/.zshrc"
echo "    source ~/.zshrc"
echo ""
echo "  No Bash:"
echo "    echo 'export GEMINI_API_KEY=\"sua_chave\"' >> ~/.bashrc"
echo "    source ~/.bashrc"
echo ""
echo "  Obtenha sua chave gratuita em:"
echo "  https://aistudio.google.com/app/apikey"
echo ""
echo "Para iniciar:"
echo "  pirecon              # ferramentas normais"
echo "  sudo -E pirecon      # bettercap / wireless (preservando API key)"
echo ""
warn "Use apenas em redes com autorização explícita."
echo ""