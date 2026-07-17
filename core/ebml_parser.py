import os
from typing import List, Dict, Any, Tuple
from core.models import Box
from core.reader import BinaryReader
from core.ebml_reader import read_vint, read_ebml_value
from core.ebml_registry import get_element_info

class EbmlElement(Box):
    """Polymorphic class representing an EBML Element. Acts like a Box to interface with the GUI."""
    def __init__(self, offset: int, size: int, element_id: int, header_size: int):
        # Format element ID as big-endian bytes for the Box superclass
        id_len = (element_id.bit_length() + 7) // 8 or 1
        id_bytes = element_id.to_bytes(id_len, byteorder="big")
        super().__init__(offset, size, id_bytes, header_size)
        
        self.element_id = element_id
        self.name, self.el_type = get_element_info(element_id)
        self.type_str = self.name
        self.children: List[EbmlElement] = []
        
    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d["element_id"] = f"0x{self.element_id:X}"
        d["element_type"] = self.el_type
        return d

def parse_ebml_stream(reader: BinaryReader, end_offset: int) -> List[EbmlElement]:
    """Recursively parses a stream of EBML elements."""
    elements = []
    
    while reader.tell() < end_offset:
        offset = reader.tell()
        
        # 1. Read Element ID
        el_id, id_len = read_vint(reader, is_id=True)
        if el_id is None:
            break
            
        # 2. Read Element Size
        el_size, size_len = read_vint(reader, is_id=False)
        header_size = id_len + size_len
        
        if el_size is None:
            # Indefinite size element runs until end of parent container / end of stream
            payload_size = end_offset - (offset + header_size)
            total_size = end_offset - offset
        else:
            payload_size = el_size
            total_size = header_size + payload_size
            
        # Create Element instance
        element = EbmlElement(offset, total_size, el_id, header_size)
        
        # Handle Master elements (containers) vs Leaf elements
        if element.el_type == "master":
            element.payload_offset = offset + header_size
            element.payload_size = payload_size
            
            # Recursively parse children
            child_end = offset + header_size + payload_size
            element.children = parse_ebml_stream(reader, min(child_end, end_offset))
            reader.seek(offset + total_size)
        else:
            # Parse value if payload size is non-zero
            if payload_size > 0:
                reader.seek(offset + header_size)
                val = read_ebml_value(reader, payload_size, element.el_type)
                
                # Format string representations for lists of tags / blocks
                if element.el_type == "binary":
                    element.fields[element.name] = f"Binary data ({payload_size} bytes)"
                else:
                    element.fields[element.name] = val
                    
                # Support metadata editing for numeric and floating values
                if element.el_type in ("uint", "int", "float", "date"):
                    fmt = None
                    t_lbl = element.el_type
                    
                    if element.el_type == "uint":
                        if payload_size == 1: fmt, t_lbl = ">B", "uint8"
                        elif payload_size == 2: fmt, t_lbl = ">H", "uint16"
                        elif payload_size == 4: fmt, t_lbl = ">I", "uint32"
                        elif payload_size == 8: fmt, t_lbl = ">Q", "uint64"
                    elif element.el_type == "int":
                        if payload_size == 1: fmt, t_lbl = ">b", "int8"
                        elif payload_size == 2: fmt, t_lbl = ">h", "int16"
                        elif payload_size == 4: fmt, t_lbl = ">i", "int32"
                        elif payload_size == 8: fmt, t_lbl = ">q", "int64"
                    elif element.el_type == "float":
                        if payload_size == 4: fmt, t_lbl = ">f", "float32"
                        elif payload_size == 8: fmt, t_lbl = ">d", "float64"
                    elif element.el_type == "date":
                        if payload_size == 8: fmt, t_lbl = ">q", "date"
                        
                    if fmt:
                        element.editable_fields[element.name] = {
                            "offset": offset + header_size,
                            "format": fmt,
                            "value": val,
                            "label": element.name,
                            "type": t_lbl
                        }
            else:
                element.fields[element.name] = ""
                
            reader.seek(offset + total_size)
            
        elements.append(element)
        
    return elements

def parse_ebml_file(filepath: str) -> List[EbmlElement]:
    """Initial entry point to parse a full MKV/WebM file as EBML hierarchy."""
    filesize = os.path.getsize(filepath)
    with open(filepath, "rb") as f:
        reader = BinaryReader(f)
        return parse_ebml_stream(reader, filesize)
