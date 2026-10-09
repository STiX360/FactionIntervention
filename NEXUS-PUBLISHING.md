# GitHub And Nexus Releases

Adapted from the working ArcaneMiscasts release pipeline. Only the production
allowlist is packaged: the manifest, four runtime scripts, localization, README,
and release notes. No tests, saves, game files, credentials, or source checkout.

## One-Time Setup

1. Set this repository's GitHub remote and push the checkout to `main`.
2. Create the Nexus mod page and manually upload the production ZIP once.
3. In GitHub Settings > Environments, create an environment named `nexus`.
4. Add environment secret `NEXUSMODS_API_KEY` for the owning Nexus account.
5. Add environment variables `NEXUSMODS_FILE_ID` (the initial uploaded file ID)
   and `NEXUSMODS_MOD_ID` (the **API Unique Mod ID** from Nexus's Advanced dialog,
   not the public page URL number). Never reuse another mod's IDs or credentials.
6. Add repository variable `NEXUSMODS_ENABLED` with value `true` when ready.
7. If restricting environment deployments, allow tags `v*`. An optional required
   reviewer pauses Nexus uploads for approval; omit that rule for fully automatic uploads.

The [official Nexus upload action](https://github.com/Nexus-Mods/upload-action)
requires an existing file to add versions to. It does not create the initial page.
GitHub Releases work even when Nexus is not configured or enabled.

## Publish A Version

Update `VERSION`, add exactly one matching `## X.Y.Z` entry in `CHANGELOG.md`, and
update README/release notes for the new version. Commit on `main`, then push the
commit before its matching tag. For the currently prepared version:

```powershell
git push origin main
git tag v0.4.0
git push origin v0.4.0
```

Ordinary commits and pull requests validate and retain a ZIP but never publish.
A `vX.Y.Z` tag push runs all mocked Lua regression tests and release/package tests,
checks that the tagged commit is reachable from `origin/main`, verifies the version
and changelog, and creates a normal GitHub Release with the install-ready ZIP.
Versions below 1.0 are not automatically marked prereleases.

When enabled, Nexus runs **after GitHub publishing succeeds**, using the same
retained ZIP and SHA-256, not a rebuild or an unrelated older latest release.
Both destinations receive that version's changelog. Nexus updates the mod-page
version without archiving old files or changing the primary mod-manager download.
Tags must be immutable; never move a published tag to changed source.

## Dry Runs And Recovery

Actions > Publish Releases > Run workflow from `main` builds and verifies only.
Manual dispatch never uploads to either destination. Download the Actions artifact
and extract its outer wrapper ZIP to obtain the contained install-ready mod ZIP.

If Nexus fails, the GitHub Release remains published. Fix its configuration and use
Re-run failed jobs on that tag's workflow run while the artifact remains available
(14 days). A GitHub retry checks an existing asset and refuses to overwrite changed
bytes. Nexus retries may create duplicate versions: inspect the Nexus Files page
after any ambiguous upload failure before rerunning. Do not rerun a successful
Nexus job just to retry another destination.

CI uses Lupa's Lua 5.1 for mocked regression tests, without licensed Morrowind data.
Local Windows tests use the installed OpenMW Lua DLL. These are not in-game tests;
`verify_readiness.py` and manual gameplay checks remain local acceptance checks.
To exercise the portable backend on Windows, install `requirements-dev.txt`, set
`$env:FI_TEST_LUA_BACKEND = 'portable'`, and run `python tests/test_prototype.py`.
Remove that variable afterward to return to the installed-engine runtime.

The workflows are prepared and locally tested. A live GitHub/Nexus upload has not
yet been verified for this mod; no remote, Nexus IDs, or credentials were inferred.
