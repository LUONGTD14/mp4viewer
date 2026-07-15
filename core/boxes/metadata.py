from core.models import Box, FullBox, ContainerBox
from core.registry import register_box, get_box_class
from core.reader import BinaryReader

@register_box("meta")
class MetaBox(ContainerBox):
    """Metadata Box: handles differences between ISO MP4 (FullBox) and QuickTime MOV formats."""
    def parse_payload(self, reader: BinaryReader) -> None:
        # Save starting offset of payload
        payload_start = self.payload_offset
        
        # Read the first 4 bytes to check if it's a valid Box type
        # (Heuristic: QT metadata starts immediately with 'hdlr' or 'keys')
        try:
            reader.seek(payload_start)
            first_u32 = reader.read_u32()
            first_type = reader.read_bytes(4)
        except (EOFError, ValueError):
            first_type = b""

        # Check if first_type looks like a valid FourCC string
        is_qt_style = False
        if len(first_type) == 4:
            # Check if it contains alphanumeric characters, spaces, or copyright symbol \xa9
            chars_ok = all(32 <= b <= 126 or b == 169 for b in first_type)
            if chars_ok:
                is_qt_style = True

        if is_qt_style:
            # QuickTime (MOV) format: No version/flags, child boxes start immediately.
            self.fields["format"] = "QuickTime (MOV) - Container style"
            # Payload starts immediately at payload_start
            self.payload_offset = payload_start
        else:
            # ISO Base Media File Format: It is a FullBox.
            self.fields["format"] = "ISO (MP4) - FullBox style"
            # Parse version and flags
            reader.seek(payload_start)
            val = reader.read_u32()
            self.version = (val >> 24) & 0xFF
            self.flags = val & 0xFFFFFF
            self.fields["version"] = self.version
            self.fields["flags"] = f"0x{self.flags:06X}"
            
            # Sub-boxes start after version/flags (4 bytes)
            self.payload_offset = payload_start + 4
            self.payload_size = max(0, self.payload_size - 4)

        # Parse sub-boxes
        super().parse_payload(reader)

@register_box("keys")
class KeysBox(FullBox):
    """Metadata Keys Box (MOV): List of key names for metadata mapping."""
    def parse_payload(self, reader: BinaryReader) -> None:
        if self.payload_size < 4:
            return
        
        entry_count = reader.read_u32()
        keys_list = []
        
        for _ in range(entry_count):
            if reader.tell() >= self.payload_offset + self.payload_size:
                break
            
            try:
                size = reader.read_u32()
                namespace = reader.read_string(4)
                # Key name is (size - 8) bytes
                name_len = size - 8
                if name_len > 0:
                    key_name = reader.read_string(name_len)
                else:
                    key_name = ""
                keys_list.append({"namespace": namespace, "key": key_name})
            except Exception:
                break
                
        self.fields["entry_count"] = entry_count
        self.fields["keys"] = keys_list

@register_box("ilst")
class IlstBox(ContainerBox):
    """Metadata Item List Box (MOV): Contains metadata values mapped to keys."""
    # This is a container, so by default children will be parsed.
    # However, each child box is index-based (integer representation of 1-based index)
    # or four-character code containing values.
    # We override to represent names nicely in metadata if possible.
    def parse_payload(self, reader: BinaryReader) -> None:
        super().parse_payload(reader)
        # We can clean up fields or label them if we can map them
        pass

@register_box("data")
class DataBox(FullBox):
    """Metadata Value Data Box: Actual data payload for an item in the ilst box."""
    def parse_payload(self, reader: BinaryReader) -> None:
        if self.payload_size < 4:
            return
            
        type_indicator = reader.read_u32()  # Type indicator / pre-defined
        data_len = self.payload_size - 4
        
        if data_len <= 0:
            return
            
        # The 'flags' parameter in FullBox tells us the data type (1 = utf8, 2 = utf16, 21 = integer)
        # Note: self.flags represents the lower 24 bits of version/flags field.
        # But QuickTime metadata data box uses type_indicator or flags differently.
        # Typically flags indicates type:
        data_type = self.flags
        
        try:
            if data_type == 1:
                # UTF-8 string
                value = reader.read_string(data_len, encoding="utf-8")
            elif data_type == 2:
                # UTF-16 BE string
                value = reader.read_string(data_len, encoding="utf-16-be")
            elif data_type == 21:
                # Integer
                if data_len == 1:
                    value = reader.read_u8()
                elif data_len == 2:
                    value = reader.read_u16()
                elif data_len == 4:
                    value = reader.read_u32()
                elif data_len == 8:
                    value = reader.read_u64()
                else:
                    value = reader.read_bytes(data_len).hex()
            elif data_type in (13, 14, 27):
                # Images (JPEG, PNG, BMP)
                value = f"[Image Cover Art: {data_len} bytes]"
            else:
                # Fallback to string or hex
                raw = reader.read_bytes(data_len)
                try:
                    value = raw.decode("utf-8")
                except Exception:
                    value = f"Hex: {raw.hex()}"
        except Exception as e:
            value = f"[Error decoding value: {str(e)}]"
            
        self.fields["type_indicator"] = type_indicator
        self.fields["data_type_flag"] = data_type
        self.fields["value"] = value
