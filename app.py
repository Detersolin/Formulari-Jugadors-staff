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

# ---------- Logo (robust) ----------
def show_logo():
    env_path = os.environ.get("LOGO_PATH")
    candidates = []
    if env_path:
        candidates.append(Path(env_path))

    candidates += [
        BASE_DIR / "static" / "logo.png",
        BASE_DIR / "static" / "logo.jpg",
        BASE_DIR / "static" / "logo.jpeg",
        BASE_DIR / "static" / "Logo VR Bo.png",
        BASE_DIR / "logo.png",
        BASE_DIR / "logo.jpg",
        BASE_DIR / "logo.jpeg",
        BASE_DIR / "Logo VR Bo.png",
    ]

    for p in candidates:
        try:
            if p.exists():
                st.image(str(p), width=200)
                return
        except Exception:
            pass

    st.warning("No s'ha trobat el logo. Posa'l com **static/logo.png** o defineix **LOGO_PATH** amb el camí complet al fitxer.")

show_logo()

# ---------- Títol ----------
st.title("ℹ️ Informació equips per l’streaming del partit")

# ---------- Informació de l’equip ----------
st.markdown("### 📝 Informació de l’equip")

team_name = st.text_input("Nom de l'equip*", placeholder="Ex.: Club Vòlei Girona")
sex = st.radio("Sexe", ["Masculí", "Femení"], horizontal=True)
category = st.radio("Categoria", ["SM", "Lliga Hiberdrola", "SM2", "SF2", "1a Nacional"], horizontal=True)

st.caption("(* camps obligatoris)")

# ---------- Pista per als desplegables de la taula ----------
st.info("Per omplir **Posició** i **Funció**, clica la cel·la i fes servir el desplegable ▾.", icon="➡️")

# ---------- Constants ----------
PLACEHOLDER = "— Tria —"

# ---------- Jugadors ----------
st.markdown("### 👥 Jugadors")

PLAYER_POSITIONS = [PLACEHOLDER, "Col·locador", "Central", "Punta", "Oposat", "Lliure"]
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
        "Posició": cc.SelectboxColumn("Posició ▾", options=PLAYER_POSITIONS, default=PLACEHOLDER),
    },
    use_container_width=True,
    hide_index=True,
    key="players_editor",
)
# guarda el que s'ha editat
st.session_state.players_df = players_df

# ---------- Staff ----------
st.markdown("### 🧑‍💼 Staff")

STAFF_ROLES = [
    PLACEHOLDER,
    "Entrenador principal",
    "Segon entrenador",
    "Preparador físic",
    "Fisioterapeuta",
    "Delegat",
    "Altres",
]
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
        "Funció": cc.SelectboxColumn("Funció ▾", options=STAFF_ROLES, default=PLACEHOLDER),
    },
    use_container_width=True,
    hide_index=True,
    key="staff_editor",
)
# guarda el que s'ha editat
st.session_state.staff_df = staff_df

# ---------- Utilitats ----------
def slugify(text: str) -> str:
    text = text.strip().lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return re.sub(r"-+", "-", text).strip("-") or "equip"

def validate_team(team_name: str) -> bool:
    return bool(team_name and team_name.strip())

def non_empty_rows_mask(df: pd.DataFrame) -> pd.Series:
    """Fila no buida si algun camp (després de normalitzar) té text."""
    if df is None or df.empty:
        return pd.Series([], dtype=bool)
    norm = df.fillna("").replace({PLACEHOLDER: ""})
    return norm.apply(lambda r: any(str(x).strip() != "" for x in r), axis=1)

def validate_dropdowns(players_df: pd.DataFrame, staff_df: pd.DataFrame) -> list[str]:
    """Si una fila té alguna dada, 'Posició'/'Funció' no poden quedar en blanc ni en PLACEHOLDER."""
    errors: list[str] = []
    # Jugadors
    if players_df is not None and not players_df.empty:
        m = non_empty_rows_mask(players_df)
        df = players_df.loc[m].copy()
        if not df.empty:
            invalid = df[df["Posició"].fillna("").isin(["", PLACEHOLDER])]
            if not invalid.empty:
                idxs = (invalid.index + 1).tolist()
                errors.append(f"Jugadors: falta **Posició** a les files {idxs}.")
    # Staff
    if staff_df is not None and not staff_df.empty:
        m = non_empty_rows_mask(staff_df)
        df = staff_df.loc[m].copy()
        if not df.empty:
            invalid = df[df["Funció"].fillna("").isin(["", PLACEHOLDER])]
            if not invalid.empty:
                idxs = (invalid.index + 1).tolist()
                errors.append(f"Staff: falta **Funció** a les files {idxs}.")
    return errors

def clean_players_df(df: pd.DataFrame) -> pd.DataFrame:
    """Conserva una fila si algun camp de jugadors té valor real (no buit ni PLACEHOLDER)."""
    cols = ["Nom", "Cognoms", "Número dorsal", "Nom del dorsal", "Posició"]
    if df is None or df.empty:
        return pd.DataFrame(columns=cols)
    df2 = df.copy().fillna("").replace({PLACEHOLDER: ""})
    keep = df2[cols].apply(lambda r: any(str(x).strip() != "" for x in r), axis=1)
    return df2.loc[keep].reset_index(drop=True)

def clean_staff_df(df: pd.DataFrame) -> pd.DataFrame:
    """Conserva una fila si algun camp de staff té valor real (no buit ni PLACEHOLDER)."""
    cols = ["Nom", "Cognoms", "Funció"]
    if df is None or df.empty:
        return pd.DataFrame(columns=cols)
    df2 = df.copy().fillna("").replace({PLACEHOLDER: ""})
    keep = df2[cols].apply(lambda r: any(str(x).strip() != "" for x in r), axis=1)
    return df2.loc[keep].reset_index(drop=True)

def export(team_name, sex, category, players_df, staff_df):
    # nom del fitxer: <equip>_<timestamp>.xlsx
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    base = f"{slugify(team_name)}_{ts}"
    saved = []

    players_df = clean_players_df(players_df)
    staff_df = clean_staff_df(staff_df)

    # Afegir metadades de l’equip
    for df in (players_df, staff_df):
        if not df.empty:
            df.insert(0, "Equip", team_name)
            df.insert(1, "Sexe", sex)
            df.insert(2, "Categoria", category)

    try:
        xlsx_path = OUTPUT_DIR / f"{base}.xlsx"
        with pd.ExcelWriter(xlsx_path, engine="openpyxl") as writer:
            pd.DataFrame({"Equip": [team_name], "Sexe": [sex], "Categoria": [category]}).to_excel(
                writer, sheet_name="Equip", index=False
            )
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
    smtp_user = os.environ.get("SMTP_USER") or "volei.retransmissions@gmail.com"
    smtp_pass = os.environ.get("SMTP_PASS")  # App Password a Render
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
                        filename=os.path.basename(f),  # ja inclou el nom de l'equip
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

# ---------- Comptadors útils ----------
def active_count(df: pd.DataFrame) -> int:
    if df is None or df.empty:
        return 0
    return int(non_empty_rows_mask(df).sum())

st.caption(f"👥 Jugadors actius: {active_count(players_df)}")
st.caption(f"🧑‍💼 Staff actiu: {active_count(staff_df)}")

# ---------- Accions ----------
col1, col2 = st.columns([1, 1])
with col1:
    save_btn = st.button(
        "💾 Desa equip",
        type="primary",
        use_container_width=True,
        disabled=not (team_name or "").strip(),  # desactivat si no hi ha nom
    )
with col2:
    reset_btn = st.button("🧹 Reinicia formulari (nou equip)", use_container_width=True)

if save_btn:
    if not validate_team(team_name):
        st.error("Cal indicar el **Nom de l'equip**.")
    else:
        # Validació desplegables
        errors = validate_dropdowns(players_df, staff_df)
        if errors:
            for e in errors:
                st.error(e)
            st.stop()

        try:
            saved_files = export(team_name, sex, category, players_df, staff_df)
            if saved_files:
                st.success("Dades desades correctament:")
                for f in saved_files:
                    st.write("• ", f)

                with st.spinner("Enviant correu..."):
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

st.caption("💡 Consell: completa els desplegables ▾, desa l’equip i prem **Reinicia** per preparar un nou equip.")
