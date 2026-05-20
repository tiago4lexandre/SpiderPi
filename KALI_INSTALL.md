# Tutorial: Instalando Kali Linux no Raspberry Pi Zero 2W (Modo Headless)

Este tutorial guia você no processo de instalação do Kali Linux ARM em um Raspberry Pi Zero 2W, configurando-o para ser operado remotamente via SSH desde o primeiro boot, sem a necessidade de monitor ou teclado externo.

## 1. Pré-requisitos

Para completar este guia, você precisará de:
- **Hardware:** Raspberry Pi Zero 2W.
- **Armazenamento:** Cartão MicroSD (mínimo 16GB, Classe 10 recomendado).
- **Conectividade:** Computador com leitor de cartão SD e acesso à internet.
- **Software:** [Raspberry Pi Imager](https://www.raspberrypi.com/software/).

## 2. Preparação da Imagem

O Kali Linux possui imagens específicas para arquitetura ARM:

1. Acesse [kali.org/get-kali/](https://www.kali.org/get-kali/#kali-arm).
2. Expanda a seção **Raspberry Pi**.
3. Procure por **Raspberry Pi Zero 2 W**.
4. Baixe a imagem (formato `.img.xz`). Não é necessário descompactar; o Imager fará isso para você.

## 3. Gravação no Cartão SD

1. Insira o cartão MicroSD no seu computador.
2. Abra o **Raspberry Pi Imager**.
3. Em **CHOOSE OS**, selecione **Use custom** e escolha o arquivo do Kali baixado.
4. Em **CHOOSE STORAGE**, selecione o seu cartão MicroSD.
5. Clique em **WRITE** e aguarde a finalização.
   *Nota: Se o Imager perguntar se você deseja aplicar configurações de customização, você pode ignorar ou recusar, pois faremos manualmente no próximo passo.*

## 4. Configuração Headless Manual (BOOT)

Após a gravação, **não remova o cartão ainda**. Se o sistema ejetar o cartão automaticamente, retire-o e insira-o novamente no computador para que a partição chamada `boot` (ou `boot.bak`) seja montada.

### A. Ativar SSH
1. Abra a partição `boot` do cartão SD no seu gerenciador de arquivos.
2. Crie um arquivo vazio chamado apenas `ssh` (sem extensão e sem conteúdo). 
   *No Windows: Botão direito > Novo > Documento de Texto. Renomeie para "ssh" e apague o ".txt".*

### B. Configurar Wi-Fi (Opcional se usar USB Gadget)
1. Na mesma partição `boot`, crie um arquivo chamado `wpa_supplicant.conf`.
2. Abra o arquivo com um editor de texto (Notepad, VS Code, etc) e cole o seguinte conteúdo, substituindo pelos seus dados:

```text
country=BR
ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
update_config=1

network={
    ssid="NOME_DO_SEU_WIFI"
    psk="SUA_SENHA_AQUI"
    key_mgmt=WPA-PSK
}
```

### C. Configurar modo USB Ethernet Gadget (Acesso via Cabo USB)
Se você não tem Wi-Fi ou prefere conectar o Pi diretamente ao seu computador via USB:

1. Na partição `boot`, abra o arquivo `config.txt`.
2. Vá até o final do arquivo e adicione a seguinte linha em uma nova linha:
   ```text
   dtoverlay=dwc2
   ```
3. Agora, abra o arquivo `cmdline.txt`.
   - **Atenção:** Este arquivo possui apenas UMA linha. Não crie linhas novas.
   - Procure por `rootwait` e insira logo após ele (com um espaço): `modules-load=dwc2,g_ether`
   - Deve ficar algo como: `... rootwait modules-load=dwc2,g_ether quiet ...`
4. Salve os arquivos e ejete o cartão.

---

## 5. Primeiro Acesso e Conexão

### Conexão Física

> ⚠️ **Atenção crítica:** O Raspberry Pi Zero 2W possui **duas portas micro-USB**:
> - A porta mais próxima da borda da placa é a **PWR** (apenas energia).
> - A porta do **meio** é a **USB** (dados + energia).
>
> Para o modo USB Gadget funcionar, o cabo **obrigatoriamente** deve estar na porta **USB (do meio)**. Conectar na PWR fará a interface `usb0` aparecer sem carrier (`NO-CARRIER`) no host, mesmo com tudo configurado corretamente.

- **Via Wi-Fi:** Conecte o cabo de energia na porta **PWR**.
- **Via USB Gadget:** Conecte o cabo USB na porta **USB** (a do meio). Esta porta fornece energia e dados simultaneamente.

---

### Acessando via Linux

#### Passo 1 — Verificar o reconhecimento da interface

Após conectar o cabo USB na porta correta e aguardar ~60 segundos para o Pi bootar, execute:

```bash
ip a
```

Você deve ver a interface `usb0` com estado `UP` (não `NO-CARRIER`):

```
4: usb0: <BROADCAST,MULTICAST,UP,LOWER_UP> ...
    inet 169.254.x.x/16 ...
```

> **Se `usb0` aparecer como `NO-CARRIER`**, há um problema de hardware ou configuração:
> 1. Confirme que o cabo está na porta **USB (do meio)**, não na PWR.
> 2. Confirme que o cabo USB suporta dados (cabos "charge-only" não funcionam).
> 3. Confirme que as alterações em `config.txt` e `cmdline.txt` foram salvas corretamente (veja o Passo 4C).
> 4. Aguarde mais tempo — o primeiro boot do Kali pode levar de 2 a 4 minutos.

#### Passo 2 — Configurar compartilhamento de IP via NetworkManager

O Linux não atribui IP automaticamente para a interface `usb0`. É necessário configurar o compartilhamento via **NetworkManager**:

**Opção A — Via interface gráfica (GNOME/KDE):**
1. Abra as **Configurações de Rede**.
2. Encontre a conexão com fio que apareceu (geralmente chamada de "Ethernet" ou "USB Ethernet").
3. Clique em editar (ícone de engrenagem).
4. Na aba **IPv4**, mude o método para **"Compartilhado com outros computadores"** (*Shared to other computers*).
5. Salve e reconecte.

**Opção B — Via terminal (nmcli):**
```bash
# Encontre o nome exato da conexão usb0
nmcli device status

# Crie ou edite a conexão para compartilhamento
sudo nmcli connection add type ethernet ifname usb0 con-name "pi-usb" \
  ipv4.method shared ipv6.method ignore

sudo nmcli connection up "pi-usb"
```

Após isso, seu computador atribuirá um IP ao Pi (geralmente na faixa `10.42.0.x`) e o `usb0` ficará com `UP`.

#### Passo 3 — Descobrir o IP do Pi e conectar via SSH

O mDNS (`.local`) pode não funcionar de imediato. Use uma das abordagens abaixo para descobrir o IP:

**Abordagem 1 — arp-scan (mais confiável):**
```bash
sudo apt install arp-scan   # se ainda não tiver instalado
sudo arp-scan --interface=usb0 --localnet
```

**Abordagem 2 — nmap:**
```bash
# Substitua 10.42.0.0/24 pela sua faixa (veja ip a para confirmar)
sudo nmap -sn 10.42.0.0/24
```

**Abordagem 3 — verificar leases do dnsmasq:**
```bash
cat /var/lib/misc/dnsmasq.leases
# ou
cat /var/lib/NetworkManager/dnsmasq-*.leases 2>/dev/null
```

Com o IP em mãos (ex: `10.42.0.100`), conecte:

```bash
ssh kali@10.42.0.100
```

> **Sobre o `kali.local`:** O hostname `.local` via mDNS depende do serviço Avahi estar ativo no Pi. No primeiro boot do Kali ele pode não estar disponível ainda. Após o sistema estar configurado e o Avahi instalado/habilitado, você poderá usar `ssh kali@kali.local`. Evite depender dele no primeiro acesso.

> **Credenciais padrão do Kali:** usuário `kali`, senha `kali`.

---

### Acessando via Windows

1. Ao conectar via USB (porta do meio), o Windows pode reconhecer o Pi como dispositivo desconhecido ou "RNDIS".
2. Abra o **Gerenciador de Dispositivos**. Se aparecer "RNDIS" com erro amarelo, instale o driver **"USB Ethernet/RNDIS Gadget"** (disponível via Windows Update ou manualmente no site da Microsoft).
3. Uma vez reconhecido como adaptador de rede, o Pi receberá um IP na faixa `169.254.x.x` (Auto-IP via APIPA).
4. Descubra o IP do Pi:
   ```powershell
   arp -a
   ```
   Procure por uma entrada na faixa `169.254.x.x` associada ao adaptador USB.
5. Conecte via PowerShell ou CMD:
   ```bash
   ssh kali@169.254.x.x
   ```

> **Credenciais padrão do Kali:** usuário `kali`, senha `kali`.

---

## 6. Pós-instalação e Atualização

Uma vez dentro do sistema, é crucial atualizar os repositórios e o sistema base:

```bash
sudo apt update
sudo apt full-upgrade -y
```

*Nota: Este processo pode demorar no Pi Zero 2W devido ao hardware limitado.*

## 6. Próximos Passos (Configuração Pi Recon)

Com o sistema pronto e acessível, você pode prosseguir para a instalação das ferramentas de reconhecimento do projeto:

1. Clone o seu repositório ou copie os arquivos para o Pi.
2. Execute o script de configuração:
   ```bash
   chmod +x setup.sh
   sudo ./setup.sh
   ```

---
**Aviso de Segurança:** Como este dispositivo estará na sua rede com ferramentas de pentest, altere a senha padrão (`passwd`) imediatamente após o primeiro login bem-sucedido.