"""Example dataset process plugin that runs FFT on numeric columns.

The runner passes a full Dataset object into run(dataset, context=None), and the
plugin returns a new Dataset instance linked back to the source dataset.
"""

from core.data_manager import Dataset
from core.fft import FFTAnalyzer


PLUGIN_INFO = {
    "name": "FFT Example",
    "description": "Runs FFT on all numeric columns in a dataset.",
}


def _resolve_sample_rate(dataset, context):
    if context is None:
        context = {}

    value = context.get("sample_rate_hz")
    if value is None:
        value = dataset.metadata.get("sample_rate_hz", 2500000)

    try:
        sample_rate = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("sample_rate_hz must be a positive number") from exc

    if sample_rate <= 0:
        raise ValueError("sample_rate_hz must be a positive number")

    return sample_rate


def run(dataset, context=None):
    if not isinstance(dataset, Dataset):
        raise TypeError("run expects a Dataset instance")

    context = context or {}

    numeric_cols = [
        col for col in dataset.df.select_dtypes(include="number").columns.tolist()
        if col != "_source_file"
    ]
    if not numeric_cols:
        raise ValueError("No numeric columns were found for FFT processing.")

    sample_rate = _resolve_sample_rate(dataset, context)
    unit = str(context.get("unit") or dataset.metadata.get("unit", "unit")).strip() or "unit"

    start_row = int(context.get("row_start", 0) or 0)
    end_row_value = context.get("row_end")
    if end_row_value is None:
        end_row = len(dataset.df)
    else:
        end_row = int(end_row_value)

    if start_row < 0 or end_row <= start_row:
        raise ValueError("row_start must be smaller than row_end")

    subset_df = dataset.df.iloc[start_row:end_row]
    if subset_df.empty:
        raise ValueError("Selected row range produced an empty dataset")

    fft_df = FFTAnalyzer.compute(subset_df, numeric_cols, sample_rate, unit)
    metadata = FFTAnalyzer.build_metadata(dataset, numeric_cols, sample_rate, unit)
    metadata.update(
        {
            "plugin_name": PLUGIN_INFO["name"],
            "plugin_file": __file__,
            "row_start": start_row,
            "row_end": end_row,
            "source_dataset_type": dataset.type,
        }
    )

    result_name = f"{dataset.name} — FFT Example"
    return Dataset(
        result_name,
        fft_df,
        metadata=metadata,
        dataset_type="fft",
        parent_id=dataset.id,
    )
