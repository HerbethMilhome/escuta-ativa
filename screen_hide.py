"""Oculta a janela de capturas de tela e screen share (Windows 10 2004+)."""

import ctypes
import ctypes.wintypes
import logging

log = logging.getLogger("assistant")

user32 = ctypes.windll.user32

# WDA_EXCLUDEFROMCAPTURE = 0x00000011 (Win10 2004+, build 19041)
# WDA_MONITOR = 0x00000001 (fallback - mostra tela preta)
WDA_NONE = 0x00000000
WDA_MONITOR = 0x00000001
WDA_EXCLUDEFROMCAPTURE = 0x00000011


def hide_from_capture(hwnd):
    """Aplica SetWindowDisplayAffinity para esconder a janela de screen capture.

    Tenta WDA_EXCLUDEFROMCAPTURE primeiro (invisivel).
    Se falhar, tenta WDA_MONITOR (mostra tela preta).
    Retorna True se alguma opcao funcionou.
    """
    if not hwnd:
        return False

    # Tentar WDA_EXCLUDEFROMCAPTURE (totalmente invisivel)
    result = user32.SetWindowDisplayAffinity(
        ctypes.wintypes.HWND(hwnd),
        ctypes.wintypes.DWORD(WDA_EXCLUDEFROMCAPTURE),
    )
    if result:
        log.info("WDA_EXCLUDEFROMCAPTURE aplicado com sucesso.")
        return True

    # Fallback: WDA_MONITOR (mostra tela preta em vez do conteudo)
    result = user32.SetWindowDisplayAffinity(
        ctypes.wintypes.HWND(hwnd),
        ctypes.wintypes.DWORD(WDA_MONITOR),
    )
    if result:
        log.info("Fallback WDA_MONITOR aplicado (tela preta no capture).")
        return True

    error = ctypes.get_last_error()
    log.warning(f"Falha ao aplicar DisplayAffinity. Erro Win32: {error}")
    return False
