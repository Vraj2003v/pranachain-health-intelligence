"""Detect meaningful changes against each patient's own baseline and link them to clinical history."""
from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from scipy import stats

from . import forecast
from .explain import check_language
from .loader import Patient
from .signals import CLUSTERS, MAX_TREND_P, MIN_EFFECT, SIGNALS, WINDOW_DAYS

RANK = {"Sufficient": 2, "Limited": 1, "Insufficient": 0}


@dataclass
class SignalResult:
    key: str
    label: str
    unit: str
    sheet: str
    coverage: float
    n_first: int
    n_last: int
    mean_first: float
    mean_last: float
    diff: float
    effect: float
    trend_p: float
    direction: str     # worsening | improving | stable
    flag: str          # Sufficient | Limited | Insufficient
    decimals: int
    window_first: tuple
    window_last: tuple


@dataclass
class Insight:
    kind: str                  # pattern | single | cycle
    title: str
    flag: str
    signals: list
    evidence: list
    context: list
    narrative: str
    asks: list = field(default_factory=list)
    forecast_key: str = ""
    summary: str = ""
    bullets: list = field(default_factory=list)
    closing: str = ""
    scenario: str = ""         # which validation scenario this belongs to


def _fmt(v, d):
    return f"{v:,.{d}f}"


def _flag(coverage, n_first, n_last):
    if coverage >= 0.85 and min(n_first, n_last) >= 72:
        return "Sufficient"
    if coverage >= 0.60 and min(n_first, n_last) >= 45:
        return "Limited"
    return "Insufficient"


def analyse_signal(p: Patient, key: str):
    sig = SIGNALS[key]
    if sig.column not in p.daily:
        return None
    s = p.daily[sig.column]
    start, end = p.window
    w = pd.Timedelta(days=WINDOW_DAYS)
    first, last = s[: start + w], s[end - w:]
    n_first, n_last = int(first.notna().sum()), int(last.notna().sum())
    coverage = float(s.notna().sum() / max(len(s), 1))
    if n_first < 10 or n_last < 10:
        return SignalResult(key, sig.label, sig.unit, sig.sheet, coverage, n_first, n_last, np.nan, np.nan,
                            np.nan, np.nan, np.nan, "stable", "Insufficient", sig.decimals,
                            (start, start + w), (end - w, end))
    mf, ml = float(first.mean()), float(last.mean())
    sd = float(np.sqrt((first.var() + last.var()) / 2)) or np.nan
    diff = ml - mf
    effect = diff / sd if sd == sd else 0.0
    wk = forecast.weekly_means(s)
    p_val = stats.kendalltau(np.arange(len(wk)), wk.values)[1] if len(wk) >= 12 else 1.0
    meaningful = abs(diff) >= sig.min_abs and abs(effect) >= MIN_EFFECT and p_val <= MAX_TREND_P
    direction = "stable"
    if meaningful:
        direction = "worsening" if np.sign(diff) == sig.bad else "improving"
    return SignalResult(key, sig.label, sig.unit, sig.sheet, coverage, n_first, n_last, mf, ml, diff, effect,
                        float(p_val), direction, _flag(coverage, n_first, n_last), sig.decimals,
                        (start, start + w), (end - w, end))


def analyse_lab(p: Patient, test: str, bad: int, min_abs: float):
    rows = p.labs[p.labs.test == test]
    if len(rows) < 2:
        return None
    first, last = rows.iloc[0], rows.iloc[-1]
    diff = float(last.result - first.result)
    meaningful = abs(diff) >= min_abs
    return {
        "test": test, "n": len(rows), "first": first, "last": last, "diff": diff,
        "direction": ("worsening" if np.sign(diff) == bad else "improving") if meaningful else "stable",
        "flag": "Sufficient" if len(rows) >= 3 else "Limited",
    }


def _context(p: Patient, keywords, tests):
    out = []
    for _, r in p.history.iterrows():
        if any(k in str(r.event).lower() for k in keywords):
            out.append(f"{r.event} ({r.date:%b %Y}, {r.status}) — Medical History sheet")
    for _, r in p.meds.iterrows():
        text = f"{r.medication} {r.indication}".lower()
        if any(k in text for k in keywords):
            out.append(f"{r.medication} for {str(r.indication).lower()} since {r.start:%b %Y} — Medication History sheet")
    for t in tests:
        rows = p.labs[p.labs.test == t]
        if len(rows):
            r = rows.iloc[-1]
            ref = f", reference {r.ref_low:g}–{r.ref_high:g}" if r.ref_low == r.ref_low and r.ref_high == r.ref_high else ""
            out.append(f"Latest {t}: {r.result:g} {r.unit} on {r.date:%d %b %Y}{ref} — Lab Results sheet")
    return out


def _bullet(r: SignalResult):
    d = r.decimals
    verb = "rose" if r.diff > 0 else "fell"
    return (f"{r.label} {verb} from {_fmt(r.mean_first, d)} to {_fmt(r.mean_last, d)} {r.unit} "
            f"({r.diff:+,.{d}f}) between the first and last {WINDOW_DAYS} days, well outside this patient's usual day-to-day variation")


def _evidence(r: SignalResult):
    return {
        "signal": r.label, "source": f"{r.sheet}",
        "first_window": f"{r.window_first[0]:%d %b %Y} – {r.window_first[1]:%d %b %Y}",
        "last_window": f"{r.window_last[0]:%d %b %Y} – {r.window_last[1]:%d %b %Y}",
        "first_mean": f"{_fmt(r.mean_first, r.decimals)} {r.unit}", "last_mean": f"{_fmt(r.mean_last, r.decimals)} {r.unit}",
        "days_with_data": f"{r.n_first} of {WINDOW_DAYS} (first), {r.n_last} of {WINDOW_DAYS} (last)",
        "overall_coverage": f"{r.coverage:.0%}",
        "size_vs_own_variation": f"{abs(r.effect):.1f}x", "trend_p": f"{r.trend_p:.4f}",
    }


def _projection_sentence(p: Patient, r: SignalResult):
    proj = forecast.project(p.daily[SIGNALS[r.key].column])
    if proj is None:
        return ""
    end = proj.iloc[-1]
    d = r.decimals
    return (f" If the recent trend simply continued, {r.label.lower()} could reach about {_fmt(end['mean'], d)} {r.unit} "
            f"in {len(proj)} weeks (range {_fmt(end['low'], d)}–{_fmt(end['high'], d)}); this is a straight-line projection, "
            f"not a prediction of health outcomes.")


def _asks(p: Patient, results, tests, lab_hits=()):
    asks = []
    for l in lab_hits:
        if l["n"] < 3:
            asks.append(f"{l['test']}: only {l['n']} results in the year — more results would strengthen this.")
    for r in results:
        if r.flag != "Sufficient":
            asks.append(f"{r.label}: only {r.coverage:.0%} of days have data — more complete {r.sheet.split()[0].lower()} data would strengthen this.")
    for t in tests:
        rows = p.labs[p.labs.test == t]
        if len(rows) and (p.window[1] - rows.date.max()).days > 120:
            asks.append(f"A repeat {t} result — the latest is from {rows.date.max():%d %b %Y}.")
    return asks


SCENARIO = {"metabolic": "Metabolic health", "cardio": "Cardiovascular / hypertension", "cycle": "Women's health (PCOS)"}


def _join(items):
    items = list(items)
    return items[0] if len(items) == 1 else ", ".join(items[:-1]) + " and " + items[-1]


def detect(p: Patient):
    """Return (insights to show, list of notes about what was held back and why)."""
    results = {k: analyse_signal(p, k) for k in SIGNALS}
    results = {k: v for k, v in results.items() if v is not None}
    held, insights, used = [], [], set()

    for cname, c in CLUSTERS.items():
        sig_hits = [results[k] for k in c["signals"] if k in results and results[k].direction == "worsening"]
        lab_hits = []
        for test, (bad, min_abs) in c["labs"].items():
            lr = analyse_lab(p, test, bad, min_abs)
            if lr and lr["direction"] == "worsening":
                lab_hits.append(lr)
        usable = [r for r in sig_hits if r.flag != "Insufficient"]
        for r in sig_hits:
            if r.flag == "Insufficient":
                msg = f"{r.label}: change seen but too few days with data to report it."
                if msg not in held:
                    held.append(msg)
        if len(usable) + len(lab_hits) < 2:
            continue
        flags = [r.flag for r in usable] + [l["flag"] for l in lab_hits]
        flag = min(flags, key=lambda f: RANK[f])
        bullets = [_bullet(r) for r in usable]
        for l in lab_hits:
            bullets.append(f"{l['test']} moved from {l['first'].result:g} to {l['last'].result:g} {l['last'].unit} "
                           f"across {l['n']} results ({l['diff']:+g})")
        ctx = _context(p, c["context"], list(c["labs"]))
        names = ", ".join([r.label.lower() for r in usable] + [l["test"] for l in lab_hits])
        names_list = [r.label for r in usable] + [l["test"] for l in lab_hits]
        text = (f"{len(bullets)} related measures moved in the same direction over this patient's year. "
                + "; ".join(bullets) + ". "
                + ("This sits alongside history in the record: " + "; ".join(x.split(" — ")[0] for x in ctx[:3]) + ". " if ctx else "")
                + "This pattern may be worth discussing with a healthcare provider."
                + (_projection_sentence(p, usable[0]) if usable else ""))
        assert not check_language(text), check_language(text)
        closing = "This pattern may be worth discussing with a healthcare provider." + (_projection_sentence(p, usable[0]) if usable else "")
        insights.append(Insight("pattern", f"{_join(names_list)} {'is' if len(names_list) == 1 else 'are'} shifting together", flag, [r.key for r in usable],
                                [_evidence(r) for r in usable] + [
                                    {"signal": l["test"], "source": "Lab Results",
                                     "first_window": f"{l['first'].date:%d %b %Y}", "last_window": f"{l['last'].date:%d %b %Y}",
                                     "first_mean": f"{l['first'].result:g} {l['first'].unit}", "last_mean": f"{l['last'].result:g} {l['last'].unit}",
                                     "days_with_data": f"{l['n']} results", "overall_coverage": "—",
                                     "size_vs_own_variation": "—", "trend_p": "—"} for l in lab_hits],
                                ctx, text, _asks(p, usable, list(c["labs"]), lab_hits), usable[0].key if usable else "",
                                f"{len(bullets)} related measures moved in the same direction over this patient's year.", bullets, closing,
                                SCENARIO[cname]))
        used.update(r.key for r in usable)

    for r in results.values():
        if r.direction == "worsening" and r.key not in used:
            if r.flag == "Insufficient":
                msg = f"{r.label}: change seen but too few days with data to report it."
                if msg not in held:
                    held.append(msg)
                continue
            text = (_bullet(r) + ". This change may be worth mentioning to a healthcare provider."
                    + _projection_sentence(p, r))
            assert not check_language(text), check_language(text)
            insights.append(Insight("single", f"{r.label} has changed", r.flag, [r.key], [_evidence(r)], [], text,
                                    _asks(p, [r], []), r.key, "One measure moved well outside this patient's usual variation.",
                                    [_bullet(r)], "This change may be worth mentioning to a healthcare provider." + _projection_sentence(p, r)))

    # cycle pattern (women's health scenario)
    cy = p.cycles
    if len(cy) >= 4:
        mean_len, sd_len = cy.cycle_length.mean(), cy.cycle_length.std()
        if sd_len >= 4 or mean_len > 35 or mean_len < 21:
            flag = "Sufficient" if len(cy) >= 8 else "Limited"
            ctx = _context(p, ["pcos", "polycystic", "thyroid", "cycle"], ["TSH"])
            text = (f"Cycle length averaged {mean_len:.0f} days across {len(cy)} cycles and varied by about {sd_len:.0f} days "
                    f"from one cycle to the next, which is outside the usual range of roughly 21–35 days with small variation. "
                    + ("History in the record: " + "; ".join(x.split(" — ")[0] for x in ctx[:2]) + ". " if ctx else "")
                    + "This pattern may be worth discussing with a healthcare provider.")
            assert not check_language(text), check_language(text)
            insights.append(Insight("cycle", "Cycle timing is irregular", flag, [], [{
                "signal": "Cycle length", "source": "Women Health", "first_window": f"{cy.start.min():%d %b %Y}",
                "last_window": f"{cy.start.max():%d %b %Y}", "first_mean": f"{mean_len:.0f} days (mean)",
                "last_mean": f"{sd_len:.1f} days (variation)", "days_with_data": f"{len(cy)} cycles",
                "overall_coverage": "—", "size_vs_own_variation": "—", "trend_p": "—"}], ctx, text, [], "",
                                "Cycle timing varies more than usual.",
                                [f"Cycle length averaged {mean_len:.0f} days across {len(cy)} cycles and varied by about {sd_len:.0f} days between cycles "
                                 "(usual range is roughly 21–35 days with small variation)"],
                                "This pattern may be worth discussing with a healthcare provider."))

    order = {"pattern": 0, "cycle": 1, "single": 2}
    insights.sort(key=lambda i: (order[i.kind], -RANK[i.flag]))
    for ins in insights:
        if not ins.scenario:
            if ins.kind == "cycle":
                ins.scenario = SCENARIO["cycle"]
            else:
                ins.scenario = SCENARIO["cardio"] if ins.signals and ins.signals[0] in ("sbp", "dbp", "rhr", "hrv") else SCENARIO["metabolic"]
    return insights, held, results
