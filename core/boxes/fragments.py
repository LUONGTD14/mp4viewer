from core.models import FullBox
from core.registry import register_box
from core.reader import BinaryReader
from core.boxes.samples import make_preview_list

@register_box("trex")
class TrexBox(FullBox):
    """Track Extends Box: sets default values for track fragments."""
    def parse_payload(self, reader: BinaryReader) -> None:
        track_id = reader.read_u32()
        default_sample_description_index = reader.read_u32()
        default_sample_duration = reader.read_u32()
        default_sample_size = reader.read_u32()
        default_sample_flags = reader.read_u32()
        
        self.fields.update({
            "track_id": track_id,
            "default_sample_description_index": default_sample_description_index,
            "default_sample_duration": default_sample_duration,
            "default_sample_size": default_sample_size,
            "default_sample_flags": f"0x{default_sample_flags:08X}"
        })

@register_box("mfhd")
class MfhdBox(FullBox):
    """Movie Fragment Header Box: sequence number for fragments."""
    def parse_payload(self, reader: BinaryReader) -> None:
        sequence_number = reader.read_u32()
        self.fields["sequence_number"] = sequence_number

@register_box("tfhd")
class TfhdBox(FullBox):
    """Track Fragment Header Box: default values for track fragment runs."""
    def parse_payload(self, reader: BinaryReader) -> None:
        track_id = reader.read_u32()
        self.fields["track_id"] = track_id
        
        flags = self.flags
        
        # Check flag bits
        if flags & 0x000001: # base-data-offset-present
            self.fields["base_data_offset"] = reader.read_u64()
        if flags & 0x000002: # sample-description-index-present
            self.fields["sample_description_index"] = reader.read_u32()
        if flags & 0x000008: # default-sample-duration-present
            self.fields["default_sample_duration"] = reader.read_u32()
        if flags & 0x000010: # default-sample-size-present
            self.fields["default_sample_size"] = reader.read_u32()
        if flags & 0x000020: # default-sample-flags-present
            self.fields["default_sample_flags"] = f"0x{reader.read_u32():08X}"
            
        # Boolean indicators based on flags
        self.fields["duration_is_empty"] = bool(flags & 0x010000)
        self.fields["default_base_is_moof"] = bool(flags & 0x020000)

@register_box("trun")
class TrunBox(FullBox):
    """Track Fragment Run Box: describes samples in a track fragment."""
    def parse_payload(self, reader: BinaryReader) -> None:
        sample_count = reader.read_u32()
        self.fields["sample_count"] = sample_count
        
        flags = self.flags
        
        if flags & 0x000001: # data-offset-present
            import struct
            self.fields["data_offset"] = struct.unpack(">i", reader.read_bytes(4))[0]
        if flags & 0x000004: # first-sample-flags-present
            self.fields["first_sample_flags"] = f"0x{reader.read_u32():08X}"
            
        # Parse sample table
        samples = []
        for _ in range(min(sample_count, 1000)):
            sample_info = {}
            if flags & 0x000100: # sample-duration-present
                sample_info["duration"] = reader.read_u32()
            if flags & 0x000200: # sample-size-present
                sample_info["size"] = reader.read_u32()
            if flags & 0x000400: # sample-flags-present
                sample_info["flags"] = f"0x{reader.read_u32():08X}"
            if flags & 0x000800: # sample-composition-time-offset-present
                if self.version == 1:
                    import struct
                    sample_info["composition_offset"] = struct.unpack(">i", reader.read_bytes(4))[0]
                else:
                    sample_info["composition_offset"] = reader.read_u32()
            samples.append(sample_info)
            
        # Skip remaining bytes if truncated
        entry_size = 0
        if flags & 0x000100: entry_size += 4
        if flags & 0x000200: entry_size += 4
        if flags & 0x000400: entry_size += 4
        if flags & 0x000800: entry_size += 4
        
        if sample_count > 1000:
            reader.skip(entry_size * (sample_count - 1000))
            
        self.fields["samples_preview"] = make_preview_list(samples, limit=20)
