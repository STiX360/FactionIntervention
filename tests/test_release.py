"""Offline release guards: no GitHub or Nexus uploads during tests."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from package import build, PRODUCTION_FILES
from prepare_nexus_upload import metadata, release_inputs, write_outputs
from publish_github_release import publish
from release_notes import release_notes
from verify_nexus_upload import verify


class ReleaseTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'VERSION').write_text('0.3.0\n')
        (self.root / 'CHANGELOG.md').write_text('# Changelog\n\n## 0.3.0\n\n- New feature.\n\n## 0.2.0\n\n- Old feature.\n')
        for name in PRODUCTION_FILES:
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('fixture\n')
        self.archive = build(self.root)
        self.checksum = hashlib.sha256(self.archive.read_bytes()).hexdigest()
        self.commands = []

    def publish(self, run, **overrides):
        args = dict(root=self.root, event='push', ref='refs/tags/v0.3.0',
                    repository='owner/FactionIntervention', version='0.3.0',
                    checksum=self.checksum, run=run)
        args.update(overrides)
        publish(**args)

    def missing_release(self, args, **kwargs):
        self.commands.append(args)
        return subprocess.CompletedProcess(args, 1 if args[1:3] == ['release', 'view'] else 0,
                                           stdout='', stderr='release not found')

    def existing_release(self, args, **kwargs):
        self.commands.append(args)
        if args[1:3] == ['release', 'view']:
            return subprocess.CompletedProcess(args, 0, json.dumps({
                'tagName': 'v0.3.0', 'isPrerelease': False, 'isDraft': False,
                'assets': [{'name': self.archive.name}], 'url': 'https://example.test/release'}), '')
        if args[1:3] == ['release', 'download']:
            (Path(args[args.index('--dir') + 1]) / self.archive.name).write_bytes(self.archive.read_bytes())
        return subprocess.CompletedProcess(args, 0, '', '')

    def test_reproducible_production_build(self):
        before = self.archive.read_bytes()
        self.assertEqual(build(self.root).read_bytes(), before)

    def test_invalid_package_version(self):
        (self.root / 'VERSION').write_text('../bad')
        with self.assertRaises(ValueError):
            build(self.root)

    def test_development_package_keeps_build_dependencies(self):
        for name in ('Test-Faction-Intervention.cmd', 'FactionInterventionTest.omwscripts',
                     'TESTING.md', 'SHRINE-TEST.md', 'requirements-dev.txt', 'NEXUS-PUBLISHING.md'):
            (self.root / name).write_text('fixture')
        import zipfile
        with zipfile.ZipFile(build(self.root, test=True)) as archive:
            self.assertIn('VERSION', archive.namelist())
            self.assertIn('CHANGELOG.md', archive.namelist())

    def test_missing_asset_uploaded_and_draft_published(self):
        def draft(args, **kwargs):
            self.commands.append(args)
            if args[1:3] == ['release', 'view']:
                return subprocess.CompletedProcess(args, 0, json.dumps({
                    'tagName': 'v0.3.0', 'isPrerelease': False, 'isDraft': True,
                    'assets': [], 'url': 'https://example.test/release'}), '')
            return subprocess.CompletedProcess(args, 0, '', '')
        self.publish(draft)
        self.assertEqual(self.commands[1][1:3], ['release', 'upload'])
        self.assertIn('--draft=false', self.commands[2])

    def test_upload_errors_propagate(self):
        def failure(args, **kwargs):
            if args[1:3] == ['release', 'create']:
                raise subprocess.CalledProcessError(1, args, stderr='Upload failed')
            return self.missing_release(args, **kwargs)
        with self.assertRaises(subprocess.CalledProcessError):
            self.publish(failure)

    def test_tag_inputs(self):
        self.assertEqual(release_inputs('push', 'refs/tags/v0.3.0', '', ''), ('false', '0.3.0'))

    def test_invalid_tags_and_branch_pushes(self):
        for ref in ('refs/heads/main', 'refs/tags/vbanana', 'refs/tags/v0.3.0-beta'):
            with self.subTest(ref=ref), self.assertRaises(ValueError):
                release_inputs('push', ref, '', '')

    def test_manual_requires_main(self):
        with self.assertRaises(ValueError):
            release_inputs('workflow_dispatch', 'refs/heads/feature', 'true', '')
        self.assertEqual(release_inputs('workflow_dispatch', 'refs/heads/main', 'true', ''), ('true', ''))

    def test_metadata_and_exact_notes(self):
        values = metadata(self.root, 'true', '')
        self.assertEqual(values['filename'], self.archive.name)
        self.assertEqual(values['sha256'], self.checksum)
        self.assertEqual(values['changelog'], '- New feature.')

    def test_real_upload_requires_matching_version(self):
        for mode, confirmation in (('false', ''), ('false', '0.2.0'), ('bogus', '')):
            with self.subTest(mode=mode, confirmation=confirmation), self.assertRaises(ValueError):
                metadata(self.root, mode, confirmation)

    def test_tag_mismatch_error_names_both_versions(self):
        with self.assertRaisesRegex(ValueError, "'0.4.0'.*VERSION '0.3.0'"):
            metadata(self.root, 'false', '0.4.0')

    def test_current_checkout_version_has_matching_release_notes(self):
        version = (ROOT / 'VERSION').read_text().strip()
        self.assertTrue(release_notes(ROOT, version))
        self.assertIn(f'Version {version}.', (ROOT / 'README.md').read_text())
        self.assertTrue((ROOT / 'RELEASE-NOTES.md').read_text().startswith(f'# Faction Intervention {version}\n'))

    def test_missing_or_duplicate_or_empty_notes(self):
        for content in ('## 0.2.0\nold', '## 0.3.0\na\n## 0.3.0\nb', '## 0.3.0\n<!-- empty -->'):
            (self.root / 'CHANGELOG.md').write_text(content)
            with self.subTest(content=content), self.assertRaises(ValueError):
                release_notes(self.root, '0.3.0')

    def test_multiline_outputs(self):
        output = self.root / 'output'
        write_outputs(output, {'changelog': '- Note\nversion=unexpected'})
        lines = output.read_text().splitlines()
        self.assertEqual(lines[0].split('<<')[1], lines[-1])
        self.assertEqual(lines[1:3], ['- Note', 'version=unexpected'])

    def test_normal_github_release_created(self):
        self.publish(self.missing_release)
        command = self.commands[-1]
        self.assertEqual(command[1:3], ['release', 'create'])
        self.assertIn('--verify-tag', command)
        self.assertIn(str(self.archive), command)
        self.assertNotIn('--prerelease', command)
        self.assertNotIn('Old feature', command[command.index('--notes') + 1])

    def test_publish_guards_before_network(self):
        for overrides in ({'event': 'workflow_dispatch'}, {'ref': 'refs/tags/v0.2.0'},
                          {'repository': 'bad'}, {'checksum': '0' * 64}):
            with self.subTest(overrides=overrides), self.assertRaises(ValueError):
                self.publish(self.missing_release, **overrides)
        self.assertEqual(self.commands, [])

    def test_existing_matching_asset_not_uploaded_again(self):
        self.publish(self.existing_release)
        self.assertFalse(any(command[2] in ('upload', 'create') for command in self.commands))

    def test_existing_changed_asset_rejected(self):
        def changed(args, **kwargs):
            result = self.existing_release(args, **kwargs)
            if args[1:3] == ['release', 'download']:
                (Path(args[args.index('--dir') + 1]) / self.archive.name).write_bytes(b'changed')
            return result
        with self.assertRaises(ValueError):
            self.publish(changed)

    def test_network_failure_not_treated_as_missing_release(self):
        def failure(args, **kwargs):
            return subprocess.CompletedProcess(args, 1, '', 'HTTP 403 forbidden')
        with self.assertRaises(RuntimeError):
            self.publish(failure)

    def test_nexus_configuration_and_checksum(self):
        values = verify(self.root, '0.3.0', self.checksum, '123', '456', 'test-only-key')
        self.assertEqual(values['sha256'], self.checksum)
        for file_id, mod_id, key, checksum in (
            ('', '456', 'key', self.checksum), ('123', 'bad', 'key', self.checksum),
            ('123', '456', '', self.checksum), ('123', '456', 'key', '0' * 64)):
            with self.subTest(file_id=file_id, mod_id=mod_id), self.assertRaises(ValueError):
                verify(self.root, '0.3.0', checksum, file_id, mod_id, key)

    def test_workflow_contract(self):
        import yaml
        workflow = yaml.safe_load((ROOT / '.github/workflows/release.yml').read_text())
        # PyYAML's YAML 1.1 treats the GitHub 'on' key as boolean True.
        triggers = workflow.get('on', workflow.get(True))
        self.assertEqual(triggers['push']['tags'], ['v*'])
        self.assertIn('workflow_dispatch', triggers)
        self.assertEqual(workflow['permissions'], {'contents': 'read'})
        jobs = workflow['jobs']
        self.assertEqual(jobs['github-release']['permissions'], {'contents': 'write'})
        self.assertEqual(jobs['nexus']['needs'], ['build', 'github-release'])
        self.assertEqual(jobs['nexus']['environment'], 'nexus')
        self.assertIn("vars.NEXUSMODS_ENABLED == 'true'", jobs['nexus']['if'])
        self.assertIn("github.event_name == 'push'", jobs['nexus']['if'])
        steps = jobs['build']['steps']
        self.assertTrue(any(step.get('run') == 'git merge-base --is-ancestor HEAD origin/main' for step in steps))
        upload = jobs['nexus']['steps'][-1]
        self.assertIn('@c96019556046053aa26044b44396cd38929daf23', upload['uses'])
        self.assertEqual(upload['with']['archive_existing_version'], 'false')
        self.assertEqual(upload['with']['filename'], 'dist/${{ needs.build.outputs.filename }}')

    def test_settings_labels_use_correct_vanilla_rank_titles(self):
        import yaml
        labels = yaml.safe_load((ROOT / 'l10n/FactionIntervention/en.yaml').read_text())
        self.assertEqual(labels['almsiviAllowances'], 'Almsivi Intervention')
        self.assertIn('99 = Unlimited uses', labels['divineFaction'])
        self.assertIn('99 = Unlimited uses', labels['almsiviFaction'])
        titles = {
            'divine': ('Layman', 'Novice', 'Initiate', 'Acolyte', 'Adept',
                       'Disciple', 'Oracle', 'Invoker', 'Theurgist', 'Primate'),
            'almsivi': ('Layman', 'Novice', 'Initiate', 'Acolyte', 'Adept',
                        'Curate', 'Disciple', 'Diviner', 'Master', 'Patriarch'),
        }
        for kind, ranks in titles.items():
            for rank, title in enumerate(ranks, 1):
                self.assertEqual(labels[f'{kind}Rank{rank}'], f'Maximum uses: {title}')


if __name__ == '__main__':
    unittest.main(verbosity=2)
