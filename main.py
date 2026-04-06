"""
Interview Assistant - Ouve a saída de áudio do sistema e gera respostas para entrevistas.

Uso:
    python main.py                          # Ollama (gratuito, padrão)
    python main.py --provider claude        # API da Anthropic
    python main.py --provider ollama --ollama-model mistral
    python main.py --context "Sou dev Python com 5 anos de experiência"
"""

import argparse
import os
import sys

from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown

load_dotenv()

console = Console()


def main():
    parser = argparse.ArgumentParser(description="Interview Assistant - IA para ajudar em entrevistas")
    parser.add_argument("--provider", type=str, default="ollama", choices=["ollama", "claude"],
                        help="Provedor de IA: 'ollama' (gratuito/local) ou 'claude' (API Anthropic)")
    parser.add_argument("--ollama-model", type=str, default="llama3.2",
                        help="Modelo do Ollama (default: llama3.2)")
    parser.add_argument("--context", type=str, default="",
                        help="Contexto sobre você (ex: 'Dev Python, 5 anos, Django e AWS')")
    parser.add_argument("--language", type=str, default="pt",
                        help="Idioma do áudio (pt, en, es, etc)")
    parser.add_argument("--model", type=str, default="tiny",
                        help="Modelo Whisper (tiny, base, small, medium, large-v3)")
    parser.add_argument("--silence", type=float, default=1.2,
                        help="Segundos de silêncio para considerar fim da fala (default: 1.2)")
    parser.add_argument("--threshold", type=float, default=0.01,
                        help="Limite de volume para detectar fala (default: 0.01)")
    args = parser.parse_args()

    # Validar API key se usar Claude
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if args.provider == "claude" and not api_key:
        console.print("[red bold]Erro: ANTHROPIC_API_KEY não encontrada.[/]")
        console.print("Crie um arquivo .env com: ANTHROPIC_API_KEY=sk-ant-sua-chave")
        sys.exit(1)

    # Header
    provider_label = "Ollama (local)" if args.provider == "ollama" else "Claude API"
    console.print(Panel.fit(
        f"[bold cyan]Interview Assistant[/]\n"
        f"Ouve o áudio do sistema e gera respostas para entrevistas\n"
        f"[dim]Provedor: {provider_label}[/]",
        border_style="cyan"
    ))

    # Inicializar componentes
    console.print("\n[yellow]Inicializando...[/]")

    console.print("[dim]Audio:[/]")
    from audio_capture import AudioCapture
    capture = AudioCapture(
        silence_threshold=args.threshold,
        silence_duration=args.silence,
    )

    console.print("[dim]Transcrição:[/]")
    from transcriber import Transcriber
    transcriber = Transcriber(model_size=args.model, language=args.language)

    console.print(f"[dim]Assistente IA ({provider_label}):[/]")
    from assistant import create_assistant
    try:
        assistant_ai = create_assistant(
            provider=args.provider,
            context=args.context,
            api_key=api_key,
            ollama_model=args.ollama_model,
        )
    except RuntimeError as e:
        console.print(f"[red bold]Erro: {e}[/]")
        sys.exit(1)
    console.print("  Pronto.\n")

    if args.context:
        console.print(f"[dim]Contexto: {args.context}[/]\n")

    console.print(Panel(
        "[green bold]Ouvindo áudio do sistema...[/]\n"
        "[dim]Fale ou reproduza uma pergunta de entrevista.\n"
        "Pressione Ctrl+C para sair.[/]",
        border_style="green"
    ))

    question_count = 0

    def on_audio_ready(audio_data, sample_rate):
        nonlocal question_count

        console.print("\n[yellow]Transcrevendo...[/]")
        text = transcriber.transcribe(audio_data, sample_rate)

        if not text or len(text.strip()) < 5:
            console.print("[dim]  (áudio muito curto ou sem fala detectada)[/]")
            return

        question_count += 1
        console.print(Panel(
            f"[bold white]{text}[/]",
            title=f"[cyan]Pergunta #{question_count}[/]",
            border_style="blue"
        ))

        # Streaming: mostra a resposta token por token
        console.print("[green bold]Resposta Sugerida:[/]")
        console.print("─" * 60)

        def on_token(token):
            console.print(token, end="", highlight=False)

        try:
            answer = assistant_ai.answer(text, on_token=on_token)
        except Exception as e:
            console.print(f"\n[red]Erro ao gerar resposta: {e}[/]")
            return

        console.print()  # newline after streaming
        console.print("─" * 60)
        console.print("[dim]Ouvindo...[/]")

    try:
        capture.capture_until_silence(on_audio_ready)
    except KeyboardInterrupt:
        console.print("\n[yellow]Encerrando...[/]")
        capture.stop()
        console.print(f"[cyan]Total de perguntas respondidas: {question_count}[/]")
        console.print("[green]Boa sorte na entrevista![/]")


if __name__ == "__main__":
    main()
