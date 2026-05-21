param(
    [int]$Bytes = 32,
    [switch]$AsEnvLine,
    [switch]$NoWrite,
    [string]$EnvPath = (Join-Path $PSScriptRoot "..\\.env")
)

if ($Bytes -lt 16) {
    throw "Bytes must be at least 16 for a strong token."
}

$buffer = New-Object byte[] $Bytes
$rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
$rng.GetBytes($buffer)
$token = [Convert]::ToBase64String($buffer)
$token = $token.Replace('+', '-').Replace('/', '_').TrimEnd('=')

if (-not $NoWrite) {
    $envFile = $EnvPath
    $lines = @()
    if (Test-Path -LiteralPath $envFile) {
        $lines = Get-Content -LiteralPath $envFile
    } else {
        $parent = Split-Path -Parent $envFile
        if ($parent -and -not (Test-Path -LiteralPath $parent)) {
            New-Item -ItemType Directory -Force -Path $parent | Out-Null
        }
    }

    $found = $false
    $updated = foreach ($line in $lines) {
        if ($line -match '^\s*ADMIN_API_TOKEN\s*=') {
            $found = $true
            "ADMIN_API_TOKEN=$token"
        } else {
            $line
        }
    }
    if (-not $found) {
        $updated += "ADMIN_API_TOKEN=$token"
    }
    Set-Content -LiteralPath $envFile -Value $updated -Encoding UTF8
}

if ($AsEnvLine) {
    Write-Output ("ADMIN_API_TOKEN=" + $token)
} else {
    Write-Output $token
}
