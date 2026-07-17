from typing import Tuple, Optional

# Map of EBML Element ID -> (Element Name, Data Type)
# Supported types: 'master' (container), 'uint', 'int', 'float', 'string', 'utf8', 'binary', 'date'
EBML_ELEMENTS = {
    # EBML Header Elements
    0x1A45DFA3: ("EBML", "master"),
    0x4286: ("EBMLVersion", "uint"),
    0x42F2: ("EBMLReadVersion", "uint"),
    0x42F7: ("EBMLMaxIDLength", "uint"),
    0x42F3: ("EBMLMaxSizeLength", "uint"),
    0x4282: ("DocType", "string"),
    0x4287: ("DocTypeVersion", "uint"),
    0x4285: ("DocTypeReadVersion", "uint"),
    
    # Global/Segment Elements
    0x18538067: ("Segment", "master"),
    0x1549A966: ("Info", "master"),
    0x73A4: ("SegmentUUID", "binary"),
    0x4D80: ("MuxingApp", "utf8"),
    0x5741: ("WritingApp", "utf8"),
    0x2AD7B1: ("TimecodeScale", "uint"),
    0x4489: ("Duration", "float"),
    0x4461: ("DateUTC", "date"),
    0x7BA9: ("Title", "utf8"),
    
    # Cluster Elements
    0x1F43B675: ("Cluster", "master"),
    0xE7: ("Timecode", "uint"),
    0xA7: ("Position", "uint"),
    0xAB: ("PrevSize", "uint"),
    0xA3: ("SimpleBlock", "binary"),
    0xA0: ("BlockGroup", "master"),
    0xA1: ("Block", "binary"),
    
    # Tracks Elements
    0x1654AE6B: ("Tracks", "master"),
    0xAE: ("TrackEntry", "master"),
    0xD7: ("TrackNumber", "uint"),
    0x73C5: ("TrackUID", "uint"),
    0x83: ("TrackType", "uint"), # 1: Video, 2: Audio, 3: Complex
    0xB9: ("FlagEnabled", "uint"),
    0x88: ("FlagDefault", "uint"),
    0x55AA: ("FlagForced", "uint"),
    0x9C: ("FlagLacing", "uint"),
    0x6DE7: ("MinCache", "uint"),
    0x6DF8: ("MaxCache", "uint"),
    0x23E383: ("DefaultDuration", "uint"),
    0x55EE: ("MaxBlockAdditionID", "uint"),
    0x22B59C: ("Language", "string"),
    0x86: ("CodecID", "string"),
    0x63A2: ("CodecPrivate", "binary"),
    0x258688: ("CodecName", "utf8"),
    
    # Video settings inside TrackEntry
    0xE0: ("Video", "master"),
    0x9A: ("FlagInterlaced", "uint"),
    0xB0: ("PixelWidth", "uint"),
    0xBA: ("PixelHeight", "uint"),
    0x54B0: ("DisplayWidth", "uint"),
    0x54BA: ("DisplayHeight", "uint"),
    0x54B2: ("DisplayUnit", "uint"),
    0x54B3: ("AspectRatioType", "uint"),
    
    # Audio settings inside TrackEntry
    0xE1: ("Audio", "master"),
    0xB5: ("SamplingFrequency", "float"),
    0x78B5: ("OutputSamplingFrequency", "float"),
    0x9F: ("Channels", "uint"),
    0x6264: ("BitDepth", "uint"),
    
    # Content Encoding (Encryption / Compression)
    0x6D80: ("ContentEncodings", "master"),
    0x6240: ("ContentEncoding", "master"),
    
    # SeekHead Elements
    0x114D9B74: ("SeekHead", "master"),
    0x4DBB: ("Seek", "master"),
    0x53AB: ("SeekID", "binary"),
    0x53AC: ("SeekPosition", "uint"),
    
    # Cues Elements
    0x1C53BB6B: ("Cues", "master"),
    0xBB: ("CuePoint", "master"),
    0xB3: ("CueTime", "uint"),
    0xB7: ("CueTrackPositions", "master"),
    0xF7: ("CueTrack", "uint"),
    0xF1: ("CueClusterPosition", "uint"),
    
    # Tags Elements
    0x1254C367: ("Tags", "master"),
    0x7373: ("Tag", "master"),
    0x63C0: ("Targets", "master"),
    0x63C5: ("TagTrackUID", "uint"),
    0x67C8: ("SimpleTag", "master"),
    0x45A3: ("TagName", "utf8"),
    0x4487: ("TagString", "utf8"),
    0x4485: ("TagBinary", "binary"),
}

def get_element_info(element_id: int) -> Tuple[str, str]:
    """Returns (name, type) for an EBML Element ID. Defaults to unknown/binary if not registered."""
    return EBML_ELEMENTS.get(element_id, (f"Unknown_0x{element_id:X}", "binary"))
