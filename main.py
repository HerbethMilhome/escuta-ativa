"""
Interview Assistant GUI - Ouve a saida de audio do sistema e gera respostas para entrevistas.
Interface grafica invisivel ao compartilhar tela (screen share, OBS, screenshots).

Uso:
    python main.py                          # Ollama (gratuito, padrao)
    python main.py --provider claude        # API da Anthropic
    python main.py --provider ollama --ollama-model mistral
    python main.py --context "Sou dev Python com 5 anos de experiencia"

Para a versao CLI original: python main_cli.py
"""

import argparse
import importlib
import logging
import os
import sys
import threading

# Python 3.8+ no Windows ignora PATH para DLLs de extensoes — registra antes de qualquer import CUDA
for _pkg in ("nvidia.cudnn", "nvidia.cublas", "nvidia.cuda_runtime"):
    try:
        _mod = importlib.import_module(_pkg)
        if _mod.__file__:
            _bin = os.path.join(os.path.dirname(_mod.__file__), "bin")
            if os.path.isdir(_bin):
                os.add_dll_directory(_bin)
    except Exception:
        pass

from dotenv import load_dotenv

load_dotenv()

# Log para arquivo quando rodando sem terminal (pythonw / .pyw)
LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assistant.log")
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("assistant")


def parse_args():
    parser = argparse.ArgumentParser(description="Interview Assistant GUI")
    parser.add_argument("--provider", type=str, default="ollama", choices=["ollama", "claude"],
                        help="Provedor de IA: 'ollama' (gratuito/local) ou 'claude' (API Anthropic)")
    parser.add_argument("--ollama-model", type=str, default="llama3.2",
                        help="Modelo do Ollama (default: llama3.2)")
    parser.add_argument("--vision-model", type=str, default="qwen2.5vl:7b",
                        help="Modelo Ollama de visao para o botao Print (default: qwen2.5vl:7b)")
    parser.add_argument("--context", type=str, default=None,
                        help="Contexto sobre voce (ex: 'Dev Python, 5 anos, Django e AWS')")
    parser.add_argument("--language", type=str, default="pt",
                        help="Idioma do audio (pt, en, es, etc)")
    parser.add_argument("--model", type=str, default="tiny",
                        help="Modelo Whisper (tiny, base, small, medium, large-v3)")
    parser.add_argument("--silence", type=float, default=0.6,
                        help="Segundos de silencio para considerar fim da fala (default: 0.6)")
    parser.add_argument("--threshold", type=float, default=0.5,
                        help="Limite de probabilidade Silero VAD para detectar fala (0..1, default: 0.5)")
    return parser.parse_args()


def load_context(args_context):
    """Carrega contexto: argumento CLI > arquivo context.txt > string vazia."""
    if args_context is not None:
        return args_context
    context_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "context.txt")
    if os.path.exists(context_file):
        with open(context_file, "r", encoding="utf-8") as f:
            text = f.read().strip()
        if text:
            log.info(f"Contexto carregado de context.txt ({len(text)} chars)")
            return text
    return ""


def main():
    args = parse_args()
    args.context = load_context(args.context)

    # Validar API key se usar Claude
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if args.provider == "claude" and not api_key:
        log.error("ANTHROPIC_API_KEY nao encontrada.")
        log.error("Crie um arquivo .env com: ANTHROPIC_API_KEY=sk-ant-sua-chave")
        sys.exit(1)

    import webview
    from gui_frontend import get_html
    from gui_api import GuiApi
    from screen_hide import hide_from_capture

    # Estado compartilhado entre init_thread e JsApi
    state = {"capture": None, "gui": None, "assistant": None, "transcriber": None, "language": "pt"}

    def _capture_screenshot_bytes():
        import mss
        import io
        from PIL import Image
        with mss.mss() as sct:
            monitor = sct.monitors[0]  # tela inteira (todos os monitores)
            shot = sct.grab(monitor)
            img = Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")
            buf = io.BytesIO()
            img.save(buf, format="PNG", optimize=True)
            return buf.getvalue()

    def _process_screenshot():
        gui = state["gui"]
        ai = state["assistant"]
        if gui is None or ai is None:
            return
        try:
            gui.set_status("transcribing", "Capturando tela...")
            img_bytes = _capture_screenshot_bytes()
            gui.add_question("[Print da tela]")
            gui.set_status("answering", "Analisando imagem...")
            gui.start_answer()

            def on_token(token):
                gui.append_token(token)

            ai.answer_image(img_bytes, on_token=on_token)
            gui.finish_answer()
            cap = state["capture"]
            if cap and not cap.is_paused():
                gui.set_status("listening", "Ouvindo...")
            else:
                gui.set_status("initializing", "Pausado")
        except Exception as e:
            gui.append_token(f"\n\n**Erro:** {e}")
            log.error(f"Erro screenshot: {e}")
            gui.finish_answer()

    class JsApi:
        def toggle_listening(self):
            cap = state["capture"]
            gui = state["gui"]
            if cap is None:
                return False
            paused = cap.toggle()
            if gui is not None:
                if paused:
                    gui.set_status("initializing", "Pausado")
                else:
                    gui.set_status("listening", "Ouvindo...")
            return paused

        def take_screenshot(self):
            threading.Thread(target=_process_screenshot, daemon=True).start()
            return True

        def set_language(self, lang):
            if lang in ("pt", "en"):
                state["language"] = lang
                tr = state["transcriber"]
                if tr is not None:
                    tr.language = lang
                log.info(f"Idioma forcado: {lang}")
            return state["language"]

    window = webview.create_window(
        "Interview Assistant",
        html=get_html(),
        width=700,
        height=800,
        resizable=True,
        text_select=True,
        on_top=True,
        js_api=JsApi(),
    )

    def on_shown():
        """Chamado quando a janela e exibida - aplica screen capture exclusion."""
        try:
            # Qt backend: window.native e um QMainWindow
            native = window.native
            if hasattr(native, 'Handle'):
                # winforms backend
                hwnd = native.Handle
            elif hasattr(native, 'winId'):
                # Qt backend
                hwnd = int(native.winId())
            else:
                log.warning("Backend nao suportado para screen hide.")
                return
            hide_from_capture(hwnd)
        except Exception as e:
            log.warning(f"Nao foi possivel ocultar da captura: {e}")

    def init_thread():
        """Thread de inicializacao - carrega componentes e inicia captura de audio."""
        gui = GuiApi(window)
        state["gui"] = gui

        try:
            gui.set_status("initializing", "Carregando audio...")
            from audio_capture import AudioCapture
            capture = AudioCapture(
                silence_threshold=args.threshold,
                silence_duration=args.silence,
            )
            state["capture"] = capture

            gui.set_status("initializing", "Carregando Whisper...")
            from transcriber import Transcriber
            transcriber = Transcriber(model_size=args.model, language=state["language"])
            state["transcriber"] = transcriber

            provider_label = "Ollama (local)" if args.provider == "ollama" else "Claude API"
            gui.set_status("initializing", f"Carregando {provider_label}...")
            from assistant import create_assistant
            assistant_ai = create_assistant(
                provider=args.provider,
                context=args.context,
                api_key=api_key,
                ollama_model=args.ollama_model,
                vision_model=args.vision_model,
            )
            state["assistant"] = assistant_ai

        except Exception as e:
            gui.set_status("error", f"Erro: {e}")
            log.error(f"Erro ao inicializar: {e}")
            return

        gui.set_status("listening", "Ouvindo...")

        def on_audio_ready(audio_data, sample_rate):
            gui.set_status("transcribing", "Transcrevendo...")

            text, _ = transcriber.transcribe(audio_data, sample_rate)
            lang = state["language"]  # idioma escolhido pelo usuario

            if not text or len(text.strip()) < 5:
                gui.set_status("listening", "Ouvindo...")
                return

            log.info(f"Idioma: {lang} | Texto: {text[:80]}")
            display_text = f"[{lang.upper()}] {text}" if lang != "pt" else text
            gui.add_question(display_text)
            gui.set_status("answering", "Respondendo...")
            gui.start_answer()

            def on_token(token):
                gui.append_token(token)

            try:
                assistant_ai.answer(text, on_token=on_token, language=lang)
            except Exception as e:
                gui.append_token(f"\n\n**Erro:** {e}")
                log.error(f"Erro ao gerar resposta: {e}")

            gui.finish_answer()
            gui.set_status("listening", "Ouvindo...")

        try:
            capture.capture_until_silence(on_audio_ready)
        except Exception as e:
            gui.set_status("error", f"Erro captura: {e}")
            log.error(f"Erro na captura de audio: {e}")

    def on_loaded():
        """Chamado quando o DOM esta pronto."""
        t = threading.Thread(target=init_thread, daemon=True)
        t.start()

    window.events.shown += on_shown
    window.events.loaded += on_loaded

    webview.start(gui="qt")


if __name__ == "__main__":
    main()
