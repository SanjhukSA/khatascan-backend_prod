# Run this script from inside khatascan-backend_prod-main\
# Watches ONLY app\ so rapidocr .venv writes never trigger a reload

Set-Location $PSScriptRoot

.venv\Scripts\uvicorn.exe app.main:app `
  --reload `
  --reload-dir app `
  --reload-exclude "*.pyc" `
  --reload-exclude "*.pyo" `
  --port 8000 `
  --log-level info

