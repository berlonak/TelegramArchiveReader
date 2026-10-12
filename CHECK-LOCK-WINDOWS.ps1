# copyright by berlonak
# telegram: @Kilax123
# This diagnostic is read-only: never closes handles and never touches archive data.
# It uses Microsoft Sysinternals Handle ONLY after explicit approval (if download needed).
param(
  [Parameter(Mandatory=$true)][string]$ExportPath,
  [string]$ReportPath = ''
)
$ErrorActionPreference = 'Stop'
$original = [IO.Path]::GetFullPath($ExportPath.Trim().Trim('"').Trim("'")).TrimEnd('\')
if (-not (Test-Path -LiteralPath $original -PathType Container)) {
  Write-Host "Directory no longer exists at $original. Check whether Move-Item moved all or part of it." -ForegroundColor Yellow
  exit 2
}
if (-not $ReportPath) {
  $ReportPath = Join-Path $env:TEMP ('tgarchive-lock-' + (Get-Date -Format 'yyyyMMdd-HHmmss') + '.txt')
}
$log = New-Object System.Collections.Generic.List[string]
function Add-Log([string]$message) {
  $log.Add($message)
  Write-Host $message
}
function Save-Log {
  try {
    $parent = Split-Path -Path $ReportPath -Parent
    if ($parent -and -not (Test-Path -LiteralPath $parent)) { New-Item -ItemType Directory -Force -Path $parent | Out-Null }
    [IO.File]::WriteAllLines($ReportPath, $log.ToArray(), [Text.Encoding]::UTF8)
    Write-Host "Log: $ReportPath"
  } catch { Write-Warning "Could not save report: $_" }
}
# Only elevated Handle scans can reliably enumerate other processes' open files.
$principal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
  Write-Host "Admin access is needed to inspect handles belonging to other processes." -ForegroundColor Yellow
  Write-Host 'Windows will ask for UAC permission. Diagnostic DOES NOT terminate processes.'
  # Use a Windows-encoded process command line with escaped double quotes.
  $quotedScript = '"' + $PSCommandPath.Replace('"', '\"') + '"'
  $quotedDir    = '"' + $original.Replace('"', '\"') + '"'
  $quotedLog    = '"' + $ReportPath.Replace('"', '\"') + '"'
  $argsToAdmin  = '-NoProfile -ExecutionPolicy Bypass -File ' + $quotedScript + ' -ExportPath ' + $quotedDir + ' -ReportPath ' + $quotedLog
  try {
    $proc = Start-Process -FilePath 'powershell.exe' -Verb RunAs -ArgumentList $argsToAdmin -PassThru -Wait -ErrorAction Stop
    if (Test-Path -LiteralPath $ReportPath) {
      Write-Host "`n=== Lock diagnostic results ===" -ForegroundColor Cyan
      # Read log from elevated process, which may have closed its own console.
      Get-Content -LiteralPath $ReportPath -Encoding UTF8 | ForEach-Object { Write-Host $_ }
      Write-Host "Log: $ReportPath"
    } else {
      Write-Host 'No report was produced (UAC denied, download canceled, or helper failed).' -ForegroundColor Yellow
    }
    exit $proc.ExitCode
  } catch {
    Write-Host "Could not elevate diagnostic: $_" -ForegroundColor Yellow
    Write-Host 'Run CHECK-LOCK.bat as administrator to try again.' -ForegroundColor Yellow
    exit 2
  }
}

Add-Log "Telegram Archive - open handles for: $original"
Add-Log ('Date: ' + (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'))
$localTools = Join-Path $PSScriptRoot 'tools'
$handlePath = Join-Path $localTools 'handle64.exe'
$architecture = $env:PROCESSOR_ARCHITECTURE
if ($architecture -eq 'ARM64') { $handlePath = Join-Path $localTools 'handle64a.exe' }
if (-not (Test-Path -LiteralPath $handlePath -PathType Leaf)) {
  Add-Log 'Microsoft Sysinternals Handle is not installed in this builder.'
  Write-Host 'Official utility: https://learn.microsoft.com/en-us/sysinternals/downloads/handle'
  $consent = Read-Host 'Download and use official Microsoft Handle.zip now? Enter YES'
  if ($consent -cne 'YES') {
    Add-Log 'Download declined. No process can be identified automatically without the diagnostic tool.'
    Save-Log
    exit 2
  }
  New-Item -ItemType Directory -Path $localTools -Force | Out-Null
  $download = Join-Path $env:TEMP ('handle-' + [Guid]::NewGuid().ToString('N') + '.zip')
  $unpack = Join-Path $env:TEMP ('handle-' + [Guid]::NewGuid().ToString('N'))
  try {
    Invoke-WebRequest -UseBasicParsing -Uri 'https://download.sysinternals.com/files/Handle.zip' -OutFile $download
    Expand-Archive -LiteralPath $download -DestinationPath $unpack -Force
    $requested = if ($architecture -eq 'ARM64') { 'handle64a.exe' } else { 'handle64.exe' }
    $found = Get-ChildItem -LiteralPath $unpack -Recurse -File | Where-Object { $_.Name -ieq $requested } | Select-Object -First 1
    if (-not $found) { throw "Official ZIP did not contain $requested" }
    $sig = Get-AuthenticodeSignature -LiteralPath $found.FullName
    if ($sig.Status -ne 'Valid' -or -not $sig.SignerCertificate -or $sig.SignerCertificate.Subject -notmatch 'Microsoft') {
      throw 'The downloaded utility has no valid Microsoft digital signature. Refusing to run it.'
    }
    Copy-Item -LiteralPath $found.FullName -Destination $handlePath -ErrorAction Stop
    Add-Log 'Downloaded official Handle; Microsoft Authenticode signature verified.'
  } catch {
    Add-Log "Could not download/validate Handle: $_"
    Add-Log 'Download manually from Microsoft, then run CHECK-LOCK.bat again.'
    Save-Log
    exit 2
  } finally {
    Remove-Item -LiteralPath $download -Force -ErrorAction SilentlyContinue
    Remove-Item -LiteralPath $unpack -Recurse -Force -ErrorAction SilentlyContinue
  }
}
$sig = Get-AuthenticodeSignature -LiteralPath $handlePath
if ($sig.Status -ne 'Valid' -or -not $sig.SignerCertificate -or $sig.SignerCertificate.Subject -notmatch 'Microsoft') {
  Add-Log 'Existing Handle executable failed Microsoft signature verification. Refusing to run.'
  Save-Log
  exit 2
}
try {
  # Search source path: Handle enumerates both directory and open child file handles.
  # -accepteula is for Sysinternals' own license dialog; user separately approved the download above.
  $output = @(& $handlePath -accepteula $original 2>&1 | ForEach-Object { "$_" })
  # Search for an actual path boundary so sibling folders sharing a prefix (Export vs Export-ready) are not matched.
  $regex = [regex]::Escape($original) + '(?=\\|\s|$)'
  $hits = @($output | Where-Object { $_ -match $regex -and $_ -match '\bpid\s*:' })
  if ($hits.Count -gt 0) {
    Add-Log ('OPEN HANDLES FOUND: ' + $hits.Count)
    foreach ($line in ($hits | Select-Object -First 60)) { Add-Log $line.Trim() }
    if ($hits.Count -gt 60) { Add-Log ('... ' + ($hits.Count - 60) + ' further entries omitted from console.') }
    Add-Log 'These processes have the directory or its files OPEN; this does not prove each one prevented the move.'
    Add-Log 'Close only the program(s) you recognize; do not force-close OS or antivirus processes.'
  } else {
    Add-Log 'Handle did not find an open handle under this exact source directory.'
    Add-Log 'Lock may be transient, path may be reported differently, or error may be permissions/destination rather than a lock.'
    # Preserve useful raw diagnostic output, but do not misattribute it to a specific process.
    foreach ($line in ($output | Select-Object -First 12)) { Add-Log $line }
  }
} catch {
  Add-Log "Handle diagnostic failed: $_"
  Save-Log
  exit 2
}
Save-Log
