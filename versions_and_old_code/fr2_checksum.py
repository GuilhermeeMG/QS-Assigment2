# This file implements the FR2 (Communication Checksum)

def checksum(payload, n: int, received_checksum: int) -> bool:
    """Validate a packet using a XOR-based checksum.

    The checksum of a payload of n bytes {b1, b2, ..., bn} is:
        b1 XOR b2 XOR ... XOR bn

    For an empty payload (n == 0), the checksum is defined as 0.

    Invalid values in the parameters return False.

    Accepted payload formats:
    - bytes / bytearray
    """

    # Validating n.
    if not isinstance(n, int) or n < 0:
        return False

    # Validating received_checksum.
    if not isinstance(received_checksum, int) or not (0 <= received_checksum <= 255):
        return False

    # Validating payload type.
    if not isinstance(payload, (bytes, bytearray)):
        return False
    
    # Validating payload length.
    if len(payload) != n:
        return False
    
    # Computing the checksum.
    computed = 0
    for b in payload:
        computed ^= b
        
    return computed == received_checksum



if __name__ == "__main__":
    # Tests Examples
    print(checksum(bytes([]), 0, 0))
    print(checksum(bytes([]), 0, 1))
    print(checksum(bytes([]), 1, 0))
    print(checksum(bytes([0]), 1, 0))
    print(checksum(bytes([1]), 1, 1))
    print(checksum(bytes([18, 52, 86]), 3, 112))
    print(checksum(bytes([18, 52, 86]), 3, 113))
