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
import datetime
import importlib
import logging
import os
import sys
import threading
import time

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

# Log da conversa: 1 arquivo por sessao em logs/conversa_YYYYMMDD_HHMMSS.txt
_LOGS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
os.makedirs(_LOGS_DIR, exist_ok=True)
CONVERSA_FILE = os.path.join(
    _LOGS_DIR, f"conversa_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
)


def _extract_section(text, *markers):
    """Extrai o conteudo de uma secao markdown tipo '**Resposta (PT):**'.
    Retorna o texto entre o marker e o proximo marker bold (ou fim). None se nao achar.
    """
    import re
    for marker in markers:
        pattern = re.compile(re.escape(marker), re.IGNORECASE)
        m = pattern.search(text)
        if not m:
            continue
        start = m.end()
        # proximo header bold "**Algo:**"
        nxt = re.search(r"\n\s*\*\*[^*]+:\*\*", text[start:])
        end = start + nxt.start() if nxt else len(text)
        return text[start:end].strip()
    return None


def log_conversa(role, text):
    """Grava uma linha no log da conversa (entrevistador / candidato)."""
    try:
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        with open(CONVERSA_FILE, "a", encoding="utf-8") as f:
            f.write(f"[{ts}] {role}: {text}\n\n")
    except Exception as e:
        log.error(f"Erro ao gravar log de conversa: {e}")


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
    parser.add_argument("--language", type=str, default="en",
                        help="Idioma do audio (pt, en, es, etc)")
    parser.add_argument("--model", type=str, default="tiny",
                        help="Modelo Whisper (tiny, base, small, medium, large-v3)")
    parser.add_argument("--silence", type=float, default=0.6,
                        help="Segundos de silencio para considerar fim da fala (default: 0.6)")
    parser.add_argument("--threshold", type=float, default=0.5,
                        help="Limite de probabilidade Silero VAD para detectar fala (0..1, default: 0.5)")
    parser.add_argument("--mode", type=str, default="interview", choices=["interview", "translate"],
                        help="Modo: 'interview' (respostas de entrevista) ou 'translate' (traduz audio EN para PT-BR)")
    parser.add_argument("--print-key", type=str, default="ctrl",
                        help="Tecla do gatilho de print por toques repetidos (default: ctrl)")
    parser.add_argument("--print-taps", type=int, default=3,
                        help="Quantos toques na tecla para disparar o print (default: 3)")
    parser.add_argument("--print-window", type=float, default=1.0,
                        help="Janela de tempo (s) para contar os toques (default: 1.0)")
    parser.add_argument("--opacity", type=float, default=0.85,
                        help="Transparencia da janela (0.2=bem transparente, 1.0=opaco, default: 0.85)")
    return parser.parse_args()


def _normalize(text):
    """Lowercase + remove acentos para matching tolerante."""
    import unicodedata
    text = text.lower().strip()
    return "".join(c for c in unicodedata.normalize("NFD", text) if unicodedata.category(c) != "Mn")


def _log_turn(interviewer_raw, response_full, lang):
    """Grava um turno completo (pergunta + resposta) com versao PT quando possivel."""
    if lang == "pt":
        log_conversa("ENTREVISTADOR", interviewer_raw)
        log_conversa("CANDIDATO", response_full)
        return
    # lang == "en": resposta tem secoes bilingues
    pergunta_pt = _extract_section(response_full, "**Pergunta (PT):**")
    resposta_pt = _extract_section(response_full, "**Resposta (PT):**")
    answer_en = _extract_section(response_full, "**Answer (EN):**", "**Answer:**")

    if pergunta_pt:
        log_conversa("ENTREVISTADOR", f"[EN] {interviewer_raw}\n[PT] {pergunta_pt}")
    else:
        log_conversa("ENTREVISTADOR", f"[EN] {interviewer_raw}")

    if answer_en and resposta_pt:
        log_conversa("CANDIDATO", f"[EN] {answer_en}\n[PT] {resposta_pt}")
    elif resposta_pt:
        log_conversa("CANDIDATO", f"[PT] {resposta_pt}")
    else:
        log_conversa("CANDIDATO", response_full)


def load_canned_answers():
    """Carrega respostas pre-cadastradas de respostas.json (se existir)."""
    import json
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "respostas.json")
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        normalized = []
        for entry in data:
            kws = [_normalize(k) for k in entry.get("keywords", []) if k.strip()]
            resp = entry.get("resposta", "").strip()
            if kws and resp:
                normalized.append({"keywords": kws, "resposta": resp})
        log.info(f"Respostas prontas carregadas: {len(normalized)}")
        return normalized
    except Exception as e:
        log.error(f"Erro ao ler respostas.json: {e}")
        return []


def match_canned(text, canned):
    """Retorna a resposta pronta se alguma keyword aparecer na transcricao, senao None."""
    if not canned or not text:
        return None
    norm_text = _normalize(text)
    for entry in canned:
        for kw in entry["keywords"]:
            if kw in norm_text:
                return entry["resposta"]
    return None


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
    from screen_hide import hide_from_capture, hide_from_taskbar, set_opacity

    # Estado compartilhado entre init_thread e JsApi
    default_lang = "en" if args.mode == "translate" else args.language
    state = {"capture": None, "gui": None, "assistant": None, "transcriber": None, "language": default_lang, "mode": args.mode, "hwnd": None, "opacity": max(0.2, min(1.0, args.opacity)), "last_shot": None, "last_effort": "low"}
    canned_answers = load_canned_answers()

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

    def _process_screenshot(effort="low", reuse=False):
        """Captura (ou reaproveita) a tela e pede analise ao modelo de visao.
        effort: low padrao; medium/high custam mais tokens, use so quando o low nao resolver.
        reuse=True reanalisa o ultimo print sem capturar de novo (mesmo problema, mais esforco).
        """
        gui = state["gui"]
        ai = state["assistant"]
        if gui is None or ai is None:
            return
        try:
            if reuse and state.get("last_shot"):
                img_bytes = state["last_shot"]
                gui.set_status("transcribing", f"Reanalisando print (esforco {effort})...")
                gui.add_question(f"[Reanalisar print — esforco {effort}]")
            else:
                gui.set_status("transcribing", "Capturando tela...")
                img_bytes = _capture_screenshot_bytes()
                state["last_shot"] = img_bytes
                gui.add_question("[Print da tela]")
            state["last_effort"] = effort
            gui.set_status("answering", f"Analisando imagem (esforco {effort})...")
            gui.start_answer()

            def on_token(token):
                gui.append_token(token)

            ai.answer_image(img_bytes, on_token=on_token, language=state["language"], effort=effort)
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
            threading.Thread(target=lambda: _process_screenshot(effort="low", reuse=False), daemon=True).start()
            return True

        def escalate_screenshot(self):
            """Reanalisa o ultimo print no proximo nivel de esforco (low->medium->high).
            Economiza tokens: so paga esforco maior quando o usuario pede, e na mesma imagem."""
            if not state.get("last_shot"):
                return False
            levels = ["low", "medium", "high"]
            cur = state.get("last_effort", "low")
            nxt = levels[min(levels.index(cur) + 1, len(levels) - 1)]
            threading.Thread(target=lambda: _process_screenshot(effort=nxt, reuse=True), daemon=True).start()
            return nxt

        def adjust_opacity(self, delta):
            """Ajusta a transparencia da janela (+/-). Thread-safe via Win32."""
            hwnd = state.get("hwnd")
            if not hwnd:
                return state["opacity"]
            new_val = max(0.2, min(1.0, state["opacity"] + delta))
            state["opacity"] = new_val
            set_opacity(hwnd, new_val)
            log.info(f"Opacidade: {new_val:.2f}")
            return new_val

        def set_language(self, lang):
            if lang in ("pt", "en"):
                state["language"] = lang
                tr = state["transcriber"]
                if tr is not None:
                    tr.language = lang
                log.info(f"Idioma forcado: {lang}")
            return state["language"]

        def set_mode(self, mode):
            if mode not in ("interview", "translate"):
                return False
            args.mode = mode
            state["mode"] = mode
            # Idioma padrao por modo (usuario ainda pode trocar manualmente nos botoes PT/EN)
            new_lang = "en" if mode == "translate" else "pt"
            state["language"] = new_lang
            tr = state["transcriber"]
            if tr is not None:
                tr.language = new_lang
            # Se ja existe assistente carregado, troca o modo em tempo real e limpa historico
            ai = state["assistant"]
            if ai is not None:
                ai.mode = mode
                ai.history = []
            gui = state["gui"]
            if gui:
                label = "Traducao EN->PT" if mode == "translate" else "Entrevista"
                gui.set_status("listening" if ai else "initializing",
                               f"{label} - " + ("Ouvindo..." if ai else "Escolha Local ou API"))
            log.info(f"Modo: {mode} | idioma: {new_lang}")
            return new_lang

        def set_provider(self, provider):
            gui = state["gui"]
            cap = state["capture"]
            if provider not in ("ollama", "claude"):
                return False
            if provider == "claude" and not api_key:
                if gui:
                    gui.set_status("error", "ANTHROPIC_API_KEY nao definida no .env")
                log.error("Tentativa de usar Claude sem API key.")
                return False
            try:
                from assistant import create_assistant
                assistant_ai = create_assistant(
                    provider=provider,
                    context=args.context,
                    api_key=api_key,
                    ollama_model=args.ollama_model,
                    vision_model=args.vision_model,
                    mode=args.mode,
                )
                state["assistant"] = assistant_ai
                state["provider"] = provider
                if cap is not None:
                    cap.resume()
                if gui:
                    gui.set_status("listening", "Ouvindo...")
                log.info(f"Provider ativado: {provider}")
                return True
            except Exception as e:
                if gui:
                    gui.set_status("error", f"Erro: {e}")
                log.error(f"Erro ao trocar provider: {e}")
                return False

    window = webview.create_window(
        "",
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
            hide_from_taskbar(hwnd)
            # Transparencia via Win32 (thread-safe) — guarda hwnd para ajuste ao vivo
            state["hwnd"] = hwnd
            set_opacity(hwnd, state["opacity"])
            log.info(f"Opacidade aplicada: {state['opacity']:.2f}")
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

        except Exception as e:
            gui.set_status("error", f"Erro: {e}")
            log.error(f"Erro ao inicializar: {e}")
            return

        # Inicia pausado; usuario precisa escolher Local ou API
        capture.pause()
        gui.set_status("initializing", "Escolha Local ou API para iniciar")

        # Gatilho discreto: tocar a tecla N vezes rapido (default: 3x Ctrl).
        # Nao gera caractere nem aparece no editor — passa despercebido em monitoramento.
        try:
            import keyboard
            trigger_key = args.print_key.lower()
            taps_needed = max(2, args.print_taps)
            tap_window = args.print_window
            # Apos o ultimo toque, espera "settle" pra contar o burst inteiro antes de decidir o nivel:
            #   taps_needed (3) = print novo em low; +1 (4) = medium; +2 (5) = high (reanalisa o ultimo).
            # Necessario porque 3/4/5 compartilham a mesma tecla — sem a espera, dispararia no 3o toque.
            settle = min(0.45, tap_window)
            levels = ["low", "medium", "high"]
            tap_state = {"times": [], "held": False, "timer": None}

            def _fire_taps():
                n = len(tap_state["times"])
                tap_state["times"] = []
                tap_state["timer"] = None
                if n < taps_needed:
                    return
                extra = n - taps_needed
                if extra <= 0:
                    threading.Thread(target=lambda: _process_screenshot(effort="low", reuse=False), daemon=True).start()
                else:
                    eff = levels[min(extra, len(levels) - 1)]
                    threading.Thread(target=lambda: _process_screenshot(effort=eff, reuse=True), daemon=True).start()

            def _on_key(event):
                name = (event.name or "").lower()
                if trigger_key not in name:
                    return
                if event.event_type == "up":
                    tap_state["held"] = False
                    return
                # event_type == "down": conta apenas a transicao (ignora auto-repeat)
                if tap_state["held"]:
                    return
                tap_state["held"] = True
                now = time.time()
                tap_state["times"].append(now)
                # mantem so os toques dentro da janela
                tap_state["times"] = [t for t in tap_state["times"] if now - t <= tap_window]
                # (re)inicia o timer de settle: decide o nivel quando os toques pararem
                if tap_state["timer"] is not None:
                    tap_state["timer"].cancel()
                tap_state["timer"] = threading.Timer(settle, _fire_taps)
                tap_state["timer"].daemon = True
                tap_state["timer"].start()

            keyboard.hook(_on_key)
            log.info(f"Gatilho de print: {taps_needed}x '{trigger_key}'=low, +1=medium, +2=high (settle {settle}s, janela {tap_window}s)")
        except Exception as e:
            log.warning(f"Nao foi possivel registrar gatilho de print: {e}")

        def on_audio_ready(audio_data, sample_rate):
            assistant_ai = state["assistant"]
            if assistant_ai is None:
                return  # nenhum provider escolhido ainda

            gui.set_status("transcribing", "Transcrevendo...")

            text, _ = transcriber.transcribe(audio_data, sample_rate)
            lang = state["language"]

            if not text or len(text.strip()) < 5:
                gui.set_status("listening", "Ouvindo...")
                return

            log.info(f"Idioma: {lang} | Texto: {text[:80]}")
            display_text = f"[{lang.upper()}] {text}" if lang != "pt" else text
            gui.add_question(display_text)
            # Log do entrevistador: original; PT sera adicionado depois (extraido da resposta)
            interviewer_raw = text

            # Resposta pronta
            canned = match_canned(text, canned_answers) if state["mode"] != "translate" else None
            if canned:
                gui.start_answer()
                collected = []
                def collect(t):
                    collected.append(t)
                    gui.append_token(t)
                if lang == "en":
                    log.info("Resposta pronta acionada (traduzindo PT->EN via AI)")
                    gui.set_status("answering", "Traduzindo resposta pronta...")
                    try:
                        assistant_ai.translate_canned(canned, on_token=collect)
                    except Exception as e:
                        gui.append_token(f"\n\n**Erro tradução:** {e}\n\n{canned}")
                        log.error(f"Erro traduzindo canned: {e}")
                else:
                    log.info("Resposta pronta acionada (PT direto, sem AI)")
                    gui.set_status("answering", "Resposta pronta...")
                    collect(canned)
                gui.finish_answer()
                full = "".join(collected)
                _log_turn(interviewer_raw, full, lang)
                gui.set_status("listening", "Ouvindo...")
                return

            gui.set_status("answering", "Respondendo...")
            gui.start_answer()

            collected_ans = []
            def on_token(token):
                collected_ans.append(token)
                gui.append_token(token)

            try:
                assistant_ai.answer(text, on_token=on_token, language=lang)
            except Exception as e:
                gui.append_token(f"\n\n**Erro:** {e}")
                log.error(f"Erro ao gerar resposta: {e}")

            gui.finish_answer()
            _log_turn(interviewer_raw, "".join(collected_ans), lang)
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
