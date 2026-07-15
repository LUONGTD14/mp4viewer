from typing import Dict, Type, Set
from core.models import Box, ContainerBox

# Registry to map 4-byte box types to specific Box subclasses
_BOX_REGISTRY: Dict[bytes, Type[Box]] = {}

# A set of known container box types. If a box isn't registered but is a known container,
# we default to parsing it as a ContainerBox so we can inspect its children.
_KNOWN_CONTAINERS: Set[bytes] = {
    b'moov', b'trak', b'mdia', b'minf', b'stbl', b'dinf', b'udta',
    b'mvex', b'moof', b'traf', b'mfra', b'meco', b'strk', b'edts',
    b'sinf', b'fiin', b'ipro', b'hli1', b'meta', b'ilst'
}

def register_box(type_str_or_bytes: str | bytes):
    """Decorator to register a custom box class parser."""
    def decorator(cls: Type[Box]):
        if isinstance(type_str_or_bytes, str):
            key = type_str_or_bytes.encode("latin1")
        else:
            key = type_str_or_bytes
        _BOX_REGISTRY[key] = cls
        return cls
    return decorator

def get_box_class(type_bytes: bytes) -> Type[Box]:
    """Retrieves the class parser for the given box type, defaulting to ContainerBox or Box."""
    if type_bytes in _BOX_REGISTRY:
        return _BOX_REGISTRY[type_bytes]
    elif type_bytes in _KNOWN_CONTAINERS:
        return ContainerBox
    return Box
