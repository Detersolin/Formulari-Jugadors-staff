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
    smtp_server = st.text_input("SMTP server", value=os.environ.get("SMTP_SERVER","smtp.gmail.com"))
    smtp_port = st.number_input("Port", value=int(os.environ.get("SMTP_PORT","587")), step=1)
    smtp_user = st.text_input("SMTP usuari", placeholder=os.environ.get("SMTP_USER","elteuusuari@gmail.com"))
    smtp_pass = st.text_input("SMTP contrasenya/app password", type="password")
    use_tls = st.checkbox("Usa TLS", value=True)

    st.markdown("---")
    st.header("⚙️ Opcions d'exportació")
    export_xlsx = st.checkbox("Exporta a Excel (.xlsx)", value=True)
    export_csv = st.checkbox("Exporta a CSV (jugadors i staff)", value=True)

# ---------- Jugadors ----------
st.markdown("### 👥 Jugadors")

PLAYER_POSITIONS = ["Col.locador", "Central", "Punta", "Oposat", "Lliure"]
player_cols = ["Nom","Cognoms","Número dorsal","Nom del dorsal","Posició"]

if "players_df" not in st.session_state:
    st.session_state.players_df = pd.DataFrame([{c: "" for c in player_cols}])

players_df = st.data_editor(
    st.session_state.players_df,
    num_rows="dynamic",
    column_order=player_cols,
    column_config={
        "Nom": cc.TextColumn("Nom"),
        "Cognoms": cc.TextColumn("Cognoms"),
        "Número dorsal": cc.TextColumn("Número dorsal", help="Ex.: 7"),
        "Nom del dorsal": cc.TextColumn("Nom del dorsal"),
        "Posició": cc.SelectboxColumn("Posició", options=PLAYER_POSITIONS),
    },
    use_container_width=True,
    hide_index=True,
    key="players_editor"
)

# ---------- Staff ----------
st.markdown("### 🧑‍💼 Staff")

staff_cols = ["Nom","Cognoms","Funció"]

if "staff_df" not in st.session_state:
    st.session_state.staff_df = pd.DataFrame([{c: "" for c in staff_cols}])

staff_df = st.data_editor(
    st.session_state.staff_df,
    num_rows="dynamic",
    column_order=staff_cols,
    column_config={
        "Nom": cc.TextColumn("Nom"),
        "Cognoms": cc.TextColumn("Cognoms"),
        "Funció": cc.SelectboxColumn(
            "Funció",
            options=[
                "Entrenador principal",
                "Segon entrenador",
                "Preparador físic",
                "Fisioterapeuta",
                "Delegat",
                "Altres",
            ],
        ),
    },
    use_container_width=True,
    hide_index=True,
    key="staff_editor"
)

# ---------- Utilitats ----------
def slugify(text: str) -> str:
    text = text.strip().lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return re.sub(r"-+", "-", text).strip("-") or "equip"

def validate_team(team_name: str) -> bool:
    return bool(team_name and team_name.strip())

def clean_df(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    mask = ~(df.fillna("").apply(lambda r: "".join(map(str, r)).strip(), axis=1) == "")
    return df.loc[mask].reset_index(drop=True)

def export(team_name, sex, category, players_df, staff_df, export_xlsx=True, export_csv=True):
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    base = f"{ts}_{slugify(team_name)}"
    saved = []

    players_df = clean_df(players_df.copy())
    staff_df = clean_df(staff_df.copy())

    # Add team meta
    for df in (players_df, staff_df):
        if not df.empty:
            df.insert(0, "Equip", team_name)
            df.insert(1, "Sexe", sex)
            df.insert(2, "Categoria", category)

    # Excel
    if export_xlsx:
        try:
            xlsx_path = OUTPUT_DIR / f"{base}.xlsx"
            with pd.ExcelWriter(xlsx_path, engine="openpyxl") as writer:
                pd.DataFrame(
                    {"Equip":[team_name], "Sexe":[sex], "Categoria":[category]}
                ).to_excel(writer, sheet_name="Equip", index=False)
                (players_df if not players_df.empty else pd.DataFrame(
                    columns=["Equip","Sexe","Categoria", *player_cols]
                )).to_excel(writer, sheet_name="Jugadors", index=False)
                (staff_df if not staff_df.empty else pd.DataFrame(
                    columns=["Equip","Sexe","Categoria", *staff_cols]
                )).to_excel(writer, sheet_name="Staff", index=False)
            saved.append(str(xlsx_path))
        except Exception as e:
            st.error(f"Error exportant Excel: {e}")
            st.code(traceback.format_exc())

    # CSV
    if export_csv:
        try:
            if not players_df.empty:
                p_csv = OUTPUT_DIR / f"{base}_jugadors.csv"
                players_df.to_csv(p_csv, index=False)
                saved.append(str(p_csv))
            if not staff_df.empty:
                s_csv = OUTPUT_DIR / f"{base}_staff.csv"
                staff_df.to_csv(s_csv, index=False)
                saved.append(str(s_csv))
        except Exception as e:
            st.error(f"Error exportant CSV: {e}")
            st.code(traceback.format_exc())

    return saved

def send_notification(files, notif_to, smtp_server, smtp_port, smtp_user, smtp_pass, use_tls):
    if not notif_to:
        return False, "Sense adreça de correu."
    try:
        msg = EmailMessage()
        msg["Subject"] = "Nova inscripció d'equip de voleibol"
        msg["From"] = smtp_user or "noreply@example.com"
        msg["To"] = notif_to
        msg.set_content("S'ha registrat una nova inscripció d'equip. Adjuntes trobes les exportacions.")

        for f in files:
            try:
                with open(f, "rb") as fh:
                    data = fh.read()
                msg.add_attachment(
                    data,
                    maintype="application",
                    subtype="octet-stream",
                    filename=os.path.basename(f),
                )
            except Exception as e:
                st.warning(f"No s'ha pogut adjuntar {f}: {e}")

        if use_tls:
            server = smtplib.SMTP(smtp_server, int(smtp_port))
            server.starttls()
        else:
            server = smtplib.SMTP_SSL(smtp_server, int(smtp_port))
        if smtp_user and smtp_pass:
            server.login(smtp_user, smtp_pass)
        server.send_message(msg)
        server.quit()
        return True, "Correu enviat correctament."
    except Exception as e:
        return False, f"No s'ha pogut enviar el correu: {e}"

# ---------- Accions ----------
col1, col2 = st.columns([1,1])
with col1:
    save_btn = st.button("💾 Desa equip", type="primary", use_container_width=True)
with col2:
    reset_btn = st.button("🧹 Reinicia formulari (nou equip)", use_container_width=True)

# Plantilla Excel buida (3 pestanyes)
import io
template_buf = io.BytesIO()
with pd.ExcelWriter(template_buf, engine="openpyxl") as writer:
    pd.DataFrame(columns=["Equip","Sexe","Categoria"]).to_excel(writer, sheet_name="Equip", index=False)
    pd.DataFrame(columns=["Equip","Sexe","Categoria","Nom","Cognoms","Número dorsal","Nom del dorsal","Posició"]).to_excel(writer, sheet_name="Jugadors", index=False)
    pd.DataFrame(columns=["Equip","Sexe","Categoria","Nom","Cognoms","Funció"]).to_excel(writer, sheet_name="Staff", index=False)
template_buf.seek(0)
st.download_button(
    "⬇️ Descarrega plantilla Excel buida (3 pestanyes)",
    data=template_buf,
    file_name="plantilla_equip_voleibol.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)

if save_btn:
    if not validate_team(team_name):
        st.error("Cal indicar el **Nom de l'equip**.")
    else:
        try:
            saved_files = export(
                team_name, sex, category,
                players_df, staff_df,
                export_xlsx=export_xlsx, export_csv=export_csv
            )
            if saved_files:
                st.success("Dades desades correctament:")
                for f in saved_files:
                    st.write("• ", f)
                if send_email:
                    ok, msg = send_notification(
                        saved_files, notif_to,
                        smtp_server, smtp_port, smtp_user, smtp_pass, use_tls
                    )
                    if ok:
                        st.info(msg)
                    else:
                        st.warning(msg)
            else:
                st.warning("No s'ha desat cap fitxer (comprova que hi hagi dades).")
        except Exception as e:
            st.error(f"S'ha produït un error intern: {e}")
            st.code(traceback.format_exc())

if reset_btn:
    st.session_state.players_df = pd.DataFrame([{c: "" for c in player_cols}])
    st.session_state.staff_df = pd.DataFrame([{c: "" for c in staff_cols}])
    st.rerun()

st.caption("💡 Consell: desa un equip, (opcional) envia un correu i prem **Reinicia** per preparar un nou equip.")
