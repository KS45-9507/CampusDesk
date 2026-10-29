$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot
$preferredPorts = @(8001, 8000, 8002, 8003, 8004, 8005)

function Test-CampusDesk([int]$Port) {
    try {
        $response = Invoke-WebRequest -Uri "http://127.0.0.1:$Port/login" -TimeoutSec 2 -UseBasicParsing
        return $response.StatusCode -eq 200
    } catch {
        return $false
    }
}

foreach ($candidate in $preferredPorts) {
    if (Test-CampusDesk $candidate) {
        $url = "http://127.0.0.1:$candidate/login"
        Write-Host "CampusDesk is already running: $url"
        Start-Process $url
        exit 0
    }
}

$port = $null
foreach ($candidate in $preferredPorts) {
    $probe = $null
    try {
        $probe = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback, $candidate)
        $probe.Start()
        $port = $candidate
        break
    } catch {
        # This port is occupied; try the next local option.
    } finally {
        if ($probe) { $probe.Stop() }
    }
}

if (-not $port) {
    Write-Error "Ports 8000–8005 are all in use. Close another CampusDesk instance and try again."
    exit 1
}

$python = Get-Command py.exe -ErrorAction SilentlyContinue
if ($python) {
    $pythonArgs = @('-3', '-u', 'main.py')
} else {
    $python = Get-Command python.exe -ErrorAction SilentlyContinue
    if (-not $python) {
        Write-Error 'Python 3 was not found. Install Python 3 or add it to PATH.'
        exit 1
    }
    $pythonArgs = @('-u', 'main.py')
}

$oldPort = $env:PORT
$env:PORT = [string]$port
$stdout = Join-Path $root 'web_server_stdout.log'
$stderr = Join-Path $root 'web_server_stderr.log'
try {
    $server = Start-Process -FilePath $python.Source -ArgumentList $pythonArgs `
        -WorkingDirectory $root -WindowStyle Minimized -PassThru `
        -RedirectStandardOutput $stdout -RedirectStandardError $stderr
} catch {
    Write-Error "Could not launch Python: $($_.Exception.Message)"
    exit 1
} finally {
    if ($null -eq $oldPort) { Remove-Item Env:PORT -ErrorAction SilentlyContinue }
    else { $env:PORT = $oldPort }
}

$url = "http://127.0.0.1:$port/login"
for ($attempt = 0; $attempt -lt 20; $attempt++) {
    Start-Sleep -Milliseconds 500
    if (Test-CampusDesk $port) {
        Write-Host "CampusDesk is ready: $url"
        Write-Host 'The server is running in a minimized window. Close that window to stop it.'
        Start-Process $url
        exit 0
    }
    if ($server.HasExited) { break }
}

$details = Get-Content -LiteralPath $stderr -Raw -ErrorAction SilentlyContinue
if (-not $details) { $details = Get-Content -LiteralPath $stdout -Raw -ErrorAction SilentlyContinue }
if ($server -and -not $server.HasExited) { Stop-Process -Id $server.Id -Force -ErrorAction SilentlyContinue }
Write-Error "CampusDesk did not become ready on port $port. $details"
exit 1
