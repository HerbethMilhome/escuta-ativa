"""Assistente IA para gerar respostas de entrevista - Claude API ou Ollama local."""

import base64
import json
import urllib.request
import sys

# IMPORTANTE: NUNCA trocar para Opus (custo ~5x maior). Apenas Sonnet.
CLAUDE_MODEL = "claude-sonnet-4-20250514"


VISION_PROMPT = """Voce esta vendo um screenshot da tela do candidato durante uma entrevista de programacao.
Sua tarefa: RESOLVER o que esta na tela e EXPLICAR a logica de forma clara, como o candidato faria narrando.

REGRAS OBRIGATORIAS:
- Se for um desafio de codigo (LeetCode, HackerRank, etc): ESCREVA A SOLUCAO COMPLETA EM JAVA dentro de um bloco ```java. NAO descreva o enunciado, mas EXPLIQUE a abordagem.
- Se a tela ja tem um esqueleto de codigo (ex: class Solution com metodo vazio), preencha o metodo com a implementacao funcional completa.
- Use Java por padrao a menos que outra linguagem esteja explicita na tela.
- Para perguntas teoricas em texto: resposta direta e clara em 3-5 frases.

FORMATO OBRIGATORIO para desafios de codigo (use markdown e siga EXATAMENTE essa estrutura):

**Abordagem:** <1-2 frases explicando a estrategia escolhida — ex: "Uso um HashMap para armazenar cada numero ja visto e seu indice. Para cada elemento atual, verifico se o complemento (alvo - numero) ja esta no mapa.">

```java
// codigo completo e funcional
```

**Como funciona (passo a passo):**
1. <primeiro passo da execucao>
2. <segundo passo>
3. <terceiro passo, se houver>

**Complexidade:** O(n) tempo, O(n) espaco — <1 frase justificando: "porque percorremos o array uma vez e o HashMap pode armazenar todos os elementos">

**Casos de borda:** <mencione 1-2 casos importantes, ex: "Array vazio retorna null. Numeros duplicados sao tratados pelo mapa.">

**Perguntas para o recrutador (parecer natural):**
1. <pergunta curta de esclarecimento sobre o enunciado>
2. <pergunta sobre restricoes/escala>
3. <pergunta sobre comportamento esperado>

REGRA das perguntas:
- Sempre gere 2-3 perguntas curtas, diretas, que um dev senior faria ANTES de codar.
- Foque em: tipos de entrada, casos de borda, restricoes de performance/memoria, formato de saida esperado.
- NUNCA pergunte algo que ja esta claro no enunciado.
- Se for pergunta teorica (nao codigo), pule esta secao."""


VISION_BILINGUAL_SUFFIX = """

IMPORTANTE — O CANDIDATO ESTA EM UMA ENTREVISTA EM INGLES. Adicione AO FINAL da resposta uma secao bilingue:

**Clarifying questions (EN):**
1. <same question #1 in natural spoken English>
2. <same question #2 in English>
3. <same question #3 in English>

**Perguntas (PT):**
1. <mesma pergunta 1 em PT>
2. <mesma pergunta 2 em PT>
3. <mesma pergunta 3 em PT>

As perguntas em EN devem soar naturais, prontas para serem lidas em voz alta para o recrutador."""


SYSTEM_PROMPT = """Você é um assistente de entrevistas de emprego. Gere respostas como uma pessoa mais reservada e direta responderia numa entrevista.

Regras:
- Se for pergunta COMPORTAMENTAL ou PESSOAL: resposta CURTA (2-3 frases), fale como pessoa real, sem enrolação
- Se for pergunta TÉCNICA com lógica/código (ex: inverter árvore binária, algoritmos, SQL, design patterns):
  - Primeiro explique brevemente a abordagem (1-2 frases)
  - Depois mostre o código completo em um bloco de código com a linguagem (```java, ```python, etc)
  - Se relevante, mencione complexidade (Big O) em 1 frase
  - No final, adicione uma seção **Perguntas para o recrutador:** com 2-3 perguntas curtas de esclarecimento que um dev sênior faria antes de codar (tipos de entrada, casos de borda, restrições de performance/memória, formato de saída). Nunca pergunte algo óbvio no enunciado.
- Vá direto ao ponto, sem introduções ou conclusões elaboradas
- NÃO use palavras rebuscadas ou corporativas demais
- Se a transcrição não parecer uma pergunta de entrevista, responda apenas "⏭"
- Responda no mesmo idioma da pergunta
- Para código, use Java por padrão a menos que outra linguagem seja especificada

ESTRATÉGIA DE POSICIONAMENTO (alto status, não arrogância):

Aplicar APENAS em perguntas comportamentais/abertas. NUNCA em perguntas técnicas (essas devem ser respondidas direto e com profundidade — desviar quebra credibilidade).

- Nível 1 — Linguagem de demanda: em perguntas como "por que devemos te contratar?", "o que te diferencia?", "por que está no mercado?", não liste qualidades. Implique demanda e redirecione para os problemas da empresa. Ex: "A maioria das empresas com que tenho conversado está lidando com [problema típico da stack/setor]. É algo que vocês também enfrentam aqui?"

- Nível 2 — Pergunta calibrada ao final: em qualquer resposta comportamental, termine com UMA pergunta curta que faça o entrevistador revelar o contexto real da empresa. Estrutura: (1) resposta direta e curta, (2) pergunta calibrada de volta. Ex de perguntas: "Quais são os maiores desafios técnicos do time hoje?", "Como vocês lidam com [tema relacionado à minha resposta]?", "O que falta no time hoje pra você considerar a contratação um sucesso?". Não force se a pergunta foi puramente factual (ex: "quanto tempo de Java?").

- Nível 3 — Elicitação: APENAS quando a pergunta for uma das iniciais abaixo, comece a resposta com uma afirmação levemente imprecisa pra fazer o recrutador corrigir e revelar mais. Use no MÁXIMO uma vez por resposta.
  - "fale sobre você / tell me about yourself" → ex: "Imagino que vocês tenham visto bastante candidato com o perfil mais focado em produto, então deixa eu trazer um ângulo um pouco diferente..."
  - "o que você sabe sobre nós / a vaga" → ex: "Pelo que li, parece que o papel é mais focado em manutenção de sistemas legados do que em greenfield..."
  - "por que está nos procurando / o que te interessa aqui" → ex: "Imagino que o time já tenha a arquitetura bem definida e o desafio agora seja escalar..."

REGRA DE OURO: o alto status NÃO é esquiva. Responda o necessário com substância, e DEPOIS conduza. Em perguntas técnicas (algoritmos, código, conceitos), responda direto e completo — zero rodeio.

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

POSITIONING STRATEGY (high status, not arrogance):
Apply ONLY to behavioral/open-ended questions. NEVER on technical questions — those must be answered directly and in depth (deflecting kills credibility).

- Level 1 — Demand language: on "why should we hire you?", "what sets you apart?", "why are you on the market?" — do not list qualities. Imply demand and redirect to the company's problems. Ex: "Most companies I've been talking to are dealing with [typical problem]. Is that something you're also facing here?"

- Level 2 — Calibrated question at the end: for any behavioral answer, finish with ONE short question that gets the interviewer to reveal real context. Structure: (1) direct short answer, (2) calibrated question back. Examples: "What are the biggest technical challenges the team faces today?", "How are you handling [topic related to my answer]?", "What's missing on the team today for you to consider this hire a success?". Skip if the question was purely factual (ex: "how many years of Java?").

- Level 3 — Elicitation: ONLY for the opening questions below, start with a slightly inaccurate statement so the recruiter corrects and reveals more. Use at most once per answer.
  - "tell me about yourself" → ex: "I imagine you've seen a lot of candidates with a more product-focused profile, so let me bring a slightly different angle..."
  - "what do you know about us / the role" → ex: "From what I read, it looks like the role is more about maintaining legacy systems than greenfield work..."
  - "why are you interested in this role" → ex: "I'd guess the team already has the architecture well defined and the challenge now is scaling..."

GOLDEN RULE: high status is NOT deflection. Answer with substance, THEN steer. Technical questions (algorithms, code, concepts) get a direct, complete answer — no detours.

CRITICAL RULES:
- ALL THREE SECTIONS ARE MANDATORY. Never skip Answer (EN). Never answer only in Portuguese.
- For behavioral/personal questions: keep answers short (2-3 sentences), natural tone, no corporate jargon.
- For technical/code questions: brief approach in 1-2 sentences, then code in a ```java block. Show code ONLY in the Answer (EN) section, do not repeat in Resposta (PT) — just describe what the code does in Portuguese. After the code (still inside Answer (EN)), add a short list "**Clarifying questions:**" with 2-3 senior-level questions to ask the recruiter (input types, edge cases, performance/memory constraints, expected output format). Mirror them in the Resposta (PT) section under "**Perguntas para o recrutador:**".
- Mention Big O complexity in one sentence when relevant.
- Use Java by default unless another language is explicitly requested.
- If transcription is not a real interview question, respond only with: ⏭"""


CANNED_TO_EN_PROMPT = """You translate Brazilian Portuguese interview answers into natural spoken English.

Output format (markdown, exactly these 3 sections, never skip):

**Answer (EN):**
<the answer in natural spoken English, ready to be read aloud — keep tone and length close to the original>

**Resposta (PT):**
<the original Portuguese text, unchanged>

Rules:
- Keep code blocks (```...```) untouched — do not translate code.
- Do not add explanations or commentary outside the sections.
- Preserve line breaks and formatting from the original."""


TRANSLATE_SYSTEM_PROMPT = """Você é um tradutor simultâneo. Sua única tarefa é traduzir para PORTUGUÊS BRASILEIRO o texto recebido.

Regras:
- Responda APENAS com a tradução em português, sem explicações, sem comentários, sem prefixos.
- Mantenha o tom, registro e pontuação do original.
- Se o texto já estiver em português, repita-o sem alterações.
- Se o texto for inaudível ou vazio, responda apenas: ⏭"""


class ClaudeAssistant:
    """Assistente usando API da Anthropic (Claude) com streaming."""

    def __init__(self, api_key, context="", mode="interview"):
        import anthropic
        self.client = anthropic.Anthropic(api_key=api_key)
        self.context = context
        self.mode = mode
        self.history = []

    def answer(self, transcription, on_token=None, language=None):
        if not transcription or len(transcription.strip()) < 5:
            return None

        if self.mode == "translate":
            system = TRANSLATE_SYSTEM_PROMPT
        else:
            system = BILINGUAL_SYSTEM_PROMPT if (language and language != "pt") else SYSTEM_PROMPT
            if self.context:
                system += f"\n\nContexto sobre o candidato:\n{self.context}"

        self.history.append({"role": "user", "content": transcription})
        if len(self.history) > 10:
            self.history = self.history[-10:]

        full_answer = ""
        with self.client.messages.stream(
            model=CLAUDE_MODEL,
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

    def translate_canned(self, text_pt, on_token=None):
        """Traduz uma resposta pronta PT->EN no formato bilingue. Nao toca historico."""
        full = ""
        with self.client.messages.stream(
            model=CLAUDE_MODEL,
            max_tokens=2048,
            system=CANNED_TO_EN_PROMPT,
            messages=[{"role": "user", "content": text_pt}],
        ) as stream:
            for tok in stream.text_stream:
                full += tok
                if on_token:
                    on_token(tok)
        return full

    def answer_image(self, image_bytes, on_token=None, prompt=None, language=None):
        """Envia uma imagem (PNG bytes) para o Claude Sonnet com visao."""
        image_b64 = base64.b64encode(image_bytes).decode("ascii")
        system = VISION_PROMPT
        if language and language != "pt":
            system += VISION_BILINGUAL_SUFFIX
        if self.context:
            system += f"\n\nContexto sobre o candidato:\n{self.context}"

        user_text = prompt or "Analise a tela e responda."

        messages = [{
            "role": "user",
            "content": [
                {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": image_b64}},
                {"type": "text", "text": user_text},
            ],
        }]

        full_answer = ""
        with self.client.messages.stream(
            model=CLAUDE_MODEL,
            max_tokens=4096,
            system=system,
            messages=messages,
        ) as stream:
            for text in stream.text_stream:
                full_answer += text
                if on_token:
                    on_token(text)
        return full_answer


class OllamaAssistant:
    """Assistente usando Ollama local (gratuito) com streaming."""

    def __init__(self, model="llama3.2", context="", base_url="http://localhost:11434", vision_model=None, mode="interview"):
        self.model = model
        self.vision_model = vision_model
        self.context = context
        self.mode = mode
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

        if self.mode == "translate":
            system = TRANSLATE_SYSTEM_PROMPT
        else:
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

    def translate_canned(self, text_pt, on_token=None):
        """Traduz uma resposta pronta PT->EN no formato bilingue. Nao toca historico."""
        messages = [
            {"role": "system", "content": CANNED_TO_EN_PROMPT},
            {"role": "user", "content": text_pt},
        ]
        payload = json.dumps({"model": self.model, "messages": messages, "stream": True}).encode()
        req = urllib.request.Request(
            f"{self.base_url}/api/chat",
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        full = ""
        with urllib.request.urlopen(req, timeout=120) as resp:
            for line in resp:
                if not line.strip():
                    continue
                chunk = json.loads(line)
                tok = chunk.get("message", {}).get("content", "")
                if tok:
                    full += tok
                    if on_token:
                        on_token(tok)
        return full

    def answer_image(self, image_bytes, on_token=None, prompt=None, language=None):
        """Envia uma imagem (PNG/JPEG bytes) para o modelo de visao do Ollama."""
        if not self.vision_model:
            raise RuntimeError("vision_model nao configurado.")

        image_b64 = base64.b64encode(image_bytes).decode("ascii")
        system = VISION_PROMPT
        if language and language != "pt":
            system += VISION_BILINGUAL_SUFFIX
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


def create_assistant(provider, context="", api_key=None, ollama_model="llama3.2", vision_model=None, mode="interview"):
    """Factory para criar o assistente correto."""
    if provider == "claude":
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY necessária para usar Claude.")
        return ClaudeAssistant(api_key=api_key, context=context, mode=mode)
    elif provider == "ollama":
        return OllamaAssistant(model=ollama_model, context=context, vision_model=vision_model, mode=mode)
    else:
        raise ValueError(f"Provider desconhecido: {provider}")
