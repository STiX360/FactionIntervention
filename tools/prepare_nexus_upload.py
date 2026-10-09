"""Validate an upload confirmation and describe the exact built ZIP; no network access."""
from pathlib import Path
import hashlib
import os
import re
import uuid
from release_notes import release_notes


def release_inputs(event, ref, dry_run, confirmation):
    if event == 'push':
        tag = re.fullmatch(r'refs/tags/v(\d+\.\d+\.\d+)', ref)
        if not tag:
            raise ValueError('Automatic uploads require a v-prefixed version tag')
        return 'false', tag.group(1)
    if event != 'workflow_dispatch' or ref != 'refs/heads/main':
        raise ValueError('Manual uploads and dry runs must run from main')
    return dry_run, confirmation


def metadata(root, dry_run, confirmation):
    if dry_run not in ('true', 'false'):
        raise ValueError('NEXUS_DRY_RUN must be true or false')
    version = (root / 'VERSION').read_text(encoding='utf-8').strip()
    if not re.fullmatch(r'\d+\.\d+\.\d+', version):
        raise ValueError('Invalid VERSION')
    if dry_run == 'false' and confirmation != version:
        raise ValueError('For a real upload, confirm_version must exactly match VERSION')
    filename = f'Faction-Intervention-OpenMW-{version}.zip'
    archive = root / 'dist' / filename
    return {'version': version, 'filename': filename,
            'sha256': hashlib.sha256(archive.read_bytes()).hexdigest(),
            'changelog': release_notes(root, version)}


def write_outputs(path, values):
    with path.open('a', encoding='utf-8', newline='\n') as stream:
        for key, value in values.items():
            delimiter = f'output_{uuid.uuid4().hex}'
            while delimiter in value.splitlines():
                delimiter = f'output_{uuid.uuid4().hex}'
            stream.write(f'{key}<<{delimiter}\n{value}\n{delimiter}\n')


if __name__ == '__main__':
    root = Path(__file__).resolve().parents[1]
    dry_run, confirmation = release_inputs(
        os.environ.get('GITHUB_EVENT_NAME', 'workflow_dispatch'),
        os.environ.get('GITHUB_REF', 'refs/heads/main'),
        os.environ.get('NEXUS_DRY_RUN', 'true'),
        os.environ.get('NEXUS_CONFIRM_VERSION', ''))
    values = metadata(root, dry_run, confirmation)
    output = os.environ.get('GITHUB_OUTPUT')
    if output:
        write_outputs(Path(output), values)
    print(f"Verified package: {values['filename']}")
    print(f"SHA256: {values['sha256']}")
    print('This command never uploads; the separate workflow publish job handles Nexus.')
