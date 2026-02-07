@echo off
REM 带代理部署 Worker（CMD，Windows 通用）
REM 用法：在 worker 目录下 deploy-with-proxy.cmd

set HTTP_PROXY=http://127.0.0.1:7897
set HTTPS_PROXY=http://127.0.0.1:7897
call npx wrangler deploy
