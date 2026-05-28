import importlib.util
import inspect
import os
import uuid

from core.data_manager import Dataset


class ScriptManager:
    """Loads and runs trusted local dataset-processing scripts from Plugin/."""

    @staticmethod
    def get_script_dir():
        return os.path.join(os.getcwd(), "Plugin")

    @staticmethod
    def ensure_script_dir():
        script_dir = ScriptManager.get_script_dir()
        os.makedirs(script_dir, exist_ok=True)
        return script_dir

    @staticmethod
    def get_available_scripts():
        script_dir = ScriptManager.ensure_script_dir()
        scripts = []

        for filename in sorted(os.listdir(script_dir)):
            if not filename.endswith(".py"):
                continue
            if filename.startswith("_"):
                continue

            scripts.append(
                {
                    "filename": filename,
                    "stem": os.path.splitext(filename)[0],
                    "path": os.path.join(script_dir, filename),
                }
            )

        return scripts

    @staticmethod
    def get_script_path(filename):
        return os.path.join(ScriptManager.ensure_script_dir(), filename)

    @staticmethod
    def _load_module(script_path):
        if not os.path.exists(script_path):
            raise FileNotFoundError(f"Script not found: {script_path}")

        module_name = f"plotter_plugin_{uuid.uuid4().hex}"
        spec = importlib.util.spec_from_file_location(module_name, script_path)
        if spec is None or spec.loader is None:
            raise ImportError(f"Could not load script: {script_path}")

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    @staticmethod
    def _get_runner(module):
        for attr_name in ("run", "process_dataset", "main"):
            runner = getattr(module, attr_name, None)
            if callable(runner):
                return runner, attr_name
        raise AttributeError(
            "Script must define a callable entry point named run(dataset), "
            "process_dataset(dataset), or main(dataset)."
        )

    @staticmethod
    def load_script(script_filename):
        script_path = ScriptManager.get_script_path(script_filename)
        module = ScriptManager._load_module(script_path)
        runner, entry_name = ScriptManager._get_runner(module)
        return module, runner, entry_name, script_path

    @staticmethod
    def _invoke_runner(runner, dataset, context):
        try:
            signature = inspect.signature(runner)
        except (TypeError, ValueError):
            return runner(dataset, context)

        params = list(signature.parameters.values())
        if len(params) <= 1:
            return runner(dataset)

        second_param = params[1]
        if second_param.kind == inspect.Parameter.KEYWORD_ONLY:
            return runner(dataset, context=context)

        if any(p.kind == inspect.Parameter.VAR_KEYWORD for p in params):
            return runner(dataset, context=context)

        return runner(dataset, context)

    @staticmethod
    def run_script(script_filename, dataset, context=None):
        if not isinstance(dataset, Dataset):
            raise TypeError("run_script expects a Dataset instance")

        _, runner, entry_name, script_path = ScriptManager.load_script(script_filename)
        runtime_context = dict(context or {})
        runtime_context.setdefault("script_filename", script_filename)
        runtime_context.setdefault("script_path", script_path)
        runtime_context.setdefault("entry_point", entry_name)

        result = ScriptManager._invoke_runner(runner, dataset, runtime_context)
        if not isinstance(result, Dataset):
            raise TypeError(
                f"Script '{script_filename}' must return a Dataset instance, got {type(result).__name__}."
            )

        if result.id == dataset.id:
            raise ValueError(
                f"Script '{script_filename}' returned the source dataset object. "
                "Please create and return a new Dataset instance."
            )

        if result.parent_id is None:
            result.parent_id = dataset.id

        if result.metadata is None:
            result.metadata = {}

        result.metadata.setdefault("script_filename", script_filename)
        result.metadata.setdefault("script_path", script_path)
        result.metadata.setdefault("script_entry_point", entry_name)
        result.metadata.setdefault("script_source_id", dataset.id)
        result.metadata.setdefault("script_source_name", dataset.name)

        return result
