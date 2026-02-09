# SPSS Syntax Generator - Production Ready

Automatické generování SPSS syntax z dat (.sav) a dotazníku (.docx).

## ✨ Co je nového v této verzi

**Verze 2.0.5-production-ready** - Opraveno všech 5 kritických problémů:

1. ✅ **Render deployment** - správný startCommand
2. ✅ **CORS bezpečnost** - pouze autorizované domény
3. ✅ **Auto-detekce prostředí** - localhost vs produkce
4. ✅ **Timeout handling** - validace, varování, limity
5. ✅ **Debug mode** - vypnut na produkci

---

## 📦 Struktura projektu

```
├── backend_app.py           # Flask API backend
├── index.html              # Frontend (single page)
├── requirements.txt        # Python závislosti
├── render.yaml            # Render.com konfigurace
├── runtime.txt            # Python 3.11.10
├── README.md              # Tento soubor
└── CHANGELOG_v2.0.5.md    # Detailní changelog
```

---

## 🚀 Deployment na Render.com

### Rychlý start:

1. **Push na GitHub:**
   ```bash
   git add .
   git commit -m "Production ready v2.0.5"
   git push origin main
   ```

2. **Render.com:**
   - Dashboard → "Manual Deploy" → "Deploy latest commit"
   - Nebo počkej na auto-deploy (~5 min)

3. **Ověření:**
   ```
   https://spss-syntax-generator.onrender.com/api/health
   ```
   Očekávaná odpověď:
   ```json
   {"status":"ok","version":"2.0.5-production-ready"}
   ```

---

## 🔧 Lokální vývoj

### Backend:

```bash
# Instalace závislostí
pip install -r requirements.txt

# Spuštění s debug modem
FLASK_ENV=development python backend_app.py

# Spuštění bez debug (jako produkce)
python backend_app.py

# Server běží na http://localhost:5000
```

### Frontend:

```bash
# Jednoduchý HTTP server
python -m http.server 8000

# Otevři http://localhost:8000
```

**Nebo** otevři `index.html` přímo v prohlížeči - automaticky detekuje localhost.

---

## 🌐 Frontend deployment (Netlify)

### Nahrání na Netlify:

1. **Drag & drop:**
   - Jdi na https://netlify.com
   - Přetáhni `index.html` do Netlify
   - Automaticky dostaneš URL

2. **Vlastní doména:**
   - Site settings → Change site name
   - Doporučeno: `syntaxgenerator` nebo podobné

**Aplikace automaticky:**
- ✅ Detekuje produkční vs lokální prostředí
- ✅ Volá správnou API URL
- ✅ Funguje okamžitě

---

## 📋 API Dokumentace

### Health Check
```http
GET /api/health

Response 200:
{
  "status": "ok",
  "version": "2.0.5-production-ready"
}
```

### Generování Syntax
```http
POST /api/generate
Content-Type: multipart/form-data

Files:
  - sav_file: .sav soubor (max 10MB)
  - docx_file: .docx dotazník

Response 200:
  - Content-Type: text/plain
  - Content-Disposition: attachment; filename="generated_syntax_XXX.sps"
  - Body: SPSS syntax soubor

Response 400:
{
  "error": "Chybí soubory"
}

Response 500:
{
  "error": "Chybová zpráva",
  "detail": "Traceback..."
}
```

---

## ⚙️ Konfigurace

### CORS (backend_app.py)

```python
CORS(app, resources={
    r"/api/*": {
        "origins": [
            "https://syntaxgenerator.netlify.app",  # Produkce
            "http://localhost:8000",                # Lokální dev
            "http://127.0.0.1:8000"
        ]
    }
})
```

**Přidání další domény:**
```python
"origins": [
    "https://syntaxgenerator.netlify.app",
    "https://tvoje-nova-domena.com",  # Přidat zde
    ...
]
```

### API URL (index.html)

```javascript
const API_URL = window.location.hostname === 'localhost' || 
                window.location.hostname === '127.0.0.1'
    ? 'http://localhost:5000/api/generate'      // Lokální
    : 'https://spss-syntax-generator.onrender.com/api/generate';  // Produkce
```

---

## 🛡️ Bezpečnostní features

1. **CORS omezení** - pouze autorizované domény
2. **Debug mode OFF** - na produkci vypnutý
3. **Validace velikosti** - max 10MB pro .sav soubory
4. **Timeout handling** - varování po 25s
5. **Error logging** - traceback pouze v logu, ne v odpovědi

---

## 📊 Limity (Render Free tier)

| Limit | Hodnota |
|-------|---------|
| Request timeout | 30 sekund |
| Max velikost .sav | ~10MB (doporučeno) |
| Cold start | ~30s při první návštěvě |
| Uptime | 24/7 (může jít do sleep po neaktivitě) |

**Upgrade na Render Starter ($7/měsíc):**
- ✅ Unlimited timeout
- ✅ Žádný cold start
- ✅ Lepší výkon

---

## 🐛 Troubleshooting

### "Application Error" na Renderu
**Řešení:**
1. Zkontroluj logy: Render Dashboard → Logs
2. Počkaj 2 minuty (cold start)
3. Zkontroluj že `render.yaml` má správný `startCommand`

### "Failed to fetch" v konzoli
**Řešení:**
1. Zkontroluj že backend běží: `/api/health`
2. Zkontroluj CORS nastavení
3. Zkontroluj API URL v `index.html`

### Timeout při zpracování
**Příčina:** Soubor je moc velký nebo složitý
**Řešení:**
1. Zkus menší .sav soubor
2. Zvažz Render Paid (bez timeoutu)
3. Implementuj async processing (advanced)

### "Soubor příliš velký"
**Příčina:** .sav soubor > 10MB
**Řešení:**
1. Zkus filtrovat data v SPSS před exportem
2. Export jen potřebné proměnné
3. Nebo zvyš limit v kódu (ale pozor na timeout)

---

## 🔄 Lokální testování před deployem

```bash
# 1. Spusť backend
FLASK_ENV=development python backend_app.py

# 2. Otevři frontend
# V prohlížeči: file:///cesta/k/index.html
# Nebo: python -m http.server 8000

# 3. Test upload
# - Nahraj malý .sav a .docx
# - Sleduj console v prohlížeči (F12)
# - Sleduj terminal kde běží backend
```

---

## 📞 Podpora

**Issues:** GitHub Issues
**Email:** Perfect Crowd s.r.o.

---

## 📜 Licence

© 2026 Perfect Crowd s.r.o.
