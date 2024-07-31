import os
import datetime
import argparse
import glob

VERSION_TEMPLATE = """
VSVersionInfo(
  ffi=FixedFileInfo(
    # filevers and prodvers should be always a tuple with four items: (1, 2, 3, 4)
    # Set not needed items to zero 0.
    filevers=({major}, {minor}, {patch}, {build}),
    prodvers=({major}, {minor}, {patch}, {build}),
    # Contains a bitmask that specifies the valid bits 'flags'r
    mask=0x3f,
    # Contains a bitmask that specifies the Boolean attributes of the file.
    flags=0x0,
    # The operating system for which this file was designed.
    # 0x4 - NT and there is no need to change it.
    OS=0x4,
    # The general type of file.
    # 0x1 - the file is an application.
    fileType=0x1,
    # The function of the file.
    # 0x0 - the function is not defined for this fileType
    subtype=0x0,
    # Creation date and time stamp.
    date=(0, 0)
    ),
  kids=[
    StringFileInfo(
      [
      StringTable(
        u'040904E4',
        [StringStruct(u'CompanyName', u'Romet'),
        StringStruct(u'FileVersion', u'{major}.{minor}.{patch}'),
        StringStruct(u'LegalCopyright', u'(c) {year} Romet'),
        StringStruct(u'ProductName', u'{product} production fixture'),
        StringStruct(u'ProductVersion', u'{major}.{minor}.{patch}')])
      ]),
    VarFileInfo([VarStruct(u'Translation', [1033, 1252])])
  ]
)
"""
import jaguar

VERSION_FILE = "release/_version"

if __name__ == "__main__":
    from jaguar.__version__ import VERSION

    fw_ver = VERSION
    major, minor, patch = [int(i) for i in fw_ver.split(".")]

    with open(VERSION_FILE, "w") as f:
        f.write(VERSION_TEMPLATE.format(**{
            "major": major,
            "minor": minor,
            "patch": patch,
            "year": datetime.datetime.now().year,
            "product": "Jaguar",
            "build": 0
        }))
