# Camera Management Script
# ========================
# PowerShell wrapper for the Python camera manager

param(
    [Parameter(Mandatory=$true)]
    [string]$Command,
    
    [Parameter(ValueFromRemainingArguments=$true)]
    [string[]]$Arguments
)

$scriptPath = Join-Path $PSScriptRoot "camera-manager.py"

# Run the Python script
python $scriptPath $Command @Arguments
