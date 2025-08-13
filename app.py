from flask import Flask, render_template_string, request, redirect, send_file
import csv
import os
from datetime import datetime
import pandas as pd

app = Flask(__name__)

CSV_FILE = "jugadors_i_staff.csv"

if not os.path.exists(CSV_FILE):
    with open(CSV_FILE, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(["Data/Hora", "Tipus", "Número", "Dorsal", "Nom", "Cognoms", "Posició / Càrrec"])

FORM_HTML = """
<!DOCTYPE html>
<html lang="ca">
<head>
    <meta charset="UTF-8">
    <title>Formulari Jugadors i Staff</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        fieldset { margin-bottom: 20px; }
    </style>
    <script>
        function afegirJugador() {
            let container = document.getElementById("jugadors");
            let bloc = document.createElement("div");
            bloc.innerHTML = `
                Número: <input type="number" name="jugador_numero" required>
                Dorsal: <input type="text" name="jugador_dorsal" required>
                Nom: <input type="text" name="jugador_nom" required>
                Cognoms: <input type="text" name="jugador_cognoms" required>
                Posició: <input type="text" name="jugador_posicio" required>
                <br><br>
            `;
            container.appendChild(bloc);
        }

        function afegirStaff() {
            let container = document.getElementById("staff");
            let bloc = document.createElement("div");
            bloc.innerHTML = `
                Nom: <input type="text" name="staff_nom" required>
                Cognoms: <input type="text" name="staff_cognoms" required>
                Càrrec: <input type="text" name="staff_carrecs" required>
                <br><br>
            `;
            container.appendChild(bloc);
        }
    </script>
</head>
<body>
    <h1>Formulari de dades</h1>
    <form method="post" action="/submit">
        <fieldset>
            <legend>Jugadors/es</legend>
            <div id="jugadors"></div>
            <button type="button" onclick="afegirJugador()">Afegir jugador/a</button>
        </fieldset>

        <fieldset>
            <legend>Staff tècnic</legend>
            <div id="staff"></div>
            <button type="button" onclick="afegirStaff()">Afegir membre staff</button>
        </fieldset>

        <br>
        <button type="submit">Enviar tot</button>
    </form>

    <hr>
    <a href="/descarregar">📥 Descarregar Excel amb totes les dades</a>
</body>
</html>
"""

@app.route("/")
def index():
    return render_template_string(FORM_HTML)

@app.route("/submit", methods=["POST"])
def submit():
    jugadors_num = request.form.getlist("jugador_numero")
    jugadors_dorsal = request.form.getlist("jugador_dorsal")
    jugadors_nom = request.form.getlist("jugador_nom")
    jugadors_cognoms = request.form.getlist("jugador_cognoms")
    jugadors_posicio = request.form.getlist("jugador_posicio")

    staff_nom = request.form.getlist("staff_nom")
    staff_cognoms = request.form.getlist("staff_cognoms")
    staff_carrecs = request.form.getlist("staff_carrecs")

    with open(CSV_FILE, mode='a', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)

        for i in range(len(jugadors_nom)):
            if jugadors_nom[i].strip():
                writer.writerow([
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "Jugador",
                    jugadors_num[i],
                    jugadors_dorsal[i],
                    jugadors_nom[i],
                    jugadors_cognoms[i],
                    jugadors_posicio[i]
                ])

        for i in range(len(staff_nom)):
            if staff_nom[i].strip():
                writer.writerow([
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "Staff",
                    "",
                    "",
                    staff_nom[i],
                    staff_cognoms[i],
                    staff_carrecs[i]
                ])

    return redirect("/")

@app.route("/descarregar")
def descarregar():
    df = pd.read_csv(CSV_FILE)
    excel_path = "jugadors_i_staff.xlsx"
    df.to_excel(excel_path, index=False)
    return send_file(excel_path, as_attachment=True)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
