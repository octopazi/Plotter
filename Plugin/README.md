# Plugin Script Writing Guide

This folder stores dataset-processing scripts for Plotter.

Use the app menu path:
- Script -> Dataset process

The runner discovers all Python files in this folder.

## Trust and Safety Model

Plugin scripts are trusted local Python code.
- Scripts run with normal Python access.
- Scripts can import modules and access files available to your environment.
- Only run scripts from trusted sources.

## Script Discovery Rules

A file is listed in the script picker if:
- Filename ends with .py
- Filename does not start with _

Examples:
- valid: my_filter.py
- hidden from picker: _helpers.py

## Required Function Contract

Your script must expose one callable entry point with one of these names:
- run
- process_dataset
- main

Preferred signatures:
```python
def run(dataset):
    ...

# or
def run(dataset, context=None):
    ...
```

The first argument must be a Dataset object from core.data_manager.

## Input and Output Requirements

Input:
- dataset is a full Dataset object with fields:
  - id
  - name
  - df (pandas DataFrame)
  - metadata (dict)
  - type
  - parent_id

Output:
- Return a NEW Dataset object.
- Do not return the original dataset object.
- Do not return a DataFrame directly.

A safe output pattern:
```python
from core.data_manager import Dataset

return Dataset(
    name=f"{dataset.name} - my process",
    dataframe=result_df,
    metadata=result_metadata,
    dataset_type="processed",
    parent_id=dataset.id,
)
```

Notes:
- If parent_id is None, Plotter will set it to the source dataset id.
- If metadata is None, Plotter will replace it with {}.
- Plotter also appends script metadata fields automatically.

## Context Dictionary (Optional)

If your function accepts a second argument, Plotter passes a context dictionary.

Current keys passed by the dialog and runner:
- selected_dataset_ids: list of all dataset ids selected in this run
- source_dataset_id: current source dataset id
- source_dataset_name: current source dataset name
- script_filename: plugin filename
- script_path: absolute path of the plugin
- entry_point: function name used (run/process_dataset/main)

Example usage:
```python
def run(dataset, context=None):
    context = context or {}
    source_name = context.get("source_dataset_name", dataset.name)
    ...
```

## Minimal Working Example

```python
from core.data_manager import Dataset


def run(dataset, context=None):
    context = context or {}

    # Work on a copy to avoid modifying the source dataset in place.
    out_df = dataset.df.copy()

    # Example transform: keep numeric columns only
    out_df = out_df.select_dtypes(include="number")
    if out_df.empty:
        raise ValueError("No numeric columns found.")

    out_meta = dict(dataset.metadata)
    out_meta["plugin"] = "numeric_only"

    return Dataset(
        name=f"{dataset.name} - numeric only",
        dataframe=out_df,
        metadata=out_meta,
        dataset_type="processed",
        parent_id=dataset.id,
    )
```

## Recommended Practices

- Validate input early and raise clear exceptions.
- Prefer returning a transformed copy of dataset.df.
- Keep metadata meaningful: include parameter values and source hints.
- Use descriptive dataset_type values (processed, filtered, fft, etc.).
- Keep script files small and focused.

## Error Handling in UI

For each selected dataset, Plotter runs your script once.
- Successes create new datasets.
- Exceptions are collected and shown in Script Warnings.
- If all selected datasets fail, no new dataset is added.

## FFT Reference Plugin

Use the included FFT plugin as a real reference implementation:
- Plugin/fft_example.py

It demonstrates:
- validating Dataset input
- reading optional context values
- using existing core analysis code
- returning a new Dataset with linked parent_id and metadata

## Troubleshooting

Problem: Script not shown in picker
- Ensure file is inside Plugin folder
- Ensure filename ends with .py
- Ensure filename does not start with _

Problem: "must return a Dataset instance"
- Return Dataset(...), not DataFrame

Problem: "returned the source dataset object"
- Create a new Dataset instead of returning dataset directly

Problem: Duplicate dataset id error
- Usually caused by reusing an existing Dataset object
- Always create a new Dataset() for output

## Quick Author Checklist

- File is in Plugin folder and ends with .py
- Entry point exists: run/process_dataset/main
- Function takes dataset (and optional context)
- Returns a new Dataset object
- Handles bad input with clear errors
- Adds useful metadata
