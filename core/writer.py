import shutil
import struct
from typing import List
from core.models import Box

def gather_all_boxes(boxes: List[Box]) -> List[Box]:
    result = []
    for box in boxes:
        result.append(box)
        if hasattr(box, "children") and box.children:
            result.extend(gather_all_boxes(box.children))
    return result

def save_modified_file(new_filepath: str, original_filepath: str, root_boxes: List[Box]) -> None:
    """Copies original file to new_filepath, then overwrites modified metadata fields at their exact offsets."""
    # 1. Copy original file to preserve structure and media payloads
    shutil.copy2(original_filepath, new_filepath)
    
    # 2. Gather all boxes in the hierarchy
    all_boxes = gather_all_boxes(root_boxes)
    
    # 3. Patch the copied file
    with open(new_filepath, "r+b") as f:
        for box in all_boxes:
            for field_name, field in box.editable_fields.items():
                val = field["value"]
                fmt = field["format"]
                offset = field["offset"]
                t = field["type"]
                
                # Format conversions
                if t == "fixed16_16":
                    raw_val = int(float(val) * 65536)
                    f.seek(offset)
                    f.write(struct.pack(fmt, raw_val))
                elif t == "fixed8_8":
                    raw_val = int(float(val) * 256)
                    f.seek(offset)
                    f.write(struct.pack(fmt, raw_val))
                elif t == "full_range_bit":
                    f.seek(offset)
                    curr_byte = f.read(1)
                    if curr_byte:
                        byte_val = curr_byte[0]
                        if val:
                            byte_val |= 0x80
                        else:
                            byte_val &= 0x7F
                        f.seek(offset)
                        f.write(bytes([byte_val]))
                else:
                    # Numeric integers (uint16, uint32, uint64, int16, int32)
                    f.seek(offset)
                    f.write(struct.pack(fmt, int(val)))
            
            # Patch raw hex bytes if user modified the payload directly
            if hasattr(box, "custom_payload_bytes") and box.custom_payload_bytes is not None:
                f.seek(box.payload_offset)
                f.write(box.custom_payload_bytes)
