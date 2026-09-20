# Test Report — yetkin360-faz0-temel-kurulum

## Backend
- `pytest -q` (DATABASE_URL env ile) → `1 passed, 1 warning in 1.11s` (`tests/test_health.py::test_health_returns_ok`)
- `ruff check .` → `All checks passed!`
- `mypy app` → önce 1 hata (`Settings` çağrısında `database_url` eksik argüman uyarısı, pydantic-settings'in env'den okuduğunu mypy bilmiyor) → `# type: ignore[call-arg]` eklendi → `Success: no issues found in 4 source files`

## Frontend
- `npm install` → ilk kurulumda `next@15.1.3` + `eslint@9.17.0` sürümlerinde kritik/yüksek CVE tespit edildi (npm audit) → `next@15.5.25`, `eslint@9.39.5`'e yükseltildi → kalan: 1 orta + 1 yüksek (Next'in kendi bağımlı olduğu `postcss`, düzeltmesi Next 16 major sürüm gerektiriyor, bilinçli ertelendi)
- `npx eslint app components` → temiz, hata yok
- `npx tsc --noEmit` → hata yok
- `npm run build` → başarılı, `Compiled successfully`, statik sayfalar üretildi

## Doğrulanamayan
- `docker compose up -d` — bu makinede Docker Desktop daemon'ı çalışmıyor (`failed to connect to the docker API`). YAML sözdizimsel olarak geçerli, gerçek ayağa kalkışı test edilemedi.
