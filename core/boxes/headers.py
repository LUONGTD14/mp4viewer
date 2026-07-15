from datetime import datetime, timezone
from core.models import FullBox
from core.registry import register_box
from core.reader import BinaryReader

def parse_mp4_time(timestamp: int) -> str:
    """Converts an MP4 timestamp (seconds since 1904-01-01) to a readable string."""
    epoch_diff = 2082844800  # seconds between 1904-01-01 and 1970-01-01
    try:
        unix_time = timestamp - epoch_diff
        # Ensure it fits in reasonable bounds
        if unix_time < -2000000000 or unix_time > 20000000000:
            return f"Raw timestamp: {timestamp}"
        return datetime.fromtimestamp(unix_time, tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
    except Exception:
        return f"Raw timestamp: {timestamp}"

def parse_language_code(lang_bits: int) -> str:
    """Parses a 16-bit packed ISO-639-2/T language code (3 characters, 5 bits each)."""
    # 1 bit padding, followed by 3 x 5-bit characters representing ascii 'a' + value
    char1 = (lang_bits >> 10) & 0x1F
    char2 = (lang_bits >> 5) & 0x1F
    char3 = lang_bits & 0x1F
    
    c1 = chr(char1 + 0x60) if char1 else ' '
    c2 = chr(char2 + 0x60) if char2 else ' '
    c3 = chr(char3 + 0x60) if char3 else ' '
    return (c1 + c2 + c3).strip()

@register_box("mvhd")
class MvhdBox(FullBox):
    """Movie Header Box: contains media-independent movie metadata."""
    def parse_payload(self, reader: BinaryReader) -> None:
        if self.version == 1:
            creation_time = reader.read_u64()
            modification_time = reader.read_u64()
            timescale = reader.read_u32()
            duration = reader.read_u64()
        else:
            creation_time = reader.read_u32()
            modification_time = reader.read_u32()
            timescale = reader.read_u32()
            duration = reader.read_u32()

        preferred_rate = reader.read_fixed_point_16_16()
        preferred_volume = reader.read_fixed_point_8_8()
        
        # Skip reserved 10 bytes
        reader.skip(10)
        
        # Read matrix (36 bytes)
        matrix = [reader.read_fixed_point_16_16() for _ in range(9)]
        
        # Skip pre-defined 24 bytes
        reader.skip(24)
        
        next_track_id = reader.read_u32()

        # Calculate duration in seconds
        duration_seconds = duration / timescale if timescale > 0 else 0

        self.fields.update({
            "creation_time": parse_mp4_time(creation_time),
            "modification_time": parse_mp4_time(modification_time),
            "timescale": timescale,
            "duration": duration,
            "duration_seconds": round(duration_seconds, 3),
            "preferred_rate": preferred_rate,
            "preferred_volume": preferred_volume,
            "matrix": [round(m, 4) for m in matrix],
            "next_track_id": next_track_id
        })

@register_box("tkhd")
class TkhdBox(FullBox):
    """Track Header Box: contains metadata for a single track within the movie."""
    def parse_payload(self, reader: BinaryReader) -> None:
        if self.version == 1:
            creation_time = reader.read_u64()
            modification_time = reader.read_u64()
            track_id = reader.read_u32()
            reader.skip(4)  # reserved
            duration = reader.read_u64()
        else:
            creation_time = reader.read_u32()
            modification_time = reader.read_u32()
            track_id = reader.read_u32()
            reader.skip(4)  # reserved
            duration = reader.read_u32()

        reader.skip(8)  # reserved
        layer = reader.read_u16()
        alternate_group = reader.read_u16()
        volume = reader.read_fixed_point_8_8()
        reader.skip(2)  # reserved
        
        # Read matrix (36 bytes)
        matrix = [reader.read_fixed_point_16_16() for _ in range(9)]
        
        width = reader.read_fixed_point_16_16()
        height = reader.read_fixed_point_16_16()

        self.fields.update({
            "creation_time": parse_mp4_time(creation_time),
            "modification_time": parse_mp4_time(modification_time),
            "track_id": track_id,
            "duration": duration,
            "layer": layer,
            "alternate_group": alternate_group,
            "volume": volume,
            "matrix": [round(m, 4) for m in matrix],
            "width": width,
            "height": height
        })

@register_box("mdhd")
class MdhdBox(FullBox):
    """Media Header Box: contains media-specific header info (timescale, language)."""
    def parse_payload(self, reader: BinaryReader) -> None:
        if self.version == 1:
            creation_time = reader.read_u64()
            modification_time = reader.read_u64()
            timescale = reader.read_u32()
            duration = reader.read_u64()
        else:
            creation_time = reader.read_u32()
            modification_time = reader.read_u32()
            timescale = reader.read_u32()
            duration = reader.read_u32()

        lang_bits = reader.read_u16()
        pre_defined = reader.read_u16()

        duration_seconds = duration / timescale if timescale > 0 else 0

        self.fields.update({
            "creation_time": parse_mp4_time(creation_time),
            "modification_time": parse_mp4_time(modification_time),
            "timescale": timescale,
            "duration": duration,
            "duration_seconds": round(duration_seconds, 3),
            "language": parse_language_code(lang_bits),
            "pre_defined": pre_defined
        })

@register_box("hdlr")
class HdlrBox(FullBox):
    """Handler Reference Box: declares the media type of the track."""
    def parse_payload(self, reader: BinaryReader) -> None:
        pre_defined = reader.read_u32()
        handler_type = reader.read_string(4)
        reader.skip(12)
        
        rem_len = self.payload_size - 20
        if rem_len > 0:
            name_bytes = reader.read_bytes(rem_len)
            if len(name_bytes) > 0:
                pascal_len = name_bytes[0]
                if pascal_len > 0 and pascal_len < len(name_bytes):
                    try:
                        name = name_bytes[1:1+pascal_len].decode("utf-8", errors="replace")
                    except Exception:
                        name = name_bytes.decode("utf-8", errors="replace").strip("\x00")
                else:
                    name = name_bytes.decode("utf-8", errors="replace").strip("\x00")
            else:
                name = ""
        else:
            name = ""
            
        self.fields.update({
            "handler_type": handler_type,
            "handler_name": name
        })

@register_box("vmhd")
class VmhdBox(FullBox):
    """Video Media Header Box: contains general video media information."""
    def parse_payload(self, reader: BinaryReader) -> None:
        graphics_mode = reader.read_u16()
        opcolor_r = reader.read_u16()
        opcolor_g = reader.read_u16()
        opcolor_b = reader.read_u16()
        
        self.fields.update({
            "graphics_mode": graphics_mode,
            "opcolor": [opcolor_r, opcolor_g, opcolor_b]
        })

@register_box("smhd")
class SmhdBox(FullBox):
    """Sound Media Header Box: contains general sound media information."""
    def parse_payload(self, reader: BinaryReader) -> None:
        balance = reader.read_fixed_point_8_8()
        reader.skip(2)
        
        self.fields.update({
            "balance": balance
        })
