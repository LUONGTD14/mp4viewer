import struct
from typing import BinaryIO, Union

class BinaryReader:
    """A seekable binary reader that parses big-endian structures from a stream or file."""
    def __init__(self, stream: BinaryIO):
        self.stream = stream

    def seek(self, offset: int, whence: int = 0) -> int:
        return self.stream.seek(offset, whence)

    def tell(self) -> int:
        return self.stream.tell()

    def skip(self, n: int) -> int:
        return self.stream.seek(n, 1)

    def read_bytes(self, n: int) -> bytes:
        if n < 0:
            raise ValueError(f"Cannot read negative bytes: {n}")
        if n == 0:
            return b""
        data = self.stream.read(n)
        if len(data) < n:
            raise EOFError(f"Unexpected EOF: expected {n} bytes, got {len(data)}")
        return data

    def read_u8(self) -> int:
        return struct.unpack(">B", self.read_bytes(1))[0]

    def read_u16(self) -> int:
        return struct.unpack(">H", self.read_bytes(2))[0]

    def read_u32(self) -> int:
        return struct.unpack(">I", self.read_bytes(4))[0]

    def read_u64(self) -> int:
        return struct.unpack(">Q", self.read_bytes(8))[0]

    def read_string(self, n: int, encoding: str = "utf-8") -> str:
        data = self.read_bytes(n)
        return data.decode(encoding, errors="replace")

    def read_fixed_point_16_16(self) -> float:
        """Reads a 32-bit fixed-point number (16 bits integer, 16 bits fraction)."""
        val = self.read_u32()
        return val / 65536.0

    def read_fixed_point_8_8(self) -> float:
        """Reads a 16-bit fixed-point number (8 bits integer, 8 bits fraction)."""
        val = self.read_u16()
        return val / 256.0
