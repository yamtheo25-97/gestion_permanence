from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import pandas as pd
from datetime import datetime, timedelta
import os

app = Flask(__name__)
app.secret_key = "cle_secrete_permanence_2026"

# Configuration de la session (30 jours pour "remember me")
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=30)

# =========================
# CONFIGURATION SYSTÈME
# =========================

# Date réelle de démarrage du système
START_DATE = datetime(2026, 2, 10, 6, 0)

# Groupe 1 commence au démarrage (index 0 en base 0)
GROUP_START_OFFSET = 0


# =========================
# CHARGEMENT DES DONNÉES
# =========================

def charger_eleves():
    try:
        df = pd.read_excel("eleves.xlsx", engine="openpyxl")
        df["telephone"] = df.get("telephone", "").fillna("").astype(str)
        return df
    except Exception as e:
        print("Erreur chargement élèves :", e)
        return pd.DataFrame()


def charger_alertes():
    try:
        df = pd.read_excel("alertes.xlsx", engine="openpyxl")
        colonnes_requises = ['Noms', 'Prenoms', 'Message', 'Date', 'Type']
        for col in colonnes_requises:
            if col not in df.columns:
                df[col] = ""
        return df
    except Exception as e:
        print("Erreur chargement alertes :", e)
        return pd.DataFrame(columns=['Noms', 'Prenoms', 'Message', 'Date', 'Type'])


# =========================
# GÉNÉRATION DU PLANNING
# =========================

def generate_schedule(start_dt, days=30):
    df = charger_eleves()
    if df.empty:
        return []

    groups = {}

    for _, row in df.iterrows():
        try:
            g = int(row.get('Groupe', 0))
        except:
            continue

        if g == 0:
            continue

        name = f"{str(row.get('Prenoms','')).strip()} {str(row.get('Noms','')).strip()}"
        guerite = str(row.get('Guerite', 'Nord')).strip()

        if g not in groups:
            groups[g] = {}

        if guerite not in groups[g]:
            groups[g][guerite] = []

        groups[g][guerite].append(name)

    group_ids = sorted(groups.keys())
    if not group_ids:
        return []

    # Initialiser les compteurs de service pour chaque membre
    member_service_count = {}
    member_last_guerite = {}
    
    for group_id in group_ids:
        for guerite in groups[group_id]:
            for member in groups[group_id][guerite]:
                member_service_count[member] = 0
                member_last_guerite[member] = None

    schedule = []
    slot_index = 0

    for day in range(days):
        current_date = start_dt + timedelta(days=day)

        for hour in range(6, 18, 2):
            slot_time = current_date.replace(hour=hour, minute=0)

            group_index = (slot_index + GROUP_START_OFFSET) % len(group_ids)
            group_id = group_ids[group_index]

            guerites_in_group = sorted(groups[group_id].keys())
            
            # Déterminer la guérite de service en alternant
            if slot_index % 2 == 0:
                guerite_service = 'Nord'
            else:
                guerite_service = 'Sud'

            all_members = []

            for g in guerites_in_group:
                members = groups[group_id].get(g, [])
                for m in members:
                    # Déterminer la guérite actuelle du membre (alternance)
                    if member_last_guerite[m] is None:
                        # Premier service : guérite d'origine
                        current_guerite = g
                    else:
                        # Alterner entre Nord et Sud
                        current_guerite = 'Sud' if member_last_guerite[m] == 'Nord' else 'Nord'
                    
                    member_last_guerite[m] = current_guerite
                    
                    all_members.append({
                        'name': m,
                        'guerite': current_guerite,
                        'service': (current_guerite == guerite_service)
                    })

            end_time = slot_time + timedelta(hours=2)

            schedule.append({
                'iso': slot_time.isoformat(),
                'display': f"{slot_time.strftime('%d/%m %H:%M')} - {end_time.strftime('%H:%M')}",
                'date': slot_time.strftime('%d/%m/%Y'),
                'group': int(group_id),
                'members': all_members,
                'guerite_service': guerite_service
            })

            slot_index += 1

    return schedule


# =========================
# LOGIN
# =========================

@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        nom = request.form["nom"].strip()
        prenom = request.form["prenom"].strip()
        remember = request.form.get("remember", "off") == "on"

        df = charger_eleves()

        match = df[
            (df["Noms"].str.strip().str.lower() == nom.lower()) &
            (df["Prenoms"].str.strip().str.lower() == prenom.lower())
        ]

        if match.empty:
            return render_template("login.html", erreur="Nom ou prénom incorrect")

        session["nom"] = nom
        session["prenom"] = prenom
        session.permanent = remember  # Rendre la session persistante si "remember me" est coché

        return redirect(url_for("dashboard"))

    return render_template("login.html")


# =========================
# MENU
# =========================

@app.route("/menu")
def menu():
    if "nom" not in session:
        return redirect(url_for("login"))

    df = charger_eleves()
    personnes = []

    for _, row in df.iterrows():
        personnes.append({
            'prenom': str(row.get('Prenoms', '')).strip(),
            'nom': str(row.get('Noms', '')).strip(),
            'groupe': row.get('Groupe', '')
        })

    return render_template("menu.html", personnes=personnes,
                           nom=session["nom"], prenom=session["prenom"])


@app.route("/menu/data")
def menu_data():
    schedule = generate_schedule(START_DATE, days=30)
    return jsonify(schedule)


# =========================
# CRÉNEAU ACTUEL
# =========================

@app.route("/current-shift")
def current_shift():
    now = datetime.now()
    schedule = generate_schedule(START_DATE, days=30)

    for slot in schedule:
        slot_start = datetime.fromisoformat(slot['iso'])
        slot_end = slot_start + timedelta(hours=2)

        if slot_start <= now < slot_end:
            return jsonify(slot)

    return jsonify({})


# =========================
# DASHBOARD
# =========================

@app.route("/dashboard")
def dashboard():
    if "nom" not in session:
        return redirect(url_for("login"))

    alertes_df = charger_alertes()

    if not alertes_df.empty and "Noms" in alertes_df.columns:
        alertes_utilisateur = alertes_df[
            alertes_df["Noms"].str.strip().str.lower() == session["nom"].lower()
        ]
    else:
        alertes_utilisateur = pd.DataFrame()

    # Récupérer les permanences de l'utilisateur connecté
    schedule = generate_schedule(START_DATE, days=30)
    user_permanences = []
    user_name = f"{session['prenom']} {session['nom']}".strip().lower()
    
    for slot in schedule:
        for member in slot.get('members', []):
            if member['name'].strip().lower() == user_name:
                user_permanences.append({
                    'date': slot['date'],
                    'display': slot['display'],
                    'guerite': member['guerite'],
                    'service': member['service'],
                    'group': slot['group'],
                    'alert_time': (datetime.fromisoformat(slot['iso']) - timedelta(minutes=30)).strftime('%d/%m %H:%M')
                })
                break

    return render_template(
        "dashboard.html",
        nom=session["nom"],
        prenom=session["prenom"],
        alertes=alertes_utilisateur.to_dict(orient="records"),
        user_permanences=user_permanences
    )


# =========================
# ALERTE 30 MINUTES
# =========================

@app.route("/alert-check")
def alert_check():
    if "nom" not in session or "prenom" not in session:
        return jsonify({'should_alert': False})
    
    now = datetime.now()
    schedule = generate_schedule(START_DATE, days=30)
    
    # Nom complet de l'utilisateur connecté
    user_name = f"{session['prenom']} {session['nom']}".strip().lower()

    for slot in schedule:
        slot_start = datetime.fromisoformat(slot['iso'])
        alert_time = slot_start - timedelta(minutes=30)

        if alert_time <= now < (alert_time + timedelta(seconds=60)):
            # Vérifier si l'utilisateur connecté est dans ce créneau
            for member in slot.get('members', []):
                if member['name'].strip().lower() == user_name:
                    return jsonify({'should_alert': True, 'slot': slot})

    return jsonify({'should_alert': False})


# =========================
# LOGOUT
# =========================

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# =========================
# LANCEMENT
# =========================

if __name__ == "__main__":
    app.run(debug=True)
