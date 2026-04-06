"""Assistente IA para gerar respostas de entrevista - Claude API ou Ollama local."""

import json
import urllib.request
import sys


SYSTEM_PROMPT = """Você é um assistente de entrevistas de emprego. Gere respostas como uma pessoa mais reservada e direta responderia numa entrevista.

Regras:
- Respostas CURTAS: máximo 2-3 frases por resposta
- Fale como uma pessoa real, tímida mas competente - sem enrolação
- Vá direto ao ponto, sem introduções ou conclusões elaboradas
- NÃO use bullet points, listas ou formatação - fale como se estivesse conversando
- NÃO use palavras rebuscadas ou corporativas demais
- Se a transcrição não parecer uma pergunta de entrevista, responda apenas "⏭"
- Responda no mesmo idioma da pergunta"""


class ClaudeAssistant:
    """Assistente usando API da Anthropic (Claude) com streaming."""

    def __init__(self, api_key, context=""):
        import anthropic
        self.client = anthropic.Anthropic(api_key=api_key)
        self.context = context
        self.history = []

    def answer(self, transcription, on_token=None):
        if not transcription or len(transcription.strip()) < 5:
            return None

        system = SYSTEM_PROMPT
        if self.context:
            system += f"\n\nContexto sobre o candidato:\n{self.context}"

        self.history.append({"role": "user", "content": transcription})
        if len(self.history) > 10:
            self.history = self.history[-10:]

        full_answer = ""
        with self.client.messages.stream(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            system=system,
            messages=self.history,
        ) as stream:
            for text in stream.text_stream:
                full_answer += text
                if on_token:
                    on_token(text)

        self.history.append({"role": "assistant", "content": full_answer})
        return full_answer


class OllamaAssistant:
    """Assistente usando Ollama local (gratuito) com streaming."""

    def __init__(self, model="llama3.2", context="", base_url="http://localhost:11434"):
        self.model = model
        self.context = context
        self.base_url = base_url
        self.history = []
        self._check_connection()

    def _check_connection(self):
        """Verifica se o Ollama está rodando."""
        try:
            req = urllib.request.Request(f"{self.base_url}/api/tags")
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read())
                models = [m["name"] for m in data.get("models", [])]
                if not any(self.model in m for m in models):
                    available = ", ".join(models) if models else "nenhum"
                    raise RuntimeError(
                        f"Modelo '{self.model}' não encontrado no Ollama.\n"
                        f"  Modelos disponíveis: {available}\n"
                        f"  Execute: ollama pull {self.model}"
                    )
        except urllib.error.URLError:
            raise RuntimeError(
                "Ollama não está rodando.\n"
                "  1. Instale: https://ollama.com\n"
                "  2. Execute: ollama serve\n"
                "  3. Baixe um modelo: ollama pull llama3.2"
            )

    def answer(self, transcription, on_token=None):
        if not transcription or len(transcription.strip()) < 5:
            return None

        system = SYSTEM_PROMPT
        if self.context:
            system += f"\n\nContexto sobre o candidato:\n{self.context}"

        self.history.append({"role": "user", "content": transcription})
        if len(self.history) > 10:
            self.history = self.history[-10:]

        messages = [{"role": "system", "content": system}] + self.history

        payload = json.dumps({
            "model": self.model,
            "messages": messages,
            "stream": True,
        }).encode()

        req = urllib.request.Request(
            f"{self.base_url}/api/chat",
            data=payload,
            headers={"Content-Type": "application/json"},
        )

        full_answer = ""
        with urllib.request.urlopen(req, timeout=120) as resp:
            for line in resp:
                if not line.strip():
                    continue
                chunk = json.loads(line)
                token = chunk.get("message", {}).get("content", "")
                if token:
                    full_answer += token
                    if on_token:
                        on_token(token)

        self.history.append({"role": "assistant", "content": full_answer})
        return full_answer


def create_assistant(provider, context="", api_key=None, ollama_model="llama3.2"):
    """Factory para criar o assistente correto."""
    if provider == "claude":
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY necessária para usar Claude.")
        return ClaudeAssistant(api_key=api_key, context=context)
    elif provider == "ollama":
        return OllamaAssistant(model=ollama_model, context=context)
    else:
        raise ValueError(f"Provider desconhecido: {provider}")
