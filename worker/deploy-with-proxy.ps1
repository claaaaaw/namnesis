# 带代理部署 Worker（PowerShell 5.1 兼容，无 &&）
# 用法：在 worker 目录下 .\deploy-with-proxy.ps1  或  powershell -File deploy-with-proxy.ps1

$env:HTTP_PROXY  = 'http://127.0.0.1:7897'
$env:HTTPS_PROXY = 'http://127.0.0.1:7897'
npx wrangler deploy
