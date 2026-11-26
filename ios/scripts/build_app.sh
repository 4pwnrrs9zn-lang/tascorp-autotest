#!/bin/zsh
# Готовит iOS-сборку TasCorp KZ для запуска на iOS Simulator (Apple Silicon).
#
# Стенд раздаёт только Enterprise-IPA для реальных iPhone (arm64, платформа iphoneos):
# Simulator такой бинарник не ставит. Исходников нет, поэтому IPA перепаковывается:
# у всех Mach-O платформа в LC_BUILD_VERSION меняется на iOS Simulator (7), подпись
# Enterprise снимается и ставится ad-hoc. Архитектура та же (arm64) — на Intel Mac не работает.
#
#   ios/scripts/build_app.sh              # скачать актуальную сборку со стенда
#   ios/scripts/build_app.sh path/to.ipa  # перепаковать локальный IPA
# Результат: ios/apps/kz/TasCorp.app
set -euo pipefail
IPA_ARG="${1:+${1:A}}"  # путь к IPA — до cd, чтобы относительный путь не сломался
cd "$(dirname "$0")/.."  # ios/

MANIFEST_URL="https://tascorp-admincp.tascredit.kz/res/manifest_test.plist"
OUT_DIR="apps/kz"
export DEVELOPER_DIR="${DEVELOPER_DIR:-/Applications/Xcode.app/Contents/Developer}"

WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT

if [[ $# -ge 1 ]]; then
  cp "$IPA_ARG" "$WORK/app.ipa"
else
  curl -fsSL "$MANIFEST_URL" -o "$WORK/manifest.plist"
  IPA_URL=$(plutil -extract items.0.assets.0.url raw "$WORK/manifest.plist")
  echo "Скачиваю $IPA_URL"
  curl -fsSL "$IPA_URL" -o "$WORK/app.ipa"
fi

unzip -q "$WORK/app.ipa" -d "$WORK"
APP=$(ls -d "$WORK"/Payload/*.app)

rm -rf "$APP/_CodeSignature" "$APP/embedded.mobileprovision"
plutil -replace CFBundleSupportedPlatforms -json '["iPhoneSimulator"]' "$APP/Info.plist"

# Все Mach-O внутри бандла: сначала вложенные (фреймворки), основной бинарник — последним
MACHOS=()
while IFS= read -r f; do
  file -b "$f" | grep -q Mach-O && MACHOS+=("$f")
done < <(find "$APP" -type f -not -path "$APP/$(plutil -extract CFBundleExecutable raw "$APP/Info.plist")")
MACHOS+=("$APP/$(plutil -extract CFBundleExecutable raw "$APP/Info.plist")")

for f in "${MACHOS[@]}"; do
  minos=$(otool -l "$f" | awk '/LC_BUILD_VERSION/{b=1} b&&/minos/{print $2; exit}')
  sdk=$(otool -l "$f" | awk '/LC_BUILD_VERSION/{b=1} b&&/sdk/{print $2; exit}')
  xcrun vtool -arch arm64 -set-build-version 7 "${minos:-15.0}" "${sdk:-17.0}" -replace -output "$f" "$f"
done

for fw in "$APP"/Frameworks/*(N); do
  codesign -f -s - "$fw"
done
codesign -f -s - "$APP"

mkdir -p "$OUT_DIR"
rm -rf "$OUT_DIR/TasCorp.app"
cp -R "$APP" "$OUT_DIR/TasCorp.app"
echo "Готово: $OUT_DIR/TasCorp.app ($(plutil -extract CFBundleIdentifier raw "$APP/Info.plist")" \
     "$(plutil -extract CFBundleShortVersionString raw "$APP/Info.plist") ($(plutil -extract CFBundleVersion raw "$APP/Info.plist")))"
