import pandas as pd
import uuid

class Dataset:
    """Represents a single block of data, either raw (imported) or derived (e.g., FFT)."""
    def __init__(self, name, dataframe, metadata=None, dataset_type="raw", parent_id=None):
        self.id = str(uuid.uuid4())
        self.name = name
        self.df = dataframe
        self.metadata = metadata or {}
        self.type = dataset_type      # e.g., 'raw', 'fft', 'filtered'
        self.parent_id = parent_id    # If derived, stores the ID of the dataset it was derived from
        
    def get_columns(self):
        return self.df.columns.tolist()

    def get_row_count(self):
        return len(self.df)


class DataManager:
    """Centralized repository for all datasets loaded or generated in the workspace."""
    def __init__(self):
        self.datasets = {}
        
    def add_dataset(self, name, dataframe, metadata=None, dataset_type="raw", parent_id=None):
        """Creates a new Dataset and stores it. Returns the new dataset's UUID."""
        ds = Dataset(name, dataframe, metadata, dataset_type, parent_id)
        self.datasets[ds.id] = ds
        return ds.id

    def register_dataset(self, dataset):
        """Stores an already-created Dataset instance and returns its UUID."""
        if not isinstance(dataset, Dataset):
            raise TypeError("register_dataset expects a Dataset instance")

        if dataset.id in self.datasets:
            raise ValueError(f"Dataset id already exists: {dataset.id}")

        self.datasets[dataset.id] = dataset
        return dataset.id
        
    def get_dataset(self, dataset_id):
        """Retrieves a dataset by UUID."""
        return self.datasets.get(dataset_id)
        
    def remove_dataset(self, dataset_id):
        """Deletes a dataset from memory."""
        if dataset_id in self.datasets:
            del self.datasets[dataset_id]
            return True
        return False
        
    def get_all_summaries(self):
        """Returns a list of dicts summarizing the available datasets for the UI."""
        summaries = []
        for ds_id, ds in self.datasets.items():
            summaries.append({
                "id": ds_id,
                "name": ds.name,
                "type": ds.type,
                "rows": ds.get_row_count(),
                "columns": ds.get_columns()
            })
        return summaries
