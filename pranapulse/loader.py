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
    # Context only (issue #95): shown beside the findings, never used by detect().
    encounters: pd.DataFrame = field(default_factory=lambda: pd.DataFrame(columns=["date", "encounter", "note"]))
    adherence: pd.DataFrame = field(default_factory=lambda: pd.DataFrame(columns=["month", "medication", "adherence", "missed", "source"]))

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

    p = Patient(str(profile.get("Patient ID", "unknown")), profile, daily, labs, history, meds, cycles)
    p.encounters, p.adherence = read_context(sheets, mm)
    return p


def read_context(sheets, med_rows):
    """Clinical notes and medication adherence, if the workbook has those sheets. Missing sheet or column gives an empty table."""
    enc = sheets.get("Encounters & Notes")
    if enc is not None and {"Date", "Encounter", "Clinical Note"} <= set(enc.columns):
        encounters = pd.DataFrame({"date": to_dates(enc["Date"]), "encounter": enc["Encounter"], "note": enc["Clinical Note"]}).sort_values("date")
    else:
        encounters = pd.DataFrame(columns=["date", "encounter", "note"])
    ad = sheets.get("Medication Adherence")
    if ad is not None and {"Month", "Medication ID", "Estimated Adherence %"} <= set(ad.columns):
        names = dict(zip(med_rows["Medication ID"], med_rows["Medication"])) if "Medication ID" in med_rows else {}
        adherence = pd.DataFrame({
            "month": to_dates(ad["Month"]), "medication": [names.get(i, str(i)) for i in ad["Medication ID"]],
            "adherence": pd.to_numeric(ad["Estimated Adherence %"], errors="coerce"),
            "missed": pd.to_numeric(ad.get("Approx Missed Doses"), errors="coerce"), "source": ad.get("Source"),
        }).sort_values(["month", "medication"])
    else:
        adherence = pd.DataFrame(columns=["month", "medication", "adherence", "missed", "source"])
    return encounters, adherence
