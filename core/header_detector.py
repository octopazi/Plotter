import pandas as pd
import re


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


def _read_header_lines(file_path, header_config):
    if not bool(header_config.get("enabled", False)):
        return []

    header_lines = int(header_config.get("lines", 0) or 0)
    if header_lines <= 0:
        return []

    output = []
    with open(file_path, "r", encoding="utf-8") as file_obj:
        for _ in range(header_lines):
            line = file_obj.readline()
            if not line:
                break
            output.append(line.rstrip("\r\n"))
    return output


def _extract_simple_mode_column_names(file_path, header_config, data_config):
    lines = _read_header_lines(file_path, header_config)
    if not lines:
        return [], None

    method = str(header_config.get("simple_select_method", "line_number") or "line_number").strip().lower()
    selected_idx = None
    selected_line = None

    if method == "marker":
        marker_text = str(header_config.get("simple_marker_text", "") or "")
        if not marker_text:
            return [], None
        for idx, line in enumerate(lines):
            if marker_text in line:
                selected_idx = idx
                selected_line = line
                break
    else:
        configured_line = int(header_config.get("simple_column_line_number", len(lines)) or len(lines))
        if configured_line < 1 or configured_line > len(lines):
            return [], None
        selected_idx = configured_line - 1
        selected_line = lines[selected_idx]

    if selected_line is None:
        return [], None

    default_sep = _sanitize_separator(data_config.get("separator", ","), ",")
    simple_sep = _sanitize_separator(header_config.get("simple_separator", ""), default_sep)
    if simple_sep in (None, ""):
        simple_sep = default_sep

    pieces = [piece.strip() for piece in str(selected_line).split(simple_sep)]
    pieces = [piece for piece in pieces if piece != ""]
    if len(pieces) <= 1:
        return [], selected_idx

    normalized = [_normalize_column_name(value, f"col{idx}") for idx, value in enumerate(pieces)]
    return _make_unique_names(normalized), selected_idx


def _extract_expert_mode_column_names(file_path, header_config):
    lines = _read_header_lines(file_path, header_config)
    if not lines:
        return []

    pattern_text = str(header_config.get("expert_regex", "") or "").strip()
    if not pattern_text:
        return []

    try:
        pattern = re.compile(pattern_text)
    except re.error as exc:
        raise ValueError(f"Expert regex is invalid: {exc}")

    name_group = int(header_config.get("expert_name_group", 1) or 1)
    index_group_raw = header_config.get("expert_index_group", "")
    index_group = None
    if index_group_raw not in (None, ""):
        index_group = int(index_group_raw)

    prefix = str(header_config.get("expert_line_prefix", "") or "")

    matched = []
    seq = 0
    for line in lines:
        candidate = line.strip()
        if prefix and not candidate.startswith(prefix):
            continue

        found = pattern.search(candidate)
        if not found:
            continue

        try:
            name = str(found.group(name_group)).strip()
        except IndexError:
            raise ValueError(
                f"expert_name_group={name_group} does not exist in the regex capture groups."
            )

        if not name:
            continue

        idx_value = None
        if index_group is not None:
            try:
                idx_text = found.group(index_group)
            except IndexError:
                raise ValueError(
                    f"expert_index_group={index_group} does not exist in the regex capture groups."
                )
            if idx_text is not None and str(idx_text).strip() != "":
                try:
                    idx_value = int(str(idx_text).strip())
                except ValueError:
                    idx_value = None

        matched.append((idx_value if idx_value is not None else seq, seq, name))
        seq += 1

    if not matched:
        return []

    matched.sort(key=lambda item: (item[0], item[1]))
    ordered_names = [name for _idx, _seq, name in matched]
    normalized = [_normalize_column_name(value, f"col{idx}") for idx, value in enumerate(ordered_names)]
    return _make_unique_names(normalized)


def _extract_configured_column_names(file_path, header_config, data_config):
    mode = str(header_config.get("column_name_mode", "simple") or "simple").strip().lower()
    lines = _read_header_lines(file_path, header_config)

    if mode == "expert":
        names = _extract_expert_mode_column_names(file_path, header_config)
        return names, False

    names, selected_idx = _extract_simple_mode_column_names(file_path, header_config, data_config)
    can_use_header_row = bool(names) and selected_idx is not None and lines and selected_idx == (len(lines) - 1)
    return names, can_use_header_row


def extract_header_metadata(file_path, header_config):
    metadata = {}
    if not header_config.get("enabled", False):
        return metadata

    header_lines = int(header_config.get("lines", 0) or 0)
    separator = _sanitize_separator(
        header_config.get("simple_separator", header_config.get("separator", ":")),
        ":",
    )
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
    header_enabled = bool(header_config.get("enabled", False))
    header_lines = int(header_config.get("lines", 0) or 0)
    header_skip = header_lines if header_enabled else 0
    separator = _sanitize_separator(data_config.get("separator", ","), ",")
    data_ignore_prefix = _sanitize_prefix(data_config.get("ignore_prefix"))

    configured_names, _can_use_header_row = _extract_configured_column_names(
        file_path, header_config, data_config
    )
    if configured_names:
        return configured_names

    # Read the first data row after the header block to estimate column count.
    skip_rows = header_skip

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

    return [f"col{idx}" for idx in range(len(normalized))]


def detect_columns_from_file(file_path, header_config, data_config):
    metadata = extract_header_metadata(file_path, header_config)
    configured_names, can_use_header_row = _extract_configured_column_names(
        file_path, header_config, data_config
    )
    columns = configured_names or extract_column_names(file_path, header_config, data_config)
    return {
        "metadata": metadata,
        "raw_columns": columns,
        "column_names_from_header": can_use_header_row,
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
