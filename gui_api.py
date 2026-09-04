"""Bridge entre Python e o frontend JS via pywebview evaluate_js."""

import json
import logging
import threading

log = logging.getLogger("assistant")


class GuiApi:
    """Envia comandos para o frontend JS via window.evaluate_js()."""

    def __init__(self, window):
        self._window = window
        # evaluate_js bloqueia esperando o resultado do JS e nao e seguro com
        # chamadas concorrentes: a ponte e o pipeline de audio rodam em threads
        # diferentes, entao serializa aqui.
        self._lock = threading.Lock()

    def _call_js(self, func, *args):
        """Chama uma funcao JS do window.appApi.

        Nunca propaga erro: o pywebview transforma erro de JS em excecao Python, e
        isso mataria em silencio a thread do pipeline, congelando o status.
        """
        args_json = ", ".join(json.dumps(a) for a in args)
        js = f"window.appApi.{func}({args_json})"
        try:
            with self._lock:
                self._window.evaluate_js(js)
        except Exception as e:
            log.error(f"Falha na GUI em appApi.{func}: {type(e).__name__}: {e}")

    def set_status(self, status, text):
        """Atualiza o status bar. status: listening|transcribing|answering|initializing|error"""
        self._call_js("setStatus", status, text)

    def add_question(self, text):
        """Adiciona uma pergunta no chat."""
        self._call_js("addQuestion", text)

    def show_bridge(self, text):
        """Mostra a frase-ponte: o que o candidato fala AGORA enquanto a IA gera."""
        self._call_js("showBridge", text)

    def clear_bridge(self):
        """Remove a frase-ponte se ela ainda nao virou uma resposta (ex: era ruido)."""
        self._call_js("clearBridge")

    def start_answer(self):
        """Inicia um bloco de resposta (antes do streaming)."""
        self._call_js("startAnswer")

    def append_token(self, token):
        """Envia um token de streaming para a resposta atual."""
        self._call_js("appendToken", token)

    def finish_answer(self):
        """Finaliza a resposta atual (remove cursor, aplica highlight)."""
        self._call_js("finishAnswer")
