<#
  ArchiveShippedLabels.ps1 - nightly archive of the shipping-label PDFs printed by ShipLabelApp.

  Scheduled on PRN01 (Task Scheduler, "ACME\ArchiveShippedLabels", daily 02:30, account svc_labels).
  Moves the label PDFs older than $RetentionDays from the print output folder to the archive share,
  one sub-folder per month, and writes one log file per run.
#>
param(
    [string]$Source = "D:\LabelPrintService\Out",
    [string]$Archive = "\\FS01\Archive\ShipLabels",
    [int]$RetentionDays = 90,
    [string]$LogDir = "C:\Logs\LabelArchive"
)

$ErrorActionPreference = "Stop"
$log = Join-Path $LogDir ("archive-{0:yyyyMMdd}.log" -f (Get-Date))
function Write-Log($msg) { "{0:HH:mm:ss} {1}" -f (Get-Date), $msg | Add-Content -Path $log }

if (-not (Test-Path $Archive)) {
    # The share is not reachable (FS01 down, permissions of svc_labels changed): nothing is moved
    Write-Log "ERROR archive share not reachable: $Archive"
    exit 2
}

$limit = (Get-Date).AddDays(-$RetentionDays)
$moved = 0
Get-ChildItem -Path $Source -Filter *.pdf | Where-Object { $_.LastWriteTime -lt $limit } | ForEach-Object {
    $target = Join-Path $Archive ("{0:yyyy-MM}" -f $_.LastWriteTime)
    if (-not (Test-Path $target)) { New-Item -ItemType Directory -Path $target | Out-Null }
    try {
        Move-Item -Path $_.FullName -Destination $target
        $moved++
    } catch {
        # A file still locked by LabelPrintService stays where it is and is retried the next night
        Write-Log "WARN locked, skipped: $($_.Exception.Message)"
    }
}
Write-Log "OK moved $moved file(s) older than $RetentionDays days"
exit 0
