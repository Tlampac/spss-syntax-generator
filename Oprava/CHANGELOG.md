# CHANGELOG - Opravy pro Render Deployment

## Verze 2.0.4-fixed (6.2.2026)

### 🔧 Hlavní opravy

1. **render.yaml**
   - ✅ Přidán explicitní port binding: `--bind 0.0.0.0:$PORT`
   - ✅ Zvýšen timeout na 120s (pro větší soubory)
   - ✅ Přidán health check path
   - ✅ Nastaveno 2 workers pro lepší výkon
   - ✅ Vylepšen build command s upgrade pip

2. **backend_app.py**
   - ✅ Změněno kódování z `cp1250` na `utf-8-sig` (Linux kompatibilita)
   - ✅ Přidáno detailní logování pro debugging
   - ✅ Vylepšen error handling s traceback
   - ✅ Aktualizována verze API na 2.0.4-fixed

3. **runtime.txt**
   - ✅ Nový soubor pro explicitní specifikaci Python 3.11.10

4. **.gitignore**
   - ✅ Nový soubor pro čistší Git repository

5. **README.md**
   - ✅ Kompletní deployment instrukce
   - ✅ Troubleshooting sekce
   - ✅ API dokumentace

### 📋 Srovnání změn

#### PŘED (nefunkční):
```yaml
startCommand: gunicorn backend_app:app
envVars:
  - key: PYTHON_VERSION
    value: 3.11.0
```

#### PO (funkční):
```yaml
startCommand: gunicorn backend_app:app --bind 0.0.0.0:$PORT --timeout 120 --workers 2
healthCheckPath: /api/health
```

### 🎯 Co to řeší?

1. **Port binding issue** - Render potřebuje explicitně `--bind 0.0.0.0:$PORT`
2. **Timeout problémy** - Zvýšen na 120s pro větší soubory
3. **Encoding problémy** - UTF-8 místo cp1250 pro Linux
4. **Monitoring** - Health check endpoint pro Render

### 📝 Deployment checklist

- [ ] Nahrát všechny soubory na GitHub
- [ ] Zkontrolovat že `render.yaml` je v root
- [ ] Na Render: New → Web Service → Connect GitHub
- [ ] Počkat na build (5-10 min)
- [ ] Otevřít `/api/health` endpoint
- [ ] Měl by vrátit: `{"status":"ok","version":"2.0.4-fixed"}`

### 🐛 Known issues

- Při prvním spuštění může být cold start ~30s
- Velké .sav soubory (>50MB) mohou trvat déle
