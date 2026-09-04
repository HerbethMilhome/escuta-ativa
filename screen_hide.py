"""Oculta a janela de capturas de tela e screen share (Windows 10 2004+)."""

import ctypes
import ctypes.wintypes
import logging
import os
import threading

log = logging.getLogger("assistant")

user32 = ctypes.WinDLL("user32", use_last_error=True)

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

_HWND = ctypes.wintypes.HWND
_DWORD = ctypes.wintypes.DWORD

user32.SetWindowDisplayAffinity.argtypes = [_HWND, _DWORD]
user32.SetWindowDisplayAffinity.restype = ctypes.wintypes.BOOL
user32.GetWindowDisplayAffinity.argtypes = [_HWND, ctypes.POINTER(_DWORD)]
user32.GetWindowDisplayAffinity.restype = ctypes.wintypes.BOOL
user32.SetLayeredWindowAttributes.argtypes = [_HWND, _DWORD, ctypes.c_ubyte, _DWORD]
user32.SetLayeredWindowAttributes.restype = ctypes.wintypes.BOOL
user32.ShowWindow.argtypes = [_HWND, ctypes.c_int]
user32.IsWindow.argtypes = [_HWND]
user32.IsWindowVisible.argtypes = [_HWND]
user32.GetWindowThreadProcessId.argtypes = [_HWND, ctypes.POINTER(_DWORD)]

_WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.wintypes.BOOL, _HWND, ctypes.wintypes.LPARAM)
user32.EnumWindows.argtypes = [_WNDENUMPROC, ctypes.wintypes.LPARAM]

_IS_64BIT = ctypes.sizeof(ctypes.c_void_p) == 8
_get_window_long = user32.GetWindowLongPtrW if _IS_64BIT else user32.GetWindowLongW
_set_window_long = user32.SetWindowLongPtrW if _IS_64BIT else user32.SetWindowLongW
_LONG_PTR = ctypes.c_ssize_t if _IS_64BIT else ctypes.c_long
_get_window_long.argtypes = [_HWND, ctypes.c_int]
_get_window_long.restype = _LONG_PTR
_set_window_long.argtypes = [_HWND, ctypes.c_int, _LONG_PTR]
_set_window_long.restype = _LONG_PTR

# Janelas ja protegidas — usadas pelo guard para reaplicar quando o Windows
# perde a afinidade (recriacao de janela, mudanca de estilo, etc.).
_protected = set()
_guard_started = False


def to_hwnd(handle):
    """Converte o handle nativo para int.

    O backend WinForms (pythonnet) entrega um System.IntPtr, que o ctypes
    recusa ("cannot be converted to pointer"); o backend Qt entrega um int
    (ou sip.voidptr). Normaliza os tres casos.
    """
    if handle is None:
        return 0
    if isinstance(handle, int):
        return handle
    for attr in ("ToInt64", "ToInt32"):  # System.IntPtr
        conv = getattr(handle, attr, None)
        if callable(conv):
            return int(conv())
    return int(handle)  # sip.voidptr e afins


def set_opacity(hwnd, alpha):
    """Define a transparencia da janela via Win32 (thread-safe).

    alpha: 0.0 (invisivel) a 1.0 (opaco). Usa WS_EX_LAYERED + SetLayeredWindowAttributes.
    Funciona de qualquer thread (ao contrario do setWindowOpacity do Qt).
    """
    hwnd = to_hwnd(hwnd)
    if not hwnd:
        return False
    try:
        alpha = max(0.0, min(1.0, alpha))
        style = _get_window_long(hwnd, GWL_EXSTYLE)
        _set_window_long(hwnd, GWL_EXSTYLE, style | WS_EX_LAYERED)
        user32.SetLayeredWindowAttributes(hwnd, 0, int(alpha * 255), LWA_ALPHA)
        # Mexer no ex-style pode derrubar a afinidade de captura: reaplica.
        if hwnd in _protected:
            hide_from_capture(hwnd)
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
    hwnd = to_hwnd(hwnd)
    if not hwnd:
        return False
    try:
        style = _get_window_long(hwnd, GWL_EXSTYLE)
        # Remove WS_EX_APPWINDOW e adiciona WS_EX_TOOLWINDOW
        new_style = (style & ~WS_EX_APPWINDOW) | WS_EX_TOOLWINDOW

        # Precisa esconder, alterar style, e mostrar de novo
        user32.ShowWindow(hwnd, SW_HIDE)
        _set_window_long(hwnd, GWL_EXSTYLE, new_style)
        user32.ShowWindow(hwnd, SW_SHOW)

        # O ciclo hide/show recria a apresentacao da janela: reaplica a afinidade.
        if hwnd in _protected:
            hide_from_capture(hwnd)

        log.info("Janela removida da barra de tarefas (WS_EX_TOOLWINDOW).")
        return True
    except Exception as e:
        log.warning(f"Falha ao remover da taskbar: {e}")
        return False


def get_display_affinity(hwnd):
    """Retorna a afinidade atual da janela, ou None se nao for possivel ler."""
    hwnd = to_hwnd(hwnd)
    if not hwnd:
        return None
    value = _DWORD(0)
    if user32.GetWindowDisplayAffinity(hwnd, ctypes.byref(value)):
        return value.value
    return None


def hide_from_capture(hwnd, quiet=False):
    """Aplica SetWindowDisplayAffinity para esconder a janela de screen capture.

    Tenta WDA_EXCLUDEFROMCAPTURE primeiro (invisivel).
    Se falhar, tenta WDA_MONITOR (mostra tela preta).
    Retorna True se alguma opcao funcionou.
    """
    hwnd = to_hwnd(hwnd)
    if not hwnd:
        log.warning("hide_from_capture: handle de janela invalido (0).")
        return False

    for affinity, label in ((WDA_EXCLUDEFROMCAPTURE, "WDA_EXCLUDEFROMCAPTURE"),
                            (WDA_MONITOR, "WDA_MONITOR (tela preta no capture)")):
        if user32.SetWindowDisplayAffinity(hwnd, affinity):
            # Confirma que o valor realmente ficou aplicado.
            if get_display_affinity(hwnd) == affinity:
                _protected.add(hwnd)
                if not quiet:
                    log.info(f"{label} aplicado com sucesso (hwnd={hwnd}).")
                return True
            if not quiet:
                log.warning(f"{label} aceito mas nao persistiu; tentando fallback.")
        elif not quiet:
            log.warning(f"{label} falhou. Erro Win32: {ctypes.get_last_error()}")

    if not quiet:
        log.warning(f"Falha ao aplicar DisplayAffinity (hwnd={hwnd}).")
    return False


def protect_process_windows(quiet=True):
    """Aplica a exclusao de captura em todas as janelas top-level deste processo.

    Cobre janelas que o backend cria depois do start (popups do WebView2,
    dialogs, janela recriada por mudanca de flags) — cada uma tem hwnd proprio
    e afinidade propria, entao precisa ser tratada individualmente.
    """
    pid = os.getpid()
    count = 0

    def _callback(hwnd, _lparam):
        nonlocal count
        wnd_pid = _DWORD(0)
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(wnd_pid))
        if wnd_pid.value == pid and user32.IsWindowVisible(hwnd):
            handle = to_hwnd(hwnd)
            if get_display_affinity(handle) != WDA_EXCLUDEFROMCAPTURE:
                if hide_from_capture(handle, quiet=quiet):
                    count += 1
        return True

    try:
        user32.EnumWindows(_WNDENUMPROC(_callback), 0)
    except Exception as e:
        log.warning(f"Falha ao varrer janelas do processo: {e}")
    return count


def start_capture_guard(interval=2.0):
    """Vigia em background e reaplica a exclusao de captura.

    O Windows perde a afinidade quando a janela e recriada ou tem o estilo
    alterado, e o backend cria janelas novas ao longo da sessao — sem isso o
    app volta a aparecer no compartilhamento de tela no meio da entrevista.
    """
    global _guard_started
    if _guard_started:
        return
    _guard_started = True

    def _loop():
        while True:
            try:
                # Limpa handles de janelas ja destruidas.
                for hwnd in list(_protected):
                    if not user32.IsWindow(hwnd):
                        _protected.discard(hwnd)
                applied = protect_process_windows(quiet=True)
                if applied:
                    log.info(f"Guard de captura reaplicado em {applied} janela(s).")
            except Exception as e:
                log.warning(f"Guard de captura falhou: {e}")
            threading.Event().wait(interval)

    threading.Thread(target=_loop, daemon=True, name="capture-guard").start()
    log.info(f"Guard de captura ativo (intervalo {interval:.1f}s).")
