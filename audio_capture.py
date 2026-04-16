"""Captura de áudio do sistema via WASAPI loopback (Windows) usando PyAudioWPatch."""

import pyaudiowpatch as pyaudio
import numpy as np
from scipy.io.wavfile import write as wav_write
from scipy.signal import resample_poly
import io
import threading
import time
import wave

import torch
from silero_vad import load_silero_vad

VAD_SAMPLE_RATE = 16000
VAD_WINDOW_SIZE = 512  # samples @ 16kHz


class AudioCapture:
    def __init__(self, silence_threshold=0.5, silence_duration=0.6, min_audio_duration=1.5):
        self.silence_threshold = silence_threshold
        self.silence_duration = silence_duration
        self.min_audio_duration = min_audio_duration
        self.sample_rate = None
        self.channels = None
        self.device_info = None
        self._running = False
        self._pa = pyaudio.PyAudio()
        self._setup_loopback()
        print("  Carregando Silero VAD...")
        self._vad_model = load_silero_vad()
        self._vad_model.eval()

    def _setup_loopback(self):
        """Encontra o dispositivo de loopback WASAPI."""
        try:
            wasapi_info = self._pa.get_host_api_info_by_type(pyaudio.paWASAPI)
        except OSError:
            raise RuntimeError("WASAPI não encontrado. Este programa requer Windows com WASAPI.")

        # Pega o dispositivo de saída padrão
        default_output_idx = wasapi_info["defaultOutputDevice"]
        default_output = self._pa.get_device_info_by_index(default_output_idx)

        # Procura o loopback correspondente
        self.device_info = None
        for i in range(self._pa.get_device_count()):
            dev = self._pa.get_device_info_by_index(i)
            if dev.get("isLoopbackDevice") and dev["name"].startswith(default_output["name"]):
                self.device_info = dev
                break

        if self.device_info is None:
            # Fallback: usa o próprio dispositivo de saída padrão
            self.device_info = default_output

        self.sample_rate = int(self.device_info["defaultSampleRate"])
        self.channels = self.device_info["maxInputChannels"]
        if self.channels == 0:
            self.channels = self.device_info["maxOutputChannels"]
        self.channels = max(self.channels, 1)

        print(f"  Dispositivo: {self.device_info['name']}")
        print(f"  Canais: {self.channels}")
        print(f"  Sample rate: {self.sample_rate} Hz")
        print(f"  Loopback: {self.device_info.get('isLoopbackDevice', False)}")

    def _detect_speech(self, audio_float):
        """Retorna a probabilidade máxima de fala em um chunk, via Silero VAD.

        Reamostra para 16kHz e avalia em janelas de 512 samples.
        """
        if self.sample_rate != VAD_SAMPLE_RATE:
            # resample_poly precisa de inteiros para up/down
            audio_16k = resample_poly(audio_float, VAD_SAMPLE_RATE, self.sample_rate)
            audio_16k = audio_16k.astype(np.float32)
        else:
            audio_16k = audio_float.astype(np.float32)

        max_prob = 0.0
        n_windows = len(audio_16k) // VAD_WINDOW_SIZE
        if n_windows == 0:
            return 0.0

        with torch.no_grad():
            for i in range(n_windows):
                start = i * VAD_WINDOW_SIZE
                window = audio_16k[start:start + VAD_WINDOW_SIZE]
                tensor = torch.from_numpy(window)
                prob = self._vad_model(tensor, VAD_SAMPLE_RATE).item()
                if prob > max_prob:
                    max_prob = prob
        return max_prob

    def capture_until_silence(self, on_audio_ready):
        """Captura áudio continuamente e envia chunks quando detecta silêncio após fala."""
        self._running = True
        buffer = []
        silence_start = None
        has_speech = False
        chunk_size = int(self.sample_rate * 0.5)  # 500ms chunks

        stream = self._pa.open(
            format=pyaudio.paInt16,
            channels=self.channels,
            rate=self.sample_rate,
            input=True,
            input_device_index=self.device_info["index"],
            frames_per_buffer=chunk_size,
        )

        try:
            while self._running:
                try:
                    data = stream.read(chunk_size, exception_on_overflow=False)
                except OSError:
                    continue

                # Converter bytes para numpy float
                audio_int16 = np.frombuffer(data, dtype=np.int16)
                # Se stereo, pegar só canal esquerdo
                if self.channels > 1:
                    audio_int16 = audio_int16[::self.channels]
                audio_float = audio_int16.astype(np.float32) / 32768.0

                speech_prob = self._detect_speech(audio_float)

                if speech_prob > self.silence_threshold:
                    has_speech = True
                    silence_start = None
                    buffer.append(audio_float)
                else:
                    buffer.append(audio_float)
                    if has_speech and silence_start is None:
                        silence_start = time.time()
                    elif has_speech and silence_start and (time.time() - silence_start) >= self.silence_duration:
                        audio_data = np.concatenate(buffer)
                        duration = len(audio_data) / self.sample_rate

                        if duration >= self.min_audio_duration:
                            threading.Thread(
                                target=on_audio_ready,
                                args=(audio_data, self.sample_rate),
                                daemon=True
                            ).start()

                        buffer.clear()
                        silence_start = None
                        has_speech = False
        finally:
            stream.stop_stream()
            stream.close()

    def stop(self):
        self._running = False

    def __del__(self):
        self._pa.terminate()
