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
sys.path.append("/opt/pi_recon")

def check_dependencies():
    print("── Verificando dependências do sistema ──")
    
    # 1. Verifica SPI habilitado
    if os.path.exists("/dev/spidev0.0"):
        print("[OK] Interface SPI detectada (/dev/spidev0.0).")
    else:
        print("[ERRO] Interface SPI NÃO detectada!")
        print("      Execute 'sudo raspi-config', vá em 'Interface Options' e habilite 'SPI'.")
    
    # 2. Verifica pacotes Python
    packages = ["PIL", "RPi.GPIO", "spidev"]
    for pkg in packages:
        try:
            if pkg == "PIL":
                from PIL import Image
            else:
                __import__(pkg)
            print(f"[OK] Biblioteca Python '{pkg}' encontrada.")
        except ImportError:
            print(f"[FALHA] Biblioteca Python '{pkg}' NÃO encontrada.")
            print(f"       Execute: pip install {pkg.lower() if pkg != 'PIL' else 'Pillow'}")

    # 3. Verifica Driver Waveshare
    print("\n── Verificando drivers Waveshare ──")
    try:
        import epaper_display
        print(f"[INFO] Modelo configurado em epaper_display.py: {epaper_display.DISPLAY_MODEL}")
        
        from waveshare_epd import epdconfig
        print("[OK] Configuração base (epdconfig) importada.")
        
        # Tenta importar o driver específico
        try:
            module_name = f"waveshare_epd.{epaper_display.DISPLAY_MODEL}"
            __import__(module_name)
            print(f"[OK] Driver específico '{module_name}' importado com sucesso.")
        except ImportError:
            print(f"[ERRO] Driver '{epaper_display.DISPLAY_MODEL}' não encontrado em 'waveshare_epd'.")
            print("       Verifique se você baixou os arquivos .py do modelo correto.")
            
    except ImportError as e:
        print(f"[ERRO] Falha ao importar módulos: {e}")
        print("       Certifique-se de que a pasta 'waveshare_epd' existe ou o driver foi instalado via pip.")

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
