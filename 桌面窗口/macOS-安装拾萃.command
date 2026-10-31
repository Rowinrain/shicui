#!/bin/bash
# 在“应用程序”里创建“拾萃”：用 Chrome / Edge 的独立窗口打开 拾萃.html（没有标签栏和地址栏）。
here="$(cd "$(dirname "$0")" && pwd)"

fail() { echo; echo "$1"; echo; osascript -e "display alert \"拾萃\" message \"$1\"" >/dev/null 2>&1; exit 1; }

# 1. 找到 拾萃.html（本文件夹或上一级文件夹）
html=""
for d in "$here" "$(dirname "$here")"; do
  if [ -f "$d/拾萃.html" ]; then html="$d/拾萃.html"; break; fi
done
[ -n "$html" ] || fail "没有找到 拾萃.html。请把“桌面窗口”文件夹放在 拾萃.html 旁边，再运行一次。"

# 2. 找到浏览器：优先 Chrome，其次 Edge
browser=""
for b in "Google Chrome" "Microsoft Edge"; do
  if open -Ra "$b" >/dev/null 2>&1; then browser="$b"; break; fi
done
[ -n "$browser" ] || fail "没有找到 Chrome 或 Edge 浏览器，请先安装其中一个。"

# 3. 文件路径 → file:// 地址
urlencode() {
  local LC_ALL=C s="$1" out="" c i
  for ((i = 0; i < ${#s}; i++)); do
    c="${s:i:1}"
    case "$c" in
      [a-zA-Z0-9/._~-]) out+="$c" ;;
      *) out+=$(printf '%%%02X' "'$c") ;;
    esac
  done
  printf '%s' "$out"
}
url="file://$(urlencode "$html")"

# 4. 生成 ~/Applications/拾萃.app
app="$HOME/Applications/拾萃.app"
mkdir -p "$HOME/Applications"
rm -rf "$app"
mkdir -p "$app/Contents/MacOS" "$app/Contents/Resources"
[ -f "$here/拾萃.icns" ] && cp "$here/拾萃.icns" "$app/Contents/Resources/AppIcon.icns"

cat > "$app/Contents/Info.plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>CFBundleName</key><string>拾萃</string>
  <key>CFBundleDisplayName</key><string>拾萃</string>
  <key>CFBundleIdentifier</key><string>local.shicui.launcher</string>
  <key>CFBundleExecutable</key><string>launch</string>
  <key>CFBundleIconFile</key><string>AppIcon</string>
  <key>CFBundlePackageType</key><string>APPL</string>
  <key>CFBundleVersion</key><string>1</string>
  <key>LSUIElement</key><true/>
</dict>
</plist>
PLIST

{
  echo '#!/bin/bash'
  printf 'HTML=%q\n' "$html"
  printf 'URL=%q\n' "$url"
  printf 'BROWSER=%q\n' "$browser"
  cat <<'LAUNCH'
if [ ! -f "$HTML" ]; then
  osascript -e 'display alert "找不到 拾萃.html" message "拾萃.html 可能被移动或删除了。请在它旁边的“桌面窗口”文件夹里重新运行“macOS-安装拾萃”。"'
  exit 1
fi
exec open -na "$BROWSER" --args --app="$URL"
LAUNCH
} > "$app/Contents/MacOS/launch"
chmod +x "$app/Contents/MacOS/launch"
touch "$app"

echo
echo "已安装：$app"
echo "程序文件：$html"
echo "使用浏览器：$browser"
echo
echo "可以在“启动台”或“应用程序”里打开“拾萃”，也可以把它拖到程序坞。"
echo "注意：之后不要移动或删除 拾萃.html；如果移动了，重新运行一次本程序即可。"
open -R "$app"
