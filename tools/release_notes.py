"""Read the exact version entry shared by GitHub and Nexus releases."""
import re


def release_notes(root, version):
    if not re.fullmatch(r'\d+\.\d+\.\d+', version):
        raise ValueError('Invalid release-notes version')
    sections = []
    current = None
    fence = None
    for line in (root / 'CHANGELOG.md').read_text(encoding='utf-8').splitlines():
        stripped = line.strip()
        marker = re.match(r'^(`{3,}|~{3,})', stripped)
        if fence:
            if re.fullmatch(re.escape(fence[0]) + '{' + str(len(fence)) + ',}', stripped):
                fence = None
        elif marker:
            fence = marker.group(1)
        elif re.match(r'^##\s+', line):
            current = [] if line.strip() == f'## {version}' else None
            if current is not None:
                sections.append(current)
            continue
        if current is not None:
            current.append(line)
    if len(sections) != 1:
        raise ValueError(f'CHANGELOG.md must contain exactly one ## {version} entry')
    notes = '\n'.join(sections[0]).strip()
    if not notes or not re.sub(r'<!--.*?-->', '', notes, flags=re.DOTALL).strip():
        raise ValueError(f'CHANGELOG.md entry for {version} is empty')
    return notes
