# Codebase Documentation Generator
# Recursively scans a directory and generates function/class documentation using local LLM
# Based on file-section-breakdown.ps1 patterns
#
# Usage: .\document-codebase.ps1 -Directory "C:\path\to\src" -OutputFile "docs\CODEBASE_MAP.md"

param(
    [Parameter(Mandatory=$true)]
    [string]$Directory,

    [string]$OutputFile = "CODEBASE_MAP.md",
    [string]$FilePattern = "*.py",  # Default to Python files
    [int]$ChunkTokens = 15000,      # Max tokens per LLM call
    [int]$OverlapTokens = 1500,
    [int]$CharsPerToken = 4,
    [int]$MaxRetries = 2
)

$ErrorActionPreference = "Stop"

# Debug logging
$debugLog = "$env:USERPROFILE\.claude\logs\document-codebase.log"
function Write-DebugLog {
    param([string]$Message)
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logDir = Split-Path $debugLog -Parent
    if (-not (Test-Path $logDir)) { New-Item -ItemType Directory -Path $logDir -Force | Out-Null }
    Add-Content -Path $debugLog -Value "$timestamp - $Message" -ErrorAction SilentlyContinue
}

Write-DebugLog "=== Document Codebase Started ==="
Write-DebugLog "Directory: $Directory"
Write-DebugLog "Pattern: $FilePattern"
Write-DebugLog "Output: $OutputFile"

# Validate directory exists
if (-not (Test-Path $Directory)) {
    Write-Error "Directory not found: $Directory"
    exit 1
}

# File analysis prompt template
$filePromptTemplate = @"
You are analyzing source code to create detailed documentation.

TASK: Document every function, class, method, and significant code block in this file.

For each item, output ONE LINE in this exact format:
Lines [START]-[END]: [TYPE] ``[NAME]`` - [DESCRIPTION]

TYPES to use:
- class: Class definition
- function: Top-level function
- method: Method within a class
- constant: Module-level constants
- import-block: Import statements
- type-definition: Type aliases, dataclasses, enums
- global: Module-level code that runs on import

RULES:
1. Document EVERY function and class, no matter how small
2. Include the full line range (start to end of definition)
3. Description should explain WHAT it does and WHY (purpose)
4. Note any important parameters or return values in the description
5. For methods, prefix the name with the class: ``ClassName.method_name``
6. Note dependencies on other functions/modules when visible

EXAMPLE OUTPUT:
Lines 1-5: import-block ``imports`` - Standard library and third-party imports
Lines 7-15: class ``ConfigManager`` - Manages application configuration with validation
Lines 9-12: method ``ConfigManager.__init__`` - Initializes config from file path, validates schema
Lines 14-15: method ``ConfigManager.get`` - Returns config value by key, raises KeyError if missing
Lines 17-30: function ``process_data`` - Main entry point, orchestrates data pipeline. Calls validate_input then transform

---

FILE: {FILENAME}
CONTENT:
{CONTENT}
"@

# Meta-summary prompt
$metaPromptTemplate = @"
You are creating a system architecture document from individual file summaries.

TASK: Create a comprehensive system map showing how all modules connect.

For each module, include:
1. Its primary purpose
2. Key functions/classes it exports
3. What other modules it depends on
4. What modules depend on it

Then create:
- A data flow diagram (text-based)
- A list of entry points (CLI commands, main functions)
- A list of shared utilities used across modules

FORMAT your output as clean markdown.

---

FILE SUMMARIES:
{SUMMARIES}
"@

function Invoke-LocalLLM {
    param(
        [string]$Prompt
    )

    # Write prompt to temp file
    $promptFile = [System.IO.Path]::GetTempFileName()
    $Prompt | Set-Content $promptFile -Encoding UTF8

    try {
        # Convert paths for bash
        $scriptPath = "$env:USERPROFILE\.claude\scripts\safe-model-load.sh".Replace('\', '/')
        if ($scriptPath -match '^([A-Za-z]):') {
            $scriptPath = '/' + $Matches[1].ToLower() + $scriptPath.Substring(2)
        }
        $unixPromptFile = $promptFile.Replace('\', '/')
        if ($unixPromptFile -match '^([A-Za-z]):') {
            $unixPromptFile = '/' + $Matches[1].ToLower() + $unixPromptFile.Substring(2)
        }

        Write-DebugLog "Calling LLM via gateway..."
        $bashExe = "C:\Program Files\Git\usr\bin\bash.exe"
        if (-not (Test-Path $bashExe)) {
            $bashExe = "bash"
        }

        $output = & $bashExe $scriptPath request text --prompt-file $unixPromptFile 2>&1
        Write-DebugLog "Gateway returned: $($output | Out-String)"

        # Extract FILE= path
        $fileLine = $output | Where-Object { $_ -match "^FILE=" } | Select-Object -First 1
        if (-not $fileLine) {
            throw "No FILE= returned from gateway. Output: $output"
        }

        $responseFile = $fileLine -replace "^FILE=", ""
        if ($responseFile -match '^/([a-zA-Z])/') {
            $drive = $Matches[1].ToUpper()
            $responseFile = $drive + ':' + $responseFile.Substring(2)
            $responseFile = $responseFile.Replace('/', '\')
        }

        # Poll for response
        $maxWaitSeconds = 300  # 5 minute max for large files
        $pollIntervalSeconds = 2
        $elapsed = 0

        while ($elapsed -lt $maxWaitSeconds) {
            if ((Test-Path $responseFile) -and ((Get-Item $responseFile).Length -gt 0)) {
                $response = Get-Content $responseFile -Raw

                try {
                    $jsonResponse = $response | ConvertFrom-Json
                    if ($jsonResponse.error) {
                        throw "LLM Error: $($jsonResponse.error)"
                    }
                    if ($jsonResponse.choices -and $jsonResponse.choices[0].message.content) {
                        return $jsonResponse.choices[0].message.content
                    }
                } catch {
                    # Not JSON - return raw
                }

                return $response
            }

            Start-Sleep -Seconds $pollIntervalSeconds
            $elapsed += $pollIntervalSeconds

            # Progress indicator
            if ($elapsed % 10 -eq 0) {
                Write-Host "." -NoNewline
            }
        }

        throw "LLM response timeout after $maxWaitSeconds seconds"

    } finally {
        Remove-Item $promptFile -Force -ErrorAction SilentlyContinue
    }
}

function Get-ChunkByTokens {
    param(
        [string[]]$Lines,
        [int]$StartLine,
        [int]$MaxTokens,
        [int]$CharsPerToken
    )

    $maxChars = $MaxTokens * $CharsPerToken
    $currentChars = 0
    $endLine = $StartLine

    for ($i = $StartLine; $i -lt $Lines.Count; $i++) {
        $lineChars = $Lines[$i].Length + 1
        if (($currentChars + $lineChars) -gt $maxChars -and $i -gt $StartLine) {
            break
        }
        $currentChars += $lineChars
        $endLine = $i
    }

    return @{
        StartLine = $StartLine
        EndLine = $endLine
        Content = ($Lines[$StartLine..$endLine] -join "`n")
        StartLineNumber = $StartLine + 1
        EndLineNumber = $endLine + 1
    }
}

function Process-SingleFile {
    param(
        [string]$FilePath,
        [string]$RelativePath
    )

    Write-Host "  Processing: $RelativePath" -ForegroundColor Cyan
    Write-DebugLog "Processing file: $FilePath"

    $fileContent = Get-Content $FilePath -Raw
    $fileLines = Get-Content $FilePath
    $totalLines = $fileLines.Count
    $totalChars = $fileContent.Length
    $estimatedTokens = [math]::Ceiling($totalChars / $CharsPerToken)

    Write-Host "    Lines: $totalLines, Tokens: ~$estimatedTokens"

    $allSections = @()

    if ($estimatedTokens -le $ChunkTokens) {
        # Single chunk
        $prompt = $filePromptTemplate -replace "\{FILENAME\}", $RelativePath -replace "\{CONTENT\}", $fileContent

        for ($retry = 0; $retry -le $MaxRetries; $retry++) {
            try {
                Write-Host "    Analyzing..." -NoNewline
                $response = Invoke-LocalLLM -Prompt $prompt
                Write-Host " done"

                # Parse sections
                $sections = @($response -split "`n" | Where-Object { $_ -match "^Lines\s*\[?\d+-(\d+|[Ee]nd)\]?:" })

                if ($sections.Count -gt 0) {
                    Write-Host "    Found $($sections.Count) items" -ForegroundColor Green
                    $allSections = $sections
                    break
                } else {
                    Write-Host "    No valid sections found, retry $($retry+1)/$MaxRetries" -ForegroundColor Yellow
                }
            } catch {
                Write-Host " failed: $_" -ForegroundColor Red
                Write-DebugLog "File $RelativePath failed: $_"
            }
        }
    } else {
        # Multiple chunks needed
        Write-Host "    Large file, chunking..." -ForegroundColor Yellow
        $overlapLines = [math]::Ceiling(($OverlapTokens * $CharsPerToken) / 80)
        $currentLine = 0
        $chunkNumber = 0

        while ($currentLine -lt $totalLines) {
            $chunkNumber++
            $chunk = Get-ChunkByTokens -Lines $fileLines -StartLine $currentLine -MaxTokens $ChunkTokens -CharsPerToken $CharsPerToken

            $chunkPrompt = $filePromptTemplate -replace "\{FILENAME\}", "$RelativePath (chunk $chunkNumber)" -replace "\{CONTENT\}", $chunk.Content

            if ($currentLine -gt 0) {
                $chunkPrompt += "`n`nNOTE: This is chunk $chunkNumber. Lines numbered from original file. First ~$OverlapTokens tokens overlap with previous chunk."
            }

            for ($retry = 0; $retry -le $MaxRetries; $retry++) {
                try {
                    Write-Host "    Chunk $chunkNumber (lines $($chunk.StartLineNumber)-$($chunk.EndLineNumber))..." -NoNewline
                    $response = Invoke-LocalLLM -Prompt $chunkPrompt
                    Write-Host " done"

                    $sections = @($response -split "`n" | Where-Object { $_ -match "^Lines\s*\[?\d+-(\d+|[Ee]nd)\]?:" })

                    if ($sections.Count -gt 0) {
                        Write-Host "      Found $($sections.Count) items" -ForegroundColor Green
                        $allSections += $sections
                        break
                    }
                } catch {
                    Write-Host " failed" -ForegroundColor Red
                }
            }

            # Move to next chunk with overlap
            $overlapStartLine = [math]::Max(0, $chunk.EndLine - $overlapLines)
            if ($overlapStartLine -le $currentLine) {
                $currentLine = $chunk.EndLine + 1
            } else {
                $currentLine = $overlapStartLine
            }

            if ($chunk.EndLine -ge ($totalLines - 1)) {
                break
            }
        }
    }

    # Deduplicate sections (by line range)
    $uniqueSections = @{}
    foreach ($section in $allSections) {
        if ($section -match "Lines\s*\[?(\d+)-(\d+|[Ee]nd)\]?:") {
            $key = "$($Matches[1])-$($Matches[2])"
            if (-not $uniqueSections.ContainsKey($key)) {
                $uniqueSections[$key] = $section
            }
        }
    }

    # Sort by start line
    $sortedSections = $uniqueSections.Values | Sort-Object {
        if ($_ -match "Lines\s*\[?(\d+)-") { [int]$Matches[1] } else { 0 }
    }

    return @{
        FilePath = $RelativePath
        TotalLines = $totalLines
        EstimatedTokens = $estimatedTokens
        Sections = $sortedSections
    }
}

# === MAIN EXECUTION ===

Write-Host ""
Write-Host "=== Codebase Documentation Generator ===" -ForegroundColor Magenta
Write-Host "Directory: $Directory"
Write-Host "Pattern: $FilePattern"
Write-Host ""

# Find all matching files
$files = Get-ChildItem -Path $Directory -Filter $FilePattern -Recurse -File
Write-Host "Found $($files.Count) files to process" -ForegroundColor Cyan
Write-Host ""

if ($files.Count -eq 0) {
    Write-Error "No files found matching pattern: $FilePattern"
    exit 1
}

# PASS 1: Process each file
$fileSummaries = @()
$fileNumber = 0

foreach ($file in $files) {
    $fileNumber++
    $relativePath = $file.FullName.Substring($Directory.Length).TrimStart('\', '/')

    Write-Host "[$fileNumber/$($files.Count)] $relativePath" -ForegroundColor White

    try {
        $summary = Process-SingleFile -FilePath $file.FullName -RelativePath $relativePath
        $fileSummaries += $summary
    } catch {
        Write-Host "  ERROR: $_" -ForegroundColor Red
        Write-DebugLog "FATAL error on $relativePath : $_"
    }

    Write-Host ""
}

# PASS 2: Generate meta-summary
Write-Host ""
Write-Host "=== Generating System Map ===" -ForegroundColor Magenta
Write-Host ""

# Build combined summary text
$summaryText = ""
foreach ($summary in $fileSummaries) {
    $summaryText += "## $($summary.FilePath)`n"
    $summaryText += "Lines: $($summary.TotalLines) | Tokens: ~$($summary.EstimatedTokens)`n`n"

    foreach ($section in $summary.Sections) {
        $summaryText += "$section`n"
    }
    $summaryText += "`n---`n`n"
}

# Check if meta-summary needs chunking
$metaTokens = [math]::Ceiling($summaryText.Length / $CharsPerToken)
Write-Host "Combined summaries: ~$metaTokens tokens"

$metaResponse = ""
if ($metaTokens -le $ChunkTokens) {
    $metaPrompt = $metaPromptTemplate -replace "\{SUMMARIES\}", $summaryText

    Write-Host "Generating system map..." -NoNewline
    try {
        $metaResponse = Invoke-LocalLLM -Prompt $metaPrompt
        Write-Host " done" -ForegroundColor Green
    } catch {
        Write-Host " failed: $_" -ForegroundColor Red
        $metaResponse = "# System Map Generation Failed`n`nError: $_"
    }
} else {
    Write-Host "Summaries too large for single meta-pass, outputting raw summaries" -ForegroundColor Yellow
    $metaResponse = "# System Map`n`n(Auto-generated meta-summary skipped - summaries exceed token limit)`n`nSee individual file summaries below."
}

# === OUTPUT ===

Write-Host ""
Write-Host "=== Writing Output ===" -ForegroundColor Magenta

$outputContent = @"
# Codebase Documentation

Generated: $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")
Directory: $Directory
Files processed: $($fileSummaries.Count)

---

$metaResponse

---

# File-by-File Documentation

"@

foreach ($summary in $fileSummaries) {
    $outputContent += "## $($summary.FilePath)`n`n"
    $outputContent += "**Lines:** $($summary.TotalLines) | **Estimated tokens:** ~$($summary.EstimatedTokens)`n`n"

    foreach ($section in $summary.Sections) {
        $outputContent += "- $section`n"
    }
    $outputContent += "`n---`n`n"
}

# Write output file
$outputPath = if ([System.IO.Path]::IsPathRooted($OutputFile)) {
    $OutputFile
} else {
    Join-Path $Directory $OutputFile
}

$outputContent | Set-Content $outputPath -Encoding UTF8
Write-Host "Documentation written to: $outputPath" -ForegroundColor Green
Write-Host ""

Write-DebugLog "=== Document Codebase Completed ==="
Write-DebugLog "Output: $outputPath"

exit 0
