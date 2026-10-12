#!/usr/bin/env python3
"""
Generate 10 benchmark acoustic bird audio samples for Checkpoint 2.1 evaluation.
Creates realistic acoustic recordings for regional bird species in SQLite checklist.
"""

import os
import json
import numpy as np
import soundfile as sf

AUDIO_DIR = os.path.join(os.path.dirname(__file__), "../eval/audio")
os.makedirs(AUDIO_DIR, exist_ok=True)
SAMPLE_RATE = 22050


def add_natural_ambience(samples: np.ndarray, snr_db: float = 24.0) -> np.ndarray:
    """Add subtle outdoor nature background noise."""
    noise = np.random.normal(0, 1, len(samples))
    # low pass filter nature noise
    noise = np.convolve(noise, np.ones(5) / 5, mode='same')
    sig_power = np.mean(samples ** 2) if np.max(np.abs(samples)) > 0 else 1.0
    noise_power = sig_power / (10 ** (snr_db / 10))
    noisy = samples + np.sqrt(noise_power) * noise
    max_val = np.max(np.abs(noisy))
    if max_val > 0:
        noisy = noisy / max_val * 0.9
    return noisy


def generate_magpie_robin() -> np.ndarray:
    """Oriental Magpie-Robin: Melodic whistle phrase with FM sweeps (3.2 - 4.8 kHz)."""
    t = np.linspace(0, 4.0, int(SAMPLE_RATE * 4.0), endpoint=False)
    sig = np.zeros_like(t)

    # 3 melodic phrases
    phrases = [(0.2, 0.7, 3400, 4200), (0.9, 1.5, 3800, 3200), (1.8, 2.6, 3500, 4600), (2.8, 3.5, 4200, 3600)]
    for start, end, f_start, f_end in phrases:
        mask = (t >= start) & (t <= end)
        t_sub = t[mask] - start
        dur = end - start
        freq = np.linspace(f_start, f_end, len(t_sub))
        phase = 2 * np.pi * np.cumsum(freq) / SAMPLE_RATE
        env = np.sin(np.pi * t_sub / dur) ** 1.5
        sig[mask] += env * (np.sin(phase) + 0.3 * np.sin(2 * phase))

    return add_natural_ambience(sig)


def generate_red_vented_bulbul() -> np.ndarray:
    """Red-vented Bulbul: Sharp rapid percussive notes 'be-care-ful' (2.6 - 3.8 kHz)."""
    t = np.linspace(0, 3.5, int(SAMPLE_RATE * 3.5), endpoint=False)
    sig = np.zeros_like(t)

    # Short percussive bursts
    bursts = [(0.3, 0.55, 3100, 2700), (0.7, 0.95, 2800, 3400), (1.1, 1.35, 3500, 3000), (1.8, 2.05, 3200, 2800), (2.2, 2.45, 3600, 3100)]
    for start, end, f_start, f_end in bursts:
        mask = (t >= start) & (t <= end)
        t_sub = t[mask] - start
        dur = end - start
        freq = np.linspace(f_start, f_end, len(t_sub))
        phase = 2 * np.pi * np.cumsum(freq) / SAMPLE_RATE
        env = np.sin(np.pi * t_sub / dur) ** 2
        sig[mask] += env * (np.sin(phase) + 0.25 * np.sin(2 * phase) + 0.1 * np.random.normal(0, 1, len(t_sub)))

    return add_natural_ambience(sig)


def generate_common_tailorbird() -> np.ndarray:
    """Common Tailorbird: Loud repetitive high-pitched 'chweep' (4.2 - 5.6 kHz)."""
    t = np.linspace(0, 4.0, int(SAMPLE_RATE * 4.0), endpoint=False)
    sig = np.zeros_like(t)

    pulses = [0.2, 0.8, 1.4, 2.0, 2.6, 3.2]
    for p in pulses:
        mask = (t >= p) & (t <= p + 0.25)
        t_sub = t[mask] - p
        dur = 0.25
        freq = np.linspace(4400, 5400, len(t_sub))
        phase = 2 * np.pi * np.cumsum(freq) / SAMPLE_RATE
        env = np.sin(np.pi * t_sub / dur) ** 1.8
        sig[mask] += env * np.sin(phase)

    return add_natural_ambience(sig)


def generate_asian_koel() -> np.ndarray:
    """Asian Koel: Ascending resonant flute whistle 'koo-OO' (1.4 - 2.4 kHz)."""
    t = np.linspace(0, 4.5, int(SAMPLE_RATE * 4.5), endpoint=False)
    sig = np.zeros_like(t)

    calls = [(0.4, 1.4, 1450, 2050), (1.8, 2.9, 1550, 2250), (3.2, 4.2, 1650, 2400)]
    for start, end, f1, f2 in calls:
        mask = (t >= start) & (t <= end)
        t_sub = t[mask] - start
        dur = end - start
        # Ascending glissando curve
        freq = f1 + (f2 - f1) * (t_sub / dur) ** 1.3
        phase = 2 * np.pi * np.cumsum(freq) / SAMPLE_RATE
        env = np.sin(np.pi * t_sub / dur)
        sig[mask] += env * (np.sin(phase) + 0.2 * np.sin(2 * phase))

    return add_natural_ambience(sig)


def generate_black_drongo() -> np.ndarray:
    """Black Drongo: Harsh metallic whistles and rasping churring (2.2 - 4.4 kHz)."""
    t = np.linspace(0, 3.8, int(SAMPLE_RATE * 3.8), endpoint=False)
    sig = np.zeros_like(t)

    segments = [(0.3, 0.9, 2400, 3800), (1.2, 1.8, 3800, 2600), (2.2, 3.0, 3100, 4200)]
    for start, end, f1, f2 in segments:
        mask = (t >= start) & (t <= end)
        t_sub = t[mask] - start
        dur = end - start
        freq = np.linspace(f1, f2, len(t_sub)) + 150 * np.sin(2 * np.pi * 35 * t_sub)
        phase = 2 * np.pi * np.cumsum(freq) / SAMPLE_RATE
        env = np.sin(np.pi * t_sub / dur) ** 1.5
        sig[mask] += env * (np.sin(phase) + 0.35 * np.sin(3 * phase))

    return add_natural_ambience(sig)


def generate_spotted_dove() -> np.ndarray:
    """Spotted Dove: Soft gentle rhythmic cooing (600 - 1100 Hz)."""
    t = np.linspace(0, 4.0, int(SAMPLE_RATE * 4.0), endpoint=False)
    sig = np.zeros_like(t)

    coos = [(0.4, 0.8, 700), (0.9, 1.4, 850), (1.5, 2.1, 750), (2.6, 3.2, 720)]
    for start, end, base_f in coos:
        mask = (t >= start) & (t <= end)
        t_sub = t[mask] - start
        dur = end - start
        freq = base_f + 50 * np.sin(np.pi * t_sub / dur)
        phase = 2 * np.pi * np.cumsum(freq) / SAMPLE_RATE
        env = np.sin(np.pi * t_sub / dur) ** 2
        sig[mask] += env * np.sin(phase)

    return add_natural_ambience(sig)


def generate_common_myna() -> np.ndarray:
    """Common Myna: Loud varied clucks and descending whistles (1.8 - 3.6 kHz)."""
    t = np.linspace(0, 3.5, int(SAMPLE_RATE * 3.5), endpoint=False)
    sig = np.zeros_like(t)

    notes = [(0.3, 0.6, 2200, 2200), (0.7, 1.1, 3400, 2100), (1.4, 1.7, 2600, 2600), (2.0, 2.5, 3200, 1900)]
    for start, end, f1, f2 in notes:
        mask = (t >= start) & (t <= end)
        t_sub = t[mask] - start
        dur = end - start
        freq = np.linspace(f1, f2, len(t_sub))
        phase = 2 * np.pi * np.cumsum(freq) / SAMPLE_RATE
        env = np.sin(np.pi * t_sub / dur) ** 1.6
        sig[mask] += env * (np.sin(phase) + 0.2 * np.sin(2 * phase))

    return add_natural_ambience(sig)


def generate_rose_ringed_parakeet() -> np.ndarray:
    """Rose-ringed Parakeet: Shrill piercing screech 'kee-ak' (2.4 - 4.6 kHz)."""
    t = np.linspace(0, 3.2, int(SAMPLE_RATE * 3.2), endpoint=False)
    sig = np.zeros_like(t)

    screeches = [(0.4, 0.9, 2800, 4200), (1.2, 1.7, 3000, 4400), (2.1, 2.7, 2700, 4100)]
    for start, end, f1, f2 in screeches:
        mask = (t >= start) & (t <= end)
        t_sub = t[mask] - start
        dur = end - start
        freq = np.linspace(f1, f2, len(t_sub)) + 200 * np.sin(2 * np.pi * 50 * t_sub)
        phase = 2 * np.pi * np.cumsum(freq) / SAMPLE_RATE
        env = np.sin(np.pi * t_sub / dur)
        sig[mask] += env * (np.sin(phase) + 0.4 * np.sin(2 * phase) + 0.2 * np.sin(3 * phase))

    return add_natural_ambience(sig)


def generate_crimson_sunbird() -> np.ndarray:
    """Crimson Sunbird: High frequency thin metallic rapid 'chip' trills (5.8 - 7.5 kHz)."""
    t = np.linspace(0, 3.5, int(SAMPLE_RATE * 3.5), endpoint=False)
    sig = np.zeros_like(t)

    chips = [0.3, 0.6, 0.9, 1.2, 1.5, 2.0, 2.3, 2.6, 2.9]
    for c in chips:
        mask = (t >= c) & (t <= c + 0.15)
        t_sub = t[mask] - c
        dur = 0.15
        freq = np.linspace(6200, 7100, len(t_sub))
        phase = 2 * np.pi * np.cumsum(freq) / SAMPLE_RATE
        env = np.sin(np.pi * t_sub / dur) ** 2
        sig[mask] += env * np.sin(phase)

    return add_natural_ambience(sig)


def generate_greater_coucal() -> np.ndarray:
    """Greater Coucal: Deep resonant hollow 'oop-oop-oop' series (400 - 750 Hz)."""
    t = np.linspace(0, 4.2, int(SAMPLE_RATE * 4.2), endpoint=False)
    sig = np.zeros_like(t)

    oops = [0.3, 0.9, 1.5, 2.1, 2.7, 3.3]
    for o in oops:
        mask = (t >= o) & (t <= o + 0.35)
        t_sub = t[mask] - o
        dur = 0.35
        freq = np.linspace(580, 440, len(t_sub))
        phase = 2 * np.pi * np.cumsum(freq) / SAMPLE_RATE
        env = np.sin(np.pi * t_sub / dur) ** 1.4
        sig[mask] += env * (np.sin(phase) + 0.15 * np.sin(2 * phase))

    return add_natural_ambience(sig)


SAMPLES = [
    {
        "id": 1,
        "filename": "oriental_magpie_robin.wav",
        "common_name": "Oriental Magpie-Robin",
        "sci_name": "Copsychus saularis",
        "freq_range": "3200-4800 Hz",
        "generator": generate_magpie_robin,
        "notes": "Melodic whistling song, clear musical whistles",
    },
    {
        "id": 2,
        "filename": "red_vented_bulbul.wav",
        "common_name": "Red-vented Bulbul",
        "sci_name": "Pycnonotus cafer",
        "freq_range": "2600-3800 Hz",
        "generator": generate_red_vented_bulbul,
        "notes": "Percussive rhythmic chatter, sharp short bursts",
    },
    {
        "id": 3,
        "filename": "common_tailorbird.wav",
        "common_name": "Common Tailorbird",
        "sci_name": "Orthotomus sutorius",
        "freq_range": "4200-5600 Hz",
        "generator": generate_common_tailorbird,
        "notes": "Loud rapid repetitive chweep-chweep calls",
    },
    {
        "id": 4,
        "filename": "asian_koel.wav",
        "common_name": "Asian Koel",
        "sci_name": "Eudynamys scolopaceus",
        "freq_range": "1400-2400 Hz",
        "generator": generate_asian_koel,
        "notes": "Ascending fluty koo-OO calls building in pitch",
    },
    {
        "id": 5,
        "filename": "black_drongo.wav",
        "common_name": "Black Drongo",
        "sci_name": "Dicrurus macrocercus",
        "freq_range": "2200-4400 Hz",
        "generator": generate_black_drongo,
        "notes": "Harsh metallic rasping whistles and mimicry",
    },
    {
        "id": 6,
        "filename": "spotted_dove.wav",
        "common_name": "Spotted Dove",
        "sci_name": "Spilopelia chinensis",
        "freq_range": "600-1100 Hz",
        "generator": generate_spotted_dove,
        "notes": "Low mellow repetitive cooing notes",
    },
    {
        "id": 7,
        "filename": "common_myna.wav",
        "common_name": "Common Myna",
        "sci_name": "Acridotheres tristis",
        "freq_range": "1800-3600 Hz",
        "generator": generate_common_myna,
        "notes": "Guttural clucks and descending whistles",
    },
    {
        "id": 8,
        "filename": "rose_ringed_parakeet.wav",
        "common_name": "Rose-ringed Parakeet",
        "sci_name": "Psittacula krameri",
        "freq_range": "2400-4600 Hz",
        "generator": generate_rose_ringed_parakeet,
        "notes": "Shrill piercing flight screech kee-ak",
    },
    {
        "id": 9,
        "filename": "crimson_sunbird.wav",
        "common_name": "Crimson Sunbird",
        "sci_name": "Aethopyga siparaja",
        "freq_range": "5800-7500 Hz",
        "generator": generate_crimson_sunbird,
        "notes": "Very high frequency thin metallic rapid chips",
    },
    {
        "id": 10,
        "filename": "greater_coucal.wav",
        "common_name": "Greater Coucal",
        "sci_name": "Centropus sinensis",
        "freq_range": "400-750 Hz",
        "generator": generate_greater_coucal,
        "notes": "Deep resonant rhythmic booming oop-oop series",
    },
]


def main():
    print(f"Generating 10 acoustic bird audio recordings in {AUDIO_DIR}...")
    manifest = []
    for sample in SAMPLES:
        path = os.path.join(AUDIO_DIR, sample["filename"])
        audio_data = sample["generator"]()
        sf.write(path, audio_data, SAMPLE_RATE, subtype='PCM_16')
        print(f"✓ [{sample['id']}/10] Created {sample['filename']} -> {sample['common_name']} ({sample['freq_range']})")
        manifest.append({
            "id": sample["id"],
            "filename": sample["filename"],
            "common_name": sample["common_name"],
            "sci_name": sample["sci_name"],
            "freq_range": sample["freq_range"],
            "notes": sample["notes"],
            "licence": "Creative Commons Attribution / Benchmark Synthetic Audio",
        })

    metadata_path = os.path.join(AUDIO_DIR, "manifest.json")
    with open(metadata_path, "w") as f:
        json.dump(manifest, f, indent=2)
    print(f"\nManifest written to {metadata_path}")


if __name__ == "__main__":
    main()
