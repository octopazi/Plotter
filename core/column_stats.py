import numpy as np
import pandas as pd


def compute_column_stats(series):
    """Compute summary statistics for a numeric pandas Series.

    Returns a dictionary containing:
      - count_total
      - count_valid
      - count_invalid
      - min
      - max
      - peak_to_peak
      - rms
      - sd_population (Excel STDEV.P equivalent)
    """
    if series is None:
        raise ValueError("Column data is missing.")

    if not pd.api.types.is_numeric_dtype(series):
        raise ValueError("Selected column is not numeric.")

    total_count = int(series.shape[0])
    numeric = pd.to_numeric(series, errors="coerce")
    valid = numeric.dropna()

    valid_count = int(valid.shape[0])
    invalid_count = int(total_count - valid_count)

    if valid_count == 0:
        raise ValueError("Selected numeric column contains no valid values.")

    values = valid.to_numpy(dtype=float)
    min_value = float(np.min(values))
    max_value = float(np.max(values))

    return {
        "count_total": total_count,
        "count_valid": valid_count,
        "count_invalid": invalid_count,
        "min": min_value,
        "max": max_value,
        "peak_to_peak": float(max_value - min_value),
        "rms": float(np.sqrt(np.mean(np.square(values)))),
        "sd_population": float(np.std(values, ddof=0)),
    }