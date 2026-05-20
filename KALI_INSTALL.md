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
- **Via Wi-Fi:** Conecte o cabo de energia na porta **PWR**.
- **Via USB Gadget:** Conecte o cabo USB na porta **USB** (a porta do meio, não a da ponta). Esta porta fornecerá energia e dados.

### Acessando via Windows
1. Ao conectar via USB, o Windows pode reconhecer o Pi como uma porta serial ou dispositivo desconhecido.
2. Abra o **Gerenciador de Dispositivos**. Se aparecer "RNDIS" com um erro, você precisará instalar o driver "USB Ethernet/RNDIS Gadget" (disponível via Windows Update ou manualmente).
3. Uma vez reconhecido, o Pi terá o endereço IP padrão `169.254.x.x` (Auto-IP).
4. Use o terminal (PowerShell/CMD) para conectar:
   ```bash
   ssh kali@pirecon.local
   ```

### Acessando via Linux
1. Ao conectar o USB, o Linux geralmente reconhece a interface de rede automaticamente (ex: `usb0`).
2. Vá nas configurações de rede do seu sistema, encontre a nova conexão com fio e altere o método IPv4 para **"Shared to other computers"** (Compartilhado com outros computadores) ou garanta que ele obtenha um IP via Link-Local.
3. Conecte via terminal:
   ```bash
   ssh kali@pirecon.local
   ```
   *(Ou use `ssh kali@169.254.x.x` se souber o IP).*

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
