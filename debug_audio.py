"""Diagnóstico de dispositivos de áudio."""
import sounddevice as sd

print("=== Host APIs ===")
for i, api in enumerate(sd.query_hostapis()):
    print(f"  [{i}] {api['name']} (default_input={api['default_input_device']}, default_output={api['default_output_device']})")

print("\n=== Dispositivos ===")
for i, dev in enumerate(sd.query_devices()):
    print(f"  [{i}] {dev['name']}")
    print(f"      hostapi={dev['hostapi']} in_ch={dev['max_input_channels']} out_ch={dev['max_output_channels']} sr={dev['default_samplerate']}")
