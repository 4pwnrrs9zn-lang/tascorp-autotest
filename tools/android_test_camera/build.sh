#!/bin/bash
# Собирает тестовую камеру для Android-эмулятора: tools/android_test_camera/TasTestCamera.apk
# Нужны только Android SDK (build-tools, platforms/android-34) и JDK — без Gradle.
set -euo pipefail
cd "$(dirname "$0")"
SDK="${ANDROID_HOME:-$HOME/Library/Android/sdk}"
BT="$SDK/build-tools/$(ls "$SDK/build-tools" | sort -V | tail -1)"
JAR="$SDK/platforms/android-34/android.jar"
export JAVA_HOME="${JAVA_HOME:-$(/usr/libexec/java_home)}"
OUT=$(mktemp -d); trap 'rm -rf "$OUT"' EXIT

"$JAVA_HOME/bin/javac" -source 8 -target 8 -bootclasspath "$JAR" -encoding UTF-8 -nowarn \
  -d "$OUT/classes" src/kz/tascorp/testcamera/*.java 2>&1 | grep -v "warning: \[options\]" || true
"$BT/d8" --min-api 28 --lib "$JAR" --output "$OUT" $(find "$OUT/classes" -name '*.class')
"$BT/aapt2" link --manifest AndroidManifest.xml -I "$JAR" -o "$OUT/base.apk"
(cd "$OUT" && zip -q base.apk classes.dex)
"$BT/zipalign" -f 4 "$OUT/base.apk" "$OUT/aligned.apk"
"$BT/apksigner" sign --ks "$HOME/.android/debug.keystore" --ks-pass pass:android \
  --out TasTestCamera.apk "$OUT/aligned.apk"
echo "Готово: $(pwd)/TasTestCamera.apk"
