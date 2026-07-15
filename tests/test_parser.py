import os
import pytest
from tests.make_mock_mp4 import generate_mock_mp4
from core.parser import parse_file
from core.models import ContainerBox

MOCK_FILE = "tests/test_temp_sample.mp4"

@pytest.fixture(scope="module", autouse=True)
def setup_mock_file():
    # Make sure tests directory exists
    os.makedirs("tests", exist_ok=True)
    generate_mock_mp4(MOCK_FILE)
    yield
    # Clean up after tests run
    if os.path.exists(MOCK_FILE):
        os.remove(MOCK_FILE)

def test_root_boxes():
    boxes = parse_file(MOCK_FILE)
    types = [b.type_str for b in boxes]
    assert "ftyp" in types
    assert "free" in types
    assert "moov" in types
    assert "mdat" in types

def test_ftyp_box():
    boxes = parse_file(MOCK_FILE)
    ftyp = next(b for b in boxes if b.type_str == "ftyp")
    assert ftyp.fields["major_brand"] == "mp42"
    assert ftyp.fields["minor_version"] == 1
    assert "mp42" in ftyp.fields["compatible_brands"]
    assert "isom" in ftyp.fields["compatible_brands"]

def test_mvhd_box():
    boxes = parse_file(MOCK_FILE)
    moov = next(b for b in boxes if b.type_str == "moov")
    assert isinstance(moov, ContainerBox)
    
    mvhd = next(b for b in moov.children if b.type_str == "mvhd")
    assert mvhd.fields["timescale"] == 1000
    assert mvhd.fields["duration"] == 5000
    assert mvhd.fields["duration_seconds"] == 5.0
    assert mvhd.fields["next_track_id"] == 2

def test_tkhd_box():
    boxes = parse_file(MOCK_FILE)
    moov = next(b for b in boxes if b.type_str == "moov")
    trak = next(b for b in moov.children if b.type_str == "trak")
    assert isinstance(trak, ContainerBox)
    
    tkhd = next(b for b in trak.children if b.type_str == "tkhd")
    assert tkhd.fields["track_id"] == 1
    assert tkhd.fields["width"] == 1920.0
    assert tkhd.fields["height"] == 1080.0

def test_sample_boxes():
    boxes = parse_file(MOCK_FILE)
    moov = next(b for b in boxes if b.type_str == "moov")
    trak = next(b for b in moov.children if b.type_str == "trak")
    mdia = next(b for b in trak.children if b.type_str == "mdia")
    minf = next(b for b in mdia.children if b.type_str == "minf")
    stbl = next(b for b in minf.children if b.type_str == "stbl")
    
    stsz = next(b for b in stbl.children if b.type_str == "stsz")
    assert stsz.fields["sample_count"] == 5
    assert stsz.fields["sample_sizes_preview"] == [1000, 1200, 950, 1100, 1050]
    
    stco = next(b for b in stbl.children if b.type_str == "stco")
    assert stco.fields["entry_count"] == 5
    assert stco.fields["chunk_offsets_preview"] == [2000, 3000, 4000, 5000, 6000]

    # Test hdlr
    hdlr = next(b for b in mdia.children if b.type_str == "hdlr")
    assert hdlr.fields["handler_type"] == "vide"
    assert hdlr.fields["handler_name"] == "VideoHandler"

    # Test vmhd
    vmhd = next(b for b in minf.children if b.type_str == "vmhd")
    assert vmhd.fields["graphics_mode"] == 0
    assert vmhd.fields["opcolor"] == [0, 0, 0]

    # Test stsd
    stsd = next(b for b in stbl.children if b.type_str == "stsd")
    assert stsd.fields["entry_count"] == 1
    assert len(stsd.children) == 1
    assert stsd.children[0].type_str == "avc1"
    
    # Test avc1 visual sample entry children (avcC and colr)
    avc1 = stsd.children[0]
    assert avc1.fields["width"] == 1920
    assert avc1.fields["height"] == 1080
    assert len(avc1.children) == 2
    assert any(b.type_str == "avcC" for b in avc1.children)
    assert any(b.type_str == "colr" for b in avc1.children)
    
    # Test avcC config parameters
    avcc = next(b for b in avc1.children if b.type_str == "avcC")
    assert avcc.fields["avc_profile_indication"] == 66
    assert avcc.fields["num_sps"] == 1
    assert avcc.fields["sps"][0]["hex"] == "6742000AF80F00440802"
    
    # Test colr parameters
    colr = next(b for b in avc1.children if b.type_str == "colr")
    assert colr.fields["colour_type"] == "nclx"
    assert colr.fields["colour_primaries"] == 1
    assert colr.fields["full_range_flag"] is True

    # Test ctts
    ctts = next(b for b in stbl.children if b.type_str == "ctts")
    assert ctts.fields["entry_count"] == 2
    assert ctts.fields["composition_time_table"][0]["sample_offset"] == 100

    # Test stss
    stss = next(b for b in stbl.children if b.type_str == "stss")
    assert stss.fields["entry_count"] == 2
    assert stss.fields["sync_samples_preview"] == [1, 4]

    # Test elst (in edts)
    edts = next(b for b in trak.children if b.type_str == "edts")
    elst = next(b for b in edts.children if b.type_str == "elst")
    assert elst.fields["entry_count"] == 1
    assert elst.fields["edit_list_table"][0]["segment_duration"] == 5000

    # Test dref & url (in dinf)
    dinf = next(b for b in minf.children if b.type_str == "dinf")
    dref = next(b for b in dinf.children if b.type_str == "dref")
    assert dref.fields["entry_count"] == 1
    assert len(dref.children) == 1
    assert dref.children[0].type_str == "url "
    assert "Self-contained" in dref.children[0].fields["location"]

def test_fragments_and_extends():
    boxes = parse_file(MOCK_FILE)
    moov = next(b for b in boxes if b.type_str == "moov")
    
    # Test mvex & trex inside moov
    mvex = next(b for b in moov.children if b.type_str == "mvex")
    trex = next(b for b in mvex.children if b.type_str == "trex")
    assert trex.fields["track_id"] == 1
    assert trex.fields["default_sample_duration"] == 1000

    # Test moof -> mfhd & traf -> tfhd & trun
    moof = next(b for b in boxes if b.type_str == "moof")
    mfhd = next(b for b in moof.children if b.type_str == "mfhd")
    assert mfhd.fields["sequence_number"] == 123
    
    traf = next(b for b in moof.children if b.type_str == "traf")
    tfhd = next(b for b in traf.children if b.type_str == "tfhd")
    assert tfhd.fields["track_id"] == 1
    assert tfhd.fields["sample_description_index"] == 1
    
    trun = next(b for b in traf.children if b.type_str == "trun")
    assert trun.fields["sample_count"] == 2
    assert trun.fields["samples_preview"][0]["size"] == 1000
    assert trun.fields["samples_preview"][1]["size"] == 1100

def test_hevc_track():
    boxes = parse_file(MOCK_FILE)
    moov = next(b for b in boxes if b.type_str == "moov")
    
    traks = [b for b in moov.children if b.type_str == "trak"]
    assert len(traks) == 2
    
    trak2 = traks[1]
    tkhd2 = next(b for b in trak2.children if b.type_str == "tkhd")
    assert tkhd2.fields["track_id"] == 2
    
    mdia = next(b for b in trak2.children if b.type_str == "mdia")
    minf = next(b for b in mdia.children if b.type_str == "minf")
    stbl = next(b for b in minf.children if b.type_str == "stbl")
    stsd = next(b for b in stbl.children if b.type_str == "stsd")
    
    hev1 = stsd.children[0]
    assert hev1.type_str == "hev1"
    
    hvcc = next(b for b in hev1.children if b.type_str == "hvcC")
    assert hvcc.fields["hevc_profile_idc"] == 1
    assert hvcc.fields["num_arrays"] == 3
    assert len(hvcc.fields["vps"]) == 1
    assert len(hvcc.fields["sps"]) == 1
    assert len(hvcc.fields["pps"]) == 1
