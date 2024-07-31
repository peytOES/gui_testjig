#!/bin/bash
export PYTHONPATH="."

# create version file
py -3 installer/pyinstaller_version.py 
# create executable
py -3 -m PyInstaller -y  --console --name=jaguar_production --version-file=installer/_version scripts/jaguar_production.py --icon assets/images/logo.ico 


#utilities scripts
# py -3 -m PyInstaller -y  --console --name=md5sum --version-file=installer/_version scripts/md5sum.py --icon assets/images/logo.ico --onefile
#py -3 -m PyInstaller -y  --console --name=fixture_id --version-file=installer/_version scripts/fixture_id.py --icon assets/images/logo.ico --onefile
