<#
.SYNOPSIS
Runs the packaged Odyss AI Flows test harness in an isolated Python environment.

.DESCRIPTION
Creates a timestamped, version-labelled sandbox under .compat/runs, installs the
core, test harness, and every local plugin as packages, then invokes the
odyss-ai-flows-test console entry point. Interactive selection is the default.

For Auto and Live runs, environment variables are loaded from a sibling
.env.local without printing secret values. Durable selections reuse the expected
local test host when present, or start isolated Azurite and Azure Functions host
processes and stop only those processes created by this script.

Cleanup controls removal of the per-run sandbox. Harness results under
tests/test_outputs are always preserved.

.EXAMPLE
.\Test-OdyssPython.ps1 -Python "C:\Path\To\Python314\python.exe"

.EXAMPLE
.\Test-OdyssPython.ps1 -Python "C:\Path\To\Python314\python.exe" `
    -Mode Live -Filter durable -Cleanup OnSuccess -NonInteractive
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string] $Python,

    [ValidateSet("Auto", "Static", "Live")]
    [string] $Mode,

    [string] $Filter,

    [string] $EnvFile = (Join-Path $PSScriptRoot ".env.local"),

    [ValidateSet("Never", "OnSuccess", "Always")]
    [string] $Cleanup = "Never",

    [string] $SandboxRoot = (
        Join-Path $PSScriptRoot ".compat\runs"
    ),

    [switch] $NonInteractive
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RepoRoot = $PSScriptRoot
$CorePath = Join-Path $RepoRoot "odyss_ai_flows_core"
$TestsPath = Join-Path $RepoRoot "tests"
$PluginsRoot = Join-Path $RepoRoot "plugins"
$DurableHostRoot = Join-Path $TestsPath "scenarios\durable"
$CompatToolsRoot = Join-Path $RepoRoot ".compat\tools"
$TestOutputsRoot = Join-Path $TestsPath "test_outputs"

$OwnedAzurite = $null
$OwnedFunctionsHost = $null
$RunRoot = $null
$HarnessExitCode = $null
$ScriptExitCode = 2


function Assert-NativeSuccess {
    param([Parameter(Mandatory = $true)][string] $Operation)

    if ($LASTEXITCODE -ne 0) {
        throw "$Operation failed with exit code $LASTEXITCODE"
    }
}


function Read-TestMode {
    Write-Host ""
    Write-Host "Select test mode:"
    Write-Host "  [1] Auto   - run local and configured integration tests"
    Write-Host "  [2] Static - do not run external integrations"
    Write-Host "  [3] Live   - force selected integration tests to run"

    while ($true) {
        switch (Read-Host "Mode [1]") {
            ""  { return "Auto" }
            "1" { return "Auto" }
            "2" { return "Static" }
            "3" { return "Live" }
            default { Write-Warning "Choose 1, 2, or 3." }
        }
    }
}


function Read-TestFilter {
    param([Parameter(Mandatory = $true)][string[]] $ScenarioIds)

    $Groups = @(
        $ScenarioIds |
            ForEach-Object { ($_ -split "/", 2)[0] } |
            Sort-Object -Unique
    )

    Write-Host ""
    Write-Host "Select test scope:"
    Write-Host "  [0] All scenarios"

    for ($Index = 0; $Index -lt $Groups.Count; $Index++) {
        Write-Host "  [$($Index + 1)] $($Groups[$Index])"
    }

    Write-Host "  [E] Enter an exact scenario or prefix"

    while ($true) {
        $Selection = (Read-Host "Scope [0]").Trim()

        if (-not $Selection -or $Selection -eq "0") {
            return ""
        }

        if ($Selection -match "^[Ee]$") {
            Write-Host ""
            $ScenarioIds | ForEach-Object { Write-Host "  $_" }
            $Entered = (Read-Host "Scenario or prefix").Trim()

            if ($ScenarioIds.Where({ $_.StartsWith($Entered) }).Count) {
                return $Entered
            }

            Write-Warning "No scenario starts with '$Entered'."
            continue
        }

        $Number = 0

        if (
            [int]::TryParse($Selection, [ref] $Number) -and
            $Number -ge 1 -and
            $Number -le $Groups.Count
        ) {
            return $Groups[$Number - 1]
        }

        Write-Warning "Choose a listed number, 0, or E."
    }
}


function Read-CleanupMode {
    Write-Host ""
    Write-Host "Remove the isolated per-run environment:"
    Write-Host "  [1] Never"
    Write-Host "  [2] Only after a successful test run"
    Write-Host "  [3] Always"

    while ($true) {
        switch (Read-Host "Cleanup [1]") {
            ""  { return "Never" }
            "1" { return "Never" }
            "2" { return "OnSuccess" }
            "3" { return "Always" }
            default { Write-Warning "Choose 1, 2, or 3." }
        }
    }
}


function Import-DotEnv {
    param([Parameter(Mandatory = $true)][string] $Path)

    foreach ($RawLine in Get-Content -LiteralPath $Path) {
        $Line = $RawLine.Trim()

        if (-not $Line -or $Line.StartsWith("#")) {
            continue
        }

        if ($Line.StartsWith("export ")) {
            $Line = $Line.Substring(7).TrimStart()
        }

        $Separator = $Line.IndexOf("=")

        if ($Separator -lt 1) {
            throw "Invalid dotenv entry in '$Path'. Expected NAME=value."
        }

        $Name = $Line.Substring(0, $Separator).Trim()
        $Value = $Line.Substring($Separator + 1).Trim()

        if ($Name -notmatch "^[A-Za-z_][A-Za-z0-9_]*$") {
            throw "Invalid environment variable name '$Name' in '$Path'."
        }

        if (
            $Value.Length -ge 2 -and
            (
                ($Value.StartsWith('"') -and $Value.EndsWith('"')) -or
                ($Value.StartsWith("'") -and $Value.EndsWith("'"))
            )
        ) {
            $Value = $Value.Substring(1, $Value.Length - 2)
        }

        $Existing = [Environment]::GetEnvironmentVariable(
            $Name,
            [EnvironmentVariableTarget]::Process
        )

        if ($null -eq $Existing) {
            [Environment]::SetEnvironmentVariable(
                $Name,
                $Value,
                [EnvironmentVariableTarget]::Process
            )
        }
    }
}


function Test-TcpPort {
    param(
        [Parameter(Mandatory = $true)][string] $ComputerName,
        [Parameter(Mandatory = $true)][int] $Port,
        [int] $TimeoutMilliseconds = 500
    )

    $ConnectHost = if ($ComputerName -eq "localhost") {
        "127.0.0.1"
    }
    else {
        $ComputerName
    }

    $Client = [Net.Sockets.TcpClient]::new()

    try {
        $Connection = $Client.BeginConnect($ConnectHost, $Port, $null, $null)

        if (-not $Connection.AsyncWaitHandle.WaitOne($TimeoutMilliseconds)) {
            return $false
        }

        $Client.EndConnect($Connection)
        return $true
    }
    catch {
        return $false
    }
    finally {
        $Client.Dispose()
    }
}


function Write-ServiceLogTail {
    param(
        [Parameter(Mandatory = $true)][string] $Path,
        [Parameter(Mandatory = $true)][string] $Label
    )

    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        return
    }

    Write-Warning "$Label (last 40 lines):"
    Get-Content -LiteralPath $Path -Tail 40 |
        ForEach-Object { Write-Host "  $_" }
}


function Test-DurableHost {
    try {
        $Health = Invoke-RestMethod `
            -Uri "http://localhost:7071/api/durable-test-health" `
            -TimeoutSec 3

        if (
            $Health.service -ne "odyss-ai-flows-durable-test-host" -or
            -not ($Health.orchestrators -contains "flow_orchestrator")
        ) {
            return $false
        }

        $Registration = Invoke-RestMethod `
            -Uri "http://localhost:7071/admin/functions/flow_orchestrator" `
            -TimeoutSec 3

        if ($Registration.name -ne "flow_orchestrator") {
            return $false
        }

        foreach ($Binding in $Registration.config.bindings) {
            if (
                $Binding.type -eq "orchestrationTrigger" -and
                $Binding.orchestration -eq "flow_orchestrator"
            ) {
                return $true
            }
        }

        return $false
    }
    catch {
        return $false
    }
}


function Wait-Until {
    param(
        [Parameter(Mandatory = $true)][scriptblock] $Condition,
        [Parameter(Mandatory = $true)][int] $TimeoutSeconds,
        [Parameter(Mandatory = $true)][string] $Description,
        [Diagnostics.Process] $Process
    )

    $Deadline = [DateTime]::UtcNow.AddSeconds($TimeoutSeconds)

    while ([DateTime]::UtcNow -lt $Deadline) {
        if ($null -ne $Process -and $Process.HasExited) {
            throw "$Description process exited with code $($Process.ExitCode)."
        }

        if (& $Condition) {
            return
        }

        Start-Sleep -Milliseconds 750
    }

    throw "Timed out waiting for $Description after $TimeoutSeconds seconds."
}


function Ensure-Azurite {
    param([Parameter(Mandatory = $true)][string] $RunDirectory)

    $Ports = @(10000, 10001, 10002)
    $Listening = @(
        $Ports | Where-Object { Test-TcpPort -ComputerName "localhost" -Port $_ }
    )

    if ($Listening.Count -eq $Ports.Count) {
        Write-Host "Reusing the existing Azurite endpoints."
        return $null
    }

    if ($Listening.Count -gt 0) {
        throw (
            "Only some Azurite ports are available. Ports 10000-10002 " +
            "must either all be free or all belong to an existing emulator."
        )
    }

    $Node = Get-Command node -ErrorAction SilentlyContinue
    $Npm = Get-Command npm -ErrorAction SilentlyContinue

    if ($null -eq $Node -or $null -eq $Npm) {
        throw "Node.js and npm are required to provision the local Azurite emulator."
    }

    $AzuriteScript = Join-Path `
        $CompatToolsRoot `
        "node_modules\azurite\dist\src\azurite.js"

    if (-not (Test-Path -LiteralPath $AzuriteScript)) {
        Write-Host "Installing an isolated Azurite copy under .compat/tools..."
        New-Item -ItemType Directory -Force -Path $CompatToolsRoot | Out-Null
        & $Npm.Source install `
            --prefix $CompatToolsRoot `
            --no-save `
            --no-audit `
            --no-fund `
            azurite | Out-Host
        Assert-NativeSuccess "Azurite installation"
    }

    $AzuriteData = Join-Path $RunDirectory "azurite"
    $ServiceLogs = Join-Path $RunDirectory "logs"
    New-Item -ItemType Directory -Force -Path $AzuriteData | Out-Null
    New-Item -ItemType Directory -Force -Path $ServiceLogs | Out-Null

    $Stdout = Join-Path $ServiceLogs "azurite.stdout.log"
    $Stderr = Join-Path $ServiceLogs "azurite.stderr.log"
    $DebugLog = Join-Path $ServiceLogs "azurite.debug.log"

    Write-Host "Starting isolated Azurite..."
    $Process = Start-Process `
        -FilePath $Node.Source `
        -ArgumentList @(
            $AzuriteScript,
            "--silent",
            "--location", $AzuriteData,
            "--debug", $DebugLog
        ) `
        -RedirectStandardOutput $Stdout `
        -RedirectStandardError $Stderr `
        -WindowStyle Hidden `
        -PassThru

    try {
        Wait-Until `
            -Condition {
                -not ($Ports.Where({
                    -not (Test-TcpPort -ComputerName "localhost" -Port $_)
                }).Count)
            } `
            -TimeoutSeconds 60 `
            -Description "Azurite" `
            -Process $Process
    }
    catch {
        Write-ServiceLogTail -Path $Stdout -Label "Azurite stdout"
        Write-ServiceLogTail -Path $Stderr -Label "Azurite stderr"
        throw
    }

    return $Process
}


function Resolve-FunctionsLaunch {
    $Func = Get-Command func -ErrorAction SilentlyContinue

    if ($null -eq $Func) {
        throw "Azure Functions Core Tools ('func') is required for durable tests."
    }

    $ShimDirectory = Split-Path -Parent $Func.Source
    $Node = Join-Path $ShimDirectory "node.exe"
    $MainScript = Join-Path `
        $ShimDirectory `
        "node_modules\azure-functions-core-tools\lib\main.js"

    if (
        (Test-Path -LiteralPath $Node) -and
        (Test-Path -LiteralPath $MainScript)
    ) {
        return @{
            FilePath = $Node
            Arguments = @($MainScript, "start", "--port", "7071")
        }
    }

    if ($Func.CommandType -eq [Management.Automation.CommandTypes]::Application) {
        return @{
            FilePath = $Func.Source
            Arguments = @("start", "--port", "7071")
        }
    }

    throw "Could not resolve the executable behind '$($Func.Source)'."
}


function Ensure-DurableFunctionsHost {
    param(
        [Parameter(Mandatory = $true)][string] $RunDirectory,
        [Parameter(Mandatory = $true)][string] $VirtualEnvironment
    )

    if (Test-DurableHost) {
        Write-Host "Reusing the existing Odyss durable test host on port 7071."
        return $null
    }

    if (Test-TcpPort -ComputerName "localhost" -Port 7071) {
        throw (
            "Port 7071 is occupied, but it is not the Odyss durable test host. " +
            "The script will not stop or replace that process."
        )
    }

    $Launch = Resolve-FunctionsLaunch
    $ServiceLogs = Join-Path $RunDirectory "logs"
    New-Item -ItemType Directory -Force -Path $ServiceLogs | Out-Null

    $Stdout = Join-Path $ServiceLogs "functions.stdout.log"
    $Stderr = Join-Path $ServiceLogs "functions.stderr.log"

    $env:VIRTUAL_ENV = $VirtualEnvironment
    $env:PATH = (
        (Join-Path $VirtualEnvironment "Scripts") +
        [IO.Path]::PathSeparator +
        $env:PATH
    )

    Write-Host "Starting the Odyss Azure Functions durable test host..."
    $Process = Start-Process `
        -FilePath $Launch.FilePath `
        -ArgumentList $Launch.Arguments `
        -WorkingDirectory $DurableHostRoot `
        -RedirectStandardOutput $Stdout `
        -RedirectStandardError $Stderr `
        -WindowStyle Hidden `
        -PassThru

    try {
        Wait-Until `
            -Condition { Test-DurableHost } `
            -TimeoutSeconds 90 `
            -Description "Odyss durable test host" `
            -Process $Process
    }
    catch {
        Write-ServiceLogTail -Path $Stdout -Label "Functions stdout"
        Write-ServiceLogTail -Path $Stderr -Label "Functions stderr"
        throw
    }

    return $Process
}


function Stop-OwnedProcess {
    param(
        [Diagnostics.Process] $Process,
        [Parameter(Mandatory = $true)][string] $Name
    )

    if ($null -eq $Process -or $Process.HasExited) {
        return
    }

    Write-Host "Stopping $Name started by this run..."
    Stop-Process -Id $Process.Id -Force -ErrorAction SilentlyContinue
    $Process.WaitForExit(5000) | Out-Null
}


try {
    if (-not (Test-Path -LiteralPath $Python -PathType Leaf)) {
        throw "Python executable not found: $Python"
    }

    foreach ($RequiredPath in @($CorePath, $TestsPath, $PluginsRoot, $DurableHostRoot)) {
        if (-not (Test-Path -LiteralPath $RequiredPath)) {
            throw "Required repository path not found: $RequiredPath"
        }
    }

    $PythonVersion = (& $Python -c "import platform; print(platform.python_version())").Trim()
    Assert-NativeSuccess "Python version detection"

    if ($PythonVersion -notmatch "^\d+\.\d+\.\d+") {
        throw "Unexpected Python version output: $PythonVersion"
    }

    $RunId = "{0}-py{1}-pid{2}" -f (
        Get-Date -Format "yyyyMMdd-HHmmss"
    ), $PythonVersion, $PID

    $RunRoot = Join-Path $SandboxRoot $RunId
    $VirtualEnvironment = Join-Path $RunRoot ".venv"
    $VenvPython = Join-Path $VirtualEnvironment "Scripts\python.exe"
    $TestRunner = Join-Path $VirtualEnvironment "Scripts\odyss-ai-flows-test.exe"

    New-Item -ItemType Directory -Path $RunRoot -Force | Out-Null

    Write-Host "Python:  $PythonVersion"
    Write-Host "Sandbox: $RunRoot"
    Write-Host "Creating isolated virtual environment..."
    & $Python -m venv $VirtualEnvironment
    Assert-NativeSuccess "Virtual environment creation"

    & $VenvPython -m pip install --upgrade pip setuptools wheel
    Assert-NativeSuccess "Build-tool installation"

    & $VenvPython -m pip install --no-build-isolation --editable $CorePath
    Assert-NativeSuccess "Core package installation"

    & $VenvPython -m pip install --no-build-isolation --editable $TestsPath
    Assert-NativeSuccess "Test harness installation"

    $PluginProjects = @(
        Get-ChildItem -LiteralPath $PluginsRoot -Directory |
            Where-Object {
                Test-Path -LiteralPath (Join-Path $_.FullName "pyproject.toml")
            } |
            Sort-Object Name
    )

    foreach ($PluginProject in $PluginProjects) {
        $PluginPyProject = Join-Path $PluginProject.FullName "pyproject.toml"
        $HasTestExtra = (
            & $VenvPython -c (
                "import pathlib, sys, tomllib; " +
                "data = tomllib.loads(pathlib.Path(sys.argv[1]).read_text(encoding='utf-8')); " +
                "print('test' in data.get('project', {}).get('optional-dependencies', {}))"
            ) $PluginPyProject
        ).Trim()
        Assert-NativeSuccess "Plugin test-extra detection: $($PluginProject.Name)"

        $PluginInstallTarget = if ($HasTestExtra -eq "True") {
            "$($PluginProject.FullName)[test]"
        }
        else {
            $PluginProject.FullName
        }

        $ExtraLabel = if ($HasTestExtra -eq "True") { " with test extra" } else { "" }
        Write-Host "Installing plugin package$($ExtraLabel): $($PluginProject.Name)"
        & $VenvPython -m pip install `
            --no-build-isolation `
            --editable `
            $PluginInstallTarget
        Assert-NativeSuccess "Plugin installation: $($PluginProject.Name)"
    }

    if (-not (Test-Path -LiteralPath $TestRunner -PathType Leaf)) {
        throw "Packaged test runner was not created: $TestRunner"
    }

    $ScenarioIds = @(
        & $TestRunner --list |
            ForEach-Object { $_.Trim() } |
            Where-Object { $_ }
    )
    Assert-NativeSuccess "Scenario discovery"

    if (-not $ScenarioIds.Count) {
        throw "The packaged test harness discovered no scenarios."
    }

    if (-not $Mode) {
        $Mode = if ($NonInteractive) { "Auto" } else { Read-TestMode }
    }

    if (-not $PSBoundParameters.ContainsKey("Filter") -and -not $NonInteractive) {
        $Filter = Read-TestFilter -ScenarioIds $ScenarioIds
    }

    if ($Filter) {
        $Matches = @($ScenarioIds.Where({ $_.StartsWith($Filter) }))

        if (-not $Matches.Count) {
            throw "No test scenario starts with '$Filter'."
        }
    }
    else {
        $Matches = $ScenarioIds
    }

    if (
        -not $PSBoundParameters.ContainsKey("Cleanup") -and
        -not $NonInteractive
    ) {
        $Cleanup = Read-CleanupMode
    }

    if (Test-Path -LiteralPath $EnvFile -PathType Leaf) {
        Import-DotEnv -Path $EnvFile
        Write-Host "Loaded process environment from: $EnvFile"
    }
    elseif ($Mode -in @("Auto", "Live")) {
        throw (
            "Environment file not found: $EnvFile. " +
            "Create the sibling .env.local before running integration tests."
        )
    }

    $IncludesDurable = @(
        $Matches.Where({ $_.StartsWith("durable/") })
    ).Count -gt 0

    if ($IncludesDurable -and $Mode -ne "Static") {
        $OwnedAzurite = Ensure-Azurite -RunDirectory $RunRoot
        $OwnedFunctionsHost = Ensure-DurableFunctionsHost `
            -RunDirectory $RunRoot `
            -VirtualEnvironment $VirtualEnvironment
    }

    $BeforeOutputDirectories = @()

    if (Test-Path -LiteralPath $TestOutputsRoot) {
        $BeforeOutputDirectories = @(
            Get-ChildItem -LiteralPath $TestOutputsRoot -Directory |
                ForEach-Object { $_.FullName }
        )
    }

    $RunnerArguments = @()

    if ($Mode -eq "Static") {
        $RunnerArguments += "--static"
    }
    elseif ($Mode -eq "Live") {
        $RunnerArguments += "--live"
    }

    if ($Filter) {
        $RunnerArguments += $Filter
    }

    Write-Host ""
    Write-Host "Running packaged test harness:"
    Write-Host "  Mode:   $Mode"
    Write-Host "  Filter: $(if ($Filter) { $Filter } else { '<all>' })"
    Write-Host ""

    Push-Location $RepoRoot

    try {
        & $TestRunner @RunnerArguments
        $HarnessExitCode = $LASTEXITCODE
    }
    finally {
        Pop-Location
    }

    $NewOutputDirectories = @()

    if (Test-Path -LiteralPath $TestOutputsRoot) {
        $NewOutputDirectories = @(
            Get-ChildItem -LiteralPath $TestOutputsRoot -Directory |
                Where-Object {
                    $_.FullName -notin $BeforeOutputDirectories
                } |
                Sort-Object LastWriteTime
        )
    }

    if ($NewOutputDirectories.Count) {
        $LatestOutput = $NewOutputDirectories[-1].FullName
        Write-Host "Test results: $LatestOutput"
        Write-Host "Summary:      $(Join-Path $LatestOutput 'summary.json')"
    }

    $ScriptExitCode = $HarnessExitCode
}
catch {
    [Console]::Error.WriteLine("ERROR: " + $_.Exception.Message)
    $ScriptExitCode = 2
}
finally {
    Stop-OwnedProcess -Process $OwnedFunctionsHost -Name "Azure Functions host"
    Stop-OwnedProcess -Process $OwnedAzurite -Name "Azurite"

    $RemoveSandbox = (
        $Cleanup -eq "Always" -or
        (
            $Cleanup -eq "OnSuccess" -and
            $null -ne $HarnessExitCode -and
            $HarnessExitCode -eq 0
        )
    )

    if ($RemoveSandbox -and $RunRoot -and (Test-Path -LiteralPath $RunRoot)) {
        $ResolvedRunRoot = (Resolve-Path -LiteralPath $RunRoot).Path
        $ResolvedSandboxRoot = (Resolve-Path -LiteralPath $SandboxRoot).Path
        $ExpectedPrefix = $ResolvedSandboxRoot + [IO.Path]::DirectorySeparatorChar

        if (
            -not $ResolvedRunRoot.StartsWith(
                $ExpectedPrefix,
                [StringComparison]::OrdinalIgnoreCase
            )
        ) {
            Write-Error "Refusing to clean a path outside the sandbox root: $ResolvedRunRoot"
            $ScriptExitCode = 2
        }
        else {
            Remove-Item -LiteralPath $ResolvedRunRoot -Recurse -Force
            Write-Host "Removed isolated sandbox: $ResolvedRunRoot"
        }
    }
    elseif ($RunRoot) {
        Write-Host "Retained isolated sandbox: $RunRoot"
    }
}

exit $ScriptExitCode
