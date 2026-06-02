import re
import struct
import sys

# Matches any symbol in the std:: namespace:
#   _ZNSt  = non-const member
#   _ZNKSt = const member
#   _ZNVSt = volatile member
#   _ZSt   = free function in std::
_STDLIB_RE = re.compile(rb"^_ZN[KVrRoO]*St|^_ZSt")


def patch(path):
    with open(path, "r+b") as f:
        data = bytearray(f.read())

    e_shoff = struct.unpack_from("<Q", data, 0x28)[0]
    e_shentsize = struct.unpack_from("<H", data, 0x3A)[0]
    e_shnum = struct.unpack_from("<H", data, 0x3C)[0]
    e_shstrndx = struct.unpack_from("<H", data, 0x3E)[0]
    shstr_off = struct.unpack_from(
        "<Q", data, e_shoff + e_shstrndx * e_shentsize + 0x18
    )[0]

    dynsym_off = dynsym_sz = dynstr_off = 0
    for i in range(e_shnum):
        sh = e_shoff + i * e_shentsize
        name = (
            data[shstr_off + struct.unpack_from("<I", data, sh)[0] :]
            .split(b"\x00")[0]
            .decode()
        )
        off = struct.unpack_from("<Q", data, sh + 0x18)[0]
        sz = struct.unpack_from("<Q", data, sh + 0x20)[0]
        if name == ".dynsym":
            dynsym_off, dynsym_sz = off, sz
        elif name == ".dynstr":
            dynstr_off = off

    count = 0
    for i in range(dynsym_sz // 24):
        sym = dynsym_off + i * 24
        st_name = struct.unpack_from("<I", data, sym)[0]
        binding = data[sym + 4] >> 4  # STB_GLOBAL == 1
        name = data[dynstr_off + st_name :].split(b"\x00")[0]
        st_shndx = struct.unpack_from("<H", data, sym + 6)[0]
        is_defined = st_shndx != 0  # SHN_UNDEF == 0; skip undefined references
        # 1=STB_GLOBAL, 2=STB_WEAK, 10=STB_GNU_UNIQUE (template instantiations)
        if binding in (1, 2, 10) and is_defined and _STDLIB_RE.match(name):
            data[sym + 5] = 2  # STV_HIDDEN
            count += 1

    print(f"Patched {count} stdlib symbols to STV_HIDDEN in {path}")
    with open(path, "wb") as f:
        f.write(bytes(data))


if __name__ == "__main__":
    patch(sys.argv[1])
