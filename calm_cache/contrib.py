import sys
from hashlib import sha1


is_python3 = sys.version_info >= (3, 0, 0)


def sha1_key_func(key, key_prefix, version):
    """
    This function is used to generate keys for Django cache backend.

    Uses SHA1 hash of the user supplied key so that the resulting key
    always has predictable length and never exceeds underlying engine's
    limitations (250 charaters for memcached)

    Usage: add
    `'KEY_FUNCTION' 'calm_cache.contrib.sha1_key_func'`
    to your cache backend definition in Django settings.
    """
    if isinstance(key, str if is_python3 else unicode):
        key = key.encode('utf-8')
    return '%s:%s:%s' % (key_prefix, version, sha1(key).hexdigest())
