import os
import struct
import pytest
from core.parser import parse_file
from core.writer import save_modified_file

# Helper to encode VINT size
def encode_vint(val: int) -> bytes:
    if val < 0:
        raise ValueError("VINT value must be positive")
    if val < 127:
        length = 1
    elif val < 16383:
        length = 2
    elif val < 2097151:
        length = 3
    elif val < 268435455:
        length = 4
    else:
        length = 8
        
    marker = 1 << (7 * length)
    encoded = val | marker
    return encoded.to_bytes(length, byteorder="big")

# Helper to encode an EBML element
def encode_element(el_id: int, payload: bytes) -> bytes:
    id_len = (el_id.bit_length() + 7) // 8 or 1
    id_bytes = el_id.to_bytes(id_len, byteorder="big")
    return id_bytes + encode_vint(len(payload)) + payload

MOCK_WEBM = "tests/mock_sample.webm"

@pytest.fixture(autouse=True)
def setup_mock_webm():
    # 1. EBML Header
    ebml_payload = (
        encode_element(0x4282, b"webm") +          # DocType
        encode_element(0x4286, b"\x01")            # EBMLVersion
    )
    ebml_element = encode_element(0x1A45DFA3, ebml_payload)
    
    # 2. Segment -> Info
    duration_payload = struct.pack(">f", 12.5)
    duration_element = encode_element(0x4489, duration_payload)
    info_payload = duration_element + encode_element(0x4D80, b"MockMuxer")
    info_element = encode_element(0x1549A966, info_payload)
    
    # 3. Segment -> Tracks -> TrackEntry
    track_num_element = encode_element(0xD7, b"\x05")  # TrackNumber = 5
    track_type_element = encode_element(0x83, b"\x01") # TrackType = 1 (Video)
    codec_id_element = encode_element(0x86, b"V_VP8")  # CodecID
    
    # Video sub-element
    width_element = encode_element(0xB0, b"\x02\x80")   # PixelWidth = 640
    height_element = encode_element(0xBA, b"\x01\xE0")  # PixelHeight = 480
    video_payload = width_element + height_element
    video_element = encode_element(0xE0, video_payload)
    
    track_entry_payload = track_num_element + track_type_element + codec_id_element + video_element
    track_entry_element = encode_element(0xAE, track_entry_payload)
    tracks_element = encode_element(0x1654AE6B, track_entry_element)
    
    segment_payload = info_element + tracks_element
    segment_element = encode_element(0x18538067, segment_payload)
    
    # Write mock WebM bytes
    with open(MOCK_WEBM, "wb") as f:
        f.write(ebml_element + segment_element)
        
    yield
    
    # Clean up
    if os.path.exists(MOCK_WEBM):
        os.remove(MOCK_WEBM)

def test_parse_ebml_webm():
    elements = parse_file(MOCK_WEBM)
    assert len(elements) == 2
    
    # Check EBML header
    ebml = elements[0]
    assert ebml.type_str == "EBML"
    doctype_el = next(c for c in ebml.children if c.name == "DocType")
    assert doctype_el.fields["DocType"] == "webm"
    
    # Check Segment
    segment = elements[1]
    assert segment.type_str == "Segment"
    
    info = next(c for c in segment.children if c.name == "Info")
    duration_el = next(c for c in info.children if c.name == "Duration")
    assert pytest.approx(duration_el.fields["Duration"]) == 12.5
    
    tracks = next(c for c in segment.children if c.name == "Tracks")
    track_entry = next(c for c in tracks.children if c.name == "TrackEntry")
    
    track_num_el = next(c for c in track_entry.children if c.name == "TrackNumber")
    assert track_num_el.fields["TrackNumber"] == 5
    
    video = next(c for c in track_entry.children if c.name == "Video")
    width_el = next(c for c in video.children if c.name == "PixelWidth")
    assert width_el.fields["PixelWidth"] == 640
    
    height_el = next(c for c in video.children if c.name == "PixelHeight")
    assert height_el.fields["PixelHeight"] == 480

def test_edit_and_save_ebml():
    elements = parse_file(MOCK_WEBM)
    segment = elements[1]
    tracks = next(c for c in segment.children if c.name == "Tracks")
    track_entry = next(c for c in tracks.children if c.name == "TrackEntry")
    video = next(c for c in track_entry.children if c.name == "Video")
    
    width_el = next(c for c in video.children if c.name == "PixelWidth")
    height_el = next(c for c in video.children if c.name == "PixelHeight")
    
    # Modify values in-memory
    width_el.editable_fields["PixelWidth"]["value"] = 1280
    height_el.editable_fields["PixelHeight"]["value"] = 720
    
    edited_file = "tests/mock_edited.webm"
    if os.path.exists(edited_file):
        os.remove(edited_file)
        
    try:
        save_modified_file(edited_file, MOCK_WEBM, elements)
        
        # Parse edited file back
        edited_elements = parse_file(edited_file)
        ed_segment = edited_elements[1]
        ed_tracks = next(c for c in ed_segment.children if c.name == "Tracks")
        ed_track_entry = next(c for c in ed_tracks.children if c.name == "TrackEntry")
        ed_video = next(c for c in ed_track_entry.children if c.name == "Video")
        
        ed_width = next(c for c in ed_video.children if c.name == "PixelWidth")
        ed_height = next(c for c in ed_video.children if c.name == "PixelHeight")
        
        # Assert values have been updated in the file!
        assert ed_width.fields["PixelWidth"] == 1280
        assert ed_height.fields["PixelHeight"] == 720
        
    finally:
        if os.path.exists(edited_file):
            os.remove(edited_file)
