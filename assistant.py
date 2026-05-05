"""Assistente IA para gerar respostas de entrevista - Claude API ou Ollama local."""

import base64
import json
import urllib.request
import sys


VISION_PROMPT = """Voce esta vendo um screenshot da tela do candidato durante uma entrevista de programacao.
Sua tarefa: RESOLVER o que esta na tela, nao descrever.

REGRAS OBRIGATORIAS:
- Se for um desafio de codigo (LeetCode, HackerRank, etc): ESCREVA A SOLUCAO COMPLETA EM JAVA dentro de um bloco ```java. NAO descreva o problema. NAO diga "o candidato deve fazer X". Apenas resolva.
- Se a tela ja tem um esqueleto de codigo (ex: class Solution com metodo vazio), preencha o metodo com a implementacao funcional completa.
- Apos o codigo, em UMA frase, mencione complexidade Big O (ex: "O(n) tempo, O(n) espaco").
- Se for pergunta teorica em texto: resposta CURTA e direta (2-3 frases).
- NUNCA explique o enunciado, NUNCA descreva o que ve. Va direto a solucao.
- Use Java por padrao a menos que outra linguagem esteja explicita na tela.

Formato esperado para desafios de codigo:
```java
// codigo completo e funcional aqui
```
**Complexidade:** O(n) tempo, O(n) espaco."""


SYSTEM_PROMPT = """Você é um assistente de entrevistas de emprego. Gere respostas como uma pessoa mais reservada e direta responderia numa entrevista.

Regras:
- Se for pergunta COMPORTAMENTAL ou PESSOAL: resposta CURTA (2-3 frases), fale como pessoa real, sem enrolação
- Se for pergunta TÉCNICA com lógica/código (ex: inverter árvore binária, algoritmos, SQL, design patterns):
  - Primeiro explique brevemente a abordagem (1-2 frases)
  - Depois mostre o código completo em um bloco de código com a linguagem (```java, ```python, etc)
  - Se relevante, mencione complexidade (Big O) em 1 frase
- Vá direto ao ponto, sem introduções ou conclusões elaboradas
- NÃO use palavras rebuscadas ou corporativas demais
- Se a transcrição não parecer uma pergunta de entrevista, responda apenas "⏭"
- Responda no mesmo idioma da pergunta
- Para código, use Java por padrão a menos que outra linguagem seja especificada"""


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
            max_tokens=4096,
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

    def __init__(self, model="llama3.2", context="", base_url="http://localhost:11434", vision_model=None):
        self.model = model
        self.vision_model = vision_model
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

    def answer_image(self, image_bytes, on_token=None, prompt=None):
        """Envia uma imagem (PNG/JPEG bytes) para o modelo de visao do Ollama."""
        if not self.vision_model:
            raise RuntimeError("vision_model nao configurado.")

        image_b64 = base64.b64encode(image_bytes).decode("ascii")
        system = VISION_PROMPT
        if self.context:
            system += f"\n\nContexto sobre o candidato:\n{self.context}"

        user_text = prompt or "Analise a tela e responda."

        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user_text, "images": [image_b64]},
        ]

        payload = json.dumps({
            "model": self.vision_model,
            "messages": messages,
            "stream": True,
        }).encode()

        req = urllib.request.Request(
            f"{self.base_url}/api/chat",
            data=payload,
            headers={"Content-Type": "application/json"},
        )

        full_answer = ""
        with urllib.request.urlopen(req, timeout=300) as resp:
            for line in resp:
                if not line.strip():
                    continue
                chunk = json.loads(line)
                token = chunk.get("message", {}).get("content", "")
                if token:
                    full_answer += token
                    if on_token:
                        on_token(token)
        return full_answer


def create_assistant(provider, context="", api_key=None, ollama_model="llama3.2", vision_model=None):
    """Factory para criar o assistente correto."""
    if provider == "claude":
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY necessária para usar Claude.")
        return ClaudeAssistant(api_key=api_key, context=context)
    elif provider == "ollama":
        return OllamaAssistant(model=ollama_model, context=context, vision_model=vision_model)
    else:
        raise ValueError(f"Provider desconhecido: {provider}")
