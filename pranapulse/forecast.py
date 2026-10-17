"""Simple, transparent trend projection: a straight line through recent weekly means, with a 95% range."""
import numpy as np
import pandas as pd
from scipy import stats

from .signals import FORECAST_WEEKS


def weekly_means(series: pd.Series) -> pd.Series:
    return series.resample("W").mean().dropna()


def project(series: pd.Series, weeks: int = FORECAST_WEEKS, fit_weeks: int = 26):
    """Return a DataFrame (date, mean, low, high) for the next `weeks` weeks, or None if too little data."""
    w = weekly_means(series).iloc[-fit_weeks:]
    if len(w) < 12:
        return None
    x = np.arange(len(w), dtype=float)
    res = stats.linregress(x, w.values)
    resid = w.values - (res.intercept + res.slope * x)
    s = np.sqrt(np.sum(resid ** 2) / (len(w) - 2))
    xm, sxx = x.mean(), np.sum((x - x.mean()) ** 2)
    t = stats.t.ppf(0.975, len(w) - 2)
    fx = np.arange(len(w), len(w) + weeks, dtype=float)
    mean = res.intercept + res.slope * fx
    half = t * s * np.sqrt(1 + 1 / len(w) + (fx - xm) ** 2 / sxx)
    dates = pd.date_range(w.index[-1] + pd.Timedelta(weeks=1), periods=weeks, freq="W")
    return pd.DataFrame({"date": dates, "mean": mean, "low": mean - half, "high": mean + half})
