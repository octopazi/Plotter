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
import re


# ─────────────────────────────────────────────────────────────────────────────
#  Internal utility
# ─────────────────────────────────────────────────────────────────────────────

def _parse_hex_str(s):
    """Convert a hex string (with or without '0x'/'0X' prefix) to int."""
    s = str(s).strip()
    # Always parse as hex (base 16), regardless of prefix
    try:
        return int(s, 16)
    except Exception as e:
        raise ValueError(f"Could not parse hex string '{s}': {e}")


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

    # Always parse string mask as hex (with or without 0x prefix)
    if isinstance(mask_val, str):
        mask_int = _parse_hex_str(mask_val)
    else:
        mask_int = int(mask_val)

    shift = int(conv.get("shift", 0))

    # Always parse string values in the series as hex
    if series.dtype == object or series.apply(lambda v: isinstance(v, str)).any():
        series = series.apply(lambda v: _parse_hex_str(v) if isinstance(v, str) else v)

    # Use numpy for element-wise right shift
    return np.right_shift(series.astype("int64") & mask_int, shift)


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

def _handle_string_op(df, conv):
    """
    Perform string operations:
      - strip: strip whitespace or custom chars
      - substring: extract substring via start/length or slicing
      - concat: concatenate multiple columns with separator
    """

    op = conv.get("operation")

    if op == "strip":
        s = _col(df, conv).astype(str)

        chars = conv.get("chars", None)  # None = whitespace
        if chars:
            return s.str.strip(chars)
        else:
            return s.str.strip()

    elif op == "substring":
        s = _col(df, conv).astype(str)

        start = conv.get("start", 0)
        length = conv.get("length")
        

        if length is not None:
            return s.str.slice(start, start + length)
        else:
            return s.str.slice(start)

    else:
        raise ValueError(f"Unsupported string operation '{op}'")

def _handle_regex(df, conv):
    """
    Apply regex to string.

    Features:
      - Validates regex pattern using re.compile()
      - Supports optional flags (IGNORECASE, MULTILINE, DOTALL)
    """

    fn = conv.get("function")

    s = _col(df, conv).astype(str)
    if fn == "sub":
        pattern = conv.get("pattern")
        repl = conv.get("repl", "")

        if not pattern:
            raise ValueError("Missing required field 'pattern'")

        # Parse flags
        flag_names = conv.get("flags", [])
        if isinstance(flag_names, str):
            flag_names = [flag_names]

        flag_map = {
            "IGNORECASE": re.IGNORECASE,
            "MULTILINE": re.MULTILINE,
            "DOTALL": re.DOTALL,
        }

        flags = 0
        for f in flag_names:
            if f not in flag_map:
                raise ValueError(f"Unsupported regex flag '{f}'")
            flags |= flag_map[f]

        # Validate regex pattern
        try:
            compiled = re.compile(pattern, flags)
        except re.error as e:
            raise ValueError(f"Invalid regex pattern '{pattern}': {e}")

        # Apply substitution
        return s.apply(lambda x: compiled.sub(repl, x))


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
    "string_op":          _handle_string_op,
    "regex":              _handle_regex,
}


# ─────────────────────────────────────────────────────────────────────────────
#  GUI Field Specifications  (drives the Config dialog dynamically)
#
#  Each type maps to a list of field-spec dicts.  The GUI reads these at
#  runtime and builds the form — no per-type widget code in the GUI module.
#
#  Supported "widget" values:
#    "lineedit"      – QLineEdit             (value: str)
#    "spinbox"       – QSpinBox              (value: int)
#    "doublespinbox" – QDoubleSpinBox        (value: float)
#    "checkbox"      – QCheckBox             (value: bool)
#    "combo"         – QComboBox             (value: str)
#    "textedit"      – QTextEdit (multiline) (value: str)
#
#  Optional spec keys:
#    "required"  – if True, non-empty check before add  (default False)
#    "default"   – initial value
#    "tooltip"   – widget tooltip
#    "placeholder" – placeholder text (lineedit / textedit)
#    "min", "max", "step", "decimals" – for numeric spinboxes
#    "items"     – list of strings for combo
#    "height"    – fixed pixel height (textedit)
#
#  To add a NEW conversion type:
#    1. Write _handle_xxx() and add it to HANDLER_REGISTRY.
#    2. Add "xxx": [...] to CONV_FIELD_SPECS below.
#    That's it — the GUI will pick it up automatically.
# ─────────────────────────────────────────────────────────────────────────────

CONV_FIELD_SPECS = {
    "expr": [
        {
            "key": "formula", "label": "Formula", "widget": "lineedit",
            "required": True,
            "placeholder": "e.g. raw_adc * 3.3 / 4096",
            "tooltip": (
                "Pandas-eval math expression using mapped column names.\n"
                "Example: 'TC1 / 1000'  or  'col2 * 0.5 + offset'"
            ),
        },
    ],

    "hex_to_int": [
        {
            "key": "source", "label": "Source Column", "widget": "lineedit",
            "required": True,
            "placeholder": "source column name",
            "tooltip": "Source column containing hex strings (e.g. '0xAA00' or 'AA00').",
        },
        {
            "key": "signed", "label": "Signed (two's complement)", "widget": "checkbox",
            "default": False,
            "tooltip": "Enable to interpret the hex value as a signed integer.",
        },
        {
            "key": "bits", "label": "Word Size (bits)", "widget": "spinbox",
            "default": 32, "min": 8, "max": 64,
            "tooltip": "Word size in bits used for signed interpretation (8, 16, 32, or 64).",
        },
    ],

    "hex_to_float": [
        {
            "key": "source", "label": "Source Column", "widget": "lineedit",
            "required": True,
            "placeholder": "source column name",
            "tooltip": "Source column containing hex strings.",
        },
        {
            "key": "method", "label": "Method", "widget": "combo",
            "items": ["ieee754", "divide"], "default": "ieee754",
            "tooltip": (
                "ieee754: reinterpret raw hex bytes as IEEE-754 float.\n"
                "divide:  convert hex → int, then divide by 'Divisor'."
            ),
        },
        {
            "key": "bits", "label": "Bits (ieee754)", "widget": "spinbox",
            "default": 32, "min": 32, "max": 64, "step": 32,
            "tooltip": "32 = float32,  64 = float64  (only for ieee754 method).",
        },
        {
            "key": "divisor", "label": "Divisor (divide)", "widget": "doublespinbox",
            "default": 1.0, "min": 0.000001, "max": 1e12, "decimals": 6,
            "tooltip": "Divisor applied after int conversion  (only for 'divide' method).",
        },
    ],

    "hex_to_fixedpoint": [
        {
            "key": "source", "label": "Source Column", "widget": "lineedit",
            "required": True,
            "placeholder": "source column name",
            "tooltip": "Source column containing hex strings.",
        },
        {
            "key": "frac_bits", "label": "Fractional Bits", "widget": "spinbox",
            "default": 8, "min": 1, "max": 63,
            "tooltip": (
                "Number of fractional bits (Q format).  result = int(hex) / 2^frac_bits\n"
                "Example: Q8.8 unsigned → frac_bits = 8"
            ),
        },
        {
            "key": "signed", "label": "Signed (two's complement)", "widget": "checkbox",
            "default": False,
            "tooltip": "Enable for signed fixed-point (e.g. Q1.15).",
        },
        {
            "key": "bits", "label": "Word Size (bits)", "widget": "spinbox",
            "default": 16, "min": 8, "max": 64,
            "tooltip": "Word size in bits used for signed check.",
        },
    ],

    "bitmask": [
        {
            "key": "source", "label": "Source Column", "widget": "lineedit",
            "required": True,
            "placeholder": "source column name",
            "tooltip": "Source column (integer or hex-string — auto-converted).",
        },
        {
            "key": "mask", "label": "Mask", "widget": "lineedit",
            "required": True,
            "placeholder": "e.g. 0x00FF",
            "tooltip": "Bitmask to apply, e.g. '0x00FF' or '255'.",
        },
        {
            "key": "shift", "label": "Shift (bits)", "widget": "spinbox",
            "default": 0, "min": 0, "max": 63,
            "tooltip": "Right-shift amount after masking.  result = (source & mask) >> shift",
        },
    ],

    "lookup": [
        {
            "key": "source", "label": "Source Column", "widget": "lineedit",
            "required": True,
            "placeholder": "source column name",
            "tooltip": "Source column whose values will be mapped.",
        },
        {
            "key": "default", "label": "Default Value", "widget": "lineedit",
            "placeholder": "(optional) e.g. UNKNOWN",
            "tooltip": "Value for entries not found in the map.  Leave blank to keep the original value.",
        },
        {
            "key": "map", "label": "Map (key=value per line)", "widget": "textedit",
            "required": True,
            "placeholder": "0=IDLE\n1=RUN\n2=FAULT",
            "height": 90,
            "tooltip": (
                "Enter one mapping per line as  key=value\n"
                "Example:\n  0=IDLE\n  1=RUN\n  2=FAULT"
            ),
        },
    ],

    "scale": [
        {
            "key": "source", "label": "Source Column", "widget": "lineedit",
            "required": True,
            "placeholder": "source column name",
            "tooltip": "Source column to scale.  result = source * factor + offset",
        },
        {
            "key": "factor", "label": "Factor", "widget": "doublespinbox",
            "default": 1.0, "min": -1e12, "max": 1e12, "decimals": 8,
            "tooltip": "Multiplicative scale factor.",
        },
        {
            "key": "offset", "label": "Offset", "widget": "doublespinbox",
            "default": 0.0, "min": -1e12, "max": 1e12, "decimals": 8,
            "tooltip": "Additive offset applied after scaling.",
        },
    ],

    "string_op": [
        {
            "key": "operation",
            "label": "Operation",
            "widget": "combo",
            "required": True,
            "items": ["strip", "substring", "concat"],
            "tooltip": "Select string operation type"
        },
        {
            "key": "source",
            "label": "Source Column",
            "widget": "lineedit",
            "required": False,
            "placeholder": "Required for strip / substring",
        },
        {
            "key": "chars",
            "label": "Strip Characters",
            "widget": "lineedit",
            "required": False,
            "placeholder": "Leave empty for whitespace",
            "tooltip": "Characters to strip"
        },
        {
            "key": "start",
            "label": "Start Index",
            "widget": "spinbox",
            "required": False,
            "default": 0,
            "min": 0,
        },
        {
            "key": "length",
            "label": "Length",
            "widget": "spinbox",
            "required": False,
            "min": 1,
            "tooltip": "Leave empty to extract till end"
        },
    ],
    "regex": [
        {
            "key": "function",
            "label": "Regex Function",
            "widget": "combo",
            "required": True,
            "items": ["sub"],
            "tooltip": "Select regex function to apply"
        },
        {
            "key": "source",
            "label": "Source Column",
            "widget": "lineedit",
            "required": True,
        },
        {
            "key": "pattern",
            "label": "Regex Pattern",
            "widget": "lineedit",
            "required": True,
            "placeholder": "e.g. \\d+",
            "tooltip": "Python regex pattern"
        },
        {
            "key": "repl",
            "label": "Replacement",
            "widget": "lineedit",
            "required": False,
            "default": "",
            "placeholder": "Replacement string"
        },
        {
            "key": "flags",
            "label": "Flags",
            "widget": "textedit",
            "required": False,
            "placeholder": "IGNORECASE\nMULTILINE",
            "tooltip": "One per line: IGNORECASE, MULTILINE, DOTALL",
            "height": 60,
        },
    ],
}


def conv_summary(conv):
    """
    Generate a one-line human-readable description from a conversion dict.
    Used by the config GUI to populate list widget items.
    Centralised here so the GUI never needs per-type formatting knowledge.
    """
    t = conv.get("type", "expr")

    match t:
        case "expr":
            return f"expr: {conv.get('formula', '')}"
        case "hex_to_int":
                signed = " signed" if conv.get("signed") else ""
                return f"hex_to_int({conv.get('source', '')}){signed}"
        case "hex_to_float":
            method = conv.get("method", "ieee754")
            if method == "ieee754":
                return f"hex_to_float({conv.get('source', '')}, ieee754 {conv.get('bits', 32)}bit)"
            else:
                return f"hex_to_float({conv.get('source', '')}, ÷{conv.get('divisor', '')})"
        case "hex_to_fixedpoint":
            return f"hex_to_fixedpoint({conv.get('source', '')}, Q.{conv.get('frac_bits', '')})"
        case "bitmask":
            return f"bitmask({conv.get('source', '')} & {conv.get('mask', '')} >> {conv.get('shift', 0)})"
        case "lookup":
            n = len(conv.get("map", {}))
            return f"lookup({conv.get('source', '')}, {n} entries)"    
        case "scale":
            return f"scale({conv.get('source', '')} × {conv.get('factor', '')} + {conv.get('offset', 0)})"
        case "string_op":
            op = conv.get("operation")
            if op == "strip":
                chars = conv.get("chars", None)
                chars_desc = f"'{chars}'" if chars else "whitespace"
                return f"strip({conv.get('source', '')}, {chars_desc})"
            elif op == "substring":
                start = conv.get("start", 0)
                length = conv.get("length")
                length_desc = f"{length} chars" if length else "till end"
                return f"substring({conv.get('source', '')}, start={start}, {length_desc})"
        case "regex":
            fn = conv.get("function")
            pattern = conv.get("pattern", "")
            return f"regex({conv.get('source', '')}, {fn}, {pattern})"

        case _:
            return t


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
