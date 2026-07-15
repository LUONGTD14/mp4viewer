import struct
from typing import BinaryIO

def write_box_header(f: BinaryIO, fourcc: bytes, size: int) -> None:
    """Writes standard 8-byte box header."""
    f.write(struct.pack(">I", size))
    f.write(fourcc)

def create_ftyp_payload(major: str, minor: int, brands: list) -> bytes:
    payload = major.encode("ascii")[:4].ljust(4)
    payload += struct.pack(">I", minor)
    for b in brands:
        payload += b.encode("ascii")[:4].ljust(4)
    return payload

def create_mvhd_payload(version: int, creation: int, modification: int, timescale: int, duration: int) -> bytes:
    # FullBox header (version + flags)
    header = struct.pack(">I", (version << 24) & 0xFF000000)
    
    if version == 1:
        times = struct.pack(">QQIQ", creation, modification, timescale, duration)
    else:
        times = struct.pack(">IIII", creation, modification, timescale, duration)
        
    rate_vol = struct.pack(">i h 10x", 0x00010000, 0x0100) # rate=1.0, volume=1.0, reserved=10
    matrix = struct.pack(">9i", 0x00010000, 0, 0, 0, 0x00010000, 0, 0, 0, 0x40000000) # matrix identity
    next_track = struct.pack(">24x I", 2) # reserved=24, next_track_id=2
    
    return header + times + rate_vol + matrix + next_track

def create_tkhd_payload(version: int, creation: int, modification: int, track_id: int, duration: int, width: int, height: int) -> bytes:
    header = struct.pack(">I", (version << 24) & 0xFF000000 | 0x03) # flags=3 (track enabled/in movie)
    
    if version == 1:
        times = struct.pack(">QQI 4x Q", creation, modification, track_id, duration)
    else:
        times = struct.pack(">III 4x I", creation, modification, track_id, duration)
        
    reserved = struct.pack(">8x h h h 2x", 0, 0, 0x0100) # reserved=8, layer=0, group=0, volume=1.0, reserved=2
    matrix = struct.pack(">9i", 0x00010000, 0, 0, 0, 0x00010000, 0, 0, 0, 0x40000000)
    sizes = struct.pack(">II", width << 16, height << 16)
    
    return header + times + reserved + matrix + sizes

def create_stsz_payload(default_size: int, sample_count: int, sizes: list = None) -> bytes:
    header = struct.pack(">I", 0) # version=0, flags=0
    payload = struct.pack(">II", default_size, sample_count)
    if default_size == 0 and sizes:
        for s in sizes[:sample_count]:
            payload += struct.pack(">I", s)
    return header + payload

def create_stco_payload(offsets: list) -> bytes:
    header = struct.pack(">I", 0) # version=0, flags=0
    payload = struct.pack(">I", len(offsets))
    for off in offsets:
        payload += struct.pack(">I", off)
    return header + payload

def create_hdlr_payload(handler_type: bytes, name: bytes) -> bytes:
    header = struct.pack(">I", 0) # version=0, flags=0
    payload = struct.pack(">I", 0) + handler_type + struct.pack(">12x") + name + b"\x00"
    return header + payload

def create_vmhd_payload() -> bytes:
    header = struct.pack(">I", 0 | 0x000001) # version=0, flags=1
    payload = struct.pack(">H H H H", 0, 0, 0, 0) # graphics_mode=0, opcolor=(0,0,0)
    return header + payload

def create_stsd_payload() -> bytes:
    header = struct.pack(">I", 0) # version=0, flags=0
    
    # 1. avcC Box
    sps = b'\x67\x42\x00\x0a\xf8\x0f\x00\x44\x08\x02'
    pps = b'\x68\xce\x38\x80'
    avcc_payload = struct.pack(">B B B B B B", 1, 66, 0, 10, 0xFF, 0xE1) + struct.pack(">H", len(sps)) + sps + struct.pack(">B", 1) + struct.pack(">H", len(pps)) + pps
    avcc_box = make_box(b"avcC", avcc_payload)
    
    # 2. colr Box
    colr_payload = b"nclx" + struct.pack(">H H H B", 1, 1, 1, 0x80)
    colr_box = make_box(b"colr", colr_payload)
    
    # 3. avc1 Box (78 bytes header + sub-boxes)
    compressor = b"AVC Coding".ljust(31, b"\x00")
    avc1_header = struct.pack(">6x H 16x H H I I 4x H B 31s H h", 1, 1920, 1080, 0x00480000, 0x00480000, 1, len(b"AVC Coding"), compressor, 24, -1)
    avc1_box = make_box(b"avc1", avc1_header + avcc_box + colr_box)
    
    return header + struct.pack(">I", 1) + avc1_box

def create_ctts_payload(entries: list) -> bytes:
    header = struct.pack(">I", 0) # version=0, flags=0
    payload = struct.pack(">I", len(entries))
    for count, offset in entries:
        payload += struct.pack(">II", count, offset)
    return header + payload

def create_stss_payload(keyframes: list) -> bytes:
    header = struct.pack(">I", 0) # version=0, flags=0
    payload = struct.pack(">I", len(keyframes))
    for k in keyframes:
        payload += struct.pack(">I", k)
    return header + payload

def create_stsd_hevc_payload() -> bytes:
    header = struct.pack(">I", 0) # version=0, flags=0
    
    # 1. hvcC Box (HEVC configuration)
    vps = b'\x40\x01\x0c\x01\xff\xff\x01\x40\x00\x00\x03\x00\x00\x03\x00\x00\x03\x00\x00\x03\x00\x99\x00'
    sps = b'\x42\x01\x01\x01\x60\x00\x00\x03\x00\x90'
    pps = b'\x44\x01\xc0\xf7\xf0'
    
    # Header format: 22 bytes configuration params (using H, I and B types)
    hvcc_payload = struct.pack(">B B I I H B H B B B B H B", 1, 0x01, 0x60000000, 0, 0, 93, 0, 0xFC, 0xFC, 0xFC, 0xFC, 0, 0xF0 | 3)
    hvcc_payload += struct.pack(">B", 3) # num_arrays = 3
    
    # Array 1: VPS (type 32)
    hvcc_payload += struct.pack(">B H", 0x80 | 32, 1) + struct.pack(">H", len(vps)) + vps
    # Array 2: SPS (type 33)
    hvcc_payload += struct.pack(">B H", 0x80 | 33, 1) + struct.pack(">H", len(sps)) + sps
    # Array 3: PPS (type 34)
    hvcc_payload += struct.pack(">B H", 0x80 | 34, 1) + struct.pack(">H", len(pps)) + pps
    
    hvcc_box = make_box(b"hvcC", hvcc_payload)
    
    # 2. hev1 Box (78 bytes header + sub-boxes)
    compressor = b"HEVC Coding".ljust(31, b"\x00")
    hev1_header = struct.pack(">6x H 16x H H I I 4x H B 31s H h", 1, 1920, 1080, 0x00480000, 0x00480000, 1, len(b"HEVC Coding"), compressor, 24, -1)
    hev1_box = make_box(b"hev1", hev1_header + hvcc_box)
    
    return header + struct.pack(">I", 1) + hev1_box

def make_box(fourcc: bytes, payload: bytes) -> bytes:
    size = len(payload) + 8
    return struct.pack(">I", size) + fourcc + payload

def generate_mock_mp4(filepath: str) -> None:
    """Generates a small valid MP4 file for parser unit testing."""
    with open(filepath, "wb") as f:
        # 1. ftyp Box
        ftyp_pay = create_ftyp_payload("mp42", 1, ["mp42", "isom"])
        f.write(make_box(b"ftyp", ftyp_pay))
        
        # 2. free Box
        f.write(make_box(b"free", b"Placeholder space inside free box"))
        
        # 3. moov Container Box
        # 3a. mvhd Box
        mvhd_pay = create_mvhd_payload(0, 3500000000, 3500000000, 1000, 5000)
        mvhd_box = make_box(b"mvhd", mvhd_pay)
        
        # 3b. Track 1: AVC Container Box (contains tkhd, edts, mdia)
        tkhd_pay = create_tkhd_payload(0, 3500000000, 3500000000, 1, 5000, 1920, 1080)
        tkhd_box = make_box(b"tkhd", tkhd_pay)
        
        # edts -> elst
        elst_payload = struct.pack(">I I I i I", 0, 1, 5000, 0, 0x00010000) # ver 0, count 1, dur 5000, media_time 0, rate 1.0
        elst_box = make_box(b"elst", elst_payload)
        edts_box = make_box(b"edts", elst_box)
        
        # mdia -> mdhd, hdlr, minf
        mdhd_pay = create_mvhd_payload(0, 3500000000, 3500000000, 1000, 5000)
        mdhd_box = make_box(b"mdhd", mdhd_pay)
        
        hdlr_pay = create_hdlr_payload(b"vide", b"VideoHandler")
        hdlr_box = make_box(b"hdlr", hdlr_pay)
        
        # minf -> vmhd, dinf, stbl
        vmhd_pay = create_vmhd_payload()
        vmhd_box = make_box(b"vmhd", vmhd_pay)
        
        # dinf -> dref -> url 
        url_box = make_box(b"url ", struct.pack(">I", 1)) # flags=1 (self contained)
        dref_payload = struct.pack(">I I", 0, 1) + url_box # ver=0, count=1
        dref_box = make_box(b"dref", dref_payload)
        dinf_box = make_box(b"dinf", dref_box)
        
        # stbl -> stsd, stts, ctts, stsc, stsz, stco, stss
        stsd_pay = create_stsd_payload()
        stsd_box = make_box(b"stsd", stsd_pay)
        
        stts_pay = struct.pack(">I I I I", 0, 1, 5, 1000)
        stts_box = make_box(b"stts", stts_pay)
        
        ctts_pay = create_ctts_payload([(3, 100), (2, 200)])
        ctts_box = make_box(b"ctts", ctts_pay)
        
        stsc_pay = struct.pack(">I I I I I", 0, 1, 1, 5, 1)
        stsc_box = make_box(b"stsc", stsc_pay)
        
        stsz_pay = create_stsz_payload(0, 5, [1000, 1200, 950, 1100, 1050])
        stsz_box = make_box(b"stsz", stsz_pay)
        
        stco_pay = create_stco_payload([2000, 3000, 4000, 5000, 6000])
        stco_box = make_box(b"stco", stco_pay)
        
        stss_pay = create_stss_payload([1, 4])
        stss_box = make_box(b"stss", stss_pay)
        
        stbl_box = make_box(b"stbl", stsd_box + stts_box + ctts_box + stsc_box + stsz_box + stco_box + stss_box)
        minf_box = make_box(b"minf", vmhd_box + dinf_box + stbl_box)
        mdia_box = make_box(b"mdia", mdhd_box + hdlr_box + minf_box)
        trak_box = make_box(b"trak", tkhd_box + edts_box + mdia_box)
        
        # 3b_2. Track 2: HEVC Track
        tkhd_pay_2 = create_tkhd_payload(0, 3500000000, 3500000000, 2, 5000, 1920, 1080)
        tkhd_box_2 = make_box(b"tkhd", tkhd_pay_2)
        
        stsd_pay_2 = create_stsd_hevc_payload()
        stsd_box_2 = make_box(b"stsd", stsd_pay_2)
        
        stbl_box_2 = make_box(b"stbl", stsd_box_2 + stts_box + ctts_box + stsc_box + stsz_box + stco_box + stss_box)
        minf_box_2 = make_box(b"minf", vmhd_box + dinf_box + stbl_box_2)
        mdia_box_2 = make_box(b"mdia", mdhd_box + hdlr_box + minf_box_2)
        trak_box_2 = make_box(b"trak", tkhd_box_2 + edts_box + mdia_box_2)
        
        # mvex -> trex
        trex_payload = struct.pack(">I I I I I I", 0, 1, 1, 1000, 1000, 0x00010000)
        trex_box = make_box(b"trex", trex_payload)
        mvex_box = make_box(b"mvex", trex_box)
        
        moov_pay = mvhd_box + trak_box + trak_box_2 + mvex_box
        f.write(make_box(b"moov", moov_pay))
        
        # 4. moof Container Box (Movie Fragment)
        mfhd_payload = struct.pack(">I I", 0, 123) # ver=0, seq_num=123
        mfhd_box = make_box(b"mfhd", mfhd_payload)
        
        tfhd_payload = struct.pack(">I I", 0x00000002, 1) + struct.pack(">I", 1) # flags=2 (default sample desc present), track_id=1, sample desc index=1
        tfhd_box = make_box(b"tfhd", tfhd_payload)
        
        trun_payload = struct.pack(">I I", 0x00000300, 2) # flags=0x300 (duration & size present), sample_count=2
        trun_payload += struct.pack(">I I", 1000, 1000) # sample 1: dur 1000, size 1000
        trun_payload += struct.pack(">I I", 1000, 1100) # sample 2: dur 1000, size 1100
        trun_box = make_box(b"trun", trun_payload)
        
        traf_box = make_box(b"traf", tfhd_box + trun_box)
        moof_box = make_box(b"moof", mfhd_box + traf_box)
        f.write(moof_box)
        
        # 5. mdat Box
        f.write(make_box(b"mdat", b"MOCK VIDEO MEDIA DATA STREAM PAYLOAD"))

if __name__ == "__main__":
    generate_mock_mp4("mock_sample.mp4")
    print("Generated mock_sample.mp4 successfully!")
