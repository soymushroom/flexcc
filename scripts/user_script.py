import importlib.util
import inspect
import sys
from typing import get_type_hints
from pathlib import Path


def load_main_function(id_: str):
    file_path = Path("scripts") / id_ / "main.py"
    spec = importlib.util.spec_from_file_location(id_, str(file_path))
    module = importlib.util.module_from_spec(spec)
    sys.modules[id_] = module
    spec.loader.exec_module(module)
    # main関数があるかチェック
    if not hasattr(module, "main"):
        raise Exception("No main functions")
    return module.main


def main():
    main_fn = load_main_function("01JWRCPA1E6C24YV81X9CWCWNZ")

    print("=== Docstring ===")
    print(inspect.getdoc(main_fn) or "None")
    print()

    print("=== Arguments ===")
    sig = inspect.signature(main_fn)
    type_hints = get_type_hints(main_fn)
    for name, param in sig.parameters.items():
        annotation = type_hints.get(name, param.annotation)
        print(f"- Name: {name}")
        print(f"  Type: {annotation}")
    print()

    print("=== Run ===")
    main_fn([Path("app.py"), Path("ui") / "console.py"], [])

if __name__ == "__main__":
    main()
