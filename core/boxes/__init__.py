# Import submodules to register custom box classes
from core.boxes.basic import FtypBox, FreeBox, MdatBox
from core.boxes.container import ContainerBox
from core.boxes.headers import MvhdBox, TkhdBox, MdhdBox, HdlrBox, VmhdBox, SmhdBox
from core.boxes.samples import (
    StszBox, StcoBox, Co64Box, SttsBox, StscBox, StsdBox, CttsBox, StssBox,
    ElstBox, DrefBox, UrlBox, Avc1Box, AvccBox, ColrBox, HvcCBox
)
from core.boxes.metadata import MetaBox, KeysBox, IlstBox
from core.boxes.fragments import TrexBox, MfhdBox, TfhdBox, TrunBox
