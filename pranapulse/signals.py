"""Signal definitions and detection thresholds.

THRESHOLDS ARE PLACEHOLDERS pending calibration on real patients (Issue #7 follow-up).
Changing a number here changes what the detector reports; note the data behind any change.
"""
from dataclasses import dataclass

WINDOW_DAYS = 90          # compare the first and last 90 days of the data window
MIN_EFFECT = 0.8          # change must exceed 0.8 x the patient's own daily variation
MAX_TREND_P = 0.01        # and show a consistent weekly trend (Kendall tau p-value)
FORECAST_WEEKS = 8


@dataclass(frozen=True)
class Signal:
    key: str
    label: str
    unit: str
    sheet: str
    column: str
    bad: int            # +1: a rise is the concerning direction, -1: a fall is
    min_abs: float      # smallest absolute change worth reporting
    decimals: int = 1


SIGNALS = {
    "weight": Signal("weight", "Weight", "kg", "Vitals Daily", "Weight kg", +1, 1.5, 1),
    "sbp": Signal("sbp", "Systolic BP", "mmHg", "Vitals Daily", "Systolic BP", +1, 4.0, 0),
    "dbp": Signal("dbp", "Diastolic BP", "mmHg", "Vitals Daily", "Diastolic BP", +1, 3.0, 0),
    "rhr": Signal("rhr", "Resting heart rate", "bpm", "Vitals Daily", "Resting HR", +1, 3.0, 0),
    "steps": Signal("steps", "Daily steps", "steps", "Wearable Daily", "Steps", -1, 600.0, 0),
    "sleep": Signal("sleep", "Sleep", "h", "Wearable Daily", "Sleep Hours", -1, 0.3, 1),
    "hrv": Signal("hrv", "HRV", "ms", "Wearable Daily", "HRV ms", -1, 3.0, 0),
}

# Groups of signals that are read together, and the history keywords that give them context.
CLUSTERS = {
    "metabolic": {
        "label": "Weight, activity and sleep",
        "signals": ["weight", "steps", "sleep"],
        "labs": {"HbA1c": (+1, 0.3), "Fasting glucose": (+1, 10.0)},
        "context": ["glyc", "diabet", "prediab", "lipid", "cholesterol", "metformin", "atorva", "obes"],
    },
    "cardio": {
        "label": "Blood pressure, heart rate and recovery",
        "signals": ["sbp", "dbp", "rhr", "hrv", "steps"],
        "labs": {"LDL cholesterol": (+1, 15.0)},
        "context": ["hypertens", "blood pressure", "amlodipine", "lipid", "cardio", "statin"],
    },
}
