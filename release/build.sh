#!/bin/bash
export PYTHONPATH="."

# create version file
py -3 installer/pyinstaller_version.py 
# create executable
# py -3 -m PyInstaller -y  --console --name=jaguar_production --version-file=release/_version scripts/jaguar_production.py --icon assets/images/logo.ico 

# Ahmed's (better) way of creating executable:
py -3 -m PyInstaller -y  --console --name=jaguar_production --version-file=release/_version scripts/jaguar_production.py --icon assets/images/icon.ico --paths=C:/Users/production/Desktop/AhmedJigTesting/desktop-app/desktop-app/.venv/Lib/site-packages --clean  --onefile

#utilities scripts
# py -3 -m PyInstaller -y  --console --name=md5sum --version-file=installer/_version scripts/md5sum.py --icon assets/images/logo.ico --onefile
#py -3 -m PyInstaller -y  --console --name=fixture_id --version-file=installer/_version scripts/fixture_id.py --icon assets/images/logo.ico --onefile
