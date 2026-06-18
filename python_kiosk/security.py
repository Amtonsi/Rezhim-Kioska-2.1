import binascii
import hashlib
import hmac
import os
import struct


DEFAULT_ITERATIONS = 200000
DEFAULT_ALGORITHM = "sha256"
SALT_BYTES = 16
KEY_BYTES = 32


class FailedAttemptLimiter(object):
    def __init__(
        self,
        threshold=3,
        base_delay_seconds=2,
        max_delay_seconds=30,
    ):
        self.threshold = int(threshold)
        self.base_delay_seconds = int(base_delay_seconds)
        self.max_delay_seconds = int(max_delay_seconds)
        self.failures = 0

    def record_failure(self):
        self.failures += 1
        if self.failures < self.threshold:
            return 0
        delay = self.base_delay_seconds * (self.failures - self.threshold + 1)
        return min(delay, self.max_delay_seconds)

    def record_success(self):
        self.failures = 0


def _to_bytes(value):
    if isinstance(value, bytes):
        return value
    return value.encode("utf-8")


def _constant_time_compare(left, right):
    if hasattr(hmac, "compare_digest"):
        return hmac.compare_digest(left, right)
    if len(left) != len(right):
        return False
    result = 0
    for index in range(len(left)):
        result |= ord(left[index:index + 1]) ^ ord(right[index:index + 1])
    return result == 0


def _pbkdf2_fallback(password_bytes, salt_bytes, iterations, dklen, digest_name):
    digest_size = hashlib.new(digest_name).digest_size
    blocks = []
    block_count = int((dklen + digest_size - 1) / digest_size)
    for block_index in range(1, block_count + 1):
        initial = hmac.new(
            password_bytes,
            salt_bytes + struct.pack(">I", block_index),
            digest_name,
        ).digest()
        block = bytearray(initial)
        previous = initial
        for _ in range(iterations - 1):
            previous = hmac.new(password_bytes, previous, digest_name).digest()
            for offset in range(len(block)):
                block[offset] ^= previous[offset]
        blocks.append(bytes(block))
    return b"".join(blocks)[:dklen]


def derive_key(password, salt, iterations=DEFAULT_ITERATIONS):
    password_bytes = _to_bytes(password)
    salt_bytes = binascii.unhexlify(salt)
    if hasattr(hashlib, "pbkdf2_hmac"):
        return hashlib.pbkdf2_hmac(
            DEFAULT_ALGORITHM,
            password_bytes,
            salt_bytes,
            iterations,
            KEY_BYTES,
        )
    return _pbkdf2_fallback(
        password_bytes,
        salt_bytes,
        iterations,
        KEY_BYTES,
        DEFAULT_ALGORITHM,
    )


def hash_password(password, iterations=DEFAULT_ITERATIONS):
    salt = binascii.hexlify(os.urandom(SALT_BYTES)).decode("ascii")
    key = derive_key(password, salt, iterations)
    return {
        "algorithm": "pbkdf2_hmac_" + DEFAULT_ALGORITHM,
        "iterations": int(iterations),
        "salt": salt,
        "hash": binascii.hexlify(key).decode("ascii"),
    }


def verify_password(password, record):
    try:
        iterations = int(record["iterations"])
        expected_hash = record["hash"]
        actual_key = derive_key(password, record["salt"], iterations)
        actual_hash = binascii.hexlify(actual_key).decode("ascii")
    except (KeyError, TypeError, ValueError, binascii.Error):
        return False
    return _constant_time_compare(actual_hash, expected_hash)
