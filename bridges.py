"""Frases-ponte: o que o candidato fala enquanto a IA ainda esta gerando a resposta.

Sao locais (zero latencia, zero token, zero rede) e existem para eliminar o silencio
entre o fim da pergunta do entrevistador e o primeiro token da resposta. Sao frases
que qualquer candidato falaria de verdade — compram de 3 a 8 segundos sem soar como
enrolacao e sem se comprometer com nenhum conteudo especifico.
"""

import random
import threading
import unicodedata


GENERIC = {
    "pt": [
        "Certo, boa pergunta. Deixa eu organizar as ideias rapidinho pra te dar uma resposta mais direta.",
        "Entendi. Vou responder em duas partes, se puder — primeiro o contexto e depois o resultado.",
        "Perfeito. Deixa eu pensar no exemplo mais relevante que eu tenho pra isso.",
        "Boa. Antes de responder, so pra ter certeza que entendi: voce quer o lado mais pratico ou o conceitual?",
        "Certo. Isso me lembra uma situacao bem especifica, deixa eu recuperar os detalhes.",
        "Sim, ja passei por isso. Deixa eu estruturar como foi, do problema ate a solucao.",
    ],
    "en": [
        "Right, good question. Let me organize my thoughts for a second so I can give you a clear answer.",
        "Got it. I'll answer that in two parts, if that's okay — the context first, then the outcome.",
        "Sure. Let me think of the most relevant example I have for that.",
        "Good one. Before I answer, just to make sure I got it right: are you after the practical side or the conceptual one?",
        "Right. That actually reminds me of a pretty specific situation, let me pull up the details.",
        "Yes, I've dealt with that before. Let me walk you through it, from the problem to the solution.",
    ],
    "es": [
        "Claro, buena pregunta. Dejame ordenar las ideas un momento para darte una respuesta mas directa.",
        "Entiendo. Voy a responder en dos partes, si te parece: primero el contexto y luego el resultado.",
        "Perfecto. Dejame pensar en el ejemplo mas relevante que tengo para eso.",
        "Buena pregunta. Antes de responder, solo para confirmar que entendi: quieres el lado practico o el conceptual?",
        "Claro. Eso me recuerda una situacion muy concreta, dejame recuperar los detalles.",
        "Si, ya pase por eso. Dejame estructurarlo, desde el problema hasta la solucion.",
    ],
}

TECHNICAL = {
    "pt": [
        "Certo. Antes de sair codando, deixa eu pensar na abordagem — prefiro acertar a estrategia e depois a implementacao.",
        "Boa. Deixa eu raciocinar em voz alta: primeiro os casos de borda, depois a estrutura de dados que faz sentido aqui.",
        "Entendi o problema. Tem uma solucao forca bruta obvia, mas deixa eu ver se da pra melhorar a complexidade.",
        "Certo. So pra alinhar antes de implementar: qual o tamanho esperado da entrada? Isso muda a estrutura que eu escolho.",
        "Deixa eu reler o enunciado rapidinho pra nao deixar passar nenhuma restricao.",
        "Legal. Vou comecar pela assinatura do metodo e pelos casos de borda, ai a implementacao sai natural.",
    ],
    "en": [
        "Right. Before I start coding, let me think about the approach — I'd rather get the strategy right first.",
        "Let me reason out loud here: edge cases first, then the data structure that actually makes sense.",
        "I see the problem. There's an obvious brute-force solution, but let me see if I can improve the complexity.",
        "Sure. Just to align before I implement: what's the expected input size? That changes the structure I'd pick.",
        "Let me re-read the statement quickly so I don't miss any constraint.",
        "Okay. I'll start from the method signature and the edge cases, then the implementation follows naturally.",
    ],
    "es": [
        "Claro. Antes de empezar a codificar, dejame pensar en el enfoque — prefiero acertar la estrategia primero.",
        "Dejame razonar en voz alta: primero los casos borde, luego la estructura de datos que tiene sentido aqui.",
        "Veo el problema. Hay una solucion de fuerza bruta obvia, pero dejame ver si puedo mejorar la complejidad.",
        "Claro. Solo para alinear antes de implementar: cual es el tamano esperado de la entrada? Eso cambia la estructura.",
        "Dejame releer el enunciado rapido para no pasar por alto ninguna restriccion.",
        "Bien. Empiezo por la firma del metodo y los casos borde, y la implementacion sale sola.",
    ],
}

BEHAVIORAL = {
    "pt": [
        "Boa pergunta. Tenho um exemplo bem concreto disso, deixa eu recuperar como foi.",
        "Certo. Vou te contar a situacao, o que eu fiz e no que deu — assim fica mais claro.",
        "Entendi. Deixa eu pensar em qual caso ilustra melhor isso.",
        "Essa e interessante. Antes de responder, voce prefere um exemplo de um projeto recente ou pode ser mais antigo?",
        "Certo. Ja vivi isso mais de uma vez, deixa eu escolher o caso mais relevante pra vaga.",
    ],
    "en": [
        "Good question. I have a pretty concrete example of that, let me recall how it went.",
        "Sure. I'll give you the situation, what I did and how it ended — that makes it clearer.",
        "Got it. Let me think about which case illustrates that best.",
        "That's an interesting one. Before I answer, would you rather hear about a recent project or is an older one fine?",
        "Right. I've been through that more than once, let me pick the one most relevant to this role.",
    ],
    "es": [
        "Buena pregunta. Tengo un ejemplo bastante concreto de eso, dejame recordar como fue.",
        "Claro. Te cuento la situacion, lo que hice y en que resulto — asi queda mas claro.",
        "Entiendo. Dejame pensar cual caso ilustra mejor eso.",
        "Esa es interesante. Antes de responder, prefieres un ejemplo de un proyecto reciente o puede ser mas antiguo?",
        "Claro. Ya pase por eso mas de una vez, dejame elegir el caso mas relevante para el puesto.",
    ],
}

_TECH_KEYWORDS = (
    "codigo", "code", "algoritmo", "algorithm", "complexidade", "complexity", "big o",
    "implementa", "implement", "funcao", "function", "metodo", "method", "classe", "class",
    "array", "matriz", "lista ligada", "linked list", "arvore", "tree", "hashmap", "hash map",
    "sql", "query", "banco de dados", "database", "indice", "index", "thread", "concorrencia",
    "concurrency", "exception", "excecao", "design pattern", "padrao de projeto", "escreva",
    "write a", "resolva", "solve", "leetcode", "api rest", "endpoint", "microservi", "docker",
    "kubernetes", "spring", "hibernate", "garbage collector", "memoria", "memory leak",
    "estrutura de dados", "data structure", "recursao", "recursion", "ordena", "sort",
    # front-end: entrevistas de Angular/React tambem sao tecnicas
    "react", "angular", "typescript", "javascript", "componente", "component", "hook",
    "css", "flexbox", "grid", "layout", "responsiv", "render", "re-render", "store",
    "redux", "ngrx", "signal", "context", "props", "generic", "acessibilidade",
    "accessibility", "bundle", "lazy load", "code splitting", "ssr", "hidrat",
    "code review", "revisao de codigo", "pipeline", "ci/cd", "integracao continua",
    "union", "tipagem", "interface", "enum", "type safety", "performance", "cache",
    "gerenciamento de estado", "state management", "teste unitario", "unit test",
)

_BEHAVIORAL_KEYWORDS = (
    "fale sobre voce", "tell me about yourself", "hablame de ti", "conte sobre", "conte-me",
    "tell me about a time", "describe a time", "me fale de uma situacao", "desafio", "challenge",
    "dificuldade", "difficult", "conflito", "conflict", "ponto fraco", "weakness", "ponto forte",
    "strength", "fortaleza", "debilidad", "por que voce", "why do you", "por que quer",
    "why are you", "por que devemos", "why should we", "onde se ve", "where do you see yourself",
    "salario", "salary", "pretensao", "expectativa", "trabalho em equipe", "teamwork",
    "lideranca", "leadership", "prazo", "deadline", "pressao", "pressure", "erro que", "mistake",
    "feedback", "motiva", "motivat",
)


_last_pick = {}
_lock = threading.Lock()


def _normalize(text):
    """Lowercase + sem acentos, para casar as keywords com a transcricao."""
    text = (text or "").lower()
    return "".join(c for c in unicodedata.normalize("NFD", text) if unicodedata.category(c) != "Mn")


def classify(text):
    """Classifica a pergunta em 'technical' | 'behavioral' | 'generic'."""
    norm = _normalize(text)
    if not norm:
        return "generic"
    if any(kw in norm for kw in _TECH_KEYWORDS):
        return "technical"
    if any(kw in norm for kw in _BEHAVIORAL_KEYWORDS):
        return "behavioral"
    return "generic"


def pick_bridge(language="pt", text=None):
    """Retorna a frase-ponte para o candidato falar imediatamente.

    language: pt | en | es (fallback pt).
    text: transcricao da pergunta, quando ja disponivel — escolhe uma ponte
          tecnica/comportamental. Sem texto, usa o pool generico (serve pra qualquer coisa).
    """
    lang = language if language in GENERIC else "pt"
    category = classify(text) if text else "generic"
    pool = {"technical": TECHNICAL, "behavioral": BEHAVIORAL}.get(category, GENERIC)[lang]

    key = (category, lang)
    with _lock:
        previous = _last_pick.get(key)
        options = [p for p in pool if p != previous] or pool
        chosen = random.choice(options)
        _last_pick[key] = chosen
    return chosen
