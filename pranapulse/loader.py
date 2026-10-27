"""Read one patient workbook into tidy tables. Handles the three date formats in the dataset."""
import re
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

EXCEL_EPOCH = pd.Timestamp("1899-12-30")


def to_dates(series: pd.Series) -> pd.Series:
    """Excel serial numbers, real datetimes and text dates all become datetimes."""
    if pd.api.types.is_datetime64_any_dtype(series):
        return pd.to_datetime(series)
    if pd.api.types.is_numeric_dtype(series):
        return EXCEL_EPOCH + pd.to_timedelta(series.astype(float), unit="D")
    return pd.to_datetime(series, errors="coerce")


def parse_range(text):
    """'70–99' -> (70, 99); '<100' -> (None, 100); anything else -> (None, None)."""
    nums = [float(x) for x in re.findall(r"\d+(?:\.\d+)?", str(text))]
    if len(nums) >= 2:
        return nums[0], nums[1]
    if len(nums) == 1 and "<" in str(text):
        return None, nums[0]
    return None, None


@dataclass
class Patient:
    patient_id: str
    profile: dict
    daily: pd.DataFrame            # one row per day; columns are the Column names in signals.py
    labs: pd.DataFrame             # date, test, result, unit, ref_low, ref_high
    history: pd.DataFrame          # date, event, status
    meds: pd.DataFrame             # medication, indication, start, end, status
    cycles: pd.DataFrame           # start, cycle_length
    notes: list = field(default_factory=list)

    @property
    def window(self):
        return self.daily.index.min(), self.daily.index.max()


def load_patient(source) -> Patient:
    sheets = pd.read_excel(source, sheet_name=None)
    profile = sheets["Patient Profile"].set_index("Field").Value.to_dict()

    vit = sheets["Vitals Daily"].copy()
    wea = sheets["Wearable Daily"].copy()
    vit["Date"], wea["Date"] = to_dates(vit["Date"]), to_dates(wea["Date"])
    daily = vit.set_index("Date").join(wea.set_index("Date"), how="outer", rsuffix="_wearable")
    if "Resting HR_wearable" in daily:  # same signal in two sheets: fall back to the wearable value
        daily["Resting HR"] = daily["Resting HR"].fillna(daily["Resting HR_wearable"])
    daily = daily.sort_index()

    labs = sheets["Lab Results"].copy()
    labs["date"] = to_dates(labs["Date"])
    rng = labs["Reference Range"].map(parse_range)
    labs = pd.DataFrame({
        "date": labs["date"], "test": labs["Test Name"], "result": labs["Result"], "unit": labs["Unit"],
        "ref_low": [r[0] for r in rng], "ref_high": [r[1] for r in rng],
    }).sort_values("date")

    mh = sheets["Medical History"]
    history = pd.DataFrame({"date": to_dates(mh["Date"]), "event": mh["Finding / Event"], "status": mh["Status"]})

    mm = sheets["Medication History"]
    meds = pd.DataFrame({
        "medication": mm["Medication"], "indication": mm["Indication"],
        "start": to_dates(mm["Start Date"]), "end": to_dates(mm["End Date"]), "status": mm["Status"],
    })

    wh = sheets["Women Health"]
    wh = wh[pd.to_numeric(wh["Cycle Length"], errors="coerce").notna()]
    cycles = pd.DataFrame({"start": to_dates(wh["Start Date"]), "cycle_length": wh["Cycle Length"].astype(float)})

    return Patient(str(profile.get("Patient ID", "unknown")), profile, daily, labs, history, meds, cycles)
