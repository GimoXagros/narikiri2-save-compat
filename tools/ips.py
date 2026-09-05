"""Small deterministic IPS encoder/decoder used by the AN9J product build."""

from __future__ import annotations


HEADER = b"PATCH"
EOF = b"EOF"
MAX_OFFSET = 0xFFFFFF
MAX_RECORD = 0xFFFF


class IpsError(ValueError):
    pass


def _ranges(source: bytes, target: bytes) -> list[tuple[int, int]]:
    offsets = [index for index, pair in enumerate(zip(source, target)) if pair[0] != pair[1]]
    if not offsets:
        return []
    result: list[tuple[int, int]] = []
    start = previous = offsets[0]
    for offset in offsets[1:]:
        if offset != previous + 1 or offset - start >= MAX_RECORD:
            result.append((start, previous + 1))
            start = offset
        previous = offset
    result.append((start, previous + 1))
    return result


def create_ips(source: bytes, target: bytes) -> bytes:
    if len(source) != len(target):
        raise IpsError("this product build requires equal source and target sizes")
    patch = bytearray(HEADER)
    for start, end in _ranges(source, target):
        if start > MAX_OFFSET:
            raise IpsError(f"record offset 0x{start:X} exceeds IPS range")
        if start.to_bytes(3, "big") == EOF:
            raise IpsError("record begins at the reserved IPS EOF offset")
        payload = target[start:end]
        patch.extend(start.to_bytes(3, "big"))
        patch.extend(len(payload).to_bytes(2, "big"))
        patch.extend(payload)
    patch.extend(EOF)
    return bytes(patch)


def apply_ips(source: bytes, patch: bytes) -> bytes:
    if not patch.startswith(HEADER):
        raise IpsError("missing IPS PATCH header")
    output = bytearray(source)
    cursor = len(HEADER)
    while True:
        if cursor + 3 > len(patch):
            raise IpsError("truncated IPS record offset")
        marker = patch[cursor:cursor + 3]
        cursor += 3
        if marker == EOF:
            if cursor not in (len(patch), len(patch) - 3):
                raise IpsError("unexpected data after IPS EOF")
            if cursor == len(patch) - 3:
                final_size = int.from_bytes(patch[cursor:cursor + 3], "big")
                del output[final_size:]
                if len(output) < final_size:
                    output.extend(b"\x00" * (final_size - len(output)))
            return bytes(output)
        offset = int.from_bytes(marker, "big")
        if cursor + 2 > len(patch):
            raise IpsError("truncated IPS record size")
        size = int.from_bytes(patch[cursor:cursor + 2], "big")
        cursor += 2
        if size == 0:
            if cursor + 3 > len(patch):
                raise IpsError("truncated IPS RLE record")
            run_length = int.from_bytes(patch[cursor:cursor + 2], "big")
            value = patch[cursor + 2]
            cursor += 3
            payload = bytes([value]) * run_length
        else:
            if cursor + size > len(patch):
                raise IpsError("truncated IPS payload")
            payload = patch[cursor:cursor + size]
            cursor += size
        end = offset + len(payload)
        if end > len(output):
            output.extend(b"\x00" * (end - len(output)))
        output[offset:end] = payload
