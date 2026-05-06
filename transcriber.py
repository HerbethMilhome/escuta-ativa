"""Transcrição de áudio usando faster-whisper (local, sem API)."""

import os
import sys

# Python 3.8+ no Windows ignora PATH para DLLs de extensoes — usa add_dll_directory
import importlib
for _pkg in ("nvidia.cudnn", "nvidia.cublas", "nvidia.cuda_runtime"):
    try:
        _mod = importlib.import_module(_pkg)
        if _mod.__file__:
            _bin = os.path.join(os.path.dirname(_mod.__file__), "bin")
            if os.path.isdir(_bin):
                os.add_dll_directory(_bin)
    except Exception:
        pass

from faster_whisper import WhisperModel
import numpy as np
import tempfile
from scipy.io.wavfile import write as wav_write


class Transcriber:
    def __init__(self, model_size="base", language=None):
        self.language = language  # None = deteccao automatica pelo Whisper
        print(f"  Carregando modelo Whisper '{model_size}'...")
        self.model = WhisperModel(
            model_size,
            device="cpu",
            compute_type="int8",
        )
        print("  Modelo carregado.")

    def transcribe(self, audio_data, sample_rate):
        """Transcreve áudio (numpy array) para texto."""
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            audio_int16 = np.int16(audio_data * 32767)
            wav_write(f, sample_rate, audio_int16)
            temp_path = f.name

        try:
            segments, info = self.model.transcribe(
                temp_path,
                language=self.language,
                beam_size=1,
                vad_filter=True,
                vad_parameters=dict(
                    min_silence_duration_ms=500,
                    speech_pad_ms=300,
                ),
            )
            text = " ".join(seg.text.strip() for seg in segments).strip()
            return text, info.language
        finally:
            os.unlink(temp_path)
