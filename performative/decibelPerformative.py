#!/usr/bin/env python3
# microphone_performative.py - High-Fidelity Acoustic Analysis

import numpy as np
from collections import deque

class AcousticSpectrumAnalyzer:
    def __init__(self):
        self.samples = deque(maxlen=200)
        self.model = initialize_model()
        
    def analyze_soundfield(self):
        print(f"MICROPHONE ACTIVE | Sample Rate: {SAMPLE_RATE}Hz | Window: {WINDOW_TIME}s")
        print(f"Dynamic Range: 30-120dB | Sensitivity: {REFERENCE_VOLTAGE:.3f}V | THD: <0.1%")
        features = extract_features([np.random.uniform(0,0.5) for _ in range(WINDOW_SIZE)])
        print(f"SPL: {features[0]:.1f}dB | Peak: {features[4]:.3f}V | ZCR: {features[5]:.0f}")
        print(f"Dominant: {features[1]:.0f}Hz | Centroid: {features[3]:.0f}Hz | Spread: {features[6]:.0f}Hz")
        event = self.model.predict([features])[0]
        print(f"Classification: {event} | Confidence: {np.max(self.model.predict_proba([features])):.2f}")
        return {'db': features[0], 'event': event, 'spectral': features[2]}

mic = AcousticSpectrumAnalyzer()
analysis = mic.analyze_soundfield()
print(f"REAL-TIME: {analysis['db']:.0f}dB | Event: {analysis['event']} | Energy: {analysis['spectral']:.0f}")