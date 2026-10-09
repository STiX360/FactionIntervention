"""Verify the public archive is complete and excludes disposable test helpers."""
from pathlib import Path
import subprocess
import sys
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]


class PackageTests(unittest.TestCase):
    def test_production_allowlist_and_manifest(self):
        subprocess.run([sys.executable, str(ROOT / 'tools' / 'package.py')], check=True)
        expected = {
            'README.md', 'RELEASE-NOTES.md', 'FactionIntervention.omwscripts',
            'l10n/FactionIntervention/en.yaml',
            *(f'scripts/faction_intervention/{name}.lua'
              for name in ('player', 'policy', 'shrines', 'shrine_policy')),
        }
        version = (ROOT / 'VERSION').read_text().strip()
        with zipfile.ZipFile(ROOT / 'dist' / f'Faction-Intervention-OpenMW-{version}.zip') as archive:
            self.assertIsNone(archive.testzip())
            self.assertEqual(set(archive.namelist()), expected)
            manifest = archive.read('FactionIntervention.omwscripts').decode('utf-8')
            entries = [line.split(':', 1) for line in manifest.splitlines() if line.strip()]
            self.assertEqual({kind.strip() for kind, _ in entries}, {'PLAYER', 'GLOBAL'})
            self.assertEqual(len(entries), 2)
            for _, script in entries:
                self.assertIn(script.strip(), expected)


if __name__ == '__main__':
    unittest.main(verbosity=2)
