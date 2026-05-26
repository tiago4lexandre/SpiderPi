#!/usr/bin/env python3
"""
Pi Recon - Ferramenta de reconhecimento com análise via Antigravity 2.0
Uso: python3 scanner.py

Dependências:
    pip install google-genai

API Key gratuita (1.000 req/dia):
    https://aistudio.google.com/app/apikey
"""

import subprocess
import json
import os
import sys
import datetime
import argparse
from pathlib import Path

# ── Importa novo SDK oficial (google-genai, GA desde maio 2025) ───────────────
try:
    from google import genai
    from google.genai import types
except ImportError:
    print("[ERRO] SDK não encontrado. Execute:")
    print("       pip install google-genai")
    sys.exit(1)

# ── Configuração ──────────────────────────────────────────────────────────────
ANTIGRAVITY_API_KEY = os.environ.get("GEMINI_API_KEY", "SUA_CHAVE_AQUI")

# gemini-3.5-flash: Padrão Antigravity 2.0 (maio 2026)
ANTIGRAVITY_MODEL = "gemini-3.5-flash"

# Define LOG_DIR como absoluto se estiver rodando via /opt/spiderpi
BASE_DIR = Path(__file__).resolve().parent
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)

# Tenta importar suporte ao e-paper (não falha se não tiver)
EPAPER_ENABLED = False
try:
    # Adiciona o diretório atual ao path para garantir que importe o local
    sys.path.append(str(BASE_DIR))
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
    DIM    = "\033[2m"
    RESET  = "\033[0m"

# ── Antigravity Engine (Gemini SDK) ───────────────────────────────────────────
def init_antigravity() -> genai.Client:
    """Inicializa cliente Antigravity com o SDK google-genai."""
    return genai.Client(api_key=ANTIGRAVITY_API_KEY)

def analyze_with_antigravity(client: genai.Client, tool_name: str, target: str, raw_output: str) -> str:
    """Envia saída da ferramenta para o Antigravity e retorna análise em português."""
    prompt = f"""Você é um especialista em cibersegurança analisando resultados de pentest autorizado.
Ferramenta usada: {tool_name}
Alvo: {target}

--- OUTPUT DA FERRAMENTA ---
{raw_output[:8000]}
--- FIM DO OUTPUT ---

Responda SOMENTE em português, de forma concisa e técnica, seguindo exatamente este formato:

RESUMO:
(2 linhas descrevendo o que foi encontrado)

VULNERABILIDADES:
(liste as mais críticas com CVE se souber; escreva "Nenhuma identificada" se não houver)

PRÓXIMOS PASSOS:
(2-3 comandos concretos e prontos para executar)

RISCO GERAL: <Baixo | Médio | Alto | Crítico>

Seja direto e técnico. Sem introduções, sem repetir o output."""

    try:
        response = client.models.generate_content(
            model=ANTIGRAVITY_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.1,       # Ainda mais determinístico para Antigravity 2.0
                max_output_tokens=2048, # Aumentado para evitar cortes
            ),
        )
        return response.text
    except Exception as e:
        return f"[Erro Antigravity] {type(e).__name__}: {e}"

# ── Executor de comandos ──────────────────────────────────────────────────────
def run_tool(cmd: list, timeout: int = 300) -> tuple:
    """Executa comando externo e retorna (stdout, stderr, returncode)."""
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return proc.stdout, proc.stderr, proc.returncode
    except subprocess.TimeoutExpired:
        return "", f"[TIMEOUT] Comando excedeu {timeout}s: {' '.join(cmd)}", -1
    except FileNotFoundError:
        return "", f"[ERRO] Ferramenta não encontrada: '{cmd[0]}'. Instale com apt.", -1
    except Exception as e:
        return "", f"[ERRO] {e}", -1

# ── Ferramentas ───────────────────────────────────────────────────────────────
def tool_nmap(target: str, interactive: bool = True) -> tuple:
    options = [
        ("Rápido — top 100 portas abertas",        ["-F", "--open"]),
        ("Completo — todas as 65535 portas",        ["-p-", "--open"]),
        ("Serviços e versões (recomendado)",        ["-sV", "-sC", "--open"]),
        ("UDP — top 20 portas",                     ["-sU", "--top-ports", "20"]),
    ]
    
    if interactive:
        print(f"\n{C.BOLD}Tipo de scan nmap:{C.RESET}")
        for i, (desc, _) in enumerate(options, 1):
            print(f"  {i}. {desc}")
        choice = input("Escolha [1-4, padrão=3]: ").strip()
        idx = (int(choice) - 1) if choice.isdigit() and 1 <= int(choice) <= 4 else 2
    else:
        idx = 2 # Default para não-interativo

    flags = options[idx][1]
    print(f"{C.CYAN}[*] nmap {' '.join(flags)} {target} ...{C.RESET}")
    cmd = ["nmap"] + flags + ["-oN", "-", target]
    stdout, stderr, rc = run_tool(cmd, timeout=600)
    return "nmap", stdout or stderr

def tool_nikto(target: str, interactive: bool = True) -> tuple:
    url = target if target.startswith("http") else f"http://{target}"
    print(f"{C.CYAN}[*] nikto -h {url} ...{C.RESET}")
    cmd = ["nikto", "-h", url, "-nointeractive", "-Tuning", "123457890"]
    stdout, stderr, rc = run_tool(cmd, timeout=300)
    return "nikto", stdout or stderr

def tool_gobuster(target: str, interactive: bool = True) -> tuple:
    url = target if target.startswith("http") else f"http://{target}"

    # Procura wordlist disponível
    candidates = [
        "/usr/share/wordlists/dirb/common.txt",
        "/usr/share/wordlists/dirbuster/directory-list-2.3-small.txt",
        "/usr/share/wordlists/dirbuster/directory-list-2.3-medium.txt",
    ]
    wordlist = next((w for w in candidates if Path(w).exists()), None)
    if not wordlist:
        return "gobuster", (
            "[ERRO] Nenhuma wordlist encontrada.\n"
            "Execute: sudo apt install wordlists && gunzip /usr/share/wordlists/rockyou.txt.gz"
        )

    if interactive:
        threads = input("Threads [padrão=20, mais rápido=50]: ").strip() or "20"
    else:
        threads = "20"

    print(f"{C.CYAN}[*] gobuster dir -u {url} -w {wordlist} -t {threads} ...{C.RESET}")
    cmd = ["gobuster", "dir", "-u", url, "-w", wordlist, "-t", threads, "-q", "--no-error"]
    stdout, stderr, rc = run_tool(cmd, timeout=300)
    return "gobuster", stdout or stderr

def tool_bettercap(target: str, interactive: bool = True) -> tuple:
    if os.geteuid() != 0:
        return "bettercap", (
            "[ERRO] bettercap requer root.\n"
            "Execute: sudo spiderpi   (ou sudo python3 scanner.py)"
        )

    if interactive:
        iface = input("Interface wireless [ex: wlan1, padrão=wlan1]: ").strip() or "wlan1"
        duration = input("Duração do recon em segundos [padrão=30]: ").strip() or "30"
    else:
        iface = "wlan1"
        duration = "30"

    print(f"{C.CYAN}[*] bettercap wifi.recon em {iface} por {duration}s ...{C.RESET}")
    script = f"set wifi.recon.channel 0; wifi.recon on; sleep {duration}; wifi.show; exit"
    cmd = ["bettercap", "-iface", iface, "-eval", script]
    stdout, stderr, rc = run_tool(cmd, timeout=int(duration) + 30)
    return "bettercap", stdout or stderr

# ── Logging ───────────────────────────────────────────────────────────────────
def save_log(target: str, tool: str, raw: str, analysis: str) -> Path:
    ts    = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    safe  = target.replace("/", "_").replace(":", "-").replace(" ", "_")
    fname = LOG_DIR / f"{ts}_{tool}_{safe}.json"
    data  = {
        "timestamp":            ts,
        "target":               target,
        "tool":                 tool,
        "antigravity_model":    ANTIGRAVITY_MODEL,
        "raw_output":           raw,
        "antigravity_analysis": analysis,
    }
    with open(fname, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return fname

# ── E-Paper ───────────────────────────────────────────────────────────────────
def display_on_epaper(tool: str, target: str, analysis: str):
    if not EPAPER_ENABLED:
        return
    try:
        epd_mod.show_scan_result(tool, target, analysis)
    except Exception as e:
        print(f"{C.YELLOW}[!] E-paper erro: {e}{C.RESET}")

# ── UI ────────────────────────────────────────────────────────────────────────
TOOLS = {
    "1": ("nmap",      tool_nmap),
    "2": ("nikto",     tool_nikto),
    "3": ("gobuster",  tool_gobuster),
    "4": ("bettercap", tool_bettercap),
}

# Mapeamento para modo não-interativo
TOOL_MAP = {
    "nmap":      tool_nmap,
    "nikto":     tool_nikto,
    "gobuster":  tool_gobuster,
    "bettercap": tool_bettercap,
}

def print_banner():
    # Usando raw string (r""") para evitar SyntaxWarning com as barras da aranha
    print(rf"""{C.GREEN}{C.BOLD}
      / _ \
    \_\(_)/_/
     _//o\\_    ███████╗██████╗ ██╗██████╗ ███████╗██████╗ ██████╗ ██╗
      /   \    ██╔════╝██╔══██╗██║██╔══██╗██╔════╝██╔══██╗██╔══██╗██║
               ███████╗██████╔╝██║██║  ██║█████╗  ██████╔╝██████╔╝██║
               ╚════██║██╔═══╝ ██║██║  ██║██╔══╝  ██╔══██╗██╔═══╝ ██║
               ███████║██║     ██║██████╔╝███████╗██║  ██║██║     ██║
               ╚══════╝╚═╝     ╚═╝╚═════╝ ╚══════╝╚═╝  ╚═╝╚═╝     ╚═╝{C.RESET}
{C.CYAN}           SpiderPi Recon Tool  ·  Powered by Antigravity 2.0{C.RESET}
{C.DIM}            Modelo: {ANTIGRAVITY_MODEL}  ·  Logs: {LOG_DIR.resolve()}{C.RESET}
""")

def print_menu():
    print(f"{C.BOLD}{'─'*52}{C.RESET}")
    print(f"{C.BOLD} FERRAMENTAS (ANTIGRAVITY READY){C.RESET}")
    print(f"{'─'*52}")
    descs = {
        "1": "nmap      — port scan e detecção de serviços",
        "2": "nikto     — vulnerabilidades em servidores web",
        "3": "gobuster  — enumeração de diretórios/arquivos",
        "4": "bettercap — recon wireless (requer root)",
    }
    for k, desc in descs.items():
        print(f"  {C.CYAN}{k}{C.RESET}. {desc}")
    print(f"  {C.CYAN}0{C.RESET}. Sair")
    print(f"{C.BOLD}{'─'*52}{C.RESET}")

def print_raw(output: str):
    print(f"\n{C.BOLD}── OUTPUT BRUTO {'─'*34}{C.RESET}")
    print(output[:3000])
    if len(output) > 3000:
        print(f"{C.DIM}[... {len(output)-3000} caracteres adicionais salvos no log ...]{C.RESET}")
    print(f"{C.BOLD}{'─'*52}{C.RESET}")

def print_analysis(analysis: str):
    print(f"\n{C.BOLD}{C.GREEN}── ANÁLISE ANTIGRAVITY ({ANTIGRAVITY_MODEL}) {'─'*14}{C.RESET}")
    # Destaca a linha de risco
    for line in analysis.splitlines():
        if "RISCO GERAL" in line.upper():
            risco = line.upper()
            if "CRÍTICO" in risco:
                print(f"{C.RED}{C.BOLD}{line}{C.RESET}")
            elif "ALTO" in risco:
                print(f"{C.YELLOW}{C.BOLD}{line}{C.RESET}")
            elif "MÉDIO" in risco or "MEDIO" in risco:
                print(f"{C.YELLOW}{line}{C.RESET}")
            else:
                print(f"{C.GREEN}{line}{C.RESET}")
        else:
            print(line)
    print(f"{C.BOLD}{'─'*52}{C.RESET}")

# ── Execução Individual (para flags) ──────────────────────────────────────────
def run_single_scan(client, tool_name, target):
    if tool_name not in TOOL_MAP:
        print(f"{C.RED}[ERRO] Ferramenta '{tool_name}' inválida.{C.RESET}")
        return
    
    tool_fn = TOOL_MAP[tool_name]
    
    try:
        _, raw_output = tool_fn(target, interactive=False)
    except Exception as e:
        print(f"{C.RED}[ERRO] Falha no scan: {e}{C.RESET}")
        return

    if not raw_output.strip():
        print(f"{C.YELLOW}[!] Nenhum output gerado.{C.RESET}")
        return

    print_raw(raw_output)
    
    print(f"\n{C.YELLOW}[*] Enviando para Antigravity AI...{C.RESET}")
    analysis = analyze_with_antigravity(client, tool_name, target, raw_output)
    print_analysis(analysis)
    
    log_path = save_log(target, tool_name, raw_output, analysis)
    print(f"{C.GREEN}[+] Log salvo: {log_path}{C.RESET}")
    
    display_on_epaper(tool_name, target, analysis)

# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="SpiderPi Recon Tool")
    parser.add_argument("--tool", help="Ferramenta para execução direta (nmap, nikto, gobuster, bettercap)")
    parser.add_argument("--target", help="Alvo para o scan")
    args = parser.parse_args()

    if not args.tool:
        print_banner()

    # Valida API key
    if ANTIGRAVITY_API_KEY == "SUA_CHAVE_AQUI":
        print(f"{C.RED}[ERRO] API Key não configurada.{C.RESET}")
        print(f"       1. Obtenha sua chave em: https://aistudio.google.com/app/apikey")
        print(f"       2. Execute: export GEMINI_API_KEY='sua_chave'")
        print(f"       3. Para persistir: echo 'export GEMINI_API_KEY=\"sua_chave\"' >> ~/.bashrc")
        sys.exit(1)

    # Inicializa cliente
    if not args.tool:
        print(f"{C.YELLOW}[*] Conectando ao Antigravity ({ANTIGRAVITY_MODEL})...{C.RESET}")
    
    try:
        client = init_antigravity()
        # Teste rápido de conectividade (opcional em modo flag para ser mais rápido)
        if not args.tool:
            client.models.generate_content(
                model=ANTIGRAVITY_MODEL,
                contents="ok",
                config=types.GenerateContentConfig(max_output_tokens=5),
            )
            print(f"{C.GREEN}[+] Antigravity conectado e pronto.{C.RESET}")
    except Exception as e:
        print(f"{C.RED}[ERRO] Falha ao conectar ao Antigravity: {e}{C.RESET}")
        sys.exit(1)

    # Modo Não-Interativo (Flags)
    if args.tool:
        if not args.target:
            print(f"{C.RED}[ERRO] Alvo (--target) obrigatório quando --tool é usado.{C.RESET}")
            sys.exit(1)
        run_single_scan(client, args.tool, args.target)
        return

    # Modo Interativo (Menu)
    if EPAPER_ENABLED:
        print(f"{C.GREEN}[+] Display e-paper detectado.{C.RESET}")
    else:
        print(f"{C.DIM}[~] Display e-paper não detectado (modo terminal).{C.RESET}")

    while True:
        print()
        print_menu()

        choice = input(f"\n{C.BOLD}Escolha [{'/'.join(TOOLS.keys())}/0]: {C.RESET}").strip()

        if choice == "0":
            print(f"\n{C.CYAN}[*] Saindo. Logs salvos em: {LOG_DIR.resolve()}{C.RESET}\n")
            break

        if choice not in TOOLS:
            print(f"{C.RED}[!] Opção inválida.{C.RESET}")
            continue

        target = input("Alvo (IP, hostname ou URL): ").strip()
        if not target:
            continue

        tool_name, tool_fn = TOOLS[choice]

        try:
            _, raw_output = tool_fn(target, interactive=True)
            if not raw_output.strip():
                print(f"{C.YELLOW}[!] Sem output.{C.RESET}")
                continue
            
            print_raw(raw_output)
            print(f"\n{C.YELLOW}[*] Enviando para Antigravity AI...{C.RESET}")
            analysis = analyze_with_antigravity(client, tool_name, target, raw_output)
            print_analysis(analysis)
            
            log_path = save_log(target, tool_name, raw_output, analysis)
            print(f"{C.GREEN}[+] Log salvo: {log_path}{C.RESET}")
            display_on_epaper(tool_name, target, analysis)
            
            input(f"\n{C.DIM}[Enter para voltar ao menu...]{C.RESET}")
        except KeyboardInterrupt:
            print(f"\n{C.YELLOW}[!] Operação interrompida.{C.RESET}")
            continue

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\n{C.CYAN}[*] Interrompido.{C.RESET}\n")
        sys.exit(0)
