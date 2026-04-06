"""Transcrição de áudio usando faster-whisper (local, sem API)."""

from faster_whisper import WhisperModel
import numpy as np
import io
import tempfile
import os
from scipy.io.wavfile import write as wav_write


class Transcriber:
    def __init__(self, model_size="base", language="pt"):
        self.language = language
        print(f"  Carregando modelo Whisper '{model_size}'...")
        self.model = WhisperModel(
            model_size,
            device="cpu",
            compute_type="int8",
        )
        print("  Modelo carregado.")

    def transcribe(self, audio_data, sample_rate):
        """Transcreve áudio (numpy array) para texto."""
        # Salvar em arquivo temporário (faster-whisper precisa de arquivo)
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            audio_int16 = np.int16(audio_data * 32767)
            wav_write(f, sample_rate, audio_int16)
            temp_path = f.name

        try:
            segments, info = self.model.transcribe(
                temp_path,
                language=self.language,
                beam_size=5,
                vad_filter=True,
                vad_parameters=dict(
                    min_silence_duration_ms=500,
                    speech_pad_ms=300,
                ),
            )
            text = " ".join(seg.text.strip() for seg in segments).strip()
            return text
        finally:
            os.unlink(temp_path)
