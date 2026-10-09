"""Fail before uploading if configuration or the retained release ZIP is invalid."""
import os
from pathlib import Path
import re
from prepare_nexus_upload import metadata


def verify(root, version, checksum, file_id, mod_id, api_key):
    for name, value in (('NEXUSMODS_FILE_ID', file_id), ('NEXUSMODS_MOD_ID', mod_id)):
        if not re.fullmatch(r'[1-9][0-9]*', value):
            raise ValueError(f'Set {name} for this mod in the nexus environment')
    if not api_key.strip():
        raise ValueError('Set the NEXUSMODS_API_KEY secret in the nexus environment')
    values = metadata(root, 'false', version)
    if not re.fullmatch(r'[0-9a-f]{64}', checksum) or values['sha256'] != checksum:
        raise ValueError('Downloaded ZIP does not match the verified GitHub release build')
    return values


if __name__ == '__main__':
    verify(Path(__file__).resolve().parents[1], os.environ['RELEASE_VERSION'],
           os.environ['ZIP_SHA256'], os.environ['NEXUS_FILE_ID'],
           os.environ['NEXUS_MOD_ID'], os.environ['NEXUS_API_KEY'])
    print('Nexus configuration and release ZIP verified; no credentials logged.')
