import importlib.util
import inspect
from typing import Any
import sys
from typing import get_type_hints
from pathlib import Path
from pydantic import BaseModel
import yaml
import ctypes
from typing import Literal, Callable, Type, Any, get_type_hints, get_origin, get_args
from itertools import islice


# カスタムスクリプト属性クラス
class CustomScriptAttributes(BaseModel):
    """
    """

    id_: str = ""
    author: str = ""
    favorite: bool = False
    name: str = ""
    star: int = 0
    tags: list[str] = []
    version: int = 1

    @classmethod
    def create(cls, id_: str) -> 'CustomScriptAttributes':
        path_ = Path("scripts") / id_ / "attributes.yaml"
        instance: CustomScriptAttributes = yaml.load(path_.read_text(encoding='utf8'), Loader=yaml.Loader)
        instance.id_ = id_
        return instance

    def dump(self) -> str:
        path_ = Path("scripts") / self.id_ / "attributes.yaml"
        # 隠しファイル属性を解除
        FILE_ATTRIBUTE_HIDDEN = 0x2
        attrs = ctypes.windll.kernel32.GetFileAttributesW(str(path_))
        if attrs & FILE_ATTRIBUTE_HIDDEN:
            ctypes.windll.kernel32.SetFileAttributesW(str(path_), attrs & ~FILE_ATTRIBUTE_HIDDEN)
        # 書き込み
        path_.write_text(yaml.dump(self, allow_unicode=True), encoding='utf8')

# YAML representer（保存時）
def custom_script_attributes_representer(dumper: yaml.Dumper, data: CustomScriptAttributes):
    return dumper.represent_mapping("!CustomScriptAttributes", data.model_dump(exclude={"id_"}))

# YAML constructor（読み込み時）
def custom_script_attributes_constructor(loader: yaml.Loader, node: yaml.MappingNode):
    return CustomScriptAttributes(**loader.construct_mapping(node, deep=True))

# YAMLに登録
yaml.add_representer(CustomScriptAttributes, custom_script_attributes_representer)
yaml.add_constructor("!CustomScriptAttributes", custom_script_attributes_constructor)


# カスタムスクリプト
class CustomScript(BaseModel):
    """
    """

    id_: str
    fn: Callable[..., Any]
    attributes: CustomScriptAttributes
    default_values: dict[str, Any]
    annotations: dict[str, Any]
    kwargs: dict[str, Any]

    @classmethod
    def get_main_fn(cls, id_: str):
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

    @classmethod
    def create(cls, id_: str, **kwargs: Any):
        fn = cls.get_main_fn(id_)
        sig = inspect.signature(fn)
        parameters = list(islice(sig.parameters.items(), 4, None))
        default_values = {}
        for name, param in parameters:
            default_values[name] = None if param.default is inspect.Parameter.empty else param.default
        annotations = dict(list(get_type_hints(fn).items())[4:])
        instance = CustomScript(
            id_=id_,
            fn=fn,
            attributes=CustomScriptAttributes.create(id_),
            default_values=default_values,
            annotations=annotations,
            kwargs=kwargs
        )
        return instance
    
    def getdoc(self):
        return inspect.getdoc(self.fn) or ""
    
    def run(self, local_sync: Any, remote_sync: Any, modified_files: list[Path], removed_files: list[Path]):
        return self.fn(
            local_sync, 
            remote_sync, 
            modified_files, 
            removed_files, 
            **self.kwargs
        )

    def dump(self, path_: Path) -> str:
        # 隠しファイル属性を解除
        FILE_ATTRIBUTE_HIDDEN = 0x2
        attrs = ctypes.windll.kernel32.GetFileAttributesW(str(path_))
        if attrs & FILE_ATTRIBUTE_HIDDEN:
            ctypes.windll.kernel32.SetFileAttributesW(str(path_), attrs & ~FILE_ATTRIBUTE_HIDDEN)
        # 書き込み
        path_.write_text(yaml.dump(self, allow_unicode=True), encoding='utf8')

# YAML representer（保存時）
def custom_script_representer(dumper: yaml.Dumper, data: CustomScript):
    from scripts.custom_script import CustomScript
    return dumper.represent_mapping("!CustomScript", {
        'id_': data.id_,
        'kwargs': data.kwargs
    })

# YAML constructor（読み込み時）
def custom_script_constructor(loader: yaml.Loader, node: yaml.MappingNode):
    from scripts.custom_script import CustomScript
    values = loader.construct_mapping(node, deep=True)
    id_ = values['id_']
    kwargs = values.get('kwargs', {})
    return CustomScript.create(id_, **kwargs)

# YAMLに登録
yaml.add_representer(CustomScript, custom_script_representer)
yaml.add_constructor("!CustomScript", custom_script_constructor)


# スクリプトのまとまり
custom_script_group_path: Path = Path('config') / 'custom_script_group.yaml'
class CustomScriptGroup(BaseModel):
    """
    ユーザー設定を保持するクラス
    """

    scripts: list[CustomScript] = []

    def dump(self) -> str:
        path_ = custom_script_group_path
        # 隠しファイル属性を解除
        FILE_ATTRIBUTE_HIDDEN = 0x2
        attrs = ctypes.windll.kernel32.GetFileAttributesW(str(path_))
        if attrs & FILE_ATTRIBUTE_HIDDEN:
            ctypes.windll.kernel32.SetFileAttributesW(str(path_), attrs & ~FILE_ATTRIBUTE_HIDDEN)
        # 書き込み
        path_.write_text(yaml.dump(self, allow_unicode=True), encoding='utf8')

# YAMLシリアライズ用の representer
def general_settings_representer(dumper: yaml.Dumper, data: CustomScriptGroup):
    # custom_scripts 以外は通常の model_dump で取得
    data_dict = data.model_dump(exclude={"scripts"})
    # custom_scripts は representer 経由でシリアライズされるようにそのまま渡す
    data_dict["scripts"] = data.scripts
    return dumper.represent_mapping("!CustomScriptGroup", data_dict)

# YAMLデシリアライズ用の constructor
def general_settings_constructor(loader: yaml.Loader, node: yaml.MappingNode):
    return CustomScriptGroup(**loader.construct_mapping(node, deep=True))

# YAMLにカスタムクラスを登録
yaml.add_representer(CustomScriptGroup, general_settings_representer)
yaml.add_constructor("!CustomScriptGroup", general_settings_constructor)

# 設定初期化
custom_script_group: CustomScriptGroup
if custom_script_group_path.exists():
    custom_script_group = yaml.load(custom_script_group_path.read_text(encoding='utf8'), Loader=yaml.Loader)
else:
    custom_script_group = CustomScriptGroup()
    custom_script_group.dump()


def main():
    main_fn = CustomScript.create("01JWRCPA1E6C24YV81X9CWCWNZ").fn

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
