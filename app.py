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

# ---------- Config ----------
st.set_page_config(page_title="Informació equips streaming", page_icon="📺", layout="wide")

BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ---------- Títol ----------
st.title("ℹ️ Informació equips per l’streaming del partit")

# ---------- Informació de l'equip ----------
st.markdown("### 📝 Informació de l’equip")
team_name = st.text_input("Nom de l'equip*", placeholder="Ex.: Club Vòlei Girona")
sex = st.selectbox("Sexe*", ["Masculí", "Femení"])
category = st.selectbox("Categoria*", ["SM", "Lliga Hiberdrola", "SM2", "SF2", "1a Nacional"])
st.caption("(* camps obligatoris)")

# ---------- Taula jugadors ----------
st.markdown("### 👥 Jugadors")
PLAYER_POSITIONS = ["Col.locador", "Central", "Punta", "Oposat", "Lliure"]
player_cols = ["Nom", "Cognoms", "Número dorsal", "Nom del dorsal", "Posició"]

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

# ---------- Taula staff ----------
st.markdown("### 🧑‍💼 Staff")
staff_cols = ["Nom", "Cognoms", "Funció"]

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

def export(team_name, sex, category, players_df, staff_df):
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
    try:
        xlsx_path = OUTPUT_DIR / f"{base}.xlsx"
        with pd.ExcelWriter(xlsx_path, engine="openpyxl") as writer:
            pd.DataFrame(
                {"Equip": [team_name], "Sexe": [sex], "Categoria": [category]}
            ).to_excel(writer, sheet_name="Equip", index=False)
            (players_df if not players_df.empty else pd.DataFrame(
                columns=["Equip", "Sexe", "Categoria", *player_cols]
            )).to_excel(writer, sheet_name="Jugadors", index=False)
            (staff_df if not staff_df.empty else pd.DataFrame(
                columns=["Equip", "Sexe", "Categoria", *staff_cols]
            )).to_excel(writer, sheet_name="Staff", index=False)
        saved.append(str(xlsx_path))
    except Exception as e:
        st.error(f"Error exportant Excel: {e}")
        st.code(traceback.format_exc())

    return saved

def send_notification(files, team_name, sex, category):
    smtp_server = "smtp.gmail.com"
    smtp_port = 587
    smtp_user = os.environ.get("SMTP_USER")
    smtp_pass = os.environ.get("SMTP_PASS")
    notif_to = "volei.retransmissions@gmail.com"

    try:
        msg = EmailMessage()
        msg["Subject"] = f"[{category} · {sex}] {team_name} – Informació per streaming"
        msg["From"] = smtp_user
        msg["To"] = notif_to
        msg.set_content(
            f"S'ha registrat informació per streaming de l'equip '{team_name}' "
            f"({sex}, {category}). Adjunt l'Excel amb totes les dades."
        )

        for f in files:
            if str(f).lower().endswith(".xlsx"):
                try:
                    with open(f, "rb") as fh:
                        data = fh.read()
                    msg.add_attachment(
                        data,
                        maintype="application",
                        subtype="vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        filename=os.path.basename(f),
                    )
                except Exception as e:
                    st.warning(f"No s'ha pogut adjuntar {f}: {e}")

        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(smtp_user, smtp_pass)
        server.send_message(msg)
        server.quit()
        return True, "Correu enviat correctament."
    except Exception as e:
        return False, f"No s'ha pogut enviar el correu: {e}"

# ---------- Accions ----------
col1, col2 = st.columns([1, 1])
with col1:
    save_btn = st.button("💾 Desa equip", type="primary", use_container_width=True)
with col2:
    reset_btn = st.button("🧹 Reinicia formulari (nou equip)", use_container_width=True)

# Plantilla Excel buida
import io
template_buf = io.BytesIO()
with pd.ExcelWriter(template_buf, engine="openpyxl") as writer:
    pd.DataFrame(columns=["Equip", "Sexe", "Categoria"]).to_excel(writer, sheet_name="Equip", index=False)
    pd.DataFrame(columns=["Equip", "Sexe", "Categoria", "Nom", "Cognoms", "Número dorsal", "Nom del dorsal", "Posició"]).to_excel(writer, sheet_name="Jugadors", index=False)
    pd.DataFrame(columns=["Equip", "Sexe", "Categoria", "Nom", "Cognoms", "Funció"]).to_excel(writer, sheet_name="Staff", index=False)
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
            saved_files = export(team_name, sex, category, players_df, staff_df)
            if saved_files:
                st.success("Dades desades correctament:")
                for f in saved_files:
                    st.write("• ", f)

                ok, msg = send_notification(saved_files, team_name, sex, category)
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
