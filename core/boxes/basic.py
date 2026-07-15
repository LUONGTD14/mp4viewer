from core.models import Box
from core.registry import register_box
from core.reader import BinaryReader

@register_box("ftyp")
class FtypBox(Box):
    """File Type Box: identifies the specifications with which the file complies."""
    def parse_payload(self, reader: BinaryReader) -> None:
        if self.payload_size < 8:
            return
        
        self.major_brand = reader.read_string(4)
        self.minor_version = reader.read_u32()
        
        # The rest of the payload size is compatible brands (4 bytes each)
        comp_size = self.payload_size - 8
        compatible_brands = []
        for _ in range(comp_size // 4):
            brand = reader.read_string(4)
            if brand.strip():
                compatible_brands.append(brand)
                
        self.fields["major_brand"] = self.major_brand
        self.fields["minor_version"] = self.minor_version
        self.fields["compatible_brands"] = compatible_brands

@register_box("free")
@register_box("skip")
class FreeBox(Box):
    """Free or Skip Box: empty space that can be used for editing in-place."""
    def parse_payload(self, reader: BinaryReader) -> None:
        self.fields["info"] = f"Placeholder space of {self.payload_size} bytes"

@register_box("mdat")
class MdatBox(Box):
    """Media Data Box: contains actual video/audio frames."""
    def parse_payload(self, reader: BinaryReader) -> None:
        self.fields["info"] = f"Raw audio/video payload ({self.payload_size} bytes)"
