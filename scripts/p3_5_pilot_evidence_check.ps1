param(
    [string]$BaseUrl = "http://127.0.0.1:8000",
    [string]$OutputDir = ".tmp\p3-5-integration",
    [string]$BackupId = "",
    [string]$AdminToken = "",
    [int]$TimeoutSec = 10
)

$ErrorActionPreference = "Stop"

function New-CheckResult {
    param(
        [string]$Name,
        [string]$Method,
        [string]$Path,
        [int[]]$ExpectedStatus,
        [bool]$Required = $true,
        [object]$Body = $null
    )

    $headers = @{}
    if ($AdminToken) {
        $headers["Authorization"] = "Bearer $AdminToken"
    }

    $uri = "$($BaseUrl.TrimEnd('/'))$Path"
    $jsonBody = $null
    if ($null -ne $Body) {
        $jsonBody = $Body | ConvertTo-Json -Depth 8
    }

    try {
        $response = Invoke-WebRequest `
            -Uri $uri `
            -Method $Method `
            -Headers $headers `
            -Body $jsonBody `
            -ContentType "application/json" `
            -TimeoutSec $TimeoutSec `
            -UseBasicParsing

        $statusCode = [int]$response.StatusCode
        $content = [string]$response.Content
        $ok = $ExpectedStatus -contains $statusCode
        return [ordered]@{
            name = $Name
            method = $Method
            path = $Path
            required = $Required
            status_code = $statusCode
            ok = $ok
            expected_status = $ExpectedStatus
            response_sample = $content.Substring(0, [Math]::Min(1200, $content.Length))
            error = ""
        }
    } catch {
        $statusCode = 0
        $content = ""
        $errorMessage = $_.Exception.Message

        $webResponse = $_.Exception.Response
        if ($webResponse) {
            $statusCode = [int]$webResponse.StatusCode
            if ($webResponse -is [System.Net.Http.HttpResponseMessage]) {
                $content = $webResponse.Content.ReadAsStringAsync().GetAwaiter().GetResult()
            } elseif ($webResponse -is [System.Net.HttpWebResponse]) {
                $stream = $webResponse.GetResponseStream()
                if ($stream) {
                    $reader = New-Object System.IO.StreamReader($stream)
                    $content = $reader.ReadToEnd()
                }
            }
        }

        $ok = $ExpectedStatus -contains $statusCode
        return [ordered]@{
            name = $Name
            method = $Method
            path = $Path
            required = $Required
            status_code = $statusCode
            ok = $ok
            expected_status = $ExpectedStatus
            response_sample = $content.Substring(0, [Math]::Min(1200, $content.Length))
            error = $errorMessage
        }
    }
}

function Write-MarkdownSummary {
    param(
        [string]$Path,
        [object]$Evidence
    )

    $lines = @(
        "# P3-5 Pilot Evidence Check",
        "",
        "- Generated at: $($Evidence.generated_at)",
        "- Base URL: $($Evidence.base_url)",
        "- Backup drill requested: $($Evidence.backup_drill_requested)",
        "- Overall status: $($Evidence.status)",
        "",
        "| Check | Method | Path | Status | Result |",
        "| --- | --- | --- | --- | --- |"
    )

    foreach ($check in $Evidence.checks) {
        $result = if ($check.ok) { "PASS" } elseif ($check.required) { "FAIL" } else { "WARN" }
        $lines += "| $($check.name) | $($check.method) | ``$($check.path)`` | $($check.status_code) | $result |"
    }

    $lines | Set-Content -Path $Path -Encoding UTF8
}

$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null

$checks = @()
$checks += New-CheckResult -Name "liveness" -Method "GET" -Path "/health" -ExpectedStatus @(200)
$checks += New-CheckResult -Name "readiness" -Method "GET" -Path "/ready" -ExpectedStatus @(200)
$checks += New-CheckResult -Name "enterprise_readiness" -Method "GET" -Path "/api/enterprise/readiness" -ExpectedStatus @(200)
$checks += New-CheckResult -Name "metrics" -Method "GET" -Path "/api/metrics" -ExpectedStatus @(200)
$checks += New-CheckResult -Name "backup_policy" -Method "GET" -Path "/api/backups/production/policy" -ExpectedStatus @(200)

if ($BackupId) {
    $checks += New-CheckResult `
        -Name "restore_drill" `
        -Method "POST" `
        -Path "/api/backups/production/drill" `
        -ExpectedStatus @(200) `
        -Body @{ backup_id = $BackupId }
}

$failedRequired = @($checks | Where-Object { $_.required -and -not $_.ok })
$status = if ($failedRequired.Count -eq 0) { "pass" } else { "fail" }

$evidence = [ordered]@{
    generated_at = (Get-Date).ToUniversalTime().ToString("o")
    base_url = $BaseUrl
    backup_drill_requested = [bool]$BackupId
    status = $status
    checks = $checks
}

$jsonPath = Join-Path $OutputDir "p3-5-pilot-evidence-$timestamp.json"
$markdownPath = Join-Path $OutputDir "p3-5-pilot-evidence-$timestamp.md"

$evidence | ConvertTo-Json -Depth 12 | Set-Content -Path $jsonPath -Encoding UTF8
Write-MarkdownSummary -Path $markdownPath -Evidence $evidence

Write-Host "Evidence JSON: $jsonPath"
Write-Host "Evidence summary: $markdownPath"
Write-Host "Status: $status"

if ($status -ne "pass") {
    exit 1
}
