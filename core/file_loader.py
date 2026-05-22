import os
import json
import pandas as pd
from pandas.errors import ParserError
from .config_manager import ConfigManager
from .conversion_handlers import apply_conversions
from .downsampling import downsample, DownsamplingError
from .header_detector import (
    extract_header_metadata,
    build_config_column_mismatch_warnings,
)

class FileLoader:
    """Handles the Loading and Parsing of Data Files based on JSON Configurations."""

    @staticmethod
    def _normalize_postprocess_names(values):
        names = []
        seen = set()
        for value in values or []:
            name = str(value).strip()
            if not name or name in seen:
                continue
            names.append(name)
            seen.add(name)
        return names

    @staticmethod
    def _apply_postprocess_columns(df, postprocess_cfg):
        if not isinstance(postprocess_cfg, dict):
            return [], []

        deleted = FileLoader._normalize_postprocess_names(postprocess_cfg.get("deleted", []))
        hidden = FileLoader._normalize_postprocess_names(postprocess_cfg.get("hidden", []))
        warnings = []

        for col_name in deleted:
            if col_name in df.columns:
                df.drop(columns=[col_name], inplace=True)
            else:
                warnings.append(f"Postprocess delete skipped: column '{col_name}' was not found.")

        deleted_set = set(deleted)
        hidden_columns = []
        for col_name in hidden:
            if col_name in deleted_set:
                continue
            if col_name in df.columns:
                hidden_columns.append(col_name)
            else:
                warnings.append(f"Postprocess hide skipped: column '{col_name}' was not found.")

        return hidden_columns, warnings
    
    @staticmethod
    def load_datalogs(file_paths, config_filename):
        """
        Loads multiple datalog files and merges them into a single dataset.
        Assumes all files share the same configuration.
        """
        all_dataframes = []
        combined_metadata = {}
        combined_hidden_columns = []

        for path in file_paths:
            result = FileLoader.load_datalog(path, config_filename)
            df = result['dataframe']
            metadata = result['metadata']
            hidden_columns = result.get('hidden_columns', [])
            
            # Add a source file column to distinguish data
            df['_source_file'] = os.path.basename(path)
            
            all_dataframes.append(df)
            
            # Simple metadata merge (last one wins for conflicting keys)
            combined_metadata.update(metadata)
            for col_name in hidden_columns:
                if col_name not in combined_hidden_columns:
                    combined_hidden_columns.append(col_name)

        if not all_dataframes:
            return None

        # Concatenate all dataframes
        # We use ignore_index=True if we want a continuous index, 
        # but if the data is time-series and needs to be aligned, 
        # we might need more complex logic later. For now, simple append.
        combined_df = pd.concat(all_dataframes, ignore_index=True)
        
        return {
            'metadata': combined_metadata,
            'dataframe': combined_df,
            'hidden_columns': combined_hidden_columns,
        }

    @staticmethod
    def load_datalog(file_path, config_filename):
        """
        Loads a datalog file using rules defined in the config.
        Returns a dictionary with 'metadata' and 'dataframe'.
        """
        # Load and implicitly sanitize the config setup using ConfigManager
        config = ConfigManager.load_config(config_filename)
            
        header_config = config.get("header", {})
        data_config = config.get("data", {})
        conversions = config.get("conversions", [])

        metadata = {}
        header_enabled = bool(header_config.get("enabled", False))
        header_lines = int(header_config.get("lines", 0) or 0)
        header_skip = header_lines if header_enabled else 0

        # 1. Parse Header Metadata
        if header_enabled:
            metadata = extract_header_metadata(file_path, header_config)
                                
        # 2. Parse Data block
        data_sep = data_config.get("separator", ",")
        if data_sep in (None, ""):
            data_sep = ","
        data_ignore_prefix = data_config.get("ignore_prefix", None)

        has_col_names = bool(header_config.get("column_names_from_header", False))
        has_header_row = has_col_names and header_skip > 0
        max_rows = int(data_config.get("total_data_lines", 0) or 0)
        nrows = max_rows if max_rows > 0 else None

        # If header row is enabled, treat the last header-area line as DataFrame column names.
        if has_header_row:
            skip_total = header_skip - 1
            header_row = 0
        else:
            skip_total = header_skip
            header_row = None

        # Determine if we have column names to read from the CSV
        

        print(f"--- DEBUG LOAD PARAMS ---")
        print(f"File Path: {file_path}")
        print(f"Separator: {repr(data_sep)}")
        print(f"Skip Rows: {skip_total}")
        print(f"Comment/Ignore Prefix: {repr(data_ignore_prefix)}")
        print(f"Header Row: {header_row}")
        print(f"-------------------------")

        # Load the CSV
        read_csv_kwargs = dict(
            sep=data_sep,
            skiprows=skip_total,
            comment=data_ignore_prefix,
            header=header_row,
            # Prevent pandas from auto-promoting the first data field to DataFrame index
            # when header/data field counts differ (e.g., trailing delimiters in data rows).
            index_col=False,
            nrows=nrows,
            engine="python",
            skipinitialspace=True,
        )

        try:
            df = pd.read_csv(
                file_path,
                **read_csv_kwargs,
            )
        except ParserError as e:
            # pandas treats multi-char separators as regex in python engine,
            # which can ignore CSV quoting rules. A common misconfiguration is
            # using ", " instead of ",".
            cleaned_sep = data_sep.strip() if isinstance(data_sep, str) else data_sep
            can_retry_with_cleaned_sep = (
                isinstance(data_sep, str)
                and data_sep != cleaned_sep
                and isinstance(cleaned_sep, str)
                and len(cleaned_sep) == 1
            )

            if can_retry_with_cleaned_sep and "multi-char delimiter" in str(e):
                print(
                    f"Retrying read_csv with normalized separator: {repr(cleaned_sep)} "
                    f"(from {repr(data_sep)})"
                )
                read_csv_kwargs["sep"] = cleaned_sep
                df = pd.read_csv(file_path, **read_csv_kwargs)
            else:
                print(f"Pandas read_csv Exception: {type(e).__name__}: {str(e)}")
                raise
        except Exception as e:
            print(f"Pandas read_csv Exception: {type(e).__name__}: {str(e)}")
            raise

        print(f"--- DEBUG LOAD RESULT ---")
        print(f"Loaded DataFrame shape: {df.shape}")
        print(f"Original Columns: {df.columns.tolist()}")
        print(f"-------------------------")
        
        # Give column standard abstract names like "col0", "col1" if no names exist in header.
        original_cols = df.columns.tolist()
        if not has_header_row:
            df.columns = [f"col{i}" for i in range(len(df.columns))]
        
        # 3. Map Standard/Domain Column Names FIRST
        # This allows users to write formulas using their mapped names (e.g., "TC1 / 1000")
        columns_mapping = data_config.get("columns", {})
        rename_map = {}
        mapping_warnings = []

        def resolve_source_column(index_value, axis_label):
            """Resolve config index to current df column name and report mapping issues."""
            try:
                idx = int(index_value)
            except (TypeError, ValueError):
                mapping_warnings.append(
                    f"{axis_label} column index '{index_value}' is not a valid integer."
                )
                return None, None

            if idx < 0:
                mapping_warnings.append(
                    f"{axis_label} column index {idx} is negative and cannot be mapped."
                )
                return None, idx

            if has_header_row:
                if idx >= len(original_cols):
                    mapping_warnings.append(
                        f"{axis_label} column index {idx} is out of range for this file "
                        f"({len(original_cols)} columns)."
                    )
                    return None, idx
                source_col = original_cols[idx]
            else:
                source_col = f"col{idx}"

            if source_col not in df.columns:
                mapping_warnings.append(
                    f"{axis_label} source column '{source_col}' was not found in imported data."
                )
                return None, idx

            return source_col, idx
        
        # Map X Axis
        x_def = columns_mapping.get("x", {})
        x_type = x_def.get("type", "column")  # Default to "column" for backward compatibility
        
        if x_type == "column":
            # Use the data from the specified column index
            if "index" in x_def:
                c_name, _x_idx = resolve_source_column(x_def["index"], "X")
                if c_name in df.columns:
                    rename_map[c_name] = x_def.get("name", "x")
        elif x_type == "index":
            # Generate an index column (row numbers)
            df.insert(0, "_x_index", range(len(df)))
            rename_map["_x_index"] = x_def.get("name", "x")
                
        # Map Y Axes
        y_defs = columns_mapping.get("y", [])
        for y_def in y_defs:
            if "index" in y_def:
                c_name, y_idx = resolve_source_column(y_def["index"], f"Y '{y_def.get('name', 'column')}'")
                y_title = y_def.get("name", f"y_{y_idx}") if y_idx is not None else y_def.get("name", "y")
                if c_name in df.columns:
                    rename_map[c_name] = y_title
                    
        df.rename(columns=rename_map, inplace=True)
        
        # Resolve x-axis column name (used by downsampling service)
        x_col_name = x_def.get("name", "x") if x_type != "index" else x_def.get("name", "x")

        # 4a. DOWNSAMPLING — before_conversions (default: faster for large files)
        ds_config    = config.get("downsampling", {"enabled": False})
        ds_timing    = ds_config.get("timing", "before_conversions")
        downsample_result_meta = None
        downsampling_error     = None

        if ds_config.get("enabled", False) and ds_timing == "before_conversions":
            try:
                df, downsample_result_meta = downsample(df, ds_config, x_col_name)
            except DownsamplingError as exc:
                downsampling_error = str(exc)

        # 4b. Apply Transformations / Conversions AFTER renaming
        # Conversions run sequentially — a later step can reference a column
        # produced by an earlier step.  Failures are collected and returned
        # to the caller rather than silently ignored.
        conversion_errors = apply_conversions(df, conversions)

        # 4c. DOWNSAMPLING — after_conversions (all derived columns included)
        if ds_config.get("enabled", False) and ds_timing == "after_conversions":
            try:
                df, downsample_result_meta = downsample(df, ds_config, x_col_name)
            except DownsamplingError as exc:
                downsampling_error = str(exc)

        # 5. Post-process columns (after all conversions/downsampling)
        postprocess_cfg = config.get("postprocess_columns", {})
        hidden_columns, postprocess_warnings = FileLoader._apply_postprocess_columns(df, postprocess_cfg)

        column_mismatch_warnings = build_config_column_mismatch_warnings(
            data_config.get("columns", {}),
            original_cols,
            has_header_row,
        )
        if mapping_warnings:
            column_mismatch_warnings.extend(mapping_warnings)
                
        return {
            "metadata": metadata,
            "dataframe": df,
            "conversion_errors": conversion_errors,
            "column_mismatch_warnings": column_mismatch_warnings,
            "downsampling_meta": downsample_result_meta,
            "downsampling_error": downsampling_error,
            "hidden_columns": hidden_columns,
            "postprocess_warnings": postprocess_warnings,
        }
