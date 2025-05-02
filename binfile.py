from struct import pack, unpack
from typing import BinaryIO


class BinFile:
	WHENCE_START: int = 0
	WHENCE_CURRENT: int = 1
	WHENCE_END: int = 2
	INT8: int = 1
	INT16: int = 2
	INT32: int = 4
	FLOAT: int = 4
	CHUNK: int = 4

	def __init__(self, filename: str, write: bool = False) -> None:
		self.filename = filename
		self.fp: BinaryIO = open(filename, 'wb+') if write else open(filename, 'rb+')

	def __stringSeek(self, string: str) -> int:
		return self.seek(
			BinFile.CHUNK - offset if (offset := len(string) % BinFile.CHUNK) != 0 else 4,
			BinFile.WHENCE_CURRENT
		)

	def __alignSeek(self, size: int) -> int:
		# print(self.tell(), size, size - offset if (offset := self.tell() % size) != 0 else 0)
		return self.seek(
			size - offset if (offset := self.tell() % size) != 0 else 0,
			BinFile.WHENCE_CURRENT
		)

	def close(self) -> None:
		return self.fp.close()

	def seek(self, offset: int, whence: int = 0) -> int:
		return self.fp.seek(offset, whence)

	def tell(self) -> int:
		return self.fp.tell()

	def read(self, size: int) -> bytes:
		self.__alignSeek(size)
		return self.fp.read(size)

	def write(self, mode: str, val: int | float) -> int:
		match mode.lower():
			case 'b':
				size: int = BinFile.INT8
			case 'h':
				size: int = BinFile.INT16
			case 'i':
				size: int = BinFile.INT32
			case 'f':
				size: int = BinFile.FLOAT
			case _:
				raise ValueError(f'Invalid mode: {mode}')

		self.__alignSeek(size)

		return self.fp.write(pack(mode, val))

	def readUInt8(self) -> int:
		return unpack('B', self.read(BinFile.INT8))[0]

	def readUInt16(self) -> int:
		return unpack('H', self.read(BinFile.INT16))[0]

	def readUInt32(self) -> int:
		return unpack('I', self.read(BinFile.INT32))[0]

	def readInt8(self) -> int:
		return unpack('b', self.read(BinFile.INT8))[0]

	def readInt16(self) -> int:
		return unpack('h', self.read(BinFile.INT16))[0]

	def readInt32(self) -> int:
		return unpack('i', self.read(BinFile.INT32))[0]

	def readFloat(self) -> float:
		return unpack('f', self.read(BinFile.FLOAT))[0]

	def readString(self) -> str:
		string_len: int = self.readUInt32() - 1
		string: str = self.fp.read(string_len).decode('ascii')
		self.__stringSeek(string)
		return string

	def writeUInt8(self, val: int) -> int:
		return self.write('B', val)

	def writeUInt16(self, val: int) -> int:
		return self.write('H', val)

	def writeUInt32(self, val: int) -> int:
		return self.write('I', val)

	def writeInt8(self, val: int) -> int:
		return self.write('b', val)

	def writeInt16(self, val: int) -> int:
		return self.write('h', val)

	def writeInt32(self, val: int) -> int:
		return self.write('i', val)

	def writeFloat(self, val: float) -> int:
		return self.write('f', val)

	def writeString(self, string: str) -> int:
		self.writeUInt32(len(string) + 1)
		result: int = self.fp.write(string.encode('ascii'))
		self.__stringSeek(string)
		return result