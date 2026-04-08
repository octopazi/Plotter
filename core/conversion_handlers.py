"""
conversion_handlers.py
======================
A pluggable registry of column-conversion handlers for the FileLoader pipeline.

Design principles
-----------------
- Each handler is a plain function with the signature:
      handler(df, conv) -> pd.Series
  where `conv` is the raw conversion dict from the config JSON.
- Handlers are registered in HANDLER_REGISTRY under their type-string key.
- Adding a new type = write one function + one registry line.  FileLoader
  and the config GUI do not need to change.
- Conversions are applied **sequentially** (the order in the config JSON
  matters). A later step can reference a column produced by an earlier step.
- On failure, the handler raises an exception; apply_conversions() catches it,
  records a structured error, and continues so that all failures are reported
  together at the end.

Supported types (config "type" field)
--------------------------------------
  "expr"           – (default) pandas df.eval() math expression
  "hex_to_int"     – hex string  →  signed/unsigned integer
  "hex_to_float"   – hex string  →  float  (via IEEE-754 reinterpret or divide)
  "hex_to_fixedpoint" – hex string → fixed-point float  (value / 2^frac_bits)
  "bitmask"        – extract bit field: (int_col & mask) >> shift
  "lookup"         – map discrete values to labels / numbers via a dict
  "scale"          – value * factor + offset  (explicit, readable alternative to expr)
"""

import pandas as pd
import numpy as np
import struct


# ─────────────────────────────────────────────────────────────────────────────
#  Internal utility
# ─────────────────────────────────────────────────────────────────────────────

def _parse_hex_str(s):
    """Convert a hex string (with or without '0x'/'0X' prefix) to int."""
    s = str(s).strip()
    if s.lower().startswith("0x"):
        return int(s, 16)
    return int(s, 16)


def _col(df, conv, key="source"):
    """Return the named column from df, raising KeyError with a clear message."""
    col_name = conv.get(key)
    if col_name is None:
        raise KeyError(f"Missing required field '{key}' in conversion config.")
    if col_name not in df.columns:
        raise KeyError(f"Column '{col_name}' not found in dataframe. "
                       f"Available columns: {df.columns.tolist()}")
    return df[col_name]


# ─────────────────────────────────────────────────────────────────────────────
#  Handler implementations
# ─────────────────────────────────────────────────────────────────────────────

def _handle_expr(df, conv):
    """
    Evaluate a pandas-eval math expression against the current dataframe.

    Config fields:
      formula  (str)  – e.g. "TC1 / 1000"  or  "col2 * 0.5 + offset"

    Note: column names with spaces must be wrapped in backticks in the formula.
    """
    formula = conv.get("formula", "")
    if not formula:
        raise ValueError("'formula' field is required for type 'expr'.")
    # Tolerate legacy bracket syntax  col[1]  →  col1
    formula = formula.replace("col[", "col").replace("]", "")
    return df.eval(formula)


def _handle_hex_to_int(df, conv):
    """
    Parse a column of hex strings into integers.

    Config fields:
      source   (str)            – source column name
      signed   (bool, optional) – interpret as signed integer (default: False)
      bits     (int,  optional) – word size for signed interpretation (default: 32)

    Accepts both prefixed ("0xFF") and bare ("FF") hex strings.
    """
    series = _col(df, conv)
    result = series.apply(_parse_hex_str)
    if conv.get("signed", False):
        bits = conv.get("bits", 32)
        cutoff = 1 << (bits - 1)
        mask   = (1 << bits) - 1
        result = result.apply(lambda v: v - (1 << bits) if (v & cutoff) else v)
    return result.astype("int64")


def _handle_hex_to_float(df, conv):
    """
    Convert a hex string to a float using one of two strategies:

    Strategy A – IEEE-754 reinterpret (default, method: "ieee754"):
      Interprets the raw hex bytes as an IEEE-754 float32 or float64.
      Config fields:
        source   (str)           – source column name
        method   (str, optional) – "ieee754" (default)
        bits     (int, optional) – 32 (float32, default) or 64 (float64)

    Strategy B – integer divide (method: "divide"):
      Converts hex → int, then divides by a divisor.
      Config fields:
        source   (str)  – source column name
        method   (str)  – "divide"
        divisor  (float) – e.g. 100.0

    Example (IEEE-754):
      { "name": "temperature", "type": "hex_to_float", "source": "raw_hex" }

    Example (divide):
      { "name": "voltage", "type": "hex_to_float", "source": "raw_hex",
        "method": "divide", "divisor": 1000.0 }
    """
    series = _col(df, conv)
    method = conv.get("method", "ieee754")

    if method == "ieee754":
        bits = conv.get("bits", 32)
        if bits == 32:
            fmt = ">f"   # big-endian float32
            def _to_f32(s):
                raw = _parse_hex_str(s)
                return struct.unpack(fmt, raw.to_bytes(4, "big"))[0]
            return series.apply(_to_f32).astype("float64")
        elif bits == 64:
            def _to_f64(s):
                raw = _parse_hex_str(s)
                return struct.unpack(">d", raw.to_bytes(8, "big"))[0]
            return series.apply(_to_f64).astype("float64")
        else:
            raise ValueError(f"Unsupported bits value '{bits}' for ieee754; use 32 or 64.")

    elif method == "divide":
        divisor = conv.get("divisor")
        if divisor is None:
            raise ValueError("'divisor' field is required when method is 'divide'.")
        return series.apply(_parse_hex_str).astype("float64") / float(divisor)

    else:
        raise ValueError(f"Unknown hex_to_float method '{method}'. Use 'ieee754' or 'divide'.")


def _handle_hex_to_fixedpoint(df, conv):
    """
    Convert a hex string to a fixed-point float:  value = int(hex) / 2^frac_bits

    Config fields:
      source     (str)           – source column name
      frac_bits  (int)           – number of fractional bits (Q format)
      signed     (bool, optional) – treat as signed integer before scaling (default: False)
      bits       (int,  optional) – word size for signed check (default: 16)

    Example (Q8.8 unsigned, 16-bit):
      { "name": "gain", "type": "hex_to_fixedpoint",
        "source": "raw_col", "frac_bits": 8 }

    Example (Q1.15 signed):
      { "name": "angle", "type": "hex_to_fixedpoint",
        "source": "raw_col", "frac_bits": 15, "signed": true, "bits": 16 }
    """
    series   = _col(df, conv)
    frac_bits = conv.get("frac_bits")
    if frac_bits is None:
        raise ValueError("'frac_bits' field is required for type 'hex_to_fixedpoint'.")
    divisor = float(1 << frac_bits)

    raw_int = series.apply(_parse_hex_str)

    if conv.get("signed", False):
        bits   = conv.get("bits", 16)
        cutoff = 1 << (bits - 1)
        raw_int = raw_int.apply(lambda v: v - (1 << bits) if (v & cutoff) else v)

    return (raw_int.astype("float64") / divisor)


def _handle_bitmask(df, conv):
    """
    Extract a bit field from an integer (or hex-string) column.
    result = (value & mask) >> shift

    Config fields:
      source  (str)            – source column name (int or hex string)
      mask    (str or int)     – bitmask, e.g. "0x00FF" or 255
      shift   (int, optional)  – right-shift amount after masking (default: 0)

    Example:
      { "name": "status_flag", "type": "bitmask",
        "source": "raw_word", "mask": "0x0F", "shift": 0 }
    """
    series = _col(df, conv)
    mask_val = conv.get("mask")
    if mask_val is None:
        raise ValueError("'mask' field is required for type 'bitmask'.")

    # Accept both integer and hex-string mask
    if isinstance(mask_val, str):
        mask_int = int(mask_val, 16) if mask_val.lower().startswith("0x") else int(mask_val)
    else:
        mask_int = int(mask_val)

    shift = int(conv.get("shift", 0))

    # If the source column is strings (hex), convert first
    if series.dtype == object:
        series = series.apply(_parse_hex_str)

    return ((series.astype("int64") & mask_int) >> shift)


def _handle_lookup(df, conv):
    """
    Map discrete column values to labels or numbers via a dictionary.
    Unmapped values become NaN (numeric map) or the original value (string map).

    Config fields:
      source   (str)           – source column name
      map      (dict)          – { "raw_value": "mapped_value", ... }
                                 Keys are matched as strings.
      default  (any, optional) – value for entries not found in map
                                 (default: NaN / original value kept)

    Example:
      { "name": "mode_label", "type": "lookup", "source": "mode_code",
        "map": { "0": "IDLE", "1": "RUN", "2": "FAULT" } }
    """
    series  = _col(df, conv)
    raw_map = conv.get("map")
    if not raw_map:
        raise ValueError("'map' field (non-empty dict) is required for type 'lookup'.")

    default = conv.get("default", pd.NA)

    # Normalise all keys to strings for consistent matching
    str_map = {str(k): v for k, v in raw_map.items()}

    return series.astype(str).map(str_map).fillna(
        series.astype(str).map(lambda x: default if default is not pd.NA else x)
        if default is pd.NA else default
    )


def _handle_scale(df, conv):
    """
    Linear scaling: result = source * factor + offset

    Config fields:
      source  (str)            – source column name
      factor  (float)          – multiplicative scale factor
      offset  (float, optional) – additive offset (default: 0.0)

    Example:
      { "name": "temperature_c", "type": "scale",
        "source": "raw_adc", "factor": 0.0625, "offset": -40.0 }
    """
    series = _col(df, conv)
    factor = conv.get("factor")
    if factor is None:
        raise ValueError("'factor' field is required for type 'scale'.")
    offset = float(conv.get("offset", 0.0))
    return series.astype("float64") * float(factor) + offset


# ─────────────────────────────────────────────────────────────────────────────
#  Handler Registry
#  To add a new type: implement _handle_<name>() above, then add one line here.
# ─────────────────────────────────────────────────────────────────────────────

HANDLER_REGISTRY = {
    "expr":               _handle_expr,
    "hex_to_int":         _handle_hex_to_int,
    "hex_to_float":       _handle_hex_to_float,
    "hex_to_fixedpoint":  _handle_hex_to_fixedpoint,
    "bitmask":            _handle_bitmask,
    "lookup":             _handle_lookup,
    "scale":              _handle_scale,
}


# ─────────────────────────────────────────────────────────────────────────────
#  Public API
# ─────────────────────────────────────────────────────────────────────────────

class ConversionError:
    """Structured record of a single conversion failure."""
    def __init__(self, step, name, conv_type, message):
        self.step      = step        # 1-based index in the conversions list
        self.name      = name        # output column name
        self.conv_type = conv_type   # type string
        self.message   = message     # exception message

    def __str__(self):
        return (f"Step {self.step} — '{self.name}' (type: '{self.conv_type}')\n"
                f"  Error: {self.message}")


def apply_conversions(df, conversions):
    """
    Apply a list of conversion configs to a DataFrame sequentially.

    Each conversion is applied in order, so a later step may reference a column
    produced by an earlier step.  If a step fails it is skipped (the output
    column is NOT added to the dataframe) and the error is recorded.

    Parameters
    ----------
    df          : pd.DataFrame  – the working dataframe (modified in-place)
    conversions : list[dict]    – the 'conversions' array from the config JSON

    Returns
    -------
    errors : list[ConversionError]
        Empty if all steps succeeded.  The caller is responsible for surfacing
        these to the user (e.g. via a QMessageBox warning dialog).
    """
    errors = []

    for step_idx, conv in enumerate(conversions, start=1):
        output_name = conv.get("name", f"<unnamed step {step_idx}>")
        conv_type   = conv.get("type", "expr")   # default to legacy "expr"

        handler = HANDLER_REGISTRY.get(conv_type)
        if handler is None:
            errors.append(ConversionError(
                step      = step_idx,
                name      = output_name,
                conv_type = conv_type,
                message   = (f"Unknown conversion type '{conv_type}'. "
                             f"Available types: {list(HANDLER_REGISTRY.keys())}")
            ))
            continue

        try:
            df[output_name] = handler(df, conv)
        except Exception as exc:
            errors.append(ConversionError(
                step      = step_idx,
                name      = output_name,
                conv_type = conv_type,
                message   = str(exc)
            ))

    return errors
