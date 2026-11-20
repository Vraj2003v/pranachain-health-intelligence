// One rule for "is there enough data to draw this?": at least 7 days with a reading.
export const MIN_READINGS = 7;
export const enough = (s) => !!s && s.rows.filter((r) => r.v != null || r.w != null).length >= MIN_READINGS;
export const usableKeys = (d) => Object.keys(d.series).filter((k) => enough(d.series[k]));
