"""
core/downsampling.py
====================
Import-time downsampling service for the Plotter application.

Supports three methods, selectable per config file:
  - decimation : integer-factor anti-alias decimation via scipy.signal.decimate
  - lttb       : Largest-Triangle-Three-Buckets via tsdownsample (visual fidelity)
  - dwt        : Discrete Wavelet Transform approximation via PyWavelets
                 (analysis-oriented; requires uniform sampling)

Public API
----------
  downsample(df, ds_config, x_col_name)
      Apply the configured downsampling to a DataFrame.
      Returns (downsampled_df, result_meta_dict).

  validate_downsampling_config(ds_config)
      Lightweight schema check called by ConfigManager.

  DownsamplingError
      Raised on preflight failures (bad config, missing deps, bad data).
      The UI layer should catch this and surface it as a warning dialog.

Method parameter keys (in config JSON under "downsampling"):
  decimation:
    factor        (int, >= 2)   – keep every Nth sample
    zero_phase    (bool)        – use zero-phase filter (default True)
  lttb:
    n_samples     (int, >= 2)   – target output sample count
  dwt:
    wavelet       (str)         – PyWavelets wavelet name (default "db4")
    level         (int, >= 1)   – decomposition level
    reconstruct   (bool)        – True = reconstruct signal from approximation
                                  False = use approximation coefficients directly
                                  (default True)
"""

import numpy as np
import pandas as pd

# ─────────────────────────────────────────────────────────────────────────────
#  Public exception
# ─────────────────────────────────────────────────────────────────────────────

class DownsamplingError(Exception):
    """Raised for any downsampling preflight or execution failure."""


# ─────────────────────────────────────────────────────────────────────────────
#  Dependency availability checks  (evaluated once at module load)
# ─────────────────────────────────────────────────────────────────────────────

def _check_scipy():
    try:
        from scipy.signal import decimate  # noqa: F401
        return True
    except ImportError:
        return False

def _check_tsdownsample():
    try:
        from tsdownsample import LTTBDownsampler  # noqa: F401
        return True
    except ImportError:
        return False

def _check_pywavelets():
    try:
        import pywt  # noqa: F401
        return True
    except ImportError:
        return False

_SCIPY_AVAILABLE      = _check_scipy()
_TSDOWNSAMPLE_AVAILABLE = _check_tsdownsample()
_PYWT_AVAILABLE       = _check_pywavelets()

PACKAGE_REQUIREMENTS = {
    "decimation": ("scipy",       _SCIPY_AVAILABLE,      "scipy"),
    "lttb":       ("tsdownsample", _TSDOWNSAMPLE_AVAILABLE, "tsdownsample"),
    "dwt":        ("PyWavelets",  _PYWT_AVAILABLE,       "PyWavelets"),
}

VALID_METHODS = set(PACKAGE_REQUIREMENTS.keys())

# ─────────────────────────────────────────────────────────────────────────────
#  Schema-level validation (called from ConfigManager)
# ─────────────────────────────────────────────────────────────────────────────

def validate_downsampling_config(ds_config):
    """
    Validate the structure of a downsampling config dict.

    Parameters
    ----------
    ds_config : dict  – the value of config["downsampling"]

    Returns
    -------
    (bool, str)  – (True, "Valid") or (False, reason)
    """
    if not isinstance(ds_config, dict):
        return False, "'downsampling' must be an object."

    enabled = ds_config.get("enabled", False)
    if not isinstance(enabled, bool):
        return False, "'downsampling.enabled' must be a boolean."

    if not enabled:
        return True, "Valid"

    method = ds_config.get("method")
    if method not in VALID_METHODS:
        return False, (
            f"'downsampling.method' must be one of {sorted(VALID_METHODS)}. "
            f"Got: {method!r}"
        )

    timing = ds_config.get("timing", "before_conversions")
    if timing not in ("before_conversions", "after_conversions"):
        return False, (
            "'downsampling.timing' must be 'before_conversions' or 'after_conversions'."
        )

    # Method-specific required fields
    if method == "decimation":
        params = ds_config.get("decimation", {})
        factor = params.get("factor")
        if factor is None:
            return False, "'downsampling.decimation.factor' is required."
        if not isinstance(factor, int) or factor < 2:
            return False, "'downsampling.decimation.factor' must be an integer >= 2."

    elif method == "lttb":
        params = ds_config.get("lttb", {})
        n = params.get("n_samples")
        if n is None:
            return False, "'downsampling.lttb.n_samples' is required."
        if not isinstance(n, int) or n < 2:
            return False, "'downsampling.lttb.n_samples' must be an integer >= 2."

    elif method == "dwt":
        params = ds_config.get("dwt", {})
        level = params.get("level")
        if level is None:
            return False, "'downsampling.dwt.level' is required."
        if not isinstance(level, int) or level < 1:
            return False, "'downsampling.dwt.level' must be an integer >= 1."
        wavelet = params.get("wavelet", "db4")
        if not isinstance(wavelet, str) or not wavelet.strip():
            return False, "'downsampling.dwt.wavelet' must be a non-empty string."

    return True, "Valid"


# ─────────────────────────────────────────────────────────────────────────────
#  Preflight helpers
# ─────────────────────────────────────────────────────────────────────────────

_UNIFORMITY_TOLERANCE = 0.05  # 5 % coefficient of variation threshold


def _require_package(method):
    """Raise DownsamplingError if the backing package for `method` is unavailable."""
    pkg_label, available, install_name = PACKAGE_REQUIREMENTS[method]
    if not available:
        raise DownsamplingError(
            f"Downsampling method '{method}' requires '{pkg_label}', "
            f"which is not installed.  Run:  pip install {install_name}"
        )


def _require_min_rows(df, minimum=4):
    if len(df) < minimum:
        raise DownsamplingError(
            f"DataFrame has only {len(df)} rows; downsampling needs at least {minimum}."
        )


def _get_x_series(df, x_col_name):
    """Return the x-axis Series, raising DownsamplingError on problems."""
    if x_col_name is None:
        raise DownsamplingError(
            "No x-axis column is defined in the config.  "
            "Downsampling requires a defined x column."
        )
    if x_col_name not in df.columns:
        raise DownsamplingError(
            f"x-axis column '{x_col_name}' not found in the DataFrame.  "
            f"Available columns: {df.columns.tolist()}"
        )
    return df[x_col_name]


def _require_monotonic_x(x_series):
    """Raise DownsamplingError if x is not monotonically increasing."""
    if not x_series.is_monotonic_increasing:
        raise DownsamplingError(
            f"x-axis column '{x_series.name}' is not monotonically increasing.  "
            "Sort data by x before applying downsampling."
        )


def _require_uniform_x(x_series):
    """
    Raise DownsamplingError if x spacing is not approximately uniform.
    Uses coefficient of variation on inter-sample differences.
    """
    _require_monotonic_x(x_series)
    diffs = np.diff(x_series.to_numpy(dtype=float))
    if len(diffs) < 2:
        return  # Too few points to judge; pass through.
    mean_diff = np.mean(diffs)
    if mean_diff == 0:
        raise DownsamplingError(
            f"x-axis column '{x_series.name}' has zero mean spacing — all values equal?"
        )
    cv = np.std(diffs) / mean_diff
    if cv > _UNIFORMITY_TOLERANCE:
        raise DownsamplingError(
            f"x-axis column '{x_series.name}' does not appear to be uniformly sampled "
            f"(spacing CV = {cv:.3f}, tolerance = {_UNIFORMITY_TOLERANCE}).  "
            "Use 'lttb' for non-uniform data, or resample to uniform spacing first."
        )


def _numeric_signal_columns(df, x_col_name):
    """Return a list of numeric columns that are not the x-axis column."""
    return [
        c for c in df.columns
        if c != x_col_name and pd.api.types.is_numeric_dtype(df[c])
    ]


# ─────────────────────────────────────────────────────────────────────────────
#  Method implementations
# ─────────────────────────────────────────────────────────────────────────────

def _apply_decimation(df, x_col_name, params):
    """
    Decimate all numeric signal columns using scipy.signal.decimate.

    Parameters applied after preflight:
      factor     (int)  – decimation factor
      zero_phase (bool) – use forward-backward (zero-phase) IIR filter

    The x column is simply stride-decimated (factor index selection) because
    it represents time — anti-alias filtering a time axis makes no sense.
    Signal columns receive proper anti-alias lowpass + decimation.
    """
    from scipy.signal import decimate as scipy_decimate

    factor     = int(params.get("factor"))
    zero_phase = bool(params.get("zero_phase", True))

    x_series = _get_x_series(df, x_col_name)
    _require_uniform_x(x_series)

    sig_cols = _numeric_signal_columns(df, x_col_name)

    # Build result dict column by column
    result = {}

    # X: stride-select (no filtering needed for time/index axis)
    result[x_col_name] = x_series.to_numpy()[::factor]

    # Signal columns: scipy decimate (anti-alias + downsample)
    for col in sig_cols:
        raw = df[col].to_numpy(dtype=float).copy()
        try:
            decimated = scipy_decimate(raw, factor, zero_phase=zero_phase)
        except Exception as exc:
            raise DownsamplingError(
                f"scipy.signal.decimate failed on column '{col}': {exc}"
            ) from exc
        result[col] = decimated

    # Non-numeric, non-x columns: stride-select (preserve as-is)
    for col in df.columns:
        if col not in result:
            result[col] = df[col].to_numpy()[::factor]

    return pd.DataFrame(result)


def _apply_lttb(df, x_col_name, params):
    """
    Reduce each numeric signal column independently using LTTB.

    LTTB runs per-signal on (x, y) pairs and returns a Boolean index mask.
    We then apply the union of all selected indices so all columns
    stay aligned on the same row subset.

    Parameters:
      n_samples (int) – target number of output samples
    """
    from tsdownsample import LTTBDownsampler

    n_samples = int(params.get("n_samples"))
    x_series  = _get_x_series(df, x_col_name)
    _require_monotonic_x(x_series)

    sig_cols = _numeric_signal_columns(df, x_col_name)
    if not sig_cols:
        raise DownsamplingError(
            "LTTB found no numeric signal columns to downsample."
        )

    if n_samples >= len(df):
        # Target count >= current count — nothing to do.
        return df.copy()

    x_arr     = x_series.to_numpy(dtype=float)
    downsampler = LTTBDownsampler()

    # Collect selected indices from each signal, then take the union
    selected_indices_set = set()
    for col in sig_cols:
        y_arr = df[col].to_numpy(dtype=float).copy()
        try:
            indices = downsampler.downsample(x_arr, y_arr, n_out=n_samples)
        except Exception as exc:
            raise DownsamplingError(
                f"LTTBDownsampler failed on column '{col}': {exc}"
            ) from exc
        selected_indices_set.update(indices.tolist())

    # Always keep first and last rows
    selected_indices_set.add(0)
    selected_indices_set.add(len(df) - 1)

    selected = sorted(selected_indices_set)
    return df.iloc[selected].reset_index(drop=True)


def _apply_dwt(df, x_col_name, params):
    """
    Reduce each numeric signal column using DWT approximation coefficients.

    Decompose each column to `level` using the specified wavelet, extract
    the approximation coefficients, and optionally reconstruct back to the
    original scale.  The output row count is:
      N / 2^level   (approximation coefficients)  if reconstruct=False
      N             (same length, smoothed)        if reconstruct=True

    The x column is resampled by uniform striding to match whichever output
    length results from the chosen strategy.

    Parameters:
      wavelet     (str)  – PyWavelets wavelet name  (default "db4")
      level       (int)  – decomposition level
      reconstruct (bool) – True: reconstruct to original length (default)
                          False: keep approximation coefficients (shorter)
    """
    import pywt

    wavelet     = str(params.get("wavelet", "db4"))
    level       = int(params.get("level"))
    reconstruct = bool(params.get("reconstruct", True))

    # Validate wavelet name early so the error is readable
    if wavelet not in pywt.wavelist():
        raise DownsamplingError(
            f"Unknown PyWavelets wavelet: '{wavelet}'.  "
            f"Call pywt.wavelist() to see available names."
        )

    x_series = _get_x_series(df, x_col_name)
    _require_uniform_x(x_series)

    sig_cols = _numeric_signal_columns(df, x_col_name)
    if not sig_cols:
        raise DownsamplingError(
            "DWT found no numeric signal columns to process."
        )

    # Validate level for the shortest signal
    min_len = min(len(df[c].dropna()) for c in sig_cols)
    max_level = pywt.dwt_max_level(min_len, wavelet)
    if level > max_level:
        raise DownsamplingError(
            f"DWT decomposition level {level} exceeds the maximum ({max_level}) "
            f"for wavelet '{wavelet}' and {min_len} samples.  Use a lower level."
        )

    result = {}

    for col in sig_cols:
        raw = df[col].to_numpy(dtype=float).copy()
        try:
            coeffs = pywt.wavedec(raw, wavelet, level=level)
        except Exception as exc:
            raise DownsamplingError(
                f"pywt.wavedec failed on column '{col}': {exc}"
            ) from exc

        if reconstruct:
            # Reconstruct signal from approximation only (zero out detail coefficients)
            coeffs_approx = [coeffs[0]] + [np.zeros_like(d) for d in coeffs[1:]]
            try:
                reconstructed = pywt.waverec(coeffs_approx, wavelet)
            except Exception as exc:
                raise DownsamplingError(
                    f"pywt.waverec failed on column '{col}': {exc}"
                ) from exc
            # waverec may add 1 extra sample for even-length inputs
            result[col] = reconstructed[: len(raw)]
        else:
            # Use approximation coefficients directly (shorter output)
            result[col] = coeffs[0]

    # Determine output length from one of the signal results
    out_len = len(next(iter(result.values())))

    # X: uniform stride to match output length
    x_arr = x_series.to_numpy(dtype=float)
    if reconstruct:
        result[x_col_name] = x_arr[:out_len]
    else:
        indices = np.round(np.linspace(0, len(x_arr) - 1, out_len)).astype(int)
        result[x_col_name] = x_arr[indices]

    # Non-numeric, non-x columns: stride-select to match output length
    for col in df.columns:
        if col not in result:
            indices = np.round(np.linspace(0, len(df) - 1, out_len)).astype(int)
            result[col] = df[col].to_numpy()[indices]

    # Preserve original column order from input DataFrame
    return pd.DataFrame(result)[list(df.columns)]


# ─────────────────────────────────────────────────────────────────────────────
#  Method registry
# ─────────────────────────────────────────────────────────────────────────────

#  Each entry: method_name -> (params_key_in_config, executor_fn)
_METHOD_REGISTRY = {
    "decimation": ("decimation", _apply_decimation),
    "lttb":       ("lttb",       _apply_lttb),
    "dwt":        ("dwt",        _apply_dwt),
}


# ─────────────────────────────────────────────────────────────────────────────
#  Public entry point
# ─────────────────────────────────────────────────────────────────────────────

def downsample(df, ds_config, x_col_name):
    """
    Apply import-time downsampling to a DataFrame.

    Parameters
    ----------
    df          : pd.DataFrame
        The working dataframe (not modified in-place; a new frame is returned).
    ds_config   : dict
        The value of config["downsampling"] — already sanitized by ConfigManager.
    x_col_name  : str | None
        The resolved name of the x-axis column in `df`. None if x is not defined.

    Returns
    -------
    (downsampled_df, result_meta) : tuple
        downsampled_df  – pd.DataFrame with fewer rows
        result_meta     – dict with keys:
            original_row_count   (int)
            downsampled_row_count (int)
            method               (str)
            timing               (str)
            parameters           (dict)

    Raises
    ------
    DownsamplingError
        If preconditions are not met or the algorithm fails.
        The caller should catch this and surface it to the user.
    """
    if not ds_config.get("enabled", False):
        # Downsampling disabled — return unchanged
        meta = {
            "original_row_count":    len(df),
            "downsampled_row_count": len(df),
            "method":                None,
            "timing":                None,
            "parameters":            {},
        }
        return df, meta

    method = ds_config.get("method")
    timing = ds_config.get("timing", "before_conversions")

    if method not in _METHOD_REGISTRY:
        raise DownsamplingError(
            f"Unknown downsampling method '{method}'.  "
            f"Valid methods: {sorted(_METHOD_REGISTRY.keys())}"
        )

    _require_package(method)
    _require_min_rows(df)

    params_key, executor = _METHOD_REGISTRY[method]
    params = ds_config.get(params_key, {})

    original_count = len(df)
    downsampled_df = executor(df, x_col_name, params)

    result_meta = {
        "original_row_count":    original_count,
        "downsampled_row_count": len(downsampled_df),
        "method":                method,
        "timing":                timing,
        "parameters":            dict(params),
    }

    return downsampled_df, result_meta
