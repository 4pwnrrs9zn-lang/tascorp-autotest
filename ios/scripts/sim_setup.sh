#!/bin/zsh
# Готовит iOS Simulator для автотестов (один раз; повторный запуск ничего не ломает).
#
# Нужно: Xcode в /Applications и runtime iOS 17.2 (Xcode 15.2 — максимум для macOS 13).
# Runtime через xcodebuild -downloadPlatform в сети компании обрывается — надёжнее скачать
# iOS_17.2_Simulator_Runtime.dmg в браузере (developer.apple.com/download/all, вход по Apple ID):
#   xcrun simctl runtime add ~/Downloads/iOS_17.2_Simulator_Runtime.dmg
set -euo pipefail
export DEVELOPER_DIR="${DEVELOPER_DIR:-/Applications/Xcode.app/Contents/Developer}"
NAME="${IOS_DEVICE_NAME:-Autotest iPhone 15}"
RUNTIME="com.apple.CoreSimulator.SimRuntime.iOS-17-2"

xcrun simctl list runtimes | grep -q "iOS 17.2" || { echo "Нет runtime iOS 17.2 — см. комментарий в начале скрипта"; exit 1; }
if ! xcrun simctl list devices available | grep -q "$NAME ("; then
  xcrun simctl create "$NAME" com.apple.CoreSimulator.SimDeviceType.iPhone-15 "$RUNTIME"
fi
xcrun simctl boot "$NAME" 2>/dev/null || true
xcrun simctl bootstatus "$NAME" -b >/dev/null
# Только английская раскладка: с русской XCUITest вводил в поле пароля половину символов
xcrun simctl spawn "$NAME" defaults write .GlobalPreferences AppleKeyboards -array "en_US@sw=QWERTY;hw=Automatic"
xcrun simctl spawn "$NAME" defaults write com.apple.Preferences KeyboardAutocorrection -bool NO
xcrun simctl spawn "$NAME" defaults write com.apple.Preferences KeyboardPrediction -bool NO
echo "Simulator «$NAME» готов"
