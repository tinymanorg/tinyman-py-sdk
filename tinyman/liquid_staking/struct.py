# TODO: move struct to parent.
import json
import re
from typing import Any


MINIMUM_BALANCE_REQUIREMENT_PER_BOX = 2_500
MINIMUM_BALANCE_REQUIREMENT_PER_BOX_BYTE = 400


structs = json.load(open("structs.json"))["structs"]


class Struct():
    def __init__(self, name, size, fields):
        self._name = name
        self._size = size
        self._fields = fields

    def __call__(self, data=None) -> Any:
        if data is None:
            data = bytearray(self._size)
        self._data = memoryview(data)
        return self

    def __getattribute__(self, name: str) -> Any:
        if name.startswith("_"):
            return super().__getattribute__(name)
        field = self._fields[name]
        start = field["offset"]
        end = field["offset"] + field["size"]
        value = self._data[start:end]
        type = get_type(field["type"])
        return type(value)

    def __setattr__(self, name: str, value: Any) -> None:
        if name.startswith("_"):
            return super().__setattr__(name, value)
        field = self._fields[name]
        start = field["offset"]
        end = field["offset"] + field["size"]
        if field["type"] in ("int",):
            value = value.to_bytes(field["size"], "big")
        if isinstance(value, (Struct, ArrayData)):
            value = value._data
        self._data[start:end] = value

    def __setitem__(self, index, value):
        if isinstance(value, (Struct, ArrayData)):
            value = value._data
        self._data[:] = value

    def __str__(self) -> str:
        return repr(bytes(self._data))

    def __repr__(self) -> str:
        fields = {f: getattr(self, f) for f in self._fields}
        return f"{self._name}({fields})"

    def __len__(self):
        return len(self._data)

    def __conform__(self, protocol):
        return bytes(self._data)

    def __bytes__(self):
        return bytes(self._data.tobytes())


class ArrayData():
    def __init__(self, struct, length):
        self._struct = struct
        self._length = length

    def __call__(self, data=None) -> Any:
        if data is None:
            data = bytearray(self._struct._size * self.length)
        self._data = memoryview(data)
        return self

    def __getitem__(self, index):
        offset = self._struct._size * index
        end = offset + self._struct._size
        value = self._data[offset:end]
        return self._struct(value)

    def __setitem__(self, index, value):
        offset = self._struct._size * index
        end = offset + self._struct._size
        if isinstance(value, Struct):
            value = value._data
        self._data[offset:end] = value

    def __repr__(self) -> str:
        return ", ".join(repr(self[i]) for i in range(self._length))


class TealishInt():
    def __call__(self, value) -> Any:
        return int.from_bytes(value, "big")


class TealishBytes():
    def __call__(self, value) -> Any:
        return value


def get_struct(name):
    return Struct(name=name, **structs[name])


def get_type(name):
    if name == "int":
        return TealishInt()
    elif name.startswith("uint"):
        return TealishInt()
    elif name.startswith("bytes"):
        return TealishBytes()
    elif name in structs:
        return Struct(**structs[name])
    elif "[" in name:
        name, length = re.match(r"([A-Za-z_0-9]+)\[(\d+)\]", name).groups()
        return ArrayData(Struct(**structs[name]), int(length))
    else:
        raise KeyError(name)


def get_box_costs(boxes):
    cost = MINIMUM_BALANCE_REQUIREMENT_PER_BOX
    for name, struct in boxes.items():
        cost += len(name) * MINIMUM_BALANCE_REQUIREMENT_PER_BOX_BYTE
        cost += struct._size * MINIMUM_BALANCE_REQUIREMENT_PER_BOX_BYTE
    return cost
