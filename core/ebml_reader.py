import struct
from typing import Tuple, Optional, Any
from core.reader import BinaryReader

def read_vint(reader: BinaryReader, is_id: bool = False) -> Tuple[Optional[int], int]:
    """
    Reads an EBML Variable-length Integer (VINT).
    If is_id is True, the leading marker bits are retained (for Element IDs).
    Returns (vint_value, vint_length). Value is None if it represents indefinite size.
    """
    first_byte = reader.read_u8()
    if first_byte is None:
        return None, 0
        
    if first_byte == 0:
        # Invalid first byte for a VINT (cannot have 8 leading zeros)
        return None, 1

    # Determine total bytes from leading zeros
    length = 1
    mask = 0x80
    while mask > 0:
        if (first_byte & mask) != 0:
            break
        length += 1
        mask >>= 1

    if length > 8:
        return None, length

    # Read remaining bytes
    value = first_byte
    if not is_id:
        value &= (mask - 1)  # Clear the leading 1 bit marker

    for _ in range(length - 1):
        next_byte = reader.read_u8()
        if next_byte is None:
            break
        value = (value << 8) | next_byte

    # Check for indefinite/unknown size VINT (all data bits are 1)
    if not is_id:
        bit_count = 7 * length
        all_ones = (1 << bit_count) - 1
        if value == all_ones:
            return None, length

    return value, length

def read_ebml_value(reader: BinaryReader, size: int, element_type: str) -> Any:
    """Decodes EBML payload bytes according to its element type."""
    if size == 0:
        if element_type in ("string", "utf8"):
            return ""
        return 0
        
    data = reader.read_bytes(size)
    if len(data) < size:
        # Stream truncated
        size = len(data)

    if element_type == "uint":
        return int.from_bytes(data, byteorder="big", signed=False)
    elif element_type == "int":
        return int.from_bytes(data, byteorder="big", signed=True)
    elif element_type == "float":
        if size == 4:
            return struct.unpack(">f", data)[0]
        elif size == 8:
            return struct.unpack(">d", data)[0]
        return 0.0
    elif element_type == "string":
        return data.decode("ascii", errors="replace").rstrip("\x00")
    elif element_type == "utf8":
        return data.decode("utf-8", errors="replace").rstrip("\x00")
    elif element_type == "binary":
        return data
    elif element_type == "date":
        # 8-byte signed integer, nanoseconds since 2001-01-01 00:00:00 UTC
        if size == 8:
            val = int.from_bytes(data, byteorder="big", signed=True)
            return val
        return 0
    return data
