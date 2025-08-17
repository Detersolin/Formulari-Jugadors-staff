
# 🏐 Inscripció d'equips de voleibol — Eina Streamlit (VERSIÓ HARDENED)

Ajustos per desplegar a **Render**:
- Escriu a la carpeta `output/` relativa a `app.py` (no a `/tmp`).
- Mostra errors de forma controlada a la UI en lloc de trencar l'app.
- No usa `sendgrid`; l'enviament és amb `smtplib` (opcional).

## Desplegar a Render
- **Runtime**: Python 3.11
- **Build Command**:
```
pip install -r requirements.txt
```
- **Start Command**:
```
streamlit run app.py --server.port $PORT --server.address 0.0.0.0
```

## Local
```
pip install -r requirements.txt
streamlit run app.py
```
