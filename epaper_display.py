#!/usr/bin/env python3
"""
epaper_display.py — Módulo de display para Waveshare e-paper
Compatível com: 2.13", 2.7", 3.7" e 4.2" (altere DISPLAY_MODEL abaixo)

Instale as dependências:
  pip install Pillow RPi.GPIO spidev
  git clone https://github.com/waveshare/e-Paper.git
  pip install ./e-Paper/RaspberryPi_JetsonNano/python/
"""

import textwrap
import time
import sys
from datetime import datetime

# Adiciona o caminho de instalação padrão como fallback
sys.path.append("/opt/pi_recon")

# ── Modelo do seu display ─────────────────────────────────────────────────────
# Altere para o modelo exato do seu Waveshare:
# "epd2in13_V4", "epd2in7", "epd3in7", "epd4in2"
DISPLAY_MODEL = "epd2in13_V4"

from PIL import Image, ImageDraw, ImageFont

# ── Importa driver dinamicamente ──────────────────────────────────────────────
epd_driver = None
DRIVER_OK = False

try:
    import importlib
    # Tenta carregar o módulo waveshare_epd.<DISPLAY_MODEL>
    waveshare_module = importlib.import_module(f"waveshare_epd.{DISPLAY_MODEL}")
    epd_driver = waveshare_module
    DRIVER_OK = True
except Exception as e:
    # Captura tanto ImportError quanto erros de hardware (GPIO busy) no import
    DRIVER_OK = False

# Fallback: Caso o usuário tenha instalado via pip e o nome seja diferente ou direto
if not DRIVER_OK:
    try:
        from waveshare_epd import epd2in13_V4 as epd_driver
        DRIVER_OK = True
    except Exception:
        pass

# Dimensões padrão por modelo (largura x altura em pixels)
DISPLAY_SIZES = {
    "epd2in13_V4": (122, 250),
    "epd2in7":     (176, 264),
    "epd3in7":     (280, 480),
    "epd4in2":     (300, 400),
}

W, H = DISPLAY_SIZES.get(DISPLAY_MODEL, (122, 250))

# ── Fonte embutida (usa default do Pillow se não tiver TTF) ───────────────────
def get_font(size: int):
    try:
        return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", size)
    except:
        return ImageFont.load_default()

# ── Renderiza imagem ──────────────────────────────────────────────────────────
def build_image(tool: str, target: str, analysis: str) -> Image.Image:
    """Monta a imagem para exibir no e-paper."""
    # Imagem em modo 1-bit (preto e branco)
    img = Image.new("1", (H, W), 255)  # rotacionado: landscape
    draw = ImageDraw.Draw(img)

    font_title  = get_font(11)
    font_body   = get_font(9)
    font_small  = get_font(8)

    y = 2

    # Cabeçalho
    draw.rectangle([0, 0, H, 14], fill=0)
    draw.text((4, 2), f"SPIDER PI  ·  {datetime.now().strftime('%H:%M')}", font=font_title, fill=255)
    y = 17

    # Ferramenta e alvo
    draw.text((2, y), f"Ferramenta: {tool.upper()}", font=font_body, fill=0)
    y += 11
    draw.text((2, y), f"Alvo: {target[:30]}", font=font_body, fill=0)
    y += 11

    # Linha divisória
    draw.line([(0, y), (H, y)], fill=0, width=1)
    y += 3

    # Extrai risco da análise
    risco = "?"
    for word in ["Crítico", "Alto", "Médio", "Baixo"]:
        if word.lower() in analysis.lower():
            risco = word
            break

    # Badge de risco
    risco_map = {"Crítico": "■ CRÍTICO", "Alto": "▲ ALTO", "Médio": "● MÉDIO", "Baixo": "○ BAIXO"}
    badge = risco_map.get(risco, f"? {risco}")
    draw.rectangle([2, y, 80, y + 12], fill=0)
    draw.text((4, y + 1), f"RISCO: {badge}", font=font_small, fill=255)
    y += 15

    # Análise (primeiras linhas)
    max_chars = 38
    lines_budget = (W - y - 4) // 10
    wrapped = []
    for paragraph in analysis.split("\n"):
        paragraph = paragraph.strip()
        if not paragraph:
            continue
        for line in textwrap.wrap(paragraph, max_chars):
            wrapped.append(line)
        if len(wrapped) >= lines_budget:
            break

    for line in wrapped[:lines_budget]:
        draw.text((2, y), line, font=font_small, fill=0)
        y += 10

    # Rodapé
    draw.line([(0, W - 11), (H, W - 11)], fill=0, width=1)
    draw.text((2, W - 10), "Log salvo  ·  SpiderPi", font=font_small, fill=0)

    return img

# ── Exibe no display ──────────────────────────────────────────────────────────
def show_scan_result(tool: str, target: str, analysis: str):
    """Atualiza o display e-paper com o resultado do scan."""
    if not DRIVER_OK:
        print(f"[e-paper] Driver '{DISPLAY_MODEL}' não disponível.")
        print("          Certifique-se de que a pasta 'waveshare_epd' existe ou execute 'sudo ./setup.sh'.")
        return

    try:
        epd = epd_driver.EPD()
        epd.init()
        epd.Clear(0xFF)

        img = build_image(tool, target, analysis)

        # Rotaciona para landscape
        img = img.rotate(90, expand=True)

        epd.display(epd.getbuffer(img))
        print("[e-paper] Display atualizado com sucesso.")

    except Exception as e:
        print(f"[e-paper] Erro ao atualizar display: {e}")
    finally:
        if DRIVER_OK:
            try:
                if 'epd' in locals():
                    epd.sleep()
                # Libera os pinos GPIO para evitar "GPIO busy"
                if hasattr(epd_driver, 'epdconfig'):
                    epd_driver.epdconfig.module_exit()
            except:
                pass

# ── Tela de boot ──────────────────────────────────────────────────────────────
def show_boot_screen():
    """Exibe tela inicial no boot."""
    if not DRIVER_OK:
        return
    try:
        epd = epd_driver.EPD()
        epd.init()
        epd.Clear(0xFF)

        img = Image.new("1", (H, W), 255)
        draw = ImageDraw.Draw(img)
        font_big   = get_font(16)
        font_small = get_font(9)

        draw.rectangle([0, 0, H, W], fill=0)
        draw.text((10, 20), "SPIDER PI", font=font_big, fill=255)
        draw.text((10, 42), "Powered by Antigravity 2.0", font=font_small, fill=255)
        draw.text((10, 54), datetime.now().strftime("%d/%m/%Y %H:%M"), font=font_small, fill=255)
        draw.text((10, 68), "SSH pronto. Aguardando...", font=font_small, fill=255)

        img = img.rotate(90, expand=True)
        epd.display(epd.getbuffer(img))
    except Exception as e:
        print(f"[e-paper] Boot screen erro: {e}")
    finally:
        if DRIVER_OK:
            try:
                if 'epd' in locals():
                    epd.sleep()
                if hasattr(epd_driver, 'epdconfig'):
                    epd_driver.epdconfig.module_exit()
            except:
                pass

if __name__ == "__main__":
    # Teste rápido
    show_scan_result(
        tool="nmap",
        target="192.168.1.1",
        analysis="RISCO GERAL: Alto\n1. Porta 22 (SSH) aberta\n2. Porta 80 (HTTP) aberta\nVULNERABILIDADES: SSH versão desatualizada\nPRÓXIMOS PASSOS: nikto -h http://192.168.1.1"
    )
