import os
from typing import List, BinaryIO, Union, Optional
from core.reader import BinaryReader
from core.models import Box, FullBox, ContainerBox
from core.registry import get_box_class

# Import box parsers to populate the registry automatically
import core.boxes  # noqa: F401

def parse_box(reader: BinaryReader, max_offset: int) -> Optional[Box]:
    """Parses a single box from the reader at its current position."""
    start_offset = reader.tell()
    if start_offset >= max_offset:
        return None

    try:
        # Read standard size and type
        try:
            size = reader.read_u32()
            type_bytes = reader.read_bytes(4)
        except (EOFError, ValueError):
            # Less than 8 bytes remaining, probably trailing padding
            return None

        header_size = 8
        uuid = None

        # Check for 64-bit size
        if size == 1:
            size = reader.read_u64()
            header_size += 8
        elif size == 0:
            # Extends to the end of the file
            size = max_offset - start_offset

        # Check for UUID box
        if type_bytes == b'uuid':
            uuid = reader.read_bytes(16)
            header_size += 16

        # Safety check for size mismatch or infinite loops
        if size < header_size:
            # Malformed box size
            raise ValueError(f"Invalid box size {size} (smaller than header size {header_size}) at offset {start_offset}")

        # Resolve box class
        box_class = get_box_class(type_bytes)
        box = box_class(start_offset, size, type_bytes, header_size, uuid)

        # FullBoxes have version/flags at the start of their payload
        if isinstance(box, FullBox):
            box.parse_header(reader)

        # Parse box payload details
        payload_end = start_offset + size
        # Ensure we don't try to read beyond the payload limit
        if payload_end > max_offset:
            # The file is truncated or size header is too large
            box.fields["truncated"] = True
            payload_end = max_offset

        # Call the box-specific payload parser
        # We seek to payload offset to be safe
        reader.seek(box.payload_offset)
        try:
            box.parse_payload(reader)
        except Exception as e:
            # Catch parsing errors inside custom boxes to keep parser robust
            box.fields["parsing_error"] = str(e)

        # Always seek reader to the exact end of the box to remain aligned
        reader.seek(start_offset + size)
        return box

    except Exception as e:
        # Return generic error box for recovery
        err_box = Box(start_offset, max_offset - start_offset, b'err ', 8)
        err_box.fields["error"] = str(e)
        reader.seek(max_offset)  # Skip to end
        return err_box

def parse_box_stream(reader: BinaryReader, end_offset: int) -> List[Box]:
    """Sequentially parses boxes from the reader until end_offset is reached."""
    boxes = []
    while reader.tell() < end_offset:
        box = parse_box(reader, end_offset)
        if box is None:
            break
        boxes.append(box)
    return boxes

def parse_file(file_path: str) -> List[Box]:
    """Helper function to parse a local MP4/MOV file by path."""
    file_size = os.path.getsize(file_path)
    with open(file_path, "rb") as f:
        reader = BinaryReader(f)
        return parse_box_stream(reader, file_size)
