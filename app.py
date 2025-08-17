import os
import re
import smtplib
import traceback
from email.message import EmailMessage
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st
from streamlit import column_config as cc

# ---------- Render-friendly server settings ----------
st.set_page_config(page_title="Inscripció d'equips de voleibol", page_icon="🏐", layout="wide")

# Base dir is the directory where this app.py lives
BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

st.title("🏐 Inscripció d'equips de voleibol")

with st.sidebar:
    st.header("ℹ️ Informació de l'equip")
    team_name = st.text_input("Nom de l'equip*", placeholder="Ex.: Club Vòlei Girona")
    sex = st.selectbox("Sexe*", ["Masculí", "Femení"])
    category = st.selectbox(
        "Categoria*",
        ["SM", "Lliga Hiberdrola", "SM2", "SF2", "1a Nacional"]
    )
    st.caption("(* camps obligatoris)")

    st.markdown("---")
    st.header("✉️ Enviament per correu (opcional)")
    send_email = st.checkbox("Enviar correu en desar")
    notif_to = st.text_input("Enviar a (correu)", placeholder="coordinacio@club.cat")

    smtp_server = st.text_input(
        "SMTP server",
        value=os.environ.get("SMTP_SERVER", "smtp.gmail.com")
    )
    smtp_port = st.number_input(
        "Port",
        value=int(os.environ.get("SMTP_PORT", "587")),
        step=1
    )
    smtp_user = st.text_input(
        "SMTP usuari",
        value=os.environ.get("SMTP_USER", ""),
        placeholder="elteuusuari@gmail.com"
    )
    smtp_pass = st.text_input(
        "SMTP contrasenya/app password",
        value=os.environ.get("SMTP_PASS", ""),
        type="password"
    )
    use_tls = st.checkbox("Usa TLS", value=True)

    st.markdown("---")
    st.header("⚙️ Opcions d'exportació")
    export_xlsx = st.checkbox("Exporta a Excel (.xlsx)", value=True)
    export_csv = st.checkbox("Exporta a CSV (jugadors i staff)", value=True)

# ---------- Jugadors ----------
st.markdown("### 👥 Jugadors")

PLAYER_POSITIONS = ["Col.locador", "Central", "Punta", "Oposat", "Lliure"]
playe
