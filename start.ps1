$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$python = Join-Path $root '.venv\Scripts\python.exe'
$envFile = Join-Path $root '.env.local'
if (-not (Test-Path -LiteralPath $python)) { throw 'Brak .venv. Uruchom instalację opisaną w README.md.' }
if (Test-Path -LiteralPath $envFile) {
    foreach ($line in [System.IO.File]::ReadAllLines($envFile)) {
        $item = $line.Trim()
        if (-not $item -or $item.StartsWith('#')) { continue }
        $parts = $item.Split('=', 2)
        if ($parts.Count -ne 2) { throw 'Nieprawidłowa linia w .env.local.' }
        [Environment]::SetEnvironmentVariable($parts[0].Trim(), $parts[1].Trim().Trim('"'), 'Process')
    }
}
& $python (Join-Path $root 'server.py')
