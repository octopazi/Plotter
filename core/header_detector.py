import pandas as pd


def _coerce_field_value(raw_value, field_type):
    if field_type == "float":
        try:
            return float(raw_value)
        except ValueError:
            return raw_value
    if field_type == "int":
        try:
            return int(raw_value)
        except ValueError:
            return raw_value
    return raw_value


def _clean_string(value):
    if not isinstance(value, str):
        return value
    return value.replace("\\t", "\t").replace("\\n", "\n").replace("\\r", "\r")


def _sanitize_separator(value, default):
    cleaned = _clean_string(value)
    if cleaned in (None, ""):
        return default
    return cleaned


def _sanitize_prefix(value):
    cleaned = _clean_string(value)
    if cleaned in (None, ""):
        return None
    return cleaned


def _strip_prefix(line, prefix):
    if prefix and line.startswith(prefix):
        return line[len(prefix):].strip()
    return line


def _normalize_column_name(name, fallback):
    text = str(name).strip()
    return text if text else fallback


def _make_unique_names(names):
    counts = {}
    output = []
    for original in names:
        count = counts.get(original, 0) + 1
        counts[original] = count
        output.append((original, count))

    # If a name appears only once keep it as-is; otherwise suffix every occurrence.
    totals = {}
    for original in names:
        totals[original] = totals.get(original, 0) + 1

    final_names = []
    for original, count in output:
        if totals.get(original, 0) > 1:
            final_names.append(f"{original}_{count}")
        else:
            final_names.append(original)
    return final_names


def _extract_header_area_column_names(file_path, header_config, data_config):
    if not header_config.get("enabled", False):
        return []

    header_lines = int(header_config.get("lines", 0) or 0)
    if header_lines <= 0:
        return []

    data_separator = _sanitize_separator(data_config.get("separator", ","), ",")
    header_separator = _sanitize_separator(header_config.get("separator", ":"), ":")
    same_as_data = bool(header_config.get("same_as_data", False))
    separator = data_separator if same_as_data else header_separator
    if separator in (None, ""):
        separator = data_separator

    ignore_prefix = _sanitize_prefix(header_config.get("ignore_prefix"))
    lines = []
    with open(file_path, "r", encoding="utf-8") as file_obj:
        for _ in range(header_lines):
            line = file_obj.readline()
            if not line:
                break
            clean_line = _strip_prefix(line.strip(), ignore_prefix)
            if clean_line:
                lines.append(clean_line)

    if not lines:
        return []

    candidate = lines[-1]
    pieces = [part.strip() for part in str(candidate).split(separator)]
    if len(pieces) <= 1:
        return []

    normalized = [
        _normalize_column_name(value, f"col{idx}")
        for idx, value in enumerate(pieces)
    ]
    return _make_unique_names(normalized)


def extract_header_metadata(file_path, header_config):
    metadata = {}
    if not header_config.get("enabled", False):
        return metadata

    header_lines = int(header_config.get("lines", 0) or 0)
    separator = _sanitize_separator(header_config.get("separator", ":"), ":")
    ignore_prefix = _sanitize_prefix(header_config.get("ignore_prefix"))
    field_map = header_config.get("fields", []) or []

    with open(file_path, "r", encoding="utf-8") as file_obj:
        for _ in range(header_lines):
            line = file_obj.readline()
            if not line:
                break
            line = _strip_prefix(line.strip(), ignore_prefix)
            if separator not in line:
                continue

            key_part, value_part = [part.strip() for part in line.split(separator, 1)]
            for field in field_map:
                if field.get("match") != key_part:
                    continue
                target_key = field.get("key")
                if not target_key:
                    continue
                metadata[target_key] = _coerce_field_value(value_part, field.get("type", "string"))
                break

    return metadata


def extract_column_names(file_path, header_config, data_config):
    header_lines = int(header_config.get("lines", 0) or 0)
    data_header_lines = int(data_config.get("header_lines", 0) or 0)
    separator = _sanitize_separator(data_config.get("separator", ","), ",")
    data_ignore_prefix = _sanitize_prefix(data_config.get("ignore_prefix"))

    if data_header_lines <= 0:
        header_area_names = _extract_header_area_column_names(file_path, header_config, data_config)
        if header_area_names:
            return header_area_names

    # If header_lines=1, read the first row after metadata as column names.
    # If header_lines=0, there is no explicit column-name row, so detection falls back to placeholders.
    skip_rows = header_lines + max(data_header_lines - 1, 0)

    raw_row = pd.read_csv(
        file_path,
        sep=separator,
        skiprows=skip_rows,
        comment=data_ignore_prefix,
        header=None,
        nrows=1,
        engine="python",
        skipinitialspace=True,
    )

    if raw_row.empty:
        return []

    raw_values = raw_row.iloc[0].tolist()
    normalized = [
        _normalize_column_name(value, f"col{idx}")
        for idx, value in enumerate(raw_values)
    ]

    if data_header_lines <= 0:
        return [f"col{idx}" for idx in range(len(normalized))]

    return _make_unique_names(normalized)


def detect_columns_from_file(file_path, header_config, data_config):
    metadata = extract_header_metadata(file_path, header_config)
    header_area_names = _extract_header_area_column_names(file_path, header_config, data_config)
    columns = header_area_names or extract_column_names(file_path, header_config, data_config)
    data_header_lines = int(data_config.get("header_lines", 0) or 0)
    has_header_area_names = bool(header_area_names)
    return {
        "metadata": metadata,
        "raw_columns": columns,
        "column_names_from_header": data_header_lines > 0 or has_header_area_names,
    }


def build_config_column_mismatch_warnings(config_columns, original_columns, has_column_names):
    warnings = []
    if not has_column_names:
        return warnings

    x_def = config_columns.get("x", {})
    if x_def.get("type", "column") == "column" and "index" in x_def:
        x_idx = x_def.get("index")
        expected = x_def.get("source_name")
        if isinstance(x_idx, int) and expected and 0 <= x_idx < len(original_columns):
            found = str(original_columns[x_idx])
            if found != expected:
                warnings.append(
                    f"X column mismatch at index {x_idx}: expected '{expected}', found '{found}'."
                )

    for y_def in config_columns.get("y", []):
        y_idx = y_def.get("index")
        expected = y_def.get("source_name")
        if not isinstance(y_idx, int) or not expected:
            continue
        if y_idx < 0 or y_idx >= len(original_columns):
            warnings.append(
                f"Y column index {y_idx} is out of range for this file ({len(original_columns)} columns)."
            )
            continue
        found = str(original_columns[y_idx])
        if found != expected:
            display = y_def.get("name", f"index {y_idx}")
            warnings.append(
                f"Y '{display}' mismatch at index {y_idx}: expected '{expected}', found '{found}'."
            )

    return warnings
