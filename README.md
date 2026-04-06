# Interview Assistant

Ouve a saída de áudio do sistema em tempo real e usa IA para gerar respostas para perguntas de entrevista.

## Como funciona

1. Captura o áudio do sistema (WASAPI loopback) - ouve o que sai nos alto-falantes/fones
2. Detecta quando alguém termina de falar (silêncio)
3. Transcreve o áudio localmente com Whisper (sem enviar áudio para nuvem)
4. IA gera uma resposta sugerida no terminal

## Dois modos de IA

| Modo | Comando | Custo | Requisito |
|------|---------|-------|-----------|
| **Ollama** (padrão) | `python main.py` | Gratuito | Ollama instalado |
| **Claude API** | `python main.py --provider claude` | ~$0.005/pergunta | Chave API Anthropic |

## Setup

```bash
# Criar e ativar ambiente virtual
python -m venv venv
venv\Scripts\activate

# Instalar dependências
pip install -r requirements.txt
```

### Opção 1: Ollama (gratuito)

```bash
# 1. Instalar Ollama: https://ollama.com
# 2. Baixar um modelo
ollama pull llama3.1

# 3. Rodar
python main.py
```

### Opção 2: Claude API

```bash
# 1. Configurar chave
copy .env.example .env
# Editar .env com sua ANTHROPIC_API_KEY

# 2. Rodar
python main.py --provider claude
```

## Uso

```bash
# Ollama (gratuito, padrão)
python main.py

# Ollama com modelo diferente
python main.py --ollama-model mistral

# Claude API
python main.py --provider claude

# Com contexto sobre você (melhora as respostas)
python main.py --context "Dev Java Senior, 8 anos, Spring Boot, AWS, microsserviços"

# Entrevista em inglês com modelo de transcrição maior
python main.py --language en --model small
```

## Opções

| Flag             | Default  | Descrição                                       |
|------------------|----------|-------------------------------------------------|
| `--provider`     | ollama   | `ollama` (local/gratuito) ou `claude` (API)     |
| `--ollama-model` | llama3.1 | Modelo do Ollama (llama3.1, mistral, etc)       |
| `--context`      | ""       | Seu perfil profissional para respostas melhores |
| `--language`     | pt       | Idioma do áudio (pt, en, es, etc)               |
| `--model`        | base     | Modelo Whisper (tiny/base/small/medium/large-v3) |
| `--silence`      | 2.0      | Segundos de silêncio para cortar a fala         |
| `--threshold`    | 0.01     | Sensibilidade de detecção de voz                |

## Requisitos

- Windows 10/11 (usa WASAPI para captura de áudio)
- Python 3.10+
- Ollama instalado **ou** chave API da Anthropic
