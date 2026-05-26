# 🕷️ SpiderPi — Guia de Uso

O SpiderPi pode ser operado de três formas principais: **CLI Interativo**, **CLI Direto (Flags)** e **Web Dashboard**.

---

## 1. CLI Interativo (Menu)
Ideal para operação manual via terminal ou SSH. O menu guiará você pelas opções de cada ferramenta.

```bash
# Inicie o menu interativo
sudo -E spiderpi
```
*   **Nota:** O `-E` é obrigatório para que o script acesse sua chave de API (`GEMINI_API_KEY`).

---

## 2. CLI Direto (Flags/Automação)
Ideal para scripts ou quando você já sabe exatamente o que quer executar. Pula todos os menus e perguntas.

```bash
# Sintaxe:
sudo -E spiderpi --tool [NOME] --target [ALVO]

# Exemplos:
sudo -E spiderpi --tool nmap --target 192.168.1.1
sudo -E spiderpi --tool nikto --target http://meu-alvo.com
sudo -E spiderpi --tool gobuster --target 10.0.0.50
sudo -E spiderpi --tool bettercap --target wlan1
```

### Ferramentas disponíveis (`--tool`):
- `nmap`: Port scan e detecção de serviços (usa `-sV -sC` por padrão).
- `nikto`: Scan de vulnerabilidades web.
- `gobuster`: Enumeração de diretórios (usa threads=20 por padrão).
- `bettercap`: Recon Wi-Fi (usa interface wlan1 e duração de 30s por padrão).

---

## 3. Web Dashboard
O painel de controle inicia automaticamente em background após o `setup.sh`.

- **Acesse:** `http://raspberrypi.local:5000` (ou o IP do dispositivo)
- **Funcionalidades:**
    - Monitoramento de hardware (Temp, CPU, RAM).
    - Histórico completo de scans (mesmo os feitos via terminal).
    - Leitura detalhada das análises do Antigravity AI.
    - Disparo de novos scans remotamente.

### Gestão do Serviço Web:
```bash
# Ver status
sudo systemctl status spiderpi-web

# Reiniciar
sudo systemctl restart spiderpi-web

# Ver logs do servidor web
tail -f /opt/spiderpi/logs/web.log
```

---

## 📂 Logs e Histórico
Todos os resultados (CLI ou Web) são salvos em formato JSON em:
`/opt/spiderpi/logs/`

Cada log contém o output bruto da ferramenta e a análise técnica gerada pela IA Antigravity.

---

## ⚠️ Requisito Obrigatório
Certifique-se de que sua API Key está configurada no seu `.zshrc` ou `.bashrc`:
```bash
export GEMINI_API_KEY="sua_chave_aqui"
```
Para testar se a chave está ativa: `echo $GEMINI_API_KEY`
