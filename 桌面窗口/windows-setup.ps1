# 在桌面和开始菜单创建“拾萃”快捷方式：用 Chrome / Edge 的独立窗口打开 拾萃.html（没有标签栏和地址栏）。
$ErrorActionPreference = 'Stop'
$here = Split-Path -Parent $MyInvocation.MyCommand.Path

function Fail($msg) { Write-Host ''; Write-Host $msg -ForegroundColor Red; Write-Host ''; exit 1 }

# 1. 找到 拾萃.html（本文件夹或上一级文件夹）
$html = @((Join-Path $here '拾萃.html'), (Join-Path (Split-Path $here -Parent) '拾萃.html')) |
  Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
if (-not $html) { Fail '没有找到 拾萃.html。请把“桌面窗口”文件夹放在 拾萃.html 旁边，或把本文件夹里的文件和 拾萃.html 放在一起，再运行一次。' }
$html = (Resolve-Path -LiteralPath $html).Path

# 2. 找到浏览器：优先 Chrome，其次 Edge
$exe = @(
  "$env:ProgramFiles\Google\Chrome\Application\chrome.exe",
  "${env:ProgramFiles(x86)}\Google\Chrome\Application\chrome.exe",
  "$env:LOCALAPPDATA\Google\Chrome\Application\chrome.exe",
  "${env:ProgramFiles(x86)}\Microsoft\Edge\Application\msedge.exe",
  "$env:ProgramFiles\Microsoft\Edge\Application\msedge.exe"
) | Where-Object { $_ -and (Test-Path -LiteralPath $_) } | Select-Object -First 1
if (-not $exe) { Fail '没有找到 Chrome 或 Edge 浏览器，请先安装其中一个。' }

# 3. 创建快捷方式
$url  = ([System.Uri]$html).AbsoluteUri
$ico  = Join-Path $here '拾萃.ico'
$ws   = New-Object -ComObject WScript.Shell
$made = @()
foreach ($dir in @([Environment]::GetFolderPath('Desktop'), [Environment]::GetFolderPath('Programs'))) {
  if (-not $dir) { continue }
  $lnk = $ws.CreateShortcut((Join-Path $dir '拾萃.lnk'))
  $lnk.TargetPath       = $exe
  $lnk.Arguments        = "--app=`"$url`""
  $lnk.WorkingDirectory = Split-Path $html -Parent
  $lnk.Description      = '拾萃 · 高中生物好题本'
  if (Test-Path -LiteralPath $ico) { $lnk.IconLocation = "$ico,0" }
  $lnk.Save()
  $made += $dir
}

Write-Host ''
Write-Host '已创建快捷方式“拾萃”：' -ForegroundColor Green
$made | ForEach-Object { Write-Host "  $_" }
Write-Host ''
Write-Host "程序文件：$html"
Write-Host "使用浏览器：$exe"
Write-Host ''
Write-Host '双击桌面上的“拾萃”即可在独立窗口中打开。也可以在开始菜单里右键“拾萃”，固定到任务栏。'
Write-Host '注意：之后不要移动或删除 拾萃.html 和这个文件夹；如果移动了，重新运行一次本程序即可。'
