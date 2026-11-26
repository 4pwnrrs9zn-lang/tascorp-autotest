#!/bin/zsh
# Проверка стабильности: гоняет весь набор N раз подряд (по умолчанию 7),
# останавливается на первом падении. Логи и скриншоты — в reports/stability/<время>/.
#   ./scripts/stability.sh        — 7 прогонов
#   ./scripts/stability.sh 3      — 3 прогона
cd "$(dirname "$0")/.."
N=${1:-7}
ADB="${ANDROID_HOME:-$HOME/Library/Android/sdk}/platform-tools/adb"
OUT="reports/stability/$(date +%Y%m%d-%H%M%S)"
mkdir -p "$OUT"
for i in $(seq 1 $N); do
  rm -rf screenshots
  # Окружение: эмулятор отвечает за 15 с, Appium готов — иначе это не падение теста
  if ! perl -e 'alarm 15; exec @ARGV' "$ADB" shell echo ok >/dev/null 2>&1; then
    echo "run $i: ENV FAIL — эмулятор не отвечает" | tee -a "$OUT/summary.txt"; exit 2
  fi
  if ! curl -s -m 5 http://127.0.0.1:4723/status | grep -q '"ready":true'; then
    echo "run $i: ENV FAIL — Appium не готов" | tee -a "$OUT/summary.txt"; exit 2
  fi
  .venv/bin/pytest -q -p no:cacheprovider --durations=0 > "$OUT/run_$i.log" 2>&1
  RC=$?
  echo "run $i: exit=$RC $(tail -1 "$OUT/run_$i.log")" | tee -a "$OUT/summary.txt"
  if [ $RC -ne 0 ]; then
    [ -d screenshots ] && cp -r screenshots "$OUT/screenshots_run_$i"
    echo "STOP at run $i" | tee -a "$OUT/summary.txt"; exit 1
  fi
done
echo "ALL $N GREEN" | tee -a "$OUT/summary.txt"
