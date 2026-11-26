#!/bin/bash
# Поднимает всё, что нужно для админки: эмулятор → Appium → admin/server.py.
# Запуск: ./scripts/start_all.sh
# Логи — в /tmp/tascorp-autotest-logs/. Админка после запуска: http://127.0.0.1:5050
set -e

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOGS=/tmp/tascorp-autotest-logs
mkdir -p "$LOGS"
ADB=~/Library/Android/sdk/platform-tools/adb
AVD=Autotest_API_34

echo "== Эмулятор =="
if ! "$ADB" devices | grep -q "device$"; then
  # DNS берём с Mac явно: сам эмулятор берёт их при старте и после смены сети на Mac
  # (Wi-Fi/VPN) перестаёт разрешать имена — вход падает на Firebase App Check
  DNS=$(scutil --dns | awk '/nameserver\[[0-9]+\]/{print $3}' | grep -E '^[0-9.]+$' | awk '!seen[$0]++' | head -4 | paste -sd, -)
  ~/Library/Android/sdk/emulator/emulator -avd "$AVD" -no-boot-anim -no-audio -gpu host -no-snapshot-save -writable-system \
    ${DNS:+-dns-server "$DNS"} \
    > "$LOGS/emulator.log" 2>&1 &
  disown
  echo "Запускаю $AVD, жду загрузки…"
  until "$ADB" shell getprop sys.boot_completed 2>/dev/null | grep -q 1; do sleep 3; done
  "$ADB" shell settings put global window_animation_scale 0
  "$ADB" shell settings put global transition_animation_scale 0
  "$ADB" shell settings put global animator_duration_scale 0
  "$ADB" shell settings put secure show_ime_with_hard_keyboard 0
  echo "Эмулятор загружен."
else
  echo "Эмулятор уже запущен."
fi

echo "== Appium =="
if ! curl -s --max-time 2 http://127.0.0.1:4723/status | grep -q '"ready":true'; then
  export ANDROID_HOME=~/Library/Android/sdk
  export JAVA_HOME=$(/usr/libexec/java_home)
  appium > "$LOGS/appium.log" 2>&1 &
  disown
  for i in $(seq 1 30); do
    curl -s --max-time 2 http://127.0.0.1:4723/status | grep -q '"ready":true' && break
    sleep 1
  done
  echo "Appium готов."
else
  echo "Appium уже запущен."
fi

echo "== Админка =="
if ! curl -s --max-time 2 http://127.0.0.1:5050/api/health >/dev/null 2>&1; then
  cd "$ROOT"
  .venv/bin/python admin/server.py > "$LOGS/admin.log" 2>&1 &
  disown
  sleep 2
  echo "Админка запущена."
else
  echo "Админка уже запущена."
fi

echo
echo "Готово: http://127.0.0.1:5050"
