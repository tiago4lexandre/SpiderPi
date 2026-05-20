#!/bin/bash
# ============================================================
#  kali-connect.sh
#  Conecta ao Kali Linux no Raspberry Pi Zero 2W via USB Gadget
# ============================================================

########################
# CONFIGURAÇÕES
########################
IFACE="usb0"
SSH_USER="kali"
HOST_IP="10.42.0.1"       # IP que seu PC assume no modo "Shared"
SUBNET="10.42.0.0/24"     # Faixa atribuída ao Pi
BOOT_WAIT=60              # Segundos máximos aguardando o Pi bootar
PING_TRIES=20             # Tentativas de ping após link subir

########################
# CORES
########################
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

ok()   { echo -e "${GREEN}[+]${NC} $*"; }
info() { echo -e "${CYAN}[*]${NC} $*"; }
warn() { echo -e "${YELLOW}[!]${NC} $*"; }
fail() { echo -e "${RED}[x]${NC} $*"; exit 1; }

########################
# VERIFICAÇÕES INICIAIS
########################
echo ""
echo -e "${CYAN}╔══════════════════════════════════════╗"
echo -e "║     Kali Pi Zero 2W — USB Connect   ║"
echo -e "╚══════════════════════════════════════╝${NC}"
echo ""

# Interface existe?
if ! ip link show "$IFACE" &>/dev/null; then
    fail "Interface $IFACE não encontrada. Verifique se o cabo está na porta USB (do meio) do Pi."
fi

########################
# CONFIGURA INTERFACE
########################
info "Resetando interface $IFACE..."
sudo ip addr flush dev "$IFACE" 2>/dev/null
sudo ip link set "$IFACE" down
sleep 1
sudo ip link set "$IFACE" up

########################
# ATIVA COMPARTILHAMENTO VIA NETWORKMANAGER
########################
info "Configurando compartilhamento de rede (NetworkManager)..."

# Verifica se já existe uma conexão para usb0
EXISTING_CON=$(nmcli -t -f NAME,DEVICE connection show --active 2>/dev/null | grep ":$IFACE" | cut -d: -f1)

if [ -n "$EXISTING_CON" ]; then
    info "Conexão ativa encontrada: '$EXISTING_CON'. Reativando..."
    sudo nmcli connection up "$EXISTING_CON" &>/dev/null
else
    # Remove conexão antiga parada com mesmo nome, se houver
    sudo nmcli connection delete "pi-kali" &>/dev/null

    info "Criando conexão compartilhada para $IFACE..."
    sudo nmcli connection add \
        type ethernet \
        ifname "$IFACE" \
        con-name "pi-kali" \
        ipv4.method shared \
        ipv6.method ignore \
        connection.autoconnect no &>/dev/null \
    && sudo nmcli connection up "pi-kali" &>/dev/null \
    || fail "Falha ao configurar o NetworkManager. Tente manualmente: sudo nmcli connection up pi-kali"
fi

########################
# AGUARDA LINK FÍSICO
########################
info "Aguardando link físico em $IFACE..."
for i in $(seq 1 15); do
    STATE=$(cat /sys/class/net/"$IFACE"/operstate 2>/dev/null)
    if [ "$STATE" = "up" ]; then
        ok "Link físico estabelecido."
        break
    fi
    printf "  %s Tentativa %d/15 (estado: %s)...\n" "$(echo -e ${YELLOW}>${NC})" "$i" "$STATE"
    sleep 2
    if [ "$i" -eq 15 ]; then
        fail "Link não subiu. Verifique o cabo (deve suportar dados) e a porta (USB do meio, não PWR)."
    fi
done

########################
# DESCOBERTA DO IP DO PI
########################
info "Descobrindo IP do Raspberry Pi em $SUBNET..."
PI_IP=""

# Aguarda o Pi bootar e responder ARP/ping
for i in $(seq 1 "$PING_TRIES"); do
    # Tenta via arp-scan se disponível
    if command -v arp-scan &>/dev/null; then
        PI_IP=$(sudo arp-scan --interface="$IFACE" --localnet 2>/dev/null \
            | grep -v "^Interface\|^Starting\|^Ending\|packets\|^$" \
            | grep -v "$HOST_IP" \
            | awk '{print $1}' | head -1)
    fi

    # Fallback: lê o lease do dnsmasq gerado pelo NetworkManager
    if [ -z "$PI_IP" ]; then
        LEASE_FILE=$(ls /var/lib/NetworkManager/dnsmasq-*.leases 2>/dev/null | head -1)
        if [ -n "$LEASE_FILE" ]; then
            PI_IP=$(awk '{print $3}' "$LEASE_FILE" | grep -v "^$" | head -1)
        fi
    fi

    # Fallback: varredura da tabela ARP do kernel
    if [ -z "$PI_IP" ]; then
        PI_IP=$(arp -n -i "$IFACE" 2>/dev/null \
            | grep -v "incomplete\|Address\|$HOST_IP" \
            | awk '{print $1}' | head -1)
    fi

    if [ -n "$PI_IP" ]; then
        ok "Pi encontrado em: $PI_IP"
        break
    fi

    printf "  %s Aguardando Pi... %d/%d\n" "$(echo -e ${YELLOW}>${NC})" "$i" "$PING_TRIES"
    sleep 3

    if [ "$i" -eq "$PING_TRIES" ]; then
        warn "Não foi possível detectar o IP automaticamente."
        echo -n "  Digite o IP do Pi manualmente (ou Enter para cancelar): "
        read -r PI_IP
        [ -z "$PI_IP" ] && fail "Sem IP. Abortando."
    fi
done

########################
# TESTE DE CONECTIVIDADE
########################
info "Testando conectividade com $PI_IP..."
if ! ping -c 3 -W 2 "$PI_IP" > /dev/null 2>&1; then
    warn "Pi não responde ao ping. Pode estar ainda bootando (primeiro boot leva ~3 min)."
    echo -n "  Tentar conectar via SSH mesmo assim? [s/N] "
    read -r FORCE
    [[ "$FORCE" != "s" && "$FORCE" != "S" ]] && fail "Abortando."
else
    ok "Pi respondendo. Latência: $(ping -c 1 -W 1 "$PI_IP" 2>/dev/null | grep 'time=' | sed 's/.*time=//;s/ ms.*//')ms"
fi

########################
# CONEXÃO SSH
########################
echo ""
info "Conectando via SSH como '${SSH_USER}@${PI_IP}'..."
echo -e "  ${YELLOW}Credenciais padrão: kali / kali${NC}"
echo ""

ssh \
    -o StrictHostKeyChecking=no \
    -o ConnectTimeout=10 \
    -o ServerAliveInterval=30 \
    "${SSH_USER}@${PI_IP}"

SSH_EXIT=$?
echo ""
if [ "$SSH_EXIT" -eq 0 ]; then
    ok "Sessão SSH encerrada normalmente."
else
    warn "SSH encerrou com código $SSH_EXIT."
fi
