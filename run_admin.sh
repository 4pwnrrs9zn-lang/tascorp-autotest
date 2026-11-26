#!/bin/zsh
# Запуск локальной админки автотестов: http://127.0.0.1:5050
cd "$(dirname "$0")"
export ANDROID_HOME="${ANDROID_HOME:-$HOME/Library/Android/sdk}"
export JAVA_HOME="${JAVA_HOME:-$(/usr/libexec/java_home)}"
# node из Homebrew (21.7.2) падает с dyld после brew-обновления icu4c 74→78 (24.10.2026),
# поэтому Appium запускается на node v20.12 из официального установщика (/usr/local/bin)
export PATH="/usr/local/bin:$PATH"

if ! curl -s http://127.0.0.1:4723/status >/dev/null; then
  echo "Appium не запущен — запускаю в фоне (лог: reports/appium.log)"
  mkdir -p reports
  appium > reports/appium.log 2>&1 &
fi

# iOS — отдельный Appium (порт 4724, драйвер xcuitest в ~/.appium-ios), см. ios/README.md
if [[ -d "$HOME/.appium-ios" ]] && ! curl -s http://127.0.0.1:4724/status >/dev/null; then
  echo "Appium для iOS не запущен — запускаю в фоне (лог: reports/appium-ios.log)"
  mkdir -p reports
  ios/scripts/appium.sh > reports/appium-ios.log 2>&1 &
fi

.venv/bin/python admin/server.py
