$ErrorActionPreference = 'Stop'

$consoleTarget = '.\src\qwenpaw\console'
$distSource = '.\console\dist'

Write-Host '1/4 构建 console...'
npm --prefix console run build

Write-Host '2/4 清理旧的 console 产物...'
if (Test-Path -LiteralPath $consoleTarget) {
	    Remove-Item -LiteralPath $consoleTarget -Recurse -Force
}

Write-Host '3/4 复制新的构建产物...'
New-Item -ItemType Directory -Path $consoleTarget -Force | Out-Null
Get-ChildItem -LiteralPath $distSource -Force | Copy-Item -Destination $consoleTarget -Recurse -Force

Write-Host '4/4 启动后端调试...'
python .\scripts\start_backend_debug.py
