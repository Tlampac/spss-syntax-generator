# SPSS Syntax Generator

Automatické generování SPSS syntax z dat (.sav) a dotazníku (.docx).

## 📦 Struktura projektu

```
├── backend_app.py      # Flask API backend
├── requirements.txt    # Python závislosti
├── render.yaml         # Render.com konfigurace
├── runtime.txt         # Python verze
└── README.md          # Tento soubor
```

## 🚀 Deployment na Render.com

### Předpoklady
- GitHub účet
- Render.com účet (zdarma)

### Postup

1. **Push do GitHubu:**
   ```bash
   git add .
   git commit -m "Fix: Updated configuration"
   git push origin main
   ```

2. **Nasazení na Render:**
   - Jdi na https://render.com
   - Klikni "New +" → "Web Service"
   - Připoj GitHub repository
   - Render automaticky detekuje `render.yaml`
   - Klikni "Create Web Service"
   - Počkej 5-10 minut na build

3. **Ověření:**
   - Otevři `https://TVOJE-URL.onrender.com/api/health`
   - Měl bys vidět: `{"status":"ok","version":"2.0.4-fixed"}`

## 🔧 Lokální vývoj

```bash
# Instalace závislostí
pip install -r requirements.txt

# Spuštění serveru
python backend_app.py

# Server běží na http://localhost:5000
```

## 📋 API Endpoints

### Health Check
```
GET /api/health
Response: {"status": "ok", "version": "2.0.4-fixed"}
```

### Generování Syntax
```
POST /api/generate
Content-Type: multipart/form-data
Files: 
  - sav_file: .sav soubor
  - docx_file: .docx dotazník
Response: .sps soubor ke stažení
```

## ✅ Hlavní změny v této verzi

1. **Explicitní port binding** - `--bind 0.0.0.0:$PORT`
2. **Lepší error handling** - detailní logování
3. **UTF-8 encoding** - kompatibilita na Linuxu
4. **Health check path** - pro Render monitoring
5. **Timeout zvýšen** - 120s pro větší soubory

## 🐛 Troubleshooting

**Problem: Application Error**
- Zkontroluj logy na Render Dashboard
- Ujisti se, že `render.yaml` je v root složce

**Problem: "Failed to fetch"**
- Zkontroluj URL v frontend `index.html`
- Zkontroluj CORS nastavení

**Problem: Timeout**
- Zvyš `--timeout` v `render.yaml`
- Zkontroluj velikost nahrávaných souborů

## 📞 Podpora

Pro problémy kontaktuj: Perfect Crowd s.r.o.
