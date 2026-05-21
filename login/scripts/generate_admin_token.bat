@echo off
setlocal

set "BYTES=%~1"
if "%BYTES%"=="" set "BYTES=32"

set "ENV_PATH=%~2"
if "%ENV_PATH%"=="" set "ENV_PATH=%~dp0..\.env"

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$bytes=[int]'%BYTES%';" ^
  "if($bytes -lt 16){throw 'Bytes must be at least 16 for a strong token.'};" ^
  "$buffer=New-Object byte[] $bytes;" ^
  "$rng=[System.Security.Cryptography.RandomNumberGenerator]::Create();" ^
  "$rng.GetBytes($buffer);" ^
  "$token=[Convert]::ToBase64String($buffer);" ^
  "$token=$token.Replace('+','-').Replace('/','_').TrimEnd('=');" ^
  "$envFile='%ENV_PATH%';" ^
  "$lines=@();" ^
  "if(Test-Path -LiteralPath $envFile){$lines=Get-Content -LiteralPath $envFile}else{$parent=Split-Path -Parent $envFile;if($parent -and -not (Test-Path -LiteralPath $parent)){New-Item -ItemType Directory -Force -Path $parent|Out-Null}};" ^
  "$found=$false;" ^
  "$updated=foreach($line in $lines){if($line -match '^\s*ADMIN_API_TOKEN\s*='){ $found=$true; 'ADMIN_API_TOKEN=' + $token } else { $line }};" ^
  "if(-not $found){$updated += 'ADMIN_API_TOKEN=' + $token};" ^
  "Set-Content -LiteralPath $envFile -Value $updated -Encoding UTF8;" ^
  "Write-Output $token"

endlocal
