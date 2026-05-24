#!/usr/bin/env python3
"""
test_epaper.py — Script de diagnóstico para o display Waveshare e-paper.
Verifica dependências, drivers e comunicação SPI.
"""

import sys
import os
import time
import subprocess

# Adiciona o caminho de instalação padrão ao path do Python como fallback
sys.path.append("/opt/spiderpi")

class C:
    RED    = "\033[91m"
    GREEN  = "\033[92m"
    YELLOW = "\033[93m"
    CYAN   = "\033[96m"
    RESET  = "\033[0m"
    BOLD   = "\033[1m"

def check_dependencies():
    print(f"{C.BOLD}── Verificando dependências do sistema ──{C.RESET}")
    
    # 1. Verifica SPI habilitado
    if os.path.exists("/dev/spidev0.0"):
        print(f"[{C.GREEN}OK{C.RESET}] Interface SPI detectada (/dev/spidev0.0).")
    else:
        print(f"[{C.RED}ERRO{C.RESET}] Interface SPI NÃO detectada!")
        print(f"      Deseja habilitar o SPI agora? (Requer ROOT e REBOOT) (s/n)")
        if input("> ").lower() == 's':
            config_files = ["/boot/config.txt", "/boot/firmware/config.txt"]
            enabled = False
            for cfg in config_files:
                if os.path.exists(cfg):
                    try:
                        with open(cfg, "a") as f:
                            f.write("\ndtparam=spi=on\n")
                        print(f"[{C.GREEN}OK{C.RESET}] SPI habilitado em {cfg}.")
                        enabled = True
                    except PermissionError:
                        print(f"[{C.RED}FALHA{C.RESET}] Sem permissão para editar {cfg}. Use 'sudo'.")
            if enabled:
                print(f"\n{C.YELLOW}[!!!] ATENÇÃO: Reinicie o Raspberry Pi para ativar o hardware!{C.RESET}")
                print(f"      Execute: {C.BOLD}sudo reboot{C.RESET}")
                sys.exit(0)
        else:
            print("      Habilite manualmente via 'sudo raspi-config' ou editando o config.txt.")
    
    # 2. Verifica pacotes Python
    packages = ["PIL", "lgpio", "spidev"]
    for pkg in packages:
        try:
            if pkg == "PIL":
                from PIL import Image
            else:
                __import__(pkg)
            print(f"[{C.GREEN}OK{C.RESET}] Biblioteca Python '{pkg}' encontrada.")
        except ImportError:
            print(f"[{C.RED}FALHA{C.RESET}] Biblioteca Python '{pkg}' NÃO encontrada.")
            print(f"       Execute: pip install {pkg.lower() if pkg != 'PIL' else 'Pillow'}")

    # 3. Verifica Driver Waveshare
    print("\n── Verificando drivers Waveshare ──")
    try:
        # Tenta importar o módulo local
        import epaper_display
        print(f"[INFO] Modelo configurado em epaper_display.py: {epaper_display.DISPLAY_MODEL}")
        
        # Tenta importar a base, capturando erro de hardware ocupado
        try:
            from waveshare_epd import epdconfig
            print("[OK] Configuração base (epdconfig) importada.")
        except Exception as e:
            print(f"[{C.RED}AVISO{C.RESET}] Falha ao acessar hardware via epdconfig: {e}")
            print("        Isso geralmente significa que os pinos GPIO já estão em uso.")
            print("        Tente: sudo systemctl stop spiderpi-boot.service")
        
        # Tenta importar o driver específico
        try:
            module_name = f"waveshare_epd.{epaper_display.DISPLAY_MODEL}"
            __import__(module_name)
            print(f"[OK] Driver específico '{module_name}' importado com sucesso.")
        except Exception as e:
            print(f"[{C.RED}FALHA{C.RESET}] Erro ao carregar driver específico: {e}")
            
    except ImportError as e:
        print(f"[{C.RED}ERRO{C.RESET}] Módulo epaper_display.py não encontrado no diretório atual.")
    except Exception as e:
        print(f"[{C.RED}ERRO{C.RESET}] Erro inesperado: {e}")

def run_test_draw():
    print("\n── Iniciando teste de renderização ──")
    try:
        import epaper_display
        from PIL import Image, ImageDraw
        
        print("[*] Criando imagem de teste...")
        # Simula um resultado de scan para teste
        epaper_display.show_scan_result(
            tool="TESTE",
            target="DISPLAY-OK",
            analysis="SISTEMA: Operacional\nDRIVER: Carregado\nSPI: Ativo\n\nEste é um teste de funcionamento do display Waveshare."
        )
        print("[OK] Comando de atualização enviado ao display.")
        print("     Verifique se a tela piscou e exibiu as informações.")
        
    except Exception as e:
        print(f"[FALHA] Erro durante o teste de hardware: {e}")

if __name__ == "__main__":
    print("========================================")
    print("   DIAGNÓSTICO WAVESHARE E-PAPER")
    print("========================================")
    
    if os.geteuid() != 0:
        print("\n[AVISO] Este script pode precisar de root para acessar o barramento SPI.")
        print("        Se falhar, tente: sudo python3 test_epaper.py\n")

    check_dependencies()
    
    print("\nDeseja tentar um teste de desenho no display agora? (s/n)")
    choice = input("> ").lower()
    if choice == 's':
        run_test_draw()
    else:
        print("Teste de desenho pulado.")
    
    print("\n========================================")
    print("   Fim do Diagnóstico")
    print("========================================")
