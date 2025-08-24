# Security Scanner for Tetheritall
# Scans for potential secrets and credentials in the codebase

param(
    [switch]$Fix,
    [switch]$Verbose
)

Write-Host "🔒 Tetheritall Security Scanner" -ForegroundColor Green
Write-Host "=================================" -ForegroundColor Green

$issues = @()
$files = Get-ChildItem -Recurse -File | Where-Object { 
    $_.Extension -match "\.(py|js|ts|json|yaml|yml|ini|cfg|conf|env|txt|md)$" -and
    $_.FullName -notmatch "node_modules|\.git|venv|__pycache__|\.terraform"
}

# Patterns to scan for
$patterns = @{
    "Database URLs" = @(
        "postgresql://",
        "mysql://", 
        "mongodb://",
        "redis://",
        "sqlite://"
    )
    "API Keys" = @(
        "sk-[a-zA-Z0-9]{32,}",
        "pk_[a-zA-Z0-9]{32,}",
        "[a-zA-Z0-9]{32,}"
    )
    "Passwords" = @(
        "password\s*[:=]\s*['""][^'""]+['""]",
        "passwd\s*[:=]\s*['""][^'""]+['""]",
        "pwd\s*[:=]\s*['""][^'""]+['""]"
    )
    "Tokens" = @(
        "token\s*[:=]\s*['""][^'""]+['""]",
        "access_token\s*[:=]\s*['""][^'""]+['""]",
        "secret\s*[:=]\s*['""][^'""]+['""]"
    )
    "AWS Keys" = @(
        "AKIA[0-9A-Z]{16}",
        "[0-9a-zA-Z/+]{40}"
    )
}

foreach ($file in $files) {
    try {
        $content = Get-Content $file.FullName -Raw -ErrorAction SilentlyContinue
        if (-not $content) { continue }
        
        foreach ($category in $patterns.Keys) {
            foreach ($pattern in $patterns[$category]) {
                if ($content -match $pattern) {
                    $matches = [regex]::Matches($content, $pattern)
                    foreach ($match in $matches) {
                        $lineNum = ($content.Substring(0, $match.Index) -split "`n").Count
                        $line = ($content -split "`n")[$lineNum - 1]
                        
                        $issue = [PSCustomObject]@{
                            File = $file.FullName
                            Category = $category
                            Pattern = $pattern
                            Line = $lineNum
                            Content = $line.Trim()
                            Match = $match.Value
                        }
                        $issues += $issue
                    }
                }
            }
        }
    }
    catch {
        if ($Verbose) {
            Write-Warning "Could not read file: $($file.FullName)"
        }
    }
}

# Report findings
if ($issues.Count -eq 0) {
    Write-Host "✅ No security issues found!" -ForegroundColor Green
} else {
    Write-Host "❌ Found $($issues.Count) potential security issues:" -ForegroundColor Red
    Write-Host ""
    
    foreach ($issue in $issues) {
        Write-Host "File: $($issue.File)" -ForegroundColor Yellow
        Write-Host "Category: $($issue.Category)" -ForegroundColor Cyan
        Write-Host "Line: $($issue.Line)" -ForegroundColor White
        Write-Host "Content: $($issue.Content)" -ForegroundColor Gray
        Write-Host "Match: $($issue.Match)" -ForegroundColor Red
        Write-Host "---"
    }
    
    if ($Fix) {
        Write-Host "🔧 Attempting to fix issues..." -ForegroundColor Yellow
        # Add fix logic here if needed
    }
}

Write-Host "`n📋 Summary:" -ForegroundColor Green
Write-Host "Files scanned: $($files.Count)" -ForegroundColor White
Write-Host "Issues found: $($issues.Count)" -ForegroundColor White

if ($issues.Count -gt 0) {
    Write-Host "`n💡 Recommendations:" -ForegroundColor Yellow
    Write-Host "1. Use environment variables for all secrets" -ForegroundColor White
    Write-Host "2. Add problematic files to .gitignore" -ForegroundColor White
    Write-Host "3. Use AWS Secrets Manager or similar for production" -ForegroundColor White
    Write-Host "4. Run this script before each commit" -ForegroundColor White
}
