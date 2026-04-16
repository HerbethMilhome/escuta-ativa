"""Bridge entre Python e o frontend JS via pywebview evaluate_js."""

import json


class GuiApi:
    """Envia comandos para o frontend JS via window.evaluate_js()."""

    def __init__(self, window):
        self._window = window

    def _call_js(self, func, *args):
        """Chama uma funcao JS do window.appApi."""
        args_json = ", ".join(json.dumps(a) for a in args)
        js = f"window.appApi.{func}({args_json})"
        self._window.evaluate_js(js)

    def set_status(self, status, text):
        """Atualiza o status bar. status: listening|transcribing|answering|initializing|error"""
        self._call_js("setStatus", status, text)

    def add_question(self, text):
        """Adiciona uma pergunta no chat."""
        self._call_js("addQuestion", text)

    def start_answer(self):
        """Inicia um bloco de resposta (antes do streaming)."""
        self._call_js("startAnswer")

    def append_token(self, token):
        """Envia um token de streaming para a resposta atual."""
        self._call_js("appendToken", token)

    def finish_answer(self):
        """Finaliza a resposta atual (remove cursor, aplica highlight)."""
        self._call_js("finishAnswer")
