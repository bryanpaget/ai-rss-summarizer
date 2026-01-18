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
    [int]$MaxRetries = 2,
    [switch]$SkipSynthesis,  # Skip system map generation (Tool 2 mode)
    [int]$MaxFiles = 0       # Limit number of files (0 = no limit)
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

# File-type specific prompt configurations
# Each has: types, examples, and language-specific guidance
$fileTypeConfigs = @{
    ".py" = @{
        Name = "Python"
        Types = @"
- class: Class definition (look for ``class Name:``)
- function: Top-level function (``def name()`` at module level)
- method: Method within a class (``def name(self)`` indented under class)
- decorator: Decorated functions/classes (lines with ``@decorator``)
- constant: Module-level UPPERCASE variables
- import-block: Import statements (``import x`` or ``from x import y``)
- dataclass: Classes with ``@dataclass`` decorator
- type-alias: Type definitions (``TypeName = ...``)
- global: Module-level code that executes on import
"@
        Examples = ""
        Guidance = @"
PYTHON-SPECIFIC RULES:
- Identify decorators (@property, @staticmethod, @dataclass) and note them
- For async functions, note ``async def`` in description
- Note if methods modify self (mutator) vs return new value (pure)
- Identify dunder methods (__init__, __str__, etc.) and their purpose
- Track inheritance: note parent class if ``class X(Parent):``
"@
    }
    ".js" = @{
        Name = "JavaScript"
        Types = @"
- class: ES6 class definition
- function: Named function declaration (``function name()``)
- arrow: Arrow function assigned to const/let (``const name = () => {}``)
- method: Method within a class
- constant: const declarations at module level
- import-block: import/require statements
- export: Exported functions/classes/values
- type-definition: JSDoc type definitions or TypeScript-style comments
"@
        Examples = @"
Lines 1-5: import-block ``imports`` - ES6 imports from react, lodash, local modules
Lines 7-10: constant ``CONFIG`` - Frozen configuration object with API endpoints
Lines 12-45: class ``DataService`` - Service class for API communication. Handles auth and retry logic
Lines 14-20: method ``DataService.constructor`` - Initializes axios instance with base URL and interceptors
Lines 22-35: method ``DataService.fetch`` - Async GET request with error handling. Returns parsed JSON
Lines 47-60: arrow ``processItems`` - Transforms array of items. Maps and filters based on status
Lines 62-80: function ``createStore`` - Factory function creating Redux-like store with dispatch/subscribe
"@
        Guidance = @"
JAVASCRIPT-SPECIFIC RULES:
- Distinguish function declarations from arrow functions (different ``this`` binding)
- Note async/await usage
- Identify React components (function returning JSX)
- Track exports (default vs named)
- Note closure patterns where inner functions capture outer scope
"@
    }
    ".ts" = @{
        Name = "TypeScript"
        Types = @"
- class: Class definition
- function: Named function declaration
- arrow: Arrow function with type annotations
- method: Method within a class
- interface: Interface definition
- type: Type alias (``type Name = ...``)
- enum: Enum definition
- constant: const with type annotation
- import-block: import statements
- export: Exported items
- generic: Generic function/class (``<T>``)
"@
        Examples = @"
Lines 1-8: import-block ``imports`` - Type imports and module imports
Lines 10-18: interface ``UserConfig`` - Configuration shape: url (string), timeout (number), retries (optional number)
Lines 20-22: type ``RequestHandler`` - Function type alias: (req: Request) => Promise<Response>
Lines 24-60: class ``ApiClient<T>`` - Generic API client. T is response type. Handles typed requests
Lines 26-32: method ``ApiClient.constructor`` - Takes config: UserConfig, validates and stores
Lines 34-50: method ``ApiClient.get`` - Generic GET: returns Promise<T>. Includes retry logic
Lines 52-60: method ``ApiClient.post`` - Generic POST: takes body of type Partial<T>
Lines 62-70: function ``createClient`` - Factory with type inference. Returns configured ApiClient
"@
        Guidance = @"
TYPESCRIPT-SPECIFIC RULES:
- Document generic type parameters (``<T>``, ``<K, V>``)
- Note type guards (``is`` keyword in return type)
- Identify utility types used (Partial, Required, Pick, Omit)
- Track interface inheritance and type intersections
- Note access modifiers (public, private, protected)
"@
    }
    ".sh" = @{
        Name = "Bash/Shell"
        Types = @"
- function: Shell function definition
- variable: Important variable assignments
- main: Main script logic (not in function)
- case-block: Case statement blocks
- loop: Significant for/while loops
- conditional: Important if/then blocks
- source-block: Source/dot commands loading other scripts
"@
        Examples = @"
Lines 1-10: variable ``CONFIG`` - Script configuration: paths, defaults, error codes
Lines 12-30: function ``log_message`` - Logging utility. Takes level and message, writes to stderr with timestamp
Lines 32-50: function ``validate_input`` - Input validation. Checks required args exist, validates file paths
Lines 52-80: function ``process_file`` - Main processing. Reads file, transforms content, writes output
Lines 82-100: main ``script_body`` - Argument parsing with getopts, calls validate_input then process_file
Lines 102-110: case-block ``error_handler`` - Trap handler for EXIT. Cleans up temp files, reports status
"@
        Guidance = @"
BASH-SPECIFIC RULES:
- Note if functions use local variables vs global
- Identify trap handlers and what signals they catch
- Track exit codes and their meanings
- Note subshell usage (command substitution, pipelines)
- Identify external command dependencies
"@
    }
    ".ps1" = @{
        Name = "PowerShell"
        Types = @"
- function: Function definition
- param: Parameter block
- variable: Important variable assignments
- main: Main script execution block
- filter: Filter definition
- class: PowerShell class (v5+)
- workflow: Workflow definition
"@
        Examples = @"
Lines 1-15: param ``script_parameters`` - Script parameters: Directory (mandatory string), OutputFile (optional string), MaxRetries (int, default 2)
Lines 17-25: function ``Write-DebugLog`` - Logging helper. Takes message, appends to log file with timestamp
Lines 27-50: function ``Invoke-LocalLLM`` - Calls LLM gateway. Takes prompt, returns response text. Handles JSON parsing
Lines 52-80: function ``Process-SingleFile`` - Processes one file. Chunks if needed, calls LLM, parses response
Lines 82-120: main ``script_execution`` - Main flow: enumerate files, process each, merge results, write output
"@
        Guidance = @"
POWERSHELL-SPECIFIC RULES:
- Note cmdlet binding and parameter attributes
- Identify pipeline input/output (``process`` block)
- Track error handling (try/catch/finally)
- Note use of PowerShell classes vs functions
- Identify WMI/CIM queries and their targets
"@
    }
    "default" = @{
        Name = "Generic"
        Types = @"
- class: Class definition
- function: Function/procedure definition
- method: Method within a class
- constant: Constants and configuration
- import-block: Import/include statements
- type-definition: Type definitions
- global: Module-level executable code
"@
        Examples = @"
Lines 1-5: import-block ``imports`` - Module dependencies
Lines 7-15: class ``ConfigManager`` - Configuration management with validation
Lines 9-12: method ``ConfigManager.init`` - Initialization from file path
Lines 14-15: method ``ConfigManager.get`` - Returns config value by key
Lines 17-30: function ``process_data`` - Main entry point, orchestrates pipeline
"@
        Guidance = @"
GENERAL RULES:
- Document every function and class
- Note input parameters and return types
- Identify dependencies between functions
"@
    }
}

function Get-FileTypeConfig {
    param([string]$Extension)

    $ext = $Extension.ToLower()
    if ($fileTypeConfigs.ContainsKey($ext)) {
        return $fileTypeConfigs[$ext]
    }
    return $fileTypeConfigs["default"]
}

function Build-FilePrompt {
    param(
        [string]$FileName,
        [string]$Content,
        [string]$Extension,
        [string]$ChunkNote = ""
    )

    $config = Get-FileTypeConfig -Extension $Extension

    # SANDWICH PROMPT: Instructions BEFORE content
    $prompt = @"
You are analyzing $($config.Name) source code to create detailed documentation.

=== YOUR TASK ===
Document every function, class, method, and significant code block in this file.

=== OUTPUT FORMAT ===
For each item, output ONE LINE in this exact format:
Lines [START]-[END]: [TYPE] ``[NAME]`` - [DESCRIPTION]

=== TYPES FOR $($config.Name.ToUpper()) ===
$($config.Types)

=== RULES ===
1. Document EVERY function and class, no matter how small
2. Include the full line range (start to end of definition)
3. Description should explain WHAT it does and WHY (purpose)
4. Note any important parameters or return values in the description
5. For methods, prefix the name with the class: ``ClassName.method_name``
6. Note dependencies on other functions/modules when visible

$($config.Guidance)



=== BEGIN FILE CONTENT ===
FILE: $FileName
$ChunkNote
---
$Content
---
=== END FILE CONTENT ===

=== REMINDER: OUTPUT FORMAT ===
For each item, output ONE LINE:
Lines [START]-[END]: [TYPE] ``[NAME]`` - [DESCRIPTION]

CRITICAL: The examples above are FORMAT DEMONSTRATIONS ONLY. Do NOT copy content from examples.
Analyze ONLY the actual file content between BEGIN/END markers.
If the file has no imports, do not document imports.
If the file has no constants, do not document constants.
Every line number you output MUST exist in the actual file content above.
VERIFY: Line 1 shows the ACTUAL first line. If it is NOT an import statement, do NOT output import-block.
Read line 1 literally. If line 1 is a docstring like `"""..."""`, that is a docstring, NOT imports.

Document ALL items. Start from line 1. Include every function, class, and method.
"@

    return $prompt
}

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

            # Progress indicator with elapsed time
            if ($elapsed % 10 -eq 0) {
                Write-Host "." -NoNewline
                if ($elapsed -ge 60) {
                    Write-Host " ${elapsed}s" -NoNewline -ForegroundColor DarkGray
                }
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
        Content = (($StartLine..$endLine) | ForEach-Object { "$($_ + 1)`t$($Lines[$_])" }) -join "`n"
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
    # Add line numbers so LLM can reference actual lines (LLMs cannot count)
    $numberedContent = ($fileLines | ForEach-Object -Begin {$i=1} -Process { "$i`t$_"; $i++ }) -join "`n"
    $totalLines = $fileLines.Count
    $totalChars = $fileContent.Length
    $estimatedTokens = [math]::Ceiling($totalChars / $CharsPerToken)
    $fileExtension = [System.IO.Path]::GetExtension($FilePath)

    Write-Host "    Lines: $totalLines, Tokens: ~$estimatedTokens"

    $allSections = @()

    if ($estimatedTokens -le $ChunkTokens) {
        # Single chunk - use file-type specific prompt with sandwich structure
        $prompt = Build-FilePrompt -FileName $RelativePath -Content $numberedContent -Extension $fileExtension

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

            # Build chunk note for context
            $chunkNote = "CHUNK $chunkNumber of file (lines $($chunk.StartLineNumber)-$($chunk.EndLineNumber))"
            if ($currentLine -gt 0) {
                $chunkNote += "`nNOTE: First ~$OverlapTokens tokens overlap with previous chunk."
            }
            if ($chunk.EndLine -lt ($totalLines - 1)) {
                $chunkNote += "`nNOTE: File continues after this chunk."
            }

            # Use file-type specific prompt with sandwich structure
            $chunkPrompt = Build-FilePrompt -FileName $RelativePath -Content $chunk.Content -Extension $fileExtension -ChunkNote $chunkNote

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

# Pre-flight check: verify LLM is responsive
Write-Host ""
Write-Host "Checking LLM availability..." -NoNewline
try {
    $testPrompt = "Reply with only: OK"
    $testResponse = Invoke-LocalLLM -Prompt $testPrompt
    if ($testResponse -match "OK") {
        Write-Host " ready" -ForegroundColor Green
    } else {
        Write-Host " responded but unexpected output" -ForegroundColor Yellow
    }
} catch {
    Write-Host " FAILED" -ForegroundColor Red
    Write-Error "LLM is not available. Error: $_"
    Write-Host "Make sure LM Studio is running and a model is loaded."
    exit 1
}

Write-Host ""
Write-Host "=== Codebase Documentation Generator ===" -ForegroundColor Magenta
Write-Host "Directory: $Directory"
Write-Host "Pattern: $FilePattern"
Write-Host ""

# Find all matching files
$files = Get-ChildItem -Path $Directory -Filter $FilePattern -Recurse -File
if ($MaxFiles -gt 0) {
    $files = $files | Select-Object -First $MaxFiles
}
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

# PASS 2: Generate meta-summary (skip if -SkipSynthesis)
if ($SkipSynthesis) {
    Write-Host ""
    Write-Host "=== Skipping System Map (Tool 2 mode) ===" -ForegroundColor Yellow
    $metaResponse = ""
} else {
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
}  # end if not SkipSynthesis

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
