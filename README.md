# Pi Recon 🔍
**Ferramenta de reconhecimento de segurança com análise via Gemini AI**
Para Raspberry Pi Zero 2W com display Waveshare e-paper

---

## Estrutura do Projeto

```
pi_recon/
├── scanner.py          # Script principal — menu e integração Gemini
├── epaper_display.py   # Driver do display Waveshare
├── setup.sh            # Instalação automática
├── logs/               # JSONs com histórico de scans
└── README.md
```

---

## Instalação Rápida

```bash
# 1. Clone ou copie os arquivos para o Pi
scp -r pi_recon/ pi@raspberrypi.local:~/

# 2. No Pi, execute o setup (requer root)
ssh pi@raspberrypi.local
cd ~/pi_recon
chmod +x setup.sh
sudo ./setup.sh

# 3. Configure a API Key do Gemini (gratuita)
# Acesse: https://aistudio.google.com/app/apikey
echo 'export GEMINI_API_KEY="sua_chave_aqui"' >> ~/.bashrc
source ~/.bashrc
```

---

## Configuração do E-Paper

Edite `epaper_display.py` e altere `DISPLAY_MODEL` para o seu modelo:

| Modelo Waveshare | Valor em DISPLAY_MODEL |
|---|---|
| 2.13" V3 (padrão Pwnagotchi) | `epd2in13_V3` |
| 2.7" | `epd2in7` |
| 3.7" | `epd3in7` |
| 4.2" | `epd4in2` |

---

## Uso

```bash
# Normal (nmap, nikto, gobuster)
pirecon

# Com root (bettercap/wireless)
sudo pirecon
```

### Fluxo de uso:
1. Escolha a ferramenta no menu
2. Informe o alvo (IP, hostname ou URL)
3. O scan executa e o output aparece no terminal
4. O Gemini analisa automaticamente
5. O display e-paper mostra o resumo
6. Log JSON salvo em `logs/`

---

## Exemplo de Output

```
── OUTPUT BRUTO ──
Starting Nmap 7.94 ( https://nmap.org )
PORT   STATE SERVICE VERSION
22/tcp open  ssh     OpenSSH 7.9
80/tcp open  http    Apache httpd 2.4.38

── ANÁLISE GEMINI ──
RESUMO: Alvo expõe SSH e HTTP. Apache desatualizado.

VULNERABILIDADES:
- Apache 2.4.38: CVE-2019-0211 (privilege escalation local)
- SSH sem rate limiting: vulnerável a brute force

PRÓXIMOS PASSOS:
1. nikto -h http://192.168.1.10
2. gobuster dir -u http://192.168.1.10 -w /usr/share/wordlists/dirb/common.txt
3. searchsploit apache 2.4.38

RISCO GERAL: Alto
```

---

## Logs

Cada scan gera um arquivo JSON em `logs/`:

```json
{
  "timestamp": "20240115_143022",
  "target": "192.168.1.10",
  "tool": "nmap",
  "raw_output": "...",
  "gemini_analysis": "..."
}
```

---

## Custo de API

O Gemini 1.5 Flash tem tier **gratuito generoso**:
- 15 requests/minuto
- 1 milhão tokens/dia gratuitos
- Para uso moderado de pentest: **$0**

---

## Requisitos de Hardware

- Raspberry Pi Zero 2W
- Display Waveshare e-paper (qualquer tamanho)
- Módulo de bateria
- Cartão MicroSD 16GB+ com Kali Linux ARM ou Raspberry Pi OS
- (Opcional) Adaptador USB WiFi extra para manter SSH enquanto monitora

---

## ⚠️ Aviso Legal

Esta ferramenta é destinada exclusivamente para:
- Testes em sua própria rede/infraestrutura
- Ambientes de lab controlados
- CTFs e programas de Bug Bounty com escopo definido

**O uso em redes sem autorização explícita é crime (Lei 12.737/2012 no Brasil).**
