#!/usr/bin/env python3
"""
Pi Recon - Ferramenta de reconhecimento com análise via Gemini AI
Uso: python3 scanner.py
"""

import subprocess
import json
import os
import sys
import time
import datetime
import textwrap
from pathlib import Path

try:
    import google.generativeai as genai
except ImportError:
    print("[ERRO] Instale: pip install google-generativeai")
    sys.exit(1)

# ── Configuração ──────────────────────────────────────────────────────────────
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "SUA_CHAVE_AQUI")
GEMINI_MODEL   = "gemini-1.5-flash"   # gratuito e rápido
LOG_DIR        = Path("./logs")
LOG_DIR.mkdir(exist_ok=True)

# Tenta importar suporte ao e-paper (não falha se não tiver)
EPAPER_ENABLED = False
try:
    import epaper_display as epd_mod
    EPAPER_ENABLED = True
except ImportError:
    pass

# ── Cores terminal ────────────────────────────────────────────────────────────
class C:
    RED    = "\033[91m"
    GREEN  = "\033[92m"
    YELLOW = "\033[93m"
    CYAN   = "\033[96m"
    BOLD   = "\033[1m"
    RESET  = "\033[0m"

# ── Gemini ────────────────────────────────────────────────────────────────────
def init_gemini():
    genai.configure(api_key=GEMINI_API_KEY)
    return genai.GenerativeModel(GEMINI_MODEL)

def analyze_with_gemini(model, tool_name: str, target: str, raw_output: str) -> str:
    """Envia saída da ferramenta para o Gemini e retorna análise."""
    prompt = f"""Você é um especialista em cibersegurança analisando resultados de pentest.
Ferramenta: {tool_name}
Alvo: {target}

--- OUTPUT ---
{raw_output[:6000]}
--- FIM ---

Responda SOMENTE em português, de forma concisa e técnica:
1. RESUMO (2 linhas): o que foi encontrado
2. VULNERABILIDADES: liste as mais críticas (se houver)
3. PRÓXIMOS PASSOS: 2-3 comandos concretos a executar
4. RISCO GERAL: Baixo / Médio / Alto / Crítico

Seja direto. Sem introduções desnecessárias."""

    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"[Erro Gemini] {e}"

# ── Ferramentas ───────────────────────────────────────────────────────────────
def run_tool(cmd: list, timeout: int = 300) -> tuple[str, str, int]:
    """Executa comando e retorna (stdout, stderr, returncode)."""
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        return proc.stdout, proc.stderr, proc.returncode
    except subprocess.TimeoutExpired:
        return "", "[TIMEOUT] O comando excedeu o tempo limite.", -1
    except FileNotFoundError:
        return "", f"[ERRO] Ferramenta não encontrada: {cmd[0]}", -1

def tool_nmap(target: str) -> tuple[str, str]:
    """Scan nmap de portas e serviços."""
    print(f"{C.CYAN}[*] Executando nmap em {target}...{C.RESET}")
    options = [
        ("Rápido (top 100 portas)",    ["-F", "--open"]),
        ("Completo (todas as portas)", ["-p-", "--open"]),
        ("Serviços e versões",         ["-sV", "-sC", "--open"]),
        ("UDP top 20",                 ["-sU", "--top-ports", "20"]),
    ]
    print("\nTipo de scan:")
    for i, (desc, _) in enumerate(options, 1):
        print(f"  {i}. {desc}")
    choice = input("Escolha [1-4]: ").strip()
    idx = int(choice) - 1 if choice.isdigit() and 1 <= int(choice) <= 4 else 0
    flags = options[idx][1]

    cmd = ["nmap"] + flags + ["-oN", "-", target]
    stdout, stderr, rc = run_tool(cmd, timeout=600)
    output = stdout or stderr
    return "nmap", output

def tool_nikto(target: str) -> tuple[str, str]:
    """Scan de vulnerabilidades web com nikto."""
    print(f"{C.CYAN}[*] Executando nikto em {target}...{C.RESET}")
    url = target if target.startswith("http") else f"http://{target}"
    cmd = ["nikto", "-h", url, "-nointeractive"]
    stdout, stderr, rc = run_tool(cmd, timeout=300)
    return "nikto", stdout or stderr

def tool_gobuster(target: str) -> tuple[str, str]:
    """Enumeração de diretórios com gobuster."""
    print(f"{C.CYAN}[*] Executando gobuster em {target}...{C.RESET}")
    url = target if target.startswith("http") else f"http://{target}"
    wordlist = "/usr/share/wordlists/dirb/common.txt"
    if not Path(wordlist).exists():
        wordlist = "/usr/share/wordlists/dirbuster/directory-list-2.3-small.txt"
    if not Path(wordlist).exists():
        return "gobuster", "[ERRO] Wordlist não encontrada. Instale: apt install wordlists"
    cmd = ["gobuster", "dir", "-u", url, "-w", wordlist, "-t", "20", "-q"]
    stdout, stderr, rc = run_tool(cmd, timeout=300)
    return "gobuster", stdout or stderr

def tool_bettercap(target: str) -> tuple[str, str]:
    """Recon wireless com bettercap (requer root)."""
    if os.geteuid() != 0:
        return "bettercap", "[ERRO] bettercap requer execução como root (sudo)."
    iface = input("Interface wireless [ex: wlan1]: ").strip() or "wlan1"
    print(f"{C.CYAN}[*] Executando bettercap (30s de captura)...{C.RESET}")
    script = f"set wifi.recon.channel 0; wifi.recon on; sleep 30; wifi.show; exit"
    cmd = ["bettercap", "-iface", iface, "-eval", script]
    stdout, stderr, rc = run_tool(cmd, timeout=60)
    return "bettercap", stdout or stderr

# ── Logging ───────────────────────────────────────────────────────────────────
def save_log(target: str, tool: str, raw: str, analysis: str):
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    fname = LOG_DIR / f"{ts}_{tool}_{target.replace('/', '_')}.json"
    data = {
        "timestamp": ts,
        "target": target,
        "tool": tool,
        "raw_output": raw,
        "gemini_analysis": analysis,
    }
    with open(fname, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"{C.GREEN}[+] Log salvo: {fname}{C.RESET}")

# ── E-Paper display ───────────────────────────────────────────────────────────
def display_on_epaper(tool: str, target: str, analysis: str):
    """Exibe resumo no display Waveshare e-paper."""
    if not EPAPER_ENABLED:
        return
    try:
        epd_mod.show_scan_result(tool, target, analysis)
    except Exception as e:
        print(f"{C.YELLOW}[!] E-paper erro: {e}{C.RESET}")

# ── Menu principal ────────────────────────────────────────────────────────────
TOOLS = {
    "1": ("nmap",      tool_nmap),
    "2": ("nikto",     tool_nikto),
    "3": ("gobuster",  tool_gobuster),
    "4": ("bettercap", tool_bettercap),
}

def print_banner():
    print(f"""{C.GREEN}{C.BOLD}
 ██████╗ ██╗    ██████╗ ███████╗ ██████╗ ██████╗ ███╗   ██╗
 ██╔══██╗██║    ██╔══██╗██╔════╝██╔════╝██╔═══██╗████╗  ██║
 ██████╔╝██║    ██████╔╝█████╗  ██║     ██║   ██║██╔██╗ ██║
 ██╔═══╝ ██║    ██╔══██╗██╔══╝  ██║     ██║   ██║██║╚██╗██║
 ██║     ██║    ██║  ██║███████╗╚██████╗╚██████╔╝██║ ╚████║
 ╚═╝     ╚═╝    ╚═╝  ╚═╝╚══════╝ ╚═════╝ ╚═════╝ ╚═╝  ╚═══╝
{C.RESET}{C.CYAN}        Raspberry Pi Recon Tool  ·  Powered by Gemini AI{C.RESET}
""")

def main():
    print_banner()

    if GEMINI_API_KEY == "SUA_CHAVE_AQUI":
        print(f"{C.RED}[ERRO] Defina sua chave: export GEMINI_API_KEY='sua_chave'{C.RESET}")
        sys.exit(1)

    print(f"{C.YELLOW}[*] Inicializando Gemini ({GEMINI_MODEL})...{C.RESET}")
    model = init_gemini()
    print(f"{C.GREEN}[+] Gemini pronto!{C.RESET}")
    if EPAPER_ENABLED:
        print(f"{C.GREEN}[+] Display e-paper detectado.{C.RESET}")

    while True:
        print(f"\n{C.BOLD}{'─'*50}{C.RESET}")
        print(f"{C.BOLD}FERRAMENTAS DISPONÍVEIS:{C.RESET}")
        for k, (name, _) in TOOLS.items():
            print(f"  {k}. {name}")
        print(f"  0. Sair")
        print(f"{C.BOLD}{'─'*50}{C.RESET}")

        choice = input("\nEscolha a ferramenta: ").strip()

        if choice == "0":
            print(f"{C.CYAN}[*] Saindo...{C.RESET}")
            break

        if choice not in TOOLS:
            print(f"{C.RED}[!] Opção inválida.{C.RESET}")
            continue

        target = input("Alvo (IP, hostname ou URL): ").strip()
        if not target:
            print(f"{C.RED}[!] Alvo não pode ser vazio.{C.RESET}")
            continue

        tool_name, tool_fn = TOOLS[choice]

        # Executa a ferramenta
        _, raw_output = tool_fn(target)

        if not raw_output.strip():
            print(f"{C.YELLOW}[!] Nenhum output gerado.{C.RESET}")
            continue

        # Mostra output bruto
        print(f"\n{C.BOLD}── OUTPUT BRUTO ──{C.RESET}")
        print(raw_output[:3000])
        if len(raw_output) > 3000:
            print(f"{C.YELLOW}[...truncado, completo no log]{C.RESET}")

        # Análise com Gemini
        print(f"\n{C.YELLOW}[*] Analisando com Gemini AI...{C.RESET}")
        analysis = analyze_with_gemini(model, tool_name, target, raw_output)

        print(f"\n{C.BOLD}{C.GREEN}── ANÁLISE GEMINI ──{C.RESET}")
        print(analysis)

        # Salva log
        save_log(target, tool_name, raw_output, analysis)

        # Exibe no e-paper
        display_on_epaper(tool_name, target, analysis)

        input(f"\n{C.CYAN}[Enter para continuar...]{C.RESET}")

if __name__ == "__main__":
    main()
