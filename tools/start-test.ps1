param(
    [string]$Engine = 'C:\Program Files\OpenMW 0.51.0\openmw.exe',
    [string]$GameData = 'D:\Steam\steamapps\common\Morrowind\Data Files',
    [switch]$PrepareOnly
)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$enginePath = (Resolve-Path -LiteralPath $Engine).Path
$gamePath = (Resolve-Path -LiteralPath $GameData).Path
$resourcesPath = Join-Path (Split-Path -Parent $enginePath) 'resources'
if (-not (Test-Path -LiteralPath $resourcesPath)) { throw 'Missing engine resources directory' }
$version = (Get-Content -LiteralPath (Join-Path $resourcesPath 'version') -TotalCount 1).Trim()
if ($version -ne '0.51.0') { throw "Test API target is OpenMW 0.51.0; found $version" }
if (-not $PrepareOnly -and (Get-Process -Name openmw -ErrorAction SilentlyContinue)) {
    throw 'Close the running OpenMW game before starting this test.'
}
if (-not (Test-Path -LiteralPath (Join-Path $projectRoot 'FactionInterventionTest.omwscripts'))) {
    throw 'Missing test manifest'
}
foreach ($file in @('Morrowind.esm', 'Morrowind.bsa')) {
    if (-not (Test-Path -LiteralPath (Join-Path $gamePath $file))) { throw "Missing $file" }
}
$profilePath = Join-Path $projectRoot '.runtime\manual-profile'
$userDataPath = Join-Path $projectRoot '.runtime\manual-user-data'
$localDataPath = Join-Path $userDataPath 'data'
New-Item -ItemType Directory -Force $profilePath,$userDataPath,$localDataPath | Out-Null
$lines = @(
    'replace=config', 'replace=data', 'replace=content', 'replace=groundcover',
    'replace=fallback-archive',
    ('resources="' + $resourcesPath.Replace('\','/') + '"'),
    ('data="' + $resourcesPath.Replace('\','/') + '/vfs-mw"'),
    ('data="' + $gamePath.Replace('\','/') + '"'),
    ('data="' + $projectRoot.Replace('\','/') + '"'),
    ('data-local="' + $localDataPath.Replace('\','/') + '"'),
    'content=Morrowind.esm', 'fallback-archive=Morrowind.bsa'
)
$lines += 'content=FactionInterventionTest.omwscripts'
[IO.File]::WriteAllLines((Join-Path $profilePath 'openmw.cfg'), $lines)
$settingsPath = Join-Path $profilePath 'settings.cfg'
if (-not (Test-Path -LiteralPath $settingsPath)) {
    [IO.File]::WriteAllText($settingsPath, "[Video]`nresolution x = 1280`nresolution y = 720`nfullscreen = false`n[Sound]`nmusic volume = 0`n")
}
Write-Host "OpenMW $version prototype profile prepared at $profilePath"
Write-Host "Test saves and logs: $userDataPath"
Write-Host 'Fresh session starts in Seyda Neen with two shrine fixtures. Read SHRINE-TEST.md.'
if (-not $PrepareOnly) {
    Start-Process -FilePath $enginePath -WorkingDirectory (Split-Path -Parent $enginePath) -WindowStyle Normal -ArgumentList @(
        '--replace', 'config', '--config', ('"' + $profilePath + '"'),
        '--user-data', ('"' + $userDataPath + '"'), '--skip-menu', '--start', '"Seyda Neen"', '--no-grab'
    )
}
