from enum import Enum
from dataclasses import dataclass
from typing import List, Optional
from binfile import BinFile
 
# we like men 🤤😜

class ImmediateState(Enum):
    UNSET = -1
    SET = 0
    NONE = 1

    def write(self, bf: BinFile) -> None:
        bf.writeInt8(self.value)

    @classmethod
    def read(cls, bf: BinFile) -> 'ImmediateState':
        return cls(bf.readInt8())


class BlendMode(Enum):
    NORMAL = 0
    ADDITIVE = 1
    SUBTRACTIVE = 2

    def write(self, bf: BinFile) -> None:
        bf.writeUInt32(self.value)

    @classmethod
    def read(cls, bf: BinFile) -> 'BlendMode':
        return cls(bf.readUInt32())


@dataclass
class Position:
    immediate: ImmediateState
    x: float
    y: float

    def write(self, bf: BinFile) -> None:
        self.immediate.write(bf)
        bf.writeFloat(self.x)
        bf.writeFloat(self.y)

    @classmethod
    def read(cls, bf: BinFile) -> 'Position':
        return cls(
            ImmediateState.read(bf),
            bf.readFloat(),
            bf.readFloat()
        )


@dataclass
class Scale:
    immediate: ImmediateState
    x: float
    y: float

    def write(self, bf: BinFile) -> None:
        self.immediate.write(bf)
        bf.writeFloat(self.x)
        bf.writeFloat(self.y)

    @classmethod
    def read(cls, bf: BinFile) -> 'Scale':
        return cls(
            ImmediateState.read(bf),
            bf.readFloat(),
            bf.readFloat()
        )


@dataclass
class Value:
    immediate: ImmediateState
    value: float

    def write(self, bf: BinFile) -> None:
        self.immediate.write(bf)
        bf.writeFloat(self.value)

    @classmethod
    def read(cls, bf: BinFile) -> 'Value':
        return cls(
            ImmediateState.read(bf),
            bf.readFloat()
        )


@dataclass
class Color:
    immediate: ImmediateState
    r: int = -1
    g: int = -1
    b: int = -1

    def write(self, bf: BinFile) -> None:
        self.immediate.write(bf)
        bf.writeInt8(self.r)
        bf.writeInt8(self.g)
        bf.writeInt8(self.b)

    @classmethod
    def read(cls, bf: BinFile) -> 'Color':
        return cls(
            ImmediateState.read(bf),
            bf.readInt8(),
            bf.readInt8(),
            bf.readInt8()
        )


@dataclass
class Sprite:
    immediate: ImmediateState
    name: str

    def write(self, bf: BinFile) -> None:
        self.immediate.write(bf)
        bf.writeString(self.name)

    @classmethod
    def read(cls, bf: BinFile) -> 'Sprite':
        return cls(
            ImmediateState.read(bf),
            bf.readString()
        )


@dataclass
class Frame:
    time: float
    position: Position
    scale: Scale
    rotation: Value
    opacity: Value
    sprite: Sprite
    color: Color

    def write(self, bf: BinFile) -> None:
        bf.writeFloat(self.time)
        self.position.write(bf)
        self.scale.write(bf)
        self.rotation.write(bf)
        self.opacity.write(bf)
        self.sprite.write(bf)
        self.color.write(bf)

    @classmethod
    def read(cls, bf: BinFile) -> 'Frame':
        return cls(
            bf.readFloat(),
            Position.read(bf),
            Scale.read(bf),
            Value.read(bf),
            Value.read(bf),
            Sprite.read(bf),
            Color.read(bf)
        )


@dataclass
class Layer:
    name: str
    type: int
    blend: BlendMode
    parent: int
    id: int
    source: int
    width: int
    height: int
    anchor_x: float
    anchor_y: float
    metadata: str
    frames: List[Frame]

    def write(self, bf: BinFile) -> None:
        bf.writeString(self.name)
        bf.writeInt32(self.type)
        self.blend.write(bf)
        bf.writeInt16(self.parent)
        bf.writeInt16(self.id)
        bf.writeInt16(self.source)
        bf.writeUInt16(self.width)
        bf.writeUInt16(self.height)
        bf.writeFloat(self.anchor_x)
        bf.writeFloat(self.anchor_y)
        bf.writeString(self.metadata)
        bf.writeUInt32(len(self.frames))
        for frame in self.frames:
            frame.write(bf)

    @classmethod
    def read(cls, bf: BinFile) -> 'Layer':
        return cls(
            bf.readString(),
            bf.readInt32(),
            BlendMode.read(bf),
            bf.readInt16(),
            bf.readInt16(),
            bf.readInt16(),
            bf.readUInt16(),
            bf.readUInt16(),
            bf.readFloat(),
            bf.readFloat(),
            bf.readString(),
            [Frame.read(bf) for _ in range(bf.readUInt32())]
        )


@dataclass
class Animation:
    name: str
    width: int
    height: int
    loop_offset: float
    centered: int
    layers: List[Layer]

    def write(self, bf: BinFile) -> None:
        bf.writeString(self.name)
        bf.writeUInt16(self.width)
        bf.writeUInt16(self.height)
        bf.writeFloat(self.loop_offset)
        bf.writeUInt32(self.centered)
        bf.writeUInt32(len(self.layers))
        for layer in self.layers:
            layer.write(bf)

    @classmethod
    def read(cls, bf: BinFile) -> 'Animation':
        return cls(
            bf.readString(),
            bf.readUInt16(),
            bf.readUInt16(),
            bf.readFloat(),
            bf.readUInt32(),
            [Layer.read(bf) for _ in range(bf.readUInt32())]
        )


@dataclass
class Source:
    path: str
    id: int
    width: int = 0
    height: int = 0

    def write(self, bf: BinFile) -> None:
        bf.writeString(self.path)
        bf.writeUInt16(self.id)
        bf.writeUInt16(self.width)
        bf.writeUInt16(self.height)

    @classmethod
    def read(cls, bf: BinFile) -> 'Source':
        return cls(
            bf.readString(),
            bf.readUInt16(),
            bf.readUInt16(),
            bf.readUInt16()
        )
