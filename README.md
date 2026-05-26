<!-- ===================================== -->
<!--        SPIDERPI RECON PLATFORM        -->
<!-- ===================================== -->

<p align="center">
  <img src="https://img.shields.io/badge/Platform-Raspberry%20Pi%20Zero%202W-black?style=for-the-badge">
  <img src="https://img.shields.io/badge/AI-Antigravity%202.1%20%7C%20Gemini%203.5%20Flash-blue?style=for-the-badge">
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Focus-Reconnaissance%20%7C%20Threat%20Analysis-red?style=flat-square">
  <img src="https://img.shields.io/badge/Discipline-Offensive%20Security-purple?style=flat-square">
  <img src="https://img.shields.io/badge/Hardware-Waveshare%20E--Paper-green?style=flat-square">
  <img src="https://img.shields.io/badge/Level-Intermediate%20%E2%86%92%20Advanced-yellow?style=flat-square">
</p>

---

# SpiderPi 🕷️ v2.1.0 — Antigravity 2.1
**Plataforma de reconhecimento automatizada com análise via Gemini 3.5 Flash**
Para Raspberry Pi Zero 2W com display Waveshare e-paper

![](assets/spiderpi.png)

---

## Estrutura do Projeto

```
spiderpi/
├── web/                # Interface Web (Flask/Dashboard)
│   ├── app.py          # Backend do dashboard
│   ├── static/         # CSS e assets web
│   └── templates/      # Templates HTML
├── scanner.py          # Script principal — menu e integração Antigravity
├── epaper_display.py   # Driver do display Waveshare (v2.0)
├── setup.sh            # Instalação automatizada
├── KALI_INSTALL.md     # Guia de instalação do Kali Linux (Headless)
├── USAGE.md            # Guia de uso detalhado (CLI + Web)
├── CHANGELOG.md        # Histórico de versões e Release Notes
├── logs/               # JSONs com histórico de scans
└── README.md
```

---

## 📚 Documentação Detalhada

Para facilitar a navegação, o projeto está dividido nos seguintes guias:

1.  **[Guia de Instalação (KALI_INSTALL.md)](KALI_INSTALL.md)**: Como preparar o Raspberry Pi Zero 2W com Kali Linux Headless.
2.  **[Guia de Uso (USAGE.md)](USAGE.md)**: Detalhes sobre os comandos CLI, flags de automação e o Dashboard Web.
3.  **[Release Notes (CHANGELOG.md)](CHANGELOG.md)**: O que há de novo na versão v2.1.0.

---

## 🛠️ Instalação Rápida

```bash
# 1. Clone ou copie os arquivos para o Pi
scp -r spiderpi/ pi@raspberrypi.local:~/

# 2. No Pi, execute o setup (requer root)
ssh pi@raspberrypi.local
cd ~/spiderpi
chmod +x setup.sh
sudo ./setup.sh

# O setup.sh criará um ambiente virtual (venv) e instalará o SDK 'google-genai'.
# Também será criado um alias 'spiderpi' para facilitar o acesso e um serviço systemd
# para mostrar uma tela de boot no e-paper.

# 3. Configure a API Key (Plataforma Antigravity / Google AI Studio)
# Durante o setup.sh, você será solicitado a inserir sua chave.
# Caso queira configurar manualmente depois:
echo 'export GEMINI_API_KEY="sua_chave_aqui"' >> ~/.zshrc
source ~/.zshrc
```

---

## 🖥️ Interface Web (Dashboard)
O SpiderPi possui um painel de controle que inicia **automaticamente** em background:

- **Monitoramento em Tempo Real:** Veja o progresso dos scans linha por linha via **Live Terminal Feed**.
- **Análise Inteligente:** Visualize as vulnerabilidades encontradas pela IA Antigravity 2.1.
- **Estatísticas:** Acompanhe CPU, Temperatura e RAM do dispositivo em tempo real.
- **Acesse:** `http://raspberrypi.local:5000` (ou o IP do seu dispositivo)

---

## 🕹️ Modos de Uso
O SpiderPi suporta operação híbrida total:

1. **Modo Interativo (Menu):** `sudo -E spiderpi`
2. **Modo Direto (Flags):** `sudo -E spiderpi --tool nmap --target 192.168.1.1`
3. **Dashboard Web:** Inicie scans remotamente pelo navegador.

---

## ⚠️ Aviso Legal
Esta ferramenta é destinada exclusivamente para fins educacionais e testes de penetração autorizados. O uso em redes sem permissão é ilegal.
