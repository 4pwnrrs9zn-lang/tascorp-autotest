#!/bin/zsh
# Собирает тестовую камеру для iOS Simulator (arm64): tools/ios_test_camera/TasTestCamera.dylib
set -euo pipefail
cd "$(dirname "$0")"
export DEVELOPER_DIR="${DEVELOPER_DIR:-/Applications/Xcode.app/Contents/Developer}"
SDK=$(xcrun --sdk iphonesimulator --show-sdk-path)
xcrun clang -arch arm64 -isysroot "$SDK" -mios-simulator-version-min=15.0 \
  -dynamiclib -fobjc-arc -framework UIKit -framework Foundation \
  -o TasTestCamera.dylib TasTestCamera.m
codesign -f -s - TasTestCamera.dylib
echo "Готово: $(pwd)/TasTestCamera.dylib"
