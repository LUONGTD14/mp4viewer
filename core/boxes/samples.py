from typing import Optional, List
from core.models import Box, FullBox
from core.registry import register_box
from core.reader import BinaryReader

def make_preview_list(full_list: list, limit: int = 10) -> list:
    """Helper to return a user-friendly preview of long lists to prevent JSON bloat."""
    if len(full_list) <= limit:
        return full_list
    half = limit // 2
    return full_list[:half] + ["... (truncated) ..."] + full_list[-half:]

@register_box("stsz")
class StszBox(FullBox):
    """Sample Size Box: defines the sizes of individual media samples."""
    def parse_payload(self, reader: BinaryReader) -> None:
        sample_size = reader.read_u32()
        sample_count = reader.read_u32()
        
        sizes = []
        if sample_size == 0:
            # Table of sizes follows (sample_count elements)
            # Avoid loading millions of entries into memory
            # We can read sequentially
            for _ in range(min(sample_count, 10000)):  # Caps limit for safety
                sizes.append(reader.read_u32())
            if sample_count > 10000:
                # Seek reader to the end of payload to keep alignment
                reader.skip(4 * (sample_count - 10000))
                
        self.fields.update({
            "default_sample_size": sample_size,
            "sample_count": sample_count,
            "sample_sizes_preview": make_preview_list(sizes) if sample_size == 0 else [sample_size] * sample_count
        })

@register_box("stco")
class StcoBox(FullBox):
    """Chunk Offset Box: defines 32-bit file offsets for media chunks."""
    def parse_payload(self, reader: BinaryReader) -> None:
        entry_count = reader.read_u32()
        offsets = []
        for _ in range(min(entry_count, 10000)):
            offsets.append(reader.read_u32())
        if entry_count > 10000:
            reader.skip(4 * (entry_count - 10000))

        self.fields.update({
            "entry_count": entry_count,
            "chunk_offsets_preview": make_preview_list(offsets)
        })

@register_box("co64")
class Co64Box(FullBox):
    """64-bit Chunk Offset Box: defines 64-bit file offsets for media chunks."""
    def parse_payload(self, reader: BinaryReader) -> None:
        entry_count = reader.read_u32()
        offsets = []
        for _ in range(min(entry_count, 10000)):
            offsets.append(reader.read_u64())
        if entry_count > 10000:
            reader.skip(8 * (entry_count - 10000))

        self.fields.update({
            "entry_count": entry_count,
            "chunk_offsets_preview": make_preview_list(offsets)
        })

@register_box("stts")
class SttsBox(FullBox):
    """Time-to-Sample Box: table mapping sample counts to duration/delta."""
    def parse_payload(self, reader: BinaryReader) -> None:
        entry_count = reader.read_u32()
        entries = []
        for _ in range(min(entry_count, 1000)):
            sample_count = reader.read_u32()
            sample_delta = reader.read_u32()
            entries.append({"sample_count": sample_count, "sample_delta": sample_delta})
        if entry_count > 1000:
            reader.skip(8 * (entry_count - 1000))

        self.fields.update({
            "entry_count": entry_count,
            "time_to_sample_table": make_preview_list(entries, limit=20)
        })

@register_box("stsc")
class StscBox(FullBox):
    """Sample-to-Chunk Box: maps samples to chunks of media."""
    def parse_payload(self, reader: BinaryReader) -> None:
        entry_count = reader.read_u32()
        entries = []
        for _ in range(min(entry_count, 1000)):
            first_chunk = reader.read_u32()
            samples_per_chunk = reader.read_u32()
            sample_desc_index = reader.read_u32()
            entries.append({
                "first_chunk": first_chunk,
                "samples_per_chunk": samples_per_chunk,
                "sample_description_index": sample_desc_index
            })
        if entry_count > 1000:
            reader.skip(12 * (entry_count - 1000))

        self.fields.update({
            "entry_count": entry_count,
            "sample_to_chunk_table": make_preview_list(entries, limit=20)
        })

@register_box("stsd")
class StsdBox(FullBox):
    """Sample Description Box: contains track media codec descriptions."""
    def __init__(self, offset: int, size: int, type_bytes: bytes, header_size: int, uuid: Optional[bytes] = None):
        super().__init__(offset, size, type_bytes, header_size, uuid)
        self.children: List[Box] = []

    def parse_payload(self, reader: BinaryReader) -> None:
        if self.payload_size < 4:
            return
        
        entry_count = reader.read_u32()
        self.fields["entry_count"] = entry_count
        
        # Parse nested sub-boxes (avc1, mp4a, etc.)
        from core.parser import parse_box_stream
        end_offset = self.payload_offset + self.payload_size
        self.children = parse_box_stream(reader, end_offset)

    def to_dict(self) -> dict:
        res = super().to_dict()
        res["is_container"] = True
        res["children"] = [child.to_dict() for child in self.children]
        return res

@register_box("ctts")
class CttsBox(FullBox):
    """Composition Time-to-Sample Box: maps decoding time to composition time."""
    def parse_payload(self, reader: BinaryReader) -> None:
        entry_count = reader.read_u32()
        entries = []
        for _ in range(min(entry_count, 1000)):
            sample_count = reader.read_u32()
            if self.version == 1:
                import struct
                sample_offset = struct.unpack(">i", reader.read_bytes(4))[0]
            else:
                sample_offset = reader.read_u32()
            entries.append({"sample_count": sample_count, "sample_offset": sample_offset})
            
        if entry_count > 1000:
            reader.skip(8 * (entry_count - 1000))
            
        self.fields.update({
            "entry_count": entry_count,
            "composition_time_table": make_preview_list(entries, limit=20)
        })

@register_box("stss")
class StssBox(FullBox):
    """Sync Sample Box: identifies keyframes (sync samples) in the track."""
    def parse_payload(self, reader: BinaryReader) -> None:
        entry_count = reader.read_u32()
        sync_samples = []
        for _ in range(min(entry_count, 10000)):
            sync_samples.append(reader.read_u32())
        if entry_count > 10000:
            reader.skip(4 * (entry_count - 10000))
            
        self.fields.update({
            "entry_count": entry_count,
            "sync_samples_preview": make_preview_list(sync_samples)
        })

@register_box("elst")
class ElstBox(FullBox):
    """Edit List Box: maps track timeline to movie timeline."""
    def parse_payload(self, reader: BinaryReader) -> None:
        entry_count = reader.read_u32()
        entries = []
        
        for _ in range(min(entry_count, 1000)):
            if self.version == 1:
                segment_duration = reader.read_u64()
                # Signed 64-bit int
                import struct
                media_time = struct.unpack(">q", reader.read_bytes(8))[0]
            else:
                segment_duration = reader.read_u32()
                import struct
                media_time = struct.unpack(">i", reader.read_bytes(4))[0]
                
            media_rate = reader.read_fixed_point_16_16()
            entries.append({
                "segment_duration": segment_duration,
                "media_time": media_time,
                "media_rate": media_rate
            })
            
        if entry_count > 1000:
            entry_size = 20 if self.version == 1 else 12
            reader.skip(entry_size * (entry_count - 1000))
            
        self.fields.update({
            "entry_count": entry_count,
            "edit_list_table": make_preview_list(entries, limit=20)
        })

@register_box("dref")
class DrefBox(FullBox):
    """Data Reference Box: contains data entry boxes (urls/urns)."""
    def __init__(self, offset: int, size: int, type_bytes: bytes, header_size: int, uuid: Optional[bytes] = None):
        super().__init__(offset, size, type_bytes, header_size, uuid)
        self.children: List[Box] = []

    def parse_payload(self, reader: BinaryReader) -> None:
        if self.payload_size < 4:
            return
        entry_count = reader.read_u32()
        self.fields["entry_count"] = entry_count
        
        # Parse nested sub-boxes (url, etc.)
        from core.parser import parse_box_stream
        end_offset = self.payload_offset + self.payload_size
        self.children = parse_box_stream(reader, end_offset)

    def to_dict(self) -> dict:
        res = super().to_dict()
        res["is_container"] = True
        res["children"] = [child.to_dict() for child in self.children]
        return res

@register_box("url ")
class UrlBox(FullBox):
    """Data Entry URL Box: points to media location."""
    def parse_payload(self, reader: BinaryReader) -> None:
        # If flag 0x000001 is set, media is in same file, URL is empty
        if self.flags & 0x000001:
            self.fields["location"] = "Self-contained (media inside this file)"
        else:
            # URL is a null-terminated string representing location
            rem_len = self.payload_size
            if rem_len > 0:
                self.fields["location"] = reader.read_string(rem_len).strip("\x00")
            else:
                self.fields["location"] = ""

@register_box("avc1")
@register_box("avc2")
@register_box("avc3")
@register_box("avc4")
@register_box("hvc1")
@register_box("hev1")
class Avc1Box(Box):
    """AVC Sample Entry: video codec sample description."""
    def __init__(self, offset: int, size: int, type_bytes: bytes, header_size: int, uuid: Optional[bytes] = None):
        super().__init__(offset, size, type_bytes, header_size, uuid)
        self.children: List[Box] = []

    def parse_payload(self, reader: BinaryReader) -> None:
        if self.payload_size < 78:
            return
        
        # Skip 6 bytes reserved
        reader.skip(6)
        data_reference_index = reader.read_u16()
        # Skip 16 bytes pre-defined/reserved
        reader.skip(16)
        
        width_offset = reader.tell()
        width = reader.read_u16()
        
        height_offset = reader.tell()
        height = reader.read_u16()
        
        horizres_offset = reader.tell()
        horizresolution = reader.read_fixed_point_16_16()
        
        vertres_offset = reader.tell()
        vertresolution = reader.read_fixed_point_16_16()
        
        # Skip 4 bytes reserved
        reader.skip(4)
        
        frame_count_offset = reader.tell()
        frame_count = reader.read_u16()
        
        # Compressor name (32 bytes Pascal string)
        comp_len = reader.read_u8()
        if comp_len > 31: comp_len = 31
        compressor = reader.read_string(comp_len)
        reader.skip(31 - comp_len) # Skip remainder of 32 bytes
        
        depth_offset = reader.tell()
        depth = reader.read_u16()
        # Skip 2 bytes pre-defined (-1)
        reader.skip(2)
        
        self.fields.update({
            "data_reference_index": data_reference_index,
            "width": width,
            "height": height,
            "horizresolution": horizresolution,
            "vertresolution": vertresolution,
            "frame_count": frame_count,
            "compressorname": compressor,
            "depth": depth
        })

        self.editable_fields.update({
            "width": {
                "offset": width_offset,
                "format": ">H",
                "value": width,
                "label": "Width",
                "type": "uint16"
            },
            "height": {
                "offset": height_offset,
                "format": ">H",
                "value": height,
                "label": "Height",
                "type": "uint16"
            },
            "horizresolution": {
                "offset": horizres_offset,
                "format": ">I",
                "value": horizresolution,
                "label": "Horizontal Resolution",
                "type": "fixed16_16"
            },
            "vertresolution": {
                "offset": vertres_offset,
                "format": ">I",
                "value": vertresolution,
                "label": "Vertical Resolution",
                "type": "fixed16_16"
            },
            "frame_count": {
                "offset": frame_count_offset,
                "format": ">H",
                "value": frame_count,
                "label": "Frame Count",
                "type": "uint16"
            },
            "depth": {
                "offset": depth_offset,
                "format": ">H",
                "value": depth,
                "label": "Depth",
                "type": "uint16"
            }
        })
        
        # Parse nested boxes starting at offset 78 (avcC, colr, etc.)
        from core.parser import parse_box_stream
        end_offset = self.payload_offset + self.payload_size
        reader.seek(self.payload_offset + 78)
        self.children = parse_box_stream(reader, end_offset)

    def to_dict(self) -> dict:
        res = super().to_dict()
        res["is_container"] = True
        res["children"] = [child.to_dict() for child in self.children]
        return res

@register_box("avcC")
class AvccBox(Box):
    """AVC Configuration Box: holds decoder configurations including SPS and PPS."""
    def parse_payload(self, reader: BinaryReader) -> None:
        if self.payload_size < 7:
            return
        
        config_version = reader.read_u8()
        profile_indication = reader.read_u8()
        profile_compatibility = reader.read_u8()
        level_indication = reader.read_u8()
        
        len_size_byte = reader.read_u8()
        length_size = (len_size_byte & 0x03) + 1
        
        num_sps_byte = reader.read_u8()
        num_sps = num_sps_byte & 0x1F
        
        sps_list = []
        for _ in range(num_sps):
            sps_len = reader.read_u16()
            sps_bytes = reader.read_bytes(sps_len)
            sps_list.append({
                "length": sps_len,
                "hex": sps_bytes.hex().upper()
            })
            
        num_pps = reader.read_u8()
        pps_list = []
        for _ in range(num_pps):
            pps_len = reader.read_u16()
            pps_bytes = reader.read_bytes(pps_len)
            pps_list.append({
                "length": pps_len,
                "hex": pps_bytes.hex().upper()
            })
            
        self.fields.update({
            "configuration_version": config_version,
            "avc_profile_indication": profile_indication,
            "profile_compatibility": f"0x{profile_compatibility:02X}",
            "avc_level_indication": level_indication,
            "length_size_bytes": length_size,
            "num_sps": num_sps,
            "sps": sps_list,
            "num_pps": num_pps,
            "pps": pps_list
        })

@register_box("colr")
class ColrBox(Box):
    """Color Information Box: video color specifications."""
    def parse_payload(self, reader: BinaryReader) -> None:
        if self.payload_size < 4:
            return
        
        colour_type = reader.read_string(4)
        self.fields["colour_type"] = colour_type
        
        if colour_type == "nclx" and self.payload_size >= 10:
            primaries_offset = reader.tell()
            colour_primaries = reader.read_u16()
            
            transfer_offset = reader.tell()
            transfer_characteristics = reader.read_u16()
            
            matrix_offset = reader.tell()
            matrix_coefficients = reader.read_u16()
            
            full_range_offset = reader.tell()
            full_range_byte = reader.read_u8()
            full_range = bool((full_range_byte >> 7) & 1)
            
            self.fields.update({
                "colour_primaries": colour_primaries,
                "transfer_characteristics": transfer_characteristics,
                "matrix_coefficients": matrix_coefficients,
                "full_range_flag": full_range
            })

            self.editable_fields.update({
                "colour_primaries": {
                    "offset": primaries_offset,
                    "format": ">H",
                    "value": colour_primaries,
                    "label": "Colour Primaries",
                    "type": "uint16"
                },
                "transfer_characteristics": {
                    "offset": transfer_offset,
                    "format": ">H",
                    "value": transfer_characteristics,
                    "label": "Transfer Characteristics",
                    "type": "uint16"
                },
                "matrix_coefficients": {
                    "offset": matrix_offset,
                    "format": ">H",
                    "value": matrix_coefficients,
                    "label": "Matrix Coefficients",
                    "type": "uint16"
                },
                "full_range_flag": {
                    "offset": full_range_offset,
                    "format": ">B",
                    "value": 1 if full_range else 0,
                    "label": "Full Range Flag",
                    "type": "full_range_bit"
                }
            })

@register_box("hvcC")
class HvcCBox(Box):
    """HEVC Configuration Box: holds decoder configurations including VPS, SPS, and PPS."""
    def parse_payload(self, reader: BinaryReader) -> None:
        if self.payload_size < 22:
            return
            
        config_version = reader.read_u8()
        
        # Profile, Tier, IDC
        profile_space_tier_idc = reader.read_u8()
        profile_space = (profile_space_tier_idc >> 6) & 0x03
        tier_flag = bool((profile_space_tier_idc >> 5) & 0x01)
        profile_idc = profile_space_tier_idc & 0x1F
        
        profile_compat_flags = reader.read_u32()
        constraint_flags = reader.read_bytes(6).hex().upper()
        level_idc = reader.read_u8()
        
        # min_spatial_segmentation_idc (16-bit, mask lower 12 bits)
        min_spatial_seg = reader.read_u16() & 0x0FFF
        
        parallelism_type = reader.read_u8() & 0x03
        chroma_format = reader.read_u8() & 0x03
        bit_depth_luma = (reader.read_u8() & 0x07) + 8
        bit_depth_chroma = (reader.read_u8() & 0x07) + 8
        avg_frame_rate = reader.read_u16()
        
        flags_byte = reader.read_u8()
        constant_frame_rate = (flags_byte >> 6) & 0x03
        num_temporal_layers = (flags_byte >> 3) & 0x07
        temporal_id_nested = bool((flags_byte >> 2) & 0x01)
        length_size = (flags_byte & 0x03) + 1
        
        num_arrays = reader.read_u8()
        
        vps_list = []
        sps_list = []
        pps_list = []
        sei_list = []
        
        for _ in range(num_arrays):
            array_info = reader.read_u8()
            completeness = bool((array_info >> 7) & 1)
            nal_type = array_info & 0x3F
            
            num_nalus = reader.read_u16()
            for _ in range(num_nalus):
                nal_len = reader.read_u16()
                nal_bytes = reader.read_bytes(nal_len)
                nal_hex = nal_bytes.hex().upper()
                
                entry = {
                    "length": nal_len,
                    "hex": nal_hex
                }
                
                if nal_type == 32: # VPS
                    vps_list.append(entry)
                elif nal_type == 33: # SPS
                    sps_list.append(entry)
                elif nal_type == 34: # PPS
                    pps_list.append(entry)
                else:
                    sei_list.append({
                        "nal_type": nal_type,
                        "length": nal_len,
                        "hex": nal_hex
                    })
                    
        self.fields.update({
            "configuration_version": config_version,
            "hevc_profile_idc": profile_idc,
            "hevc_level_idc": level_idc,
            "tier_flag": tier_flag,
            "bit_depth_luma_minus8": bit_depth_luma - 8,
            "bit_depth_chroma_minus8": bit_depth_chroma - 8,
            "chroma_format_idc": chroma_format,
            "length_size_bytes": length_size,
            "avg_frame_rate": avg_frame_rate,
            "num_arrays": num_arrays,
            "vps": vps_list,
            "sps": sps_list,
            "pps": pps_list
        })
        if sei_list:
            self.fields["other_nalus"] = sei_list
