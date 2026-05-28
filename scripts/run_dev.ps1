Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

uvicorn app.main:app --reload

