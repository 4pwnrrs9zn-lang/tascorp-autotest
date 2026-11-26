#!/bin/zsh
# Appium для iOS-сборок: порт 4724, драйвер xcuitest в отдельном APPIUM_HOME.
#
# Общий ~/.appium (там uiautomator2 для Android) частично принадлежит root, и npm не может
# доставить туда xcuitest без sudo — поэтому iOS живёт в ~/.appium-ios и не трогает Android.
# Первый раз:
#   APPIUM_HOME=~/.appium-ios npm_config_cache=/tmp/npm-ios appium driver install xcuitest@7.13.0
# (7.13.0 — последняя версия, совместимая с установленным Appium 2.5.2)
cd "$(dirname "$0")/.."  # ios/
export APPIUM_HOME="$HOME/.appium-ios"
# node из Homebrew (21.7.2) падает с dyld после brew-обновления icu4c 74→78 (24.10.2026),
# поэтому Appium запускается на node v20.12 из официального установщика (/usr/local/bin)
export PATH="/usr/local/bin:$PATH"
export DEVELOPER_DIR="${DEVELOPER_DIR:-/Applications/Xcode.app/Contents/Developer}"
exec appium --port 4724 --log-timestamp "$@"
