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
- Para código, use Java por padrão a menos que outra linguagem seja especificada

REGRA CRÍTICA SOBRE EXPERIÊNCIA:
- Olhe atentamente o contexto do candidato antes de responder.
- Se a pergunta for sobre uma tecnologia/tópico que NÃO está nas experiências profissionais do candidato (mas pode estar listado como "conhecimento teórico em estudo"): comece a resposta com um disclaimer honesto curto, tipo "Ainda não tive experiência direta em produção com isso, mas pelo que estudei..." ou "Não trabalhei diretamente com X, mas conheço o conceito...".
- NUNCA invente projetos, empresas ou experiências que não estão no contexto.
- NUNCA afirme "trabalhei com X" se X não aparecer nas experiências profissionais reais do candidato.
- É melhor admitir falta de experiência prática e dar uma resposta teórica boa do que mentir e quebrar a credibilidade na entrevista."""


BILINGUAL_SYSTEM_PROMPT = """You are an interview assistant for a Brazilian Java developer being interviewed in English.

The candidate needs to:
1. Understand the question in Portuguese
2. Read the answer aloud in English
3. Verify the meaning of their answer in Portuguese

YOU MUST RESPOND IN THIS EXACT FORMAT (use markdown, fill all 3 sections, do NOT skip any):

**Pergunta (PT):** <translate the question to Brazilian Portuguese in one short sentence>

**Answer (EN):**
<answer in English, ready to be spoken aloud — direct, natural, 2-3 sentences for behavioral, or with code block for technical>

**Resposta (PT):**
<the same answer translated to Brazilian Portuguese, so the candidate understands what they will say>

CRITICAL RULES:
- ALL THREE SECTIONS ARE MANDATORY. Never skip Answer (EN). Never answer only in Portuguese.
- For behavioral/personal questions: keep answers short (2-3 sentences), natural tone, no corporate jargon.
- For technical/code questions: brief approach in 1-2 sentences, then code in a ```java block. Show code ONLY in the Answer (EN) section, do not repeat in Resposta (PT) — just describe what the code does in Portuguese.
- Mention Big O complexity in one sentence when relevant.
- Use Java by default unless another language is explicitly requested.
- If transcription is not a real interview question, respond only with: ⏭"""


class ClaudeAssistant:
    """Assistente usando API da Anthropic (Claude) com streaming."""

    def __init__(self, api_key, context=""):
        import anthropic
        self.client = anthropic.Anthropic(api_key=api_key)
        self.context = context
        self.history = []

    def answer(self, transcription, on_token=None, language=None):
        if not transcription or len(transcription.strip()) < 5:
            return None

        system = BILINGUAL_SYSTEM_PROMPT if (language and language != "pt") else SYSTEM_PROMPT
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

    def answer(self, transcription, on_token=None, language=None):
        if not transcription or len(transcription.strip()) < 5:
            return None

        system = BILINGUAL_SYSTEM_PROMPT if (language and language != "pt") else SYSTEM_PROMPT
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
