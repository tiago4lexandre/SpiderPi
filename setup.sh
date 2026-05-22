#!/bin/bash
# setup.sh — Instalação do SpiderPi no Raspberry Pi Zero 2W
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
echo "   SPIDER PI — Setup & Instalação"
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

log "Atualizando listas do APT..."
apt-get update -qq

step "Instalando ferramentas de sistema e hardware"

# Pacotes de sistema necessários para o display e ferramentas
APT_PACKAGES=(
    "nmap" "nikto" "gobuster" "bettercap" "aircrack-ng" "wordlists"
    "python3-pip" "python3-venv" "python3-dev" "git" "fonts-dejavu"
    "libjpeg-dev" "zlib1g-dev" "libfreetype6-dev"
    "python3-spidev" "python3-rpi.gpio" "python3-gpiozero"
    "wget" "unzip" "make" "gcc" "swig" # Para compilar liblgpio
)

for pkg in "${APT_PACKAGES[@]}"; do
    if dpkg -s "$pkg" &>/dev/null; then
        log "$pkg já instalado."
    else
        log "Instalando $pkg..."
        apt-get install -y -qq "$pkg" || warn "Falha ao instalar $pkg."
    fi
done

# ── Habilitar SPI ─────────────────────────────────────────────────────────────
step "Configurando Hardware (SPI)"
CONFIG_FILES=("/boot/config.txt" "/boot/firmware/config.txt")
SPI_ENABLED=false

for cfg in "${CONFIG_FILES[@]}"; do
    if [ -f "$cfg" ]; then
        if grep -q "^dtparam=spi=on" "$cfg"; then
            log "SPI já habilitado em $cfg"
            SPI_ENABLED=true
        else
            log "Habilitando SPI em $cfg..."
            echo "dtparam=spi=on" >> "$cfg"
            SPI_ENABLED=true
        fi
    fi
done
[ "$SPI_ENABLED" = false ] && warn "Arquivo de configuração de boot não encontrado. Habilite SPI manualmente."

# ── Compilar liblgpio ─────────────────────────────────────────────────────────
step "Instalando liblgpio (Nativo)"
if [ ! -f /usr/local/include/lgpio.h ]; then
    log "Baixando e compilando liblgpio..."
    TEMP_DIR=$(mktemp -d)
    cd "$TEMP_DIR"
    wget -q https://github.com/joan2937/lg/archive/master.zip -O lg.zip
    unzip -q lg.zip
    cd lg-master
    make -s
    make install -s
    cd - > /dev/null
    rm -rf "$TEMP_DIR"
    log "liblgpio instalada com sucesso."
else
    log "liblgpio já está instalada."
fi

# Configura permissões para o usuário atual (se não for root)
CURRENT_USER=$(logname 2>/dev/null || echo $SUDO_USER)
if [ ! -z "$CURRENT_USER" ]; then
    log "Configurando permissões para o usuário: $CURRENT_USER"
    usermod -a -G gpio,spi,i2c "$CURRENT_USER" || true
fi

# ── Wordlists ─────────────────────────────────────────────────────────────────
if [ -f /usr/share/wordlists/rockyou.txt.gz ]; then
    log "Descomprimindo rockyou.txt..."
    gunzip -f /usr/share/wordlists/rockyou.txt.gz || true
fi

# ════════════════════════════════════════════════════════
# 3. PYTHON — ambiente virtual + dependências
# ════════════════════════════════════════════════════════
step "Configurando Ambiente Virtual Python"

VENV_PATH="/opt/spiderpi_env"
if [ ! -d "$VENV_PATH" ]; then
    python3 -m venv "$VENV_PATH"
fi

PIP="$VENV_PATH/bin/pip"
$PIP install --upgrade pip -q

log "Instalando dependências Python no venv..."
# No Python 3.13+, RPi.GPIO falha no edge detection.
# Usamos rpi-lgpio como shim de compatibilidade sobre a liblgpio compilada.
$PIP uninstall RPi.GPIO -y -q 2>/dev/null || true
$PIP install google-genai Pillow spidev gpiozero lgpio rpi-lgpio -q

# ════════════════════════════════════════════════════════
# 4. DRIVER WAVESHARE E-PAPER
# ════════════════════════════════════════════════════════
step "Instalando drivers Waveshare"

DISPLAY_MODEL=$(grep "^DISPLAY_MODEL =" epaper_display.py | cut -d'"' -f2 || echo "epd2in13_V4")
TARGET_LIB_DIR="/opt/pi_recon/waveshare_epd"
LOCAL_LIB_DIR="./waveshare_epd"

mkdir -p "$TARGET_LIB_DIR"
mkdir -p "$LOCAL_LIB_DIR"

BASE_URL="https://raw.githubusercontent.com/waveshareteam/e-Paper/master/RaspberryPi_JetsonNano/python/lib/waveshare_epd"

install_drivers() {
    local dest="$1"
    log "Instalando drivers em $dest..."
    if curl -s -f "$BASE_URL/__init__.py" -o "$dest/__init__.py" && \
       curl -s -f "$BASE_URL/epdconfig.py" -o "$dest/epdconfig.py" && \
       curl -s -f "$BASE_URL/${DISPLAY_MODEL}.py" -o "$dest/${DISPLAY_MODEL}.py"; then
        return 0
    else
        return 1
    fi
}

log "Baixando drivers para $DISPLAY_MODEL..."
if install_drivers "$TARGET_LIB_DIR" && cp -r "$TARGET_LIB_DIR/"* "$LOCAL_LIB_DIR/"; then
    log "Drivers instalados com sucesso."
else
    warn "Falha no download via curl, tentando fallback com clone esparso..."
    
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
        cp -r RaspberryPi_JetsonNano/python/lib/waveshare_epd/* "$LOCAL_LIB_DIR/"
        log "Drivers instalados via clone esparso de fallback."
    else
        warn "Falha crítica ao obter drivers do e-paper."
    fi
    cd - > /dev/null
    rm -rf "$EPAPER_DIR"
fi

# ════════════════════════════════════════════════════════
# 5. ARQUIVOS DO SPIDER PI
# ════════════════════════════════════════════════════════
step "Instalando SpiderPi"

mkdir -p /opt/spiderpi/logs
chmod 777 /opt/spiderpi/logs
chmod 755 /opt/spiderpi

for f in scanner.py epaper_display.py test_epaper.py; do
    if [ -f "./$f" ]; then
        cp "./$f" /opt/spiderpi/
        log "$f copiado."
    else
        warn "$f não encontrado no diretório atual."
    fi
done

# ── Comando global spiderpi ────────────────────────────────────────────────────
cat > /usr/local/bin/spiderpi << 'EOF'
#!/bin/bash
cd /opt/spiderpi
source /opt/spiderpi_env/bin/activate
exec python3 scanner.py "$@"
EOF
chmod +x /usr/local/bin/spiderpi
log "Comando 'spiderpi' criado em /usr/local/bin/"

# ── Serviço systemd (boot screen no e-paper) ─────────────────────────────────
cat > /etc/systemd/system/spiderpi-boot.service << 'EOF'
[Unit]
Description=SpiderPi Boot Screen (e-paper)
After=network.target

[Service]
Type=oneshot
WorkingDirectory=/opt/spiderpi
ExecStart=/opt/spiderpi_env/bin/python3 -c "import epaper_display; epaper_display.show_boot_screen()"
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable spiderpi-boot.service 2>/dev/null || true
log "Serviço de boot screen configurado."

# ════════════════════════════════════════════════════════
# 6. RESUMO FINAL
# ════════════════════════════════════════════════════════
echo ""
echo -e "${GREEN}════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}   ✓ INSTALAÇÃO DO SPIDERPI CONCLUÍDA!${NC}"
echo -e "${GREEN}════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "${CYAN}1. CONFIGURAÇÃO DA API KEY (OBRIGATÓRIO)${NC}"
echo "   Para que a análise do Antigravity funcione, você precisa de uma chave gratuita."
echo "   Obtenha em: https://aistudio.google.com/app/apikey"
echo ""
echo "   Para configurar permanentemente (recomendado):"
echo -e "   ${YELLOW}echo 'export GEMINI_API_KEY=\"sua_chave_aqui\"' >> ~/.zshrc${NC} (se usar Kali)"
echo -e "   ${YELLOW}echo 'export GEMINI_API_KEY=\"sua_chave_aqui\"' >> ~/.bashrc${NC} (se usar Raspberry Pi OS)"
echo "   Em seguida, rode: source ~/.zshrc$ (ou .bashrc)"
echo ""
echo -e "${CYAN}2. TESTE DE HARDWARE${NC}"
echo "   Antes de iniciar, verifique se o display e o SPI estão funcionando:"
echo -e "   ${YELLOW}sudo spiderpi_env/bin/python3 test_epaper.py${NC}"
echo "   (Siga as instruções na tela para habilitar SPI se necessário e reiniciar)"
echo ""
echo -e "${CYAN}3. INICIAR O SPIDERPI${NC}"
echo "   Simplesmente digite:"
echo -e "   ${GREEN}spiderpi${NC}"
echo ""
echo "   Para scans que exigem root (ex: Bettercap):"
echo -e "   ${GREEN}sudo -E spiderpi${NC}"
echo ""
echo -e "${RED}⚠ AVISO: Use apenas em redes com autorização explícita.${NC}"
echo -e "${GREEN}════════════════════════════════════════════════════════${NC}"
echo ""
