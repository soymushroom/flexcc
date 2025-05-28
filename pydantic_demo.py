from __future__ import annotations
from abc import ABC
from pydantic import BaseModel, field_validator
import yaml

# --- Carモデル ---
class Car(BaseModel):
    make: str
    model: str
    year: int

    @field_validator("year")
    @classmethod
    def validate_year(cls, v: int) -> int:
        if v < 1886 or v > 2100:
            raise ValueError("年式は1886〜2100の範囲である必要があります。")
        return v

# --- 抽象 Person クラス ---
class Person(BaseModel, ABC):
    name: str
    age: int
    hobbies: list[str]
    cars: list[Car] = []
    friends: list[Person] = []

    @field_validator("age")
    @classmethod
    def age_must_be_positive(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("年齢は正の整数である必要があります。")
        return v

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("名前は空にできません。")
        return v

# --- Man / Woman クラス ---
class Man(Person):
    pass

class Woman(Person):
    pass

# --- YAML 変換処理 ---
def car_representer(dumper, data: Car):
    return dumper.represent_mapping("!Car", data.model_dump())

def car_constructor(loader: yaml.Loader, node: yaml.MappingNode):
    return Car(**loader.construct_mapping(node, deep=True))

def man_representer(dumper, data: Man):
    return dumper.represent_mapping("!Man", data.model_dump())

def man_constructor(loader, node):
    return Man(**loader.construct_mapping(node, deep=True))

def woman_representer(dumper, data: Woman):
    return dumper.represent_mapping("!Woman", data.model_dump())

def woman_constructor(loader, node):
    return Woman(**loader.construct_mapping(node, deep=True))

yaml.add_representer(Car, car_representer)
yaml.add_constructor("!Car", car_constructor)

yaml.add_representer(Man, man_representer)
yaml.add_constructor("!Man", man_constructor)

yaml.add_representer(Woman, woman_representer)
yaml.add_constructor("!Woman", woman_constructor)

# --- 実行例 ---
if __name__ == "__main__":
    car1 = Car(make="Mazda", model="CX-5", year=2021)
    car2 = Car(make="Toyota", model="Prius", year=2018)

    alice = Woman(name="Alice", age=29, hobbies=["piano"], cars=[car1])
    bob = Man(name="Bob", age=33, hobbies=["cycling"], cars=[car2], friends=[alice])

    yaml_str = yaml.dump(bob, allow_unicode=True)
    print("🔸 YAML:")
    print(yaml_str)

    restored = yaml.load(yaml_str, Loader=yaml.Loader)
    print("🔹 復元:")
    print(restored)
