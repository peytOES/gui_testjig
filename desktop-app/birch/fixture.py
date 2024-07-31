import sys
import binascii
import uuid
import hashlib

APPLICATION_ID = b'\xbe\xd8\xb9\xc77\xe6\x0e\x84\xc9\xdc\x9e\xc6\xef_\xc6\x13'


def fixture_id():
    if sys.platform == "win32":
        import winreg
        registry = winreg.HKEY_LOCAL_MACHINE
        address = 'SOFTWARE\\Microsoft\\Cryptography'
        keyargs = winreg.KEY_READ | winreg.KEY_WOW64_64KEY
        key = winreg.OpenKey(registry, address, 0, keyargs)
        value = winreg.QueryValueEx(key, 'MachineGuid')
        winreg.CloseKey(key)
        machine_id = bytearray(value[0], "utf-8")
    else:
        val = open("/etc/machine-id").read().strip()
        machine_id = binascii.a2b_hex(val)

    dk = hashlib.pbkdf2_hmac("sha256", APPLICATION_ID, machine_id, 1000)
    o = hashlib.md5(dk)
    return o.hexdigest()


if __name__ == "__main__":
    print(fixture_id())
