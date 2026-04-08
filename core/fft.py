import numpy as np
import pandas as pd


class FFTAnalyzer:
    """
    Performs FFT analysis on one or more signal columns from a DataFrame.

    The logic is adapted from Sample/FFT.py and integrated with the project's
    DataManager/Dataset data structures.

    FFT Output Columns (per signal):
        - Frequency (Hz)
        - <signal>_Mag (<unit>)       : Normalised RMS amplitude spectrum
        - <signal>_Mag_CPK (<unit>)   : Cumulative peak (CPK) of magnitude
        - <signal>_Phase (deg)        : Phase angle in degrees
    """

    @staticmethod
    def compute(dataframe: pd.DataFrame, signal_columns: list[str],
                sample_rate: float, unit: str = "unit") -> pd.DataFrame:
        """
        Run FFT on the selected signal columns and return a combined result DataFrame.

        Parameters
        ----------
        dataframe      : Source DataFrame that contains the signal columns.
        signal_columns : List of column names to transform (must be numeric).
        sample_rate    : Sampling frequency in Hz.
        unit           : Physical unit label used in output column names.

        Returns
        -------
        pd.DataFrame with columns:
            Frequency (Hz), <sig>_Mag (<unit>), <sig>_Mag_CPK (<unit>), <sig>_Phase (deg)
            … repeated for each signal in signal_columns.
        """
        if not signal_columns:
            raise ValueError("No signal columns specified for FFT.")

        result_df = None

        for sig in signal_columns:
            if sig not in dataframe.columns:
                raise KeyError(f"Column '{sig}' not found in the dataset.")

            raw = dataframe[sig].dropna().to_numpy(dtype=float)
            sample_length = len(raw)

            if sample_length < 2:
                raise ValueError(f"Column '{sig}' has fewer than 2 data points.")

            # --- Core FFT (mirrors Sample/FFT.py logic exactly) ---
            fft_vals = np.fft.rfft(raw)

            # Normalised RMS magnitude spectrum
            fft_vals_norm = np.abs(fft_vals) / sample_length * (2 ** 0.5)
            fft_vals_norm[0] /= (2 ** 0.5)   # DC component correction

            # Phase in degrees
            fft_phase = np.degrees(np.angle(fft_vals))

            # Cumulative peak (CPK)
            n_bins = len(fft_vals_norm)
            fft_vals_cpk = np.zeros(n_bins)
            for j in range(1, n_bins):
                fft_vals_cpk[j] = (fft_vals_norm[j] ** 2 + fft_vals_cpk[j - 1] ** 2) ** 0.5

            # Frequency axis
            fft_freq = np.fft.rfftfreq(sample_length, d=1.0 / sample_rate)

            # Build per-signal columns
            sig_df = pd.DataFrame({
                f"{sig}_Mag ({unit})":      fft_vals_norm,
                f"{sig}_Mag_CPK ({unit})":  fft_vals_cpk,
                f"{sig}_Phase (deg)":       fft_phase,
            })

            if result_df is None:
                result_df = pd.DataFrame({"Frequency (Hz)": fft_freq})

            result_df = pd.concat([result_df, sig_df], axis=1)

        return result_df

    @staticmethod
    def build_metadata(source_dataset, signal_columns: list[str],
                       sample_rate: float, unit: str) -> dict:
        """
        Returns a metadata dict to attach to the resulting FFT Dataset,
        consistent with how 'raw' datasets store metadata.
        """
        return {
            "fft_source_id":   source_dataset.id,
            "fft_source_name": source_dataset.name,
            "signal_columns":  signal_columns,
            "sample_rate_hz":  sample_rate,
            "unit":            unit,
        }
