#!/bin/zsh
cd "$(dirname "$0")" || exit 1
mkdir -p .data
if ! /usr/bin/curl --silent --fail --max-time 2 http://127.0.0.1:56615/api/status >/dev/null; then
  /usr/bin/nohup /usr/bin/python3 server.py --port 56615 >.data/server.log 2>&1 </dev/null &
  for attempt in {1..40}; do
    /usr/bin/curl --silent --fail --max-time 1 http://127.0.0.1:56615/api/status >/dev/null && break
    sleep 0.25
  done
fi
if /usr/bin/curl --silent --fail --max-time 2 http://127.0.0.1:56615/api/status >/dev/null; then
  /usr/bin/open http://127.0.0.1:56615/
else
  echo '本机服务未启动，请查看此目录 .data/server.log。'
  read '?按回车关闭。'
  exit 1
fi
