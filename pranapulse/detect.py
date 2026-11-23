"""Detect meaningful changes against each patient's own baseline and link them to clinical history."""
from dataclasses import dataclass, field

import re

import numpy as np
import pandas as pd
from scipy import stats

from . import forecast
from . import reference as ref
from .explain import check_language
from .loader import Patient
from .signals import CLUSTERS, MAX_TREND_P, MIN_EFFECT, RECENT_DAYS, RECENT_MIN_EFFECT, RECENT_PERSIST_SHARE, SIGNALS, WINDOW_DAYS

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
    onset: object = None        # the day the 14-day average crossed the change threshold and stayed across it
    onset_value: float = None   # that 14-day average on the onset day
    threshold: float = None     # the level that counts as a change (baseline plus or minus the threshold distance)


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
    insight_id: str = ""       # F1, F2, ... for this patient, in the order shown
    tier: str = ""             # where the latest readings sit against the usual range (see reference.py)
    onsets: list = field(default_factory=list)   # when each measure crossed the change threshold: [{key, label, date, ...}]
    limits: str = ""           # what this finding cannot tell (reading counts, data flag, no condition named); see limits_line


def _fmt(v, d):
    return f"{v:,.{d}f}"


def _flag(coverage, n_first, n_last):
    if coverage >= 0.85 and min(n_first, n_last) >= 72:
        return "Sufficient"
    if coverage >= 0.60 and min(n_first, n_last) >= 45:
        return "Limited"
    return "Insufficient"


ONSET_WINDOW = "14D"   # a day-to-day dip should not move the date, so the average over two weeks is used


def find_onset(s, base_mean, sd, sign, min_effect, start=None):
    """The first day the 14-day average moved min_effect x the baseline's own variation from the baseline, in the
    direction `sign`, and stayed there to the end. A short dip back (below half the distance) restarts the search,
    so noise does not give an early date. Returns (date, average on that day, threshold level) or None."""
    if not sd or sd != sd:
        return None
    roll = s.rolling(ONSET_WINDOW, min_periods=7).mean().dropna()
    if start is not None:
        roll = roll[start:]
    if roll.empty:
        return None
    dev = sign * (roll - base_mean) / sd
    if dev.iloc[-1] < min_effect:
        return None
    low = dev[dev < 0.5 * min_effect]
    after = dev[low.index[-1]:] if len(low) else dev
    hit = after[after >= min_effect]
    if hit.empty:
        return None
    d = hit.index[0]
    return d, float(roll[d]), float(base_mean + sign * min_effect * sd)


def analyse_signal(p: Patient, key: str):
    sig = SIGNALS[key]
    if sig.column not in p.daily:
        return None
    s = p.daily[sig.column]
    start, end = p.window
    w = pd.Timedelta(days=WINDOW_DAYS - 1)   # label slices are inclusive, so this gives exactly WINDOW_DAYS days
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
    on = None
    if meaningful:
        direction = "worsening" if np.sign(diff) == sig.bad else "improving"
        on = find_onset(s, mf, sd, int(np.sign(diff)), MIN_EFFECT)
    return SignalResult(key, sig.label, sig.unit, sig.sheet, coverage, n_first, n_last, mf, ml, diff, effect,
                        float(p_val), direction, _flag(coverage, n_first, n_last), sig.decimals,
                        (start, start + w), (end - w, end), *(on or (None, None, None)))


def _onsets_for(results):
    """One entry per measure whose change has a date: when it crossed the threshold, and by how much it has moved since."""
    out = []
    for r in results:
        if r.onset is None:
            continue
        out.append({"key": r.key, "label": r.label, "date": f"{r.onset:%Y-%m-%d}", "unit": r.unit, "decimals": r.decimals,
                    "baseline": round(r.mean_first, 4), "at_onset": round(r.onset_value, 4), "now": round(r.mean_last, 4),
                    "threshold": round(r.threshold, 4), "kind": "signal"})
    return out


def _lab_onset(p: Patient, lr, bad, min_abs):
    """The first lab result that moved min_abs from the first result in the concerning direction and was not reversed later."""
    rows = p.labs[p.labs.test == lr["test"]].sort_values("date")
    base = float(rows.iloc[0].result)
    moved = [(bad * (float(r.result) - base)) >= min_abs for r in rows.itertuples()]
    if not moved[-1]:
        return None
    i = len(moved) - 1
    while i > 0 and moved[i - 1]:
        i -= 1
    r = rows.iloc[i]
    return {"key": lr["test"], "label": lr["test"], "date": f"{r.date:%Y-%m-%d}", "unit": str(r.unit), "decimals": 2 if abs(base) < 10 else 1,
            "baseline": round(base, 4), "at_onset": round(float(r.result), 4), "now": round(float(rows.iloc[-1].result), 4),
            "threshold": round(base + bad * min_abs, 4), "kind": "lab"}


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


def _range_fields(rng, value):
    pos = ref.position(value, rng)
    return {"reference_range": ref.text(rng), "range_position": pos or "no range"}


def _evidence(r: SignalResult):
    return {**_range_fields(ref.RANGES.get(r.key), r.mean_last),
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


def _persists(s, r_start, end, base_mean, sd, bad):
    """The change must hold in both of the latest two weeks, not just one: each week has to sit on the same side of
    the baseline and show at least RECENT_PERSIST_SHARE of the distance the threshold asks for."""
    mid = r_start + pd.Timedelta(days=RECENT_DAYS // 2)
    for part in (s[r_start:mid - pd.Timedelta(days=1)].dropna(), s[mid:end].dropna()):
        if len(part) < 3:
            return False
        effect = (float(part.mean()) - base_mean) / sd
        if np.sign(effect) != bad or abs(effect) < RECENT_PERSIST_SHARE * RECENT_MIN_EFFECT:
            return False
    return True


def recent_check(p: Patient, key: str):
    """Latest RECENT_DAYS against the patient's own average over the WINDOW_DAYS before them (the baseline).
    Returns a dict when the latest readings moved in the concerning direction, else None."""
    sig = SIGNALS[key]
    if sig.column not in p.daily:
        return None
    s = p.daily[sig.column]
    end = p.window[1]
    r_start = end - pd.Timedelta(days=RECENT_DAYS - 1)
    b_end = r_start - pd.Timedelta(days=1)
    b_start = b_end - pd.Timedelta(days=WINDOW_DAYS - 1)
    rec, base = s[r_start:end].dropna(), s[b_start:b_end].dropna()
    if len(rec) < 7 or len(base) < 45:
        return None
    sd = float(base.std())
    if not sd or sd != sd:
        return None
    diff = float(rec.mean() - base.mean())
    effect = diff / sd
    if np.sign(diff) != sig.bad or abs(diff) < sig.min_abs or abs(effect) < RECENT_MIN_EFFECT:
        return None
    if not _persists(s, r_start, end, float(base.mean()), sd, sig.bad):
        return None
    flag = "Sufficient" if len(base) >= 72 and len(rec) >= 11 else "Limited"
    on = find_onset(s, float(base.mean()), sd, int(np.sign(diff)), RECENT_MIN_EFFECT, b_end)
    return {"onset": on, "sig": sig, "base": float(base.mean()), "rec": float(rec.mean()), "diff": diff, "effect": effect,
            "n_base": len(base), "n_rec": len(rec), "flag": flag,
            "base_win": (b_start, b_end), "rec_win": (r_start, end)}


def number_evidence(insights):
    """Give every finding an ID (F1, F2, ...) and every evidence row an ID (E1, E2, ...).

    The numbers run across the patient's findings in the order they are shown, so a sentence
    or a chart can point to exactly the row that supports it.
    """
    n = 0
    for f, ins in enumerate(insights, 1):
        ins.insight_id = f"F{f}"
        for e in ins.evidence:
            n += 1
            e["id"] = f"E{n}"


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
                                     "size_vs_own_variation": "—", "trend_p": "—",
                                     **_range_fields(ref.lab_range(l["last"].ref_low, l["last"].ref_high, l["last"].unit), float(l["last"].result))}
                                    for l in lab_hits],
                                ctx, text, _asks(p, usable, list(c["labs"]), lab_hits), usable[0].key if usable else "",
                                f"{len(bullets)} related measures moved in the same direction over this patient's year.", bullets, closing,
                                SCENARIO[cname], onsets=_onsets_for(usable) + [o for o in (_lab_onset(p, l, c["labs"][l["test"]][0], c["labs"][l["test"]][1]) for l in lab_hits) if o]))
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
                                    [_bullet(r)], "This change may be worth mentioning to a healthcare provider." + _projection_sentence(p, r),
                                    onsets=_onsets_for([r])))

    # latest readings against the patient's own 90-day baseline (recent deviation)
    covered = set(used) | {i.signals[0] for i in insights if i.kind == "single" and i.signals}
    for key in SIGNALS:
        if key in covered:
            continue
        rc = recent_check(p, key)
        if not rc:
            continue
        sig, d = rc["sig"], SIGNALS[key].decimals
        bullet = (f"{sig.label} averaged {rc['rec']:,.{d}f} {sig.unit} over the latest {RECENT_DAYS} days, compared with "
                  f"{rc['base']:,.{d}f} {sig.unit} over the {WINDOW_DAYS} days before ({rc['diff']:+,.{d}f} {sig.unit})")
        closing = "This change may be worth mentioning to a healthcare provider."
        text = bullet + ". " + closing
        assert not check_language(text), check_language(text)
        w = lambda t: f"{t[0]:%d %b %Y} to {t[1]:%d %b %Y}"
        insights.append(Insight("recent", f"{sig.label} is different from the usual last {WINDOW_DAYS} days", rc["flag"], [],
                                [{"signal": sig.label, "source": sig.sheet, "first_window": w(rc["base_win"]), "last_window": w(rc["rec_win"]),
                                  "first_mean": f"{rc['base']:,.{d}f} {sig.unit}", "last_mean": f"{rc['rec']:,.{d}f} {sig.unit}",
                                  "days_with_data": f"{rc['n_base']} baseline, {rc['n_rec']} recent", "overall_coverage": "—",
                                  "size_vs_own_variation": f"{abs(rc['effect']):.1f}x", "trend_p": "—",
                                  **_range_fields(ref.RANGES.get(key), rc["rec"])}],
                                [], text, [], key, "The latest readings differ from this patient's own recent baseline.", [bullet], closing,
                                SCENARIO["cardio"] if key in ("sbp", "dbp", "rhr", "hrv") else SCENARIO["metabolic"],
                                onsets=[{"key": key, "label": sig.label, "date": f"{rc['onset'][0]:%Y-%m-%d}", "unit": sig.unit, "decimals": d,
                                         "baseline": round(rc["base"], 4), "at_onset": round(rc["onset"][1], 4), "now": round(rc["rec"], 4),
                                         "threshold": round(rc["onset"][2], 4), "kind": "signal"}] if rc["onset"] else []))

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
            odd = cy[(cy.cycle_length < 21) | (cy.cycle_length > 35)].sort_values("start")
            cyc_on = ([{"key": "cycle", "label": "Cycle length", "date": f"{odd.iloc[0].start:%Y-%m-%d}", "unit": "days", "decimals": 0,
                        "baseline": 28.0, "at_onset": round(float(odd.iloc[0].cycle_length), 4), "now": round(float(mean_len), 4),
                        "threshold": 35.0, "kind": "cycle", "count": int(len(odd)), "of": int(len(cy))}] if len(odd) else [])
            insights.append(Insight("cycle", "Cycle timing is irregular", flag, [], [{
                "signal": "Cycle length", "source": "Women Health", "first_window": f"{cy.start.min():%d %b %Y}",
                "last_window": f"{cy.start.max():%d %b %Y}", "first_mean": f"{mean_len:.0f} days (mean)",
                "last_mean": f"{sd_len:.1f} days (variation)", "days_with_data": f"{len(cy)} cycles",
                "overall_coverage": "—", "size_vs_own_variation": "—", "trend_p": "—",
                **_range_fields(ref.CYCLE_RANGE, float(mean_len))}], ctx, text, [], "",
                                "Cycle timing varies more than usual.",
                                [f"Cycle length averaged {mean_len:.0f} days across {len(cy)} cycles and varied by about {sd_len:.0f} days between cycles "
                                 "(usual range is roughly 21–35 days with small variation)"],
                                "This pattern may be worth discussing with a healthcare provider.", onsets=cyc_on))

    order = {"pattern": 0, "cycle": 1, "recent": 2, "single": 3}
    insights.sort(key=lambda i: (order[i.kind], -RANK[i.flag]))
    for ins in insights:
        if not ins.scenario:
            if ins.kind == "cycle":
                ins.scenario = SCENARIO["cycle"]
            else:
                ins.scenario = SCENARIO["cardio"] if ins.signals and ins.signals[0] in ("sbp", "dbp", "rhr", "hrv") else SCENARIO["metabolic"]
    for ins in insights:
        ins.tier = ref.tier([e.get("range_position") if e.get("range_position") != "no range" else None for e in ins.evidence])
    number_evidence(insights)
    for ins in insights:
        ins.limits = limits_line(ins)
    return insights, held, results


def _count_text(days):
    """The evidence table's reading count, said plainly."""
    m = re.fullmatch(r"(\d+) of (\d+) \(first\), (\d+) of \d+ \(last\)", days or "")
    if m:
        return f"{m[1]} of {m[2]} days in both windows" if m[1] == m[3] else f"{m[1]} of {m[2]} days earlier, {m[3]} of {m[2]} recently"
    m = re.fullmatch(r"(\d+) baseline, (\d+) recent", days or "")
    if m:
        return f"{m[1]} baseline and {m[2]} recent days"
    return days or "count not recorded"


def limits_line(ins):
    """What a finding cannot tell, built only from data it already holds: the reading counts and the data flag."""
    based = "; ".join(f"{e['signal']} ({_count_text(e.get('days_with_data'))})" for e in ins.evidence)
    parts = [f"Based on {based}." if based else "Based on the readings in this record."]
    parts.append("Some expected readings were missing, so this could change as more data arrives."
                 if ins.flag == "Limited" else "There were enough readings for each measure.")
    parts.append({"recent": f"It looks only at the latest {RECENT_DAYS} days against the {WINDOW_DAYS} days before them.",
                  "cycle": "It uses cycle start dates only."}.get(ins.kind,
                 "It compares this person's earlier and recent readings and cannot say what caused the change."))
    parts.append("It does not name or rule out any condition; only a healthcare provider can say what it may mean.")
    text = " ".join(parts)
    assert not check_language(text), check_language(text)
    return text


def disease_input_problems(insights):
    """Reasons a finding uses a measure that does not belong to its disease area. Empty when every finding is clean."""
    out = []
    for ins in insights:
        area = ref.AREAS.get(ins.scenario)
        if area is None:
            out.append(f"{ins.insight_id} {ins.title}: unknown area {ins.scenario!r}")
            continue
        for k in ins.signals:
            if k not in area.signals:
                out.append(f"{ins.insight_id} {ins.title}: {k} does not belong to {area.short}")
        for e in ins.evidence:
            if e["source"] == "Lab Results" and e["signal"] not in area.labs:
                out.append(f"{ins.insight_id} {ins.title}: lab {e['signal']} does not belong to {area.short}")
    return out
