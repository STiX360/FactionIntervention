"""Publish the verified tag build, without replacing existing release assets."""
from pathlib import Path
import hashlib
import json
import os
import re
import subprocess
import tempfile
from release_notes import release_notes


def publish(root, event, ref, repository, version, checksum, run=subprocess.run):
    if event != 'push' or not re.fullmatch(r'\d+\.\d+\.\d+', version):
        raise ValueError('GitHub releases require a version-tag push')
    if ref != f'refs/tags/v{version}':
        raise ValueError('Release tag must match the verified version')
    if (root / 'VERSION').read_text(encoding='utf-8').strip() != version:
        raise ValueError('Checkout VERSION must match the verified build')
    if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', repository):
        raise ValueError('Invalid GitHub repository')
    filename = f'Faction-Intervention-OpenMW-{version}.zip'
    archive = root / 'dist' / filename
    if not re.fullmatch(r'[0-9a-f]{64}', checksum):
        raise ValueError('Invalid build checksum')
    if hashlib.sha256(archive.read_bytes()).hexdigest() != checksum:
        raise ValueError('Downloaded ZIP does not match the verified build')
    changelog = release_notes(root, version)

    tag = f'v{version}'
    prerelease = False

    def gh(*args, check=True):
        try:
            return run(['gh', *args, '--repo', repository], check=check,
                       capture_output=True, text=True)
        except subprocess.CalledProcessError as error:
            if error.stderr:
                print(error.stderr)
            raise

    result = gh('release', 'view', tag, '--json',
                'assets,isDraft,isPrerelease,tagName,url', check=False)
    if result.returncode:
        if 'release not found' not in result.stderr.lower() and 'HTTP 404' not in result.stderr:
            raise RuntimeError('Unable to inspect GitHub release: ' + result.stderr)
        notes = (f'{changelog}\n\n---\n\n'
                 'Download the Faction-Intervention-OpenMW ZIP under Assets, not the source archives.\n\n'
                 'Requires OpenMW 0.51.0. Enable FactionIntervention.omwscripts. '
                 'See README.md for installation and compatibility boundaries.')
        args = ['release', 'create', tag, str(archive), '--verify-tag',
                '--title', f'Faction Intervention {version}', '--notes', notes]
        if prerelease:
            args.extend(['--prerelease', '--latest=false'])
        gh(*args)
        return

    release = json.loads(result.stdout)
    if release['tagName'] != tag or release['isPrerelease'] != prerelease:
        raise ValueError('Existing release tag or prerelease status differs; review manually')
    if any(asset['name'] == filename for asset in release['assets']):
        # Retry only when the already-published asset is exactly the same build.
        with tempfile.TemporaryDirectory() as directory:
            gh('release', 'download', tag, '--pattern', filename, '--dir', directory)
            existing = Path(directory) / filename
            if hashlib.sha256(existing.read_bytes()).hexdigest() != checksum:
                raise ValueError('Existing release ZIP differs; refusing to replace it')
    else:
        gh('release', 'upload', tag, str(archive))
    if release['isDraft']:
        gh('release', 'edit', tag, '--draft=false')
    print(f"Verified release: {release['url']}")


if __name__ == '__main__':
    publish(Path(__file__).resolve().parents[1],
            os.environ['GITHUB_EVENT_NAME'], os.environ['GITHUB_REF'],
            os.environ['GITHUB_REPOSITORY'], os.environ['RELEASE_VERSION'],
            os.environ['ZIP_SHA256'])
