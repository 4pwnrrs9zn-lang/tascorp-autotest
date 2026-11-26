#!/bin/bash
# Ставит тестовую камеру на эмулятор системным приложением (/system/app).
#
# С Android 11 на intent «сделать снимок» отвечают только системные камеры — обычная
# установка (adb install) не сработает. Для записи в /system эмулятор должен быть
# запущен с -writable-system (так его запускает scripts/start_all.sh) и без Play Store
# (образ google_apis — там есть adb root). Повторный запуск ничего не ломает.
set -euo pipefail
cd "$(dirname "$0")"
ADB="${ANDROID_HOME:-$HOME/Library/Android/sdk}/platform-tools/adb"
[ -f TasTestCamera.apk ] || ./build.sh

wait_boot() {
  "$ADB" wait-for-device
  until "$ADB" shell getprop sys.boot_completed 2>/dev/null | grep -q 1; do sleep 3; done
}

"$ADB" root >/dev/null; sleep 3
if "$ADB" remount 2>&1 | grep -q "reboot"; then   # первый раз — включает overlayfs
  "$ADB" reboot; wait_boot; "$ADB" root >/dev/null; sleep 3; "$ADB" remount
fi
"$ADB" uninstall kz.tascorp.testcamera >/dev/null 2>&1 || true   # обычная установка мешает системной
"$ADB" shell mkdir -p /system/app/TasTestCamera
"$ADB" push TasTestCamera.apk /system/app/TasTestCamera/TasTestCamera.apk
"$ADB" shell chmod 644 /system/app/TasTestCamera/TasTestCamera.apk
"$ADB" reboot; wait_boot
"$ADB" unroot >/dev/null 2>&1 || true
"$ADB" shell pm list packages -s | grep -q kz.tascorp.testcamera && echo "Тестовая камера установлена"
