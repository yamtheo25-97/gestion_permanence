from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import pandas as pd
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = "cle_secrete_permanence_2026"


# =========================
# FONCTIONS DE CHARGEMENT
# =========================

def charger_eleves():
    try:
        df = pd.read_excel("eleves.xlsx", engine="openpyxl")
        # Convertir la colonne telephone en string et gérer les valeurs manquantes
        df["telephone"] = df["telephone"].fillna("").astype(str)
        return df
    except Exception as e:
        print("Erreur chargement élèves :", e)
        return pd.DataFrame()


def charger_alertes():
    try:
        df = pd.read_excel("alertes.xlsx", engine="openpyxl")
        # Ajouter les colonnes manquantes si nécessaire
        colonnes_requises = ['Noms', 'Prenoms', 'Message', 'Date', 'Type']
        for col in colonnes_requises:
            if col not in df.columns:
                df[col] = ""
        return df
    except Exception as e:
        print("Erreur chargement alertes :", e)
        # Retourner un DataFrame vide avec les bonnes colonnes
        return pd.DataFrame(columns=['Noms', 'Prenoms', 'Message', 'Date', 'Type'])


# =========================
# FONCTIONS DE PLANNING
# =========================

def generate_schedule(start_dt, days=4):
    """Génère un planning avec créneaux de 2h de 6h à 18h pour N jours.
    Rotation des groupes, et pour chaque groupe sa rotation de guérite (Nord→Sud→Nord...).
    Affiche les personnes des deux guérites.
    """
    df = charger_eleves()
    if df.empty:
        return []

    # Construire dictionnaire {groupe: {guérite: [membres]}}
    groups = {}
    for _, row in df.iterrows():
        try:
            g = int(row.get('Groupe', 0))
        except Exception:
            g = 0
        if g == 0:
            continue
        
        name = f"{str(row.get('Prenoms','')).strip()} {str(row.get('Noms','')).strip()}".strip()
        guerite = str(row.get('Guerite', 'Nord')).strip()
        
        if g not in groups:
            groups[g] = {}
        if guerite not in groups[g]:
            groups[g][guerite] = []
        groups[g][guerite].append(name)

    group_ids = sorted([gid for gid in groups.keys()])
    if not group_ids:
        return []

    schedule = []
    slot_index = 0
    # N jours, 6 créneaux par jour (6-8h, 8-10h, ..., 16-18h)
    for day in range(days):
        current_date = start_dt + timedelta(days=day)
        for hour in range(6, 18, 2):  # 6, 8, 10, 12, 14, 16
            slot_time = current_date.replace(hour=hour, minute=0)
            
            # Déterminer le groupe
            group_id = group_ids[slot_index % len(group_ids)]
            
            # Déterminer le cycle du groupe (0, 1, 2...)
            cycle = slot_index // len(group_ids)
            
            # Lister les guérites du groupe dans l'ordre
            guerites_in_group = sorted(groups[group_id].keys())
            
            # Déterminer la guérite en service pour ce cycle
            guerite_service = guerites_in_group[cycle % len(guerites_in_group)]
            
            # Récupérer les membres des deux guérites
            all_members = []
            for g in guerites_in_group:
                members = groups[group_id].get(g, [])
                for m in members:
                    all_members.append({'name': m, 'guerite': g, 'service': (g == guerite_service)})
            
            end_time = slot_time + timedelta(hours=2)
            schedule.append({
                'iso': slot_time.isoformat(),
                'display': f"{slot_time.strftime('%a %d/%m %H:%M')} - {end_time.strftime('%H:%M')}",
                'group': int(group_id),
                'members': all_members,
                'guerite_service': guerite_service
            })
            slot_index += 1

    return schedule


# =========================
# ROUTE LOGIN
# =========================

@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        nom = request.form["nom"].strip()
        prenom = request.form["prenom"].strip()

        df = charger_eleves()

        match = df[
            (df["Noms"].str.strip().str.lower() == nom.lower()) &
            (df["Prenoms"].str.strip().str.lower() == prenom.lower())
        ]

        if match.empty:
            return render_template("login.html", erreur="Nom ou prénom incorrect")

        session["nom"] = nom
        session["prenom"] = prenom

        # Après connexion, afficher directement le menu (planning)
        return redirect(url_for("menu"))

    return render_template("login.html")


# =========================
# AJOUTER TÉLÉPHONE
# =========================

@app.route("/add_phone", methods=["GET", "POST"])
def add_phone():
    if "nom" not in session:
        return redirect(url_for("login"))
    
    if request.method == "POST":
        telephone = request.form.get("telephone", "").strip()
        
        if not telephone:
            return render_template("add_phone.html", erreur="Veuillez entrer un numéro")
        
        session["telephone"] = telephone
        return redirect(url_for("dashboard"))
    
    return render_template("add_phone.html")


# =========================
# MENU - PLANNING
# =========================

@app.route("/menu")
def menu():
    if "nom" not in session:
        return redirect(url_for("login"))
    # Fournir la liste des personnes avec leur groupe pour information
    df = charger_eleves()
    personnes = []
    if not df.empty:
        for _, row in df.iterrows():
            personnes.append({
                'prenom': str(row.get('Prenoms', '')).strip(),
                'nom': str(row.get('Noms', '')).strip(),
                'groupe': row.get('Groupe', '')
            })

    return render_template("menu.html", personnes=personnes, nom=session.get("nom",""), prenom=session.get("prenom",""))


@app.route("/menu/data")
def menu_data():
    # Démarrer la rotation demain à 06:00, pour 4 jours
    now = datetime.now()
    tomorrow = (now + timedelta(days=1)).date()
    start_dt = datetime.combine(tomorrow, datetime.min.time()).replace(hour=6)
    schedule = generate_schedule(start_dt, days=4)
    return jsonify(schedule)


@app.route("/current-shift")
def current_shift():
    """Retourne le créneau actuel ou le prochain."""
    now = datetime.now()
    tomorrow = (now + timedelta(days=1)).date()
    start_dt = datetime.combine(tomorrow, datetime.min.time()).replace(hour=6)
    schedule = generate_schedule(start_dt, days=30)  # Planning sur 30 jours
    
    # Trouver le créneau actuel ou le prochain
    current_slot = None
    for slot in schedule:
        slot_start = datetime.fromisoformat(slot['iso'])
        slot_end = slot_start + timedelta(hours=2)
        if slot_start <= now < slot_end:
            current_slot = slot
            break
    
    # Si pas de créneau actuel, prendre le prochain
    if not current_slot and schedule:
        current_slot = schedule[0]
    
    return jsonify(current_slot if current_slot else {})


# =========================
# DASHBOARD
# =========================

@app.route("/dashboard")
def dashboard():
    if "nom" not in session:
        return redirect(url_for("login"))

    alertes_df = charger_alertes()

    # Vérifier que le DataFrame n'est pas vide et qu'il contient la colonne Noms
    if not alertes_df.empty and "Noms" in alertes_df.columns:
        alertes_utilisateur = alertes_df[
            alertes_df["Noms"].str.strip().str.lower() == session["nom"].lower()
        ]
    else:
        alertes_utilisateur = pd.DataFrame()

    return render_template(
        "dashboard.html",
        nom=session["nom"],
        prenom=session["prenom"],
        alertes=alertes_utilisateur.to_dict(orient="records")
    )


# =========================
# DÉCONNEXION
# =========================

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# =========================
# LANCEMENT
# =========================


# =========================
# CHECK ALERT 30MINUTE
# =========================

@app.route("/alert-check")
def alert_check():
    """Renvoie si une alerte doit être déclenchée (30 minutes avant un créneau).
    Le client appelle cette route toutes les 60s; on retourne `should_alert: true`
    si l'heure actuelle est dans la fenêtre [alert_time, alert_time + 60s).
    """
    now = datetime.now()
    # Même démarrage que pour le planning (demain 06:00)
    tomorrow = (now + timedelta(days=1)).date()
    start_dt = datetime.combine(tomorrow, datetime.min.time()).replace(hour=6)
    schedule = generate_schedule(start_dt, days=30)

    for slot in schedule:
        try:
            slot_start = datetime.fromisoformat(slot['iso'])
        except Exception:
            continue
        alert_time = slot_start - timedelta(minutes=30)
        # Fenêtre d'alerte d'une minute
        if alert_time <= now < (alert_time + timedelta(seconds=60)):
            return jsonify({'should_alert': True, 'slot': slot, 'alert_time': alert_time.isoformat()})

    return jsonify({'should_alert': False, 'slot': None, 'alert_time': None})

if __name__ == "__main__":
    app.run(debug=True)

