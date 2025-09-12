from math import ceil
from tinyman.utils import int_to_bytes
from hashlib import sha256


def int_array(elements, size, default=0):
    array = [default] * size

    for i in range(len(elements)):
        array[i] = elements[i]
    bytes = b"".join(map(int_to_bytes, array))
    return bytes


def calculate_approval_hash(bytecode):
    approval_hash = bytes(32)
    # the AVM gives access to approval programs in chunks of up to 4096 bytes
    chunk_size = 4096
    num_chunks = ceil(len(bytecode) / chunk_size)
    chunk_hashes = b""
    for i in range(num_chunks):
        offset = (i * chunk_size)
        chunk = bytecode[offset: offset + chunk_size]
        chunk_hashes += sha256(chunk).digest()
    approval_hash = sha256(chunk_hashes).digest()
    return approval_hash
