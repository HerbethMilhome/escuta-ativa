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

# Window styles
GWL_EXSTYLE = -20
WS_EX_APPWINDOW = 0x00040000
WS_EX_TOOLWINDOW = 0x00000080
WS_EX_LAYERED = 0x00080000
LWA_ALPHA = 0x00000002
SW_HIDE = 0
SW_SHOW = 5


def set_opacity(hwnd, alpha):
    """Define a transparencia da janela via Win32 (thread-safe).

    alpha: 0.0 (invisivel) a 1.0 (opaco). Usa WS_EX_LAYERED + SetLayeredWindowAttributes.
    Funciona de qualquer thread (ao contrario do setWindowOpacity do Qt).
    """
    if not hwnd:
        return False
    try:
        alpha = max(0.0, min(1.0, alpha))
        get_window_long = user32.GetWindowLongPtrW if ctypes.sizeof(ctypes.c_void_p) == 8 else user32.GetWindowLongW
        set_window_long = user32.SetWindowLongPtrW if ctypes.sizeof(ctypes.c_void_p) == 8 else user32.SetWindowLongW

        style = get_window_long(ctypes.wintypes.HWND(hwnd), GWL_EXSTYLE)
        set_window_long(ctypes.wintypes.HWND(hwnd), GWL_EXSTYLE, style | WS_EX_LAYERED)
        user32.SetLayeredWindowAttributes(
            ctypes.wintypes.HWND(hwnd),
            0,
            int(alpha * 255),
            ctypes.wintypes.DWORD(LWA_ALPHA),
        )
        return True
    except Exception as e:
        log.warning(f"Falha ao definir opacidade: {e}")
        return False


def hide_from_taskbar(hwnd):
    """Remove a janela da barra de tarefas usando WS_EX_TOOLWINDOW.

    A janela continua acessivel via Alt+Tab e mantem foco normal,
    mas nao aparece na taskbar (e por consequencia, nao aparece em
    screen share da tela inteira).
    """
    if not hwnd:
        return False
    try:
        # Get current style
        get_window_long = user32.GetWindowLongPtrW if ctypes.sizeof(ctypes.c_void_p) == 8 else user32.GetWindowLongW
        set_window_long = user32.SetWindowLongPtrW if ctypes.sizeof(ctypes.c_void_p) == 8 else user32.SetWindowLongW

        style = get_window_long(ctypes.wintypes.HWND(hwnd), GWL_EXSTYLE)
        # Remove WS_EX_APPWINDOW e adiciona WS_EX_TOOLWINDOW
        new_style = (style & ~WS_EX_APPWINDOW) | WS_EX_TOOLWINDOW

        # Precisa esconder, alterar style, e mostrar de novo
        user32.ShowWindow(ctypes.wintypes.HWND(hwnd), SW_HIDE)
        set_window_long(ctypes.wintypes.HWND(hwnd), GWL_EXSTYLE, new_style)
        user32.ShowWindow(ctypes.wintypes.HWND(hwnd), SW_SHOW)

        log.info("Janela removida da barra de tarefas (WS_EX_TOOLWINDOW).")
        return True
    except Exception as e:
        log.warning(f"Falha ao remover da taskbar: {e}")
        return False


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
