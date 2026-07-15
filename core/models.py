from typing import List, Dict, Any, Optional
from core.reader import BinaryReader

class Box:
    """Base class for all MP4/MOV boxes (atoms)."""
    def __init__(self, offset: int, size: int, type_bytes: bytes, header_size: int, uuid: Optional[bytes] = None):
        self.offset = offset
        self.size = size
        self.type_bytes = type_bytes
        self.type_str = type_bytes.decode("latin1")
        self.header_size = header_size
        self.payload_offset = offset + header_size
        self.payload_size = size - header_size
        self.uuid = uuid
        self.fields: Dict[str, Any] = {}
        self.editable_fields: Dict[str, Dict[str, Any]] = {}
        self.custom_payload_bytes: Optional[bytes] = None

    def parse_payload(self, reader: BinaryReader) -> None:
        """Subclasses should override this method to parse their specific fields."""
        # By default, do nothing (generic box)
        pass

    def to_dict(self) -> Dict[str, Any]:
        """Returns a dictionary representation of the box metadata for API serialization."""
        res = {
            "type": self.type_str,
            "offset": self.offset,
            "size": self.size,
            "header_size": self.header_size,
            "payload_offset": self.payload_offset,
            "payload_size": self.payload_size,
            "is_container": isinstance(self, ContainerBox),
            "fields": self.fields
        }
        if self.uuid:
            res["uuid"] = self.uuid.hex()
        return res

class FullBox(Box):
    """A box that contains a version and flags."""
    def __init__(self, offset: int, size: int, type_bytes: bytes, header_size: int, uuid: Optional[bytes] = None):
        super().__init__(offset, size, type_bytes, header_size, uuid)
        self.version: int = 0
        self.flags: int = 0

    def parse_header(self, reader: BinaryReader) -> None:
        """Parses the version and flags from the start of the payload."""
        # Note: calling this consumes 4 bytes from the payload segment
        val = reader.read_u32()
        self.version = (val >> 24) & 0xFF
        self.flags = val & 0xFFFFFF
        self.header_size += 4
        self.payload_offset += 4
        self.payload_size -= 4
        self.fields["version"] = self.version
        self.fields["flags"] = f"0x{self.flags:06X}"

class ContainerBox(Box):
    """A box that contains other boxes."""
    def __init__(self, offset: int, size: int, type_bytes: bytes, header_size: int, uuid: Optional[bytes] = None):
        super().__init__(offset, size, type_bytes, header_size, uuid)
        self.children: List[Box] = []

    def parse_payload(self, reader: BinaryReader) -> None:
        """Parses the child boxes contained inside this container box."""
        from core.parser import parse_box_stream
        
        end_offset = self.payload_offset + self.payload_size
        reader.seek(self.payload_offset)
        self.children = parse_box_stream(reader, end_offset)

    def to_dict(self) -> Dict[str, Any]:
        res = super().to_dict()
        res["children"] = [child.to_dict() for child in self.children]
        return res
