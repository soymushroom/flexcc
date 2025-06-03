import importlib.util
import inspect
import sys
from typing import get_type_hints
from pathlib import Path
from pydantic import BaseModel
import yaml
import ctypes


# カスタムスクリプト属性クラス
class CustomScriptAttributes(BaseModel):
    author: str
    favorite: bool
    name: str
    star: int
    tags: list[str]
    version: int


    @classmethod
    def create(cls, id_: str) -> 'CustomScriptAttributes':
        path_ = Path("scripts") / id_ / "attributes.yaml"
        return yaml.load(path_.read_text(encoding='utf8'), Loader=yaml.Loader)


    def dump(self, path_: Path) -> str:
        # 隠しファイル属性を解除
        FILE_ATTRIBUTE_HIDDEN = 0x2
        attrs = ctypes.windll.kernel32.GetFileAttributesW(str(path_))
        if attrs & FILE_ATTRIBUTE_HIDDEN:
            ctypes.windll.kernel32.SetFileAttributesW(str(path_), attrs & ~FILE_ATTRIBUTE_HIDDEN)
        # 書き込み
        path_.write_text(yaml.dump(self, allow_unicode=True), encoding='utf8')


# YAML representer（保存時）
def custom_script_attributes_representer(dumper: yaml.Dumper, data: CustomScriptAttributes):
    return dumper.represent_mapping("!CustomScriptAttributes", data.model_dump())

# YAML constructor（読み込み時）
def custom_script_attributes_constructor(loader: yaml.Loader, node: yaml.MappingNode):
    return CustomScriptAttributes(**loader.construct_mapping(node, deep=True))

# YAMLに登録
yaml.add_representer(CustomScriptAttributes, custom_script_attributes_representer)
yaml.add_constructor("!CustomScriptAttributes", custom_script_attributes_constructor)


def load_main_function(id_: str):
    # モジュールの取得
    if id_ in sys.modules.keys():
        module = sys.modules[id_]
    else:
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
