"""Download a community Windows build, verify release digest, extract locally."""
from pathlib import Path
import hashlib
import json
import urllib.request
import zipfile

runtime=Path('C:/Users/TIEN PC/AppData/Local/Temp/opencode/reality-compute-queue-20261116')
url='https://github.com/redis-windows/redis-windows/releases/download/8.10.3/Redis-8.10.3-Windows-x64-cygwin.zip'
expected='8000848c48668c8cd32f21386ce951d0e02c1aefae39443ab9d3de11ff8ebf9e'
dest=runtime/'redis.zip'
urllib.request.urlretrieve(url,dest)
actual=hashlib.sha256(dest.read_bytes()).hexdigest()
assert actual==expected
with zipfile.ZipFile(dest) as archive:
    assert all(not Path(name).is_absolute() and '..' not in Path(name).parts for name in archive.namelist())
    archive.extractall(runtime/'broker')
(Path(__file__).parent/'runtime-download.json').write_text(json.dumps({
    'official_memurai':'3 publicly linked MSI URLs returned HTTP403; no installer ran',
    'url':url,'sha256':actual,'bytes':dest.stat().st_size,
    'provenance':'Community Windows Cygwin build of Redis, not an official Redis binary',
    'scope':'Temporary local synthetic verification only; no service/global install'},indent=2))
print('Verified release SHA256; extracted portable broker')
