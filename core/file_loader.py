import os
import json
import pandas as pd
from .config_manager import ConfigManager
from .conversion_handlers import apply_conversions

class FileLoader:
    """Handles the Loading and Parsing of Data Files based on JSON Configurations."""
    
    @staticmethod
    def load_datalogs(file_paths, config_filename):
        """
        Loads multiple datalog files and merges them into a single dataset.
        Assumes all files share the same configuration.
        """
        all_dataframes = []
        combined_metadata = {}

        for path in file_paths:
            result = FileLoader.load_datalog(path, config_filename)
            df = result['dataframe']
            metadata = result['metadata']
            
            # Add a source file column to distinguish data
            df['_source_file'] = os.path.basename(path)
            
            all_dataframes.append(df)
            
            # Simple metadata merge (last one wins for conflicting keys)
            combined_metadata.update(metadata)

        if not all_dataframes:
            return None

        # Concatenate all dataframes
        # We use ignore_index=True if we want a continuous index, 
        # but if the data is time-series and needs to be aligned, 
        # we might need more complex logic later. For now, simple append.
        combined_df = pd.concat(all_dataframes, ignore_index=True)
        
        return {
            'metadata': combined_metadata,
            'dataframe': combined_df
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
        header_lines = header_config.get("lines", 0)
        
        # 1. Parse Header
        if header_config.get("enabled", False):
            with open(file_path, 'r', encoding='utf-8') as f:
                for i in range(header_lines):
                    line = f.readline().strip()
                    
                    # Handle ignore prefix for header
                    ignore_prefix = header_config.get("ignore_prefix")
                    if ignore_prefix and line.startswith(ignore_prefix):
                        line = line[len(ignore_prefix):].strip()
                        
                    sep = header_config.get("separator", ":")
                    if sep in line:
                        parts = line.split(sep, 1)
                        key_part, val_part = parts[0].strip(), parts[1].strip()
                        
                        # Match fields with config mapping
                        for field in header_config.get("fields", []):
                            if field.get("match") == key_part:
                                val = val_part
                                if field.get("type") == "float":
                                    try:
                                        val = float(val_part)
                                    except ValueError:
                                        pass
                                metadata[field.get("key")] = val
                                
        # 2. Parse Data block
        data_sep = data_config.get("separator", ",")
        data_ignore_prefix = data_config.get("ignore_prefix", None)
            
        has_col_names = header_config.get("column_names_from_header", False)
        
        # We start skipping lines corresponding to the metadata block
        # plus any additional lines specified by "header_lines" in the data object.
        skip_total = header_lines + data_config.get("header_lines", 0)
        
        # Determine if we have column names to read from the CSV
        header_row = 0 if has_col_names else None 

        print(f"--- DEBUG LOAD PARAMS ---")
        print(f"File Path: {file_path}")
        print(f"Separator: {repr(data_sep)}")
        print(f"Skip Rows: {skip_total}")
        print(f"Comment/Ignore Prefix: {repr(data_ignore_prefix)}")
        print(f"Header Row: {header_row}")
        print(f"-------------------------")

        # Load the CSV
        try:
            df = pd.read_csv(
                file_path,
                sep=data_sep,
                skiprows=skip_total,
                comment=data_ignore_prefix,
                header=header_row,
                engine="python",
                skipinitialspace=True
            )
        except Exception as e:
            print(f"Pandas read_csv Exception: {type(e).__name__}: {str(e)}")
            raise

        print(f"--- DEBUG LOAD RESULT ---")
        print(f"Loaded DataFrame shape: {df.shape}")
        print(f"Original Columns: {df.columns.tolist()}")
        print(f"-------------------------")
        
        # Give column standard abstract names like "col0", "col1" if no names exist in header.
        original_cols = df.columns.tolist()
        if not has_col_names:
            df.columns = [f"col{i}" for i in range(len(df.columns))]
        
        # 3. Map Standard/Domain Column Names FIRST
        # This allows users to write formulas using their mapped names (e.g., "TC1 / 1000")
        columns_mapping = data_config.get("columns", {})
        rename_map = {}
        
        # Map X Axis
        x_def = columns_mapping.get("x", {})
        x_type = x_def.get("type", "column")  # Default to "column" for backward compatibility
        
        if x_type == "column":
            # Use the data from the specified column index
            if "index" in x_def:
                x_idx = x_def["index"]
                c_name = f"col{x_idx}" if not has_col_names else original_cols[x_idx]
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
                y_idx = y_def["index"]
                y_title = y_def.get("name", f"y_{y_idx}")
                c_name = f"col{y_idx}" if not has_col_names else original_cols[y_idx]
                if c_name in df.columns:
                    rename_map[c_name] = y_title
                    
        df.rename(columns=rename_map, inplace=True)
        
        # 4. Apply Transformations / Conversions AFTER renaming
        # Conversions run sequentially — a later step can reference a column
        # produced by an earlier step.  Failures are collected and returned
        # to the caller rather than silently ignored.
        conversion_errors = apply_conversions(df, conversions)
                
        return {
            "metadata": metadata,
            "dataframe": df,
            "conversion_errors": conversion_errors
        }
