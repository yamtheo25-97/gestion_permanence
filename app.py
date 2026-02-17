from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import pandas as pd
from datetime import datetime, timedelta
import os

app = Flask(__name__)
app.secret_key = "cle_secrete_permanence_2026"

# Configuration de la session (30 jours pour "remember me")
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=30)

# =========================
# CONSTANTES
# =========================

# Date réelle de démarrage du système
START_DATE = datetime(2026, 2, 10, 6, 0)

# Groupe 1 commence au démarrage (index 0 en base 0)
GROUP_START_OFFSET = 0

# =========================
# FONCTIONS UTILITAIRES
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

def get_access_code():
    """Récupérer le code d'accès actuel"""
    try:
        if not os.path.exists("access_code.txt"):
            return None
        with open("access_code.txt", "r") as f:
            code = f.read().strip()
            return code if code else None
    except Exception as e:
        print(f"Erreur lecture code d'accès: {e}")
        return None

def set_access_code(code):
    """Définir le code d'accès"""
    try:
        if code and code.strip():
            with open("access_code.txt", "w") as f:
                f.write(code.strip())
        else:
            # Si le code est vide, supprimer le fichier
            if os.path.exists("access_code.txt"):
                os.remove("access_code.txt")
    except Exception as e:
        print(f"Erreur écriture code d'accès: {e}")

def verify_access_code(code):
    """Vérifier si le code d'accès est correct"""
    stored_code = get_access_code()
    if stored_code is None:  # Pas de code défini
        return True
    return code == stored_code


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
        access_code = request.form.get("access_code", "").strip()

        # Vérification des identifiants administrateur
        if nom.upper() == "IFPB" and prenom.upper() == "END":
            session["nom"] = nom
            session["prenom"] = prenom
            session["is_admin"] = True
            session.permanent = remember
            return redirect(url_for("admin"))

        df = charger_eleves()

        match = df[
            (df["Noms"].str.strip().str.lower() == nom.lower()) &
            (df["Prenoms"].str.strip().str.lower() == prenom.lower())
        ]

        if match.empty:
            return render_template("login.html", erreur="Nom ou prénom incorrect")

        # Vérifier le code d'accès si nécessaire
        if not verify_access_code(access_code):
            return render_template("login.html", 
                               erreur="Code d'accès incorrect",
                               nom=nom, 
                               prenom=prenom,
                               access_code_required=get_access_code() is not None)

        session["nom"] = nom
        session["prenom"] = prenom
        session["is_admin"] = False
        session.permanent = remember  # Rendre la session persistante si "remember me" est coché

        return redirect(url_for("dashboard"))

    return render_template("login.html", access_code_required=get_access_code() is not None)


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

@app.route("/enhanced-alert-check")
def enhanced_alert_check():
    """Route améliorée pour les alertes avec support de notifications push"""
    if "nom" not in session or "prenom" not in session:
        return jsonify({
            'should_alert': False, 
            'user_logged_in': False,
            'message': 'Utilisateur non connecté'
        })
    
    now = datetime.now()
    schedule = generate_schedule(START_DATE, days=30)
    
    # Nom complet de l'utilisateur connecté
    user_name = f"{session['prenom']} {session['nom']}".strip().lower()
    
    # Vérifier les alertes dans les 60 prochaines minutes
    upcoming_alerts = []
    
    for slot in schedule:
        slot_start = datetime.fromisoformat(slot['iso'])
        alert_time = slot_start - timedelta(minutes=30)
        
        # Vérifier si l'alerte est dans la prochaine heure
        if alert_time <= now < (alert_time + timedelta(minutes=60)):
            # Vérifier si l'utilisateur connecté est dans ce créneau
            for member in slot.get('members', []):
                if member['name'].strip().lower() == user_name:
                    upcoming_alerts.append({
                        'slot': slot,
                        'alert_time': alert_time.isoformat(),
                        'minutes_until': int((alert_time - now).total_seconds() / 60),
                        'is_immediate': alert_time <= now <= (alert_time + timedelta(seconds=60))
                    })
                    break
    
    # Trier par temps jusqu'à l'alerte
    upcoming_alerts.sort(key=lambda x: x['minutes_until'])
    
    return jsonify({
        'should_alert': len([a for a in upcoming_alerts if a['is_immediate']]) > 0,
        'user_logged_in': True,
        'user_name': session['prenom'] + ' ' + session['nom'],
        'upcoming_alerts': upcoming_alerts[:3],  # Limiter à 3 prochaines alertes
        'current_time': now.isoformat(),
        'notification_enabled': True
    })

@app.route("/register-device", methods=["POST"])
def register_device():
    """Enregistrer un appareil pour les notifications push"""
    if "nom" not in session or "prenom" not in session:
        return jsonify({'success': False, 'message': 'Non authentifié'})
    
    try:
        device_token = request.json.get('device_token')
        user_name = f"{session['prenom']} {session['nom']}".strip()
        
        # Ici vous pourriez sauvegarder le token dans une base de données
        # Pour l'instant, on simule l'enregistrement
        print(f"Appareil enregistré pour {user_name}: {device_token}")
        
        return jsonify({
            'success': True, 
            'message': 'Appareil enregistré avec succès',
            'user_name': user_name
        })
    except Exception as e:
        return jsonify({
            'success': False, 
            'message': f'Erreur: {str(e)}'
        })

@app.route("/test-notification")
def test_notification():
    """Route pour tester les notifications"""
    if "nom" not in session or "prenom" not in session:
        return jsonify({'success': False, 'message': 'Non authentifié'})
    
    return jsonify({
        'success': True,
        'message': 'Notification de test envoyée',
        'user_name': session['prenom'] + ' ' + session['nom'],
        'timestamp': datetime.now().isoformat()
    })


# =========================
# ADMINISTRATION
# =========================

@app.route("/admin")
def admin():
    if not session.get("is_admin", False):
        return redirect(url_for("login"))
    
    df = charger_eleves()
    personnes = []
    
    for _, row in df.iterrows():
        personnes.append({
            'prenom': str(row.get('Prenoms', '')).strip(),
            'nom': str(row.get('Noms', '')).strip(),
            'groupe': row.get('Groupe', ''),
            'guerite': str(row.get('Guerite', '')).strip()
        })
    
    return render_template("admin.html", 
                       nom=session["nom"], 
                       prenom=session["prenom"],
                       personnes=personnes)

@app.route("/admin/add_person", methods=["GET", "POST"])
def add_person():
    if not session.get("is_admin", False):
        return redirect(url_for("login"))
    
    if request.method == "POST":
        try:
            # Charger le fichier Excel existant
            df = charger_eleves()
            
            # Ajouter la nouvelle personne
            new_row = {
                'Prenoms': request.form["prenom"].strip(),
                'Noms': request.form["nom"].strip(),
                'Groupe': int(request.form["groupe"]),
                'Guerite': request.form["guerite"].strip(),
                'telephone': request.form.get("telephone", "").strip()
            }
            
            # Ajouter au DataFrame
            df_new = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
            
            # Sauvegarder dans le fichier Excel
            df_new.to_excel("eleves.xlsx", index=False, engine="openpyxl")
            
            return redirect(url_for("admin"))
        except Exception as e:
            return render_template("add_person.html", erreur=str(e))
    
    return render_template("add_person.html")

@app.route("/admin/delete_person/<prenom>/<nom>")
def delete_person(prenom, nom):
    if not session.get("is_admin", False):
        return redirect(url_for("login"))
    
    try:
        # Charger le fichier Excel
        df = charger_eleves()
        
        # Supprimer la personne
        df_filtered = df[
            ~((df["Prenoms"].str.strip() == prenom) & 
              (df["Noms"].str.strip() == nom))
        ]
        
        # Sauvegarder
        df_filtered.to_excel("eleves.xlsx", index=False, engine="openpyxl")
        
    except Exception as e:
        print(f"Erreur suppression: {e}")
    
    return redirect(url_for("admin"))

@app.route("/admin/update_hours", methods=["GET", "POST"])
def update_hours():
    if not session.get("is_admin", False):
        return redirect(url_for("login"))
    
    if request.method == "POST":
        try:
            # Mettre à jour les heures dans le fichier de configuration
            start_hour = int(request.form["start_hour"])
            end_hour = int(request.form["end_hour"])
            alert_minutes = int(request.form["alert_minutes"])
            
            # Pour l'instant, on affiche les valeurs (à intégrer dans la logique)
            return render_template("update_hours.html", 
                               success=True,
                               start_hour=start_hour,
                               end_hour=end_hour,
                               alert_minutes=alert_minutes)
        except Exception as e:
            return render_template("update_hours.html", erreur=str(e))
    
    return render_template("update_hours.html")

@app.route("/admin/manage_groups", methods=["GET", "POST"])
def manage_groups():
    if not session.get("is_admin", False):
        return redirect(url_for("login"))
    
    if request.method == "POST":
        try:
            action = request.form.get("action")
            
            if action == "create_groups":
                # Créer des groupes avec taille personnalisée
                group_size = int(request.form["group_size"])
                
                # Charger les élèves existants
                df = charger_eleves()
                
                if df.empty:
                    return render_template("manage_groups.html", 
                                       erreur="Aucun élève trouvé dans la base de données")
                
                # Organiser les élèves en groupes avec la taille spécifiée
                df_organized = organize_random_groups(df, group_size)
                
                # Sauvegarder les modifications
                df_organized.to_excel("eleves.xlsx", index=False, engine="openpyxl")
                
                # Calculer les statistiques
                total_students = len(df_organized)
                num_groups = df_organized['Groupe'].nunique()
                
                return render_template("manage_groups.html", 
                                   success=True,
                                   group_size=group_size,
                                   total_students=total_students,
                                   num_groups=num_groups,
                                   message=f"Groupes créés avec succès! {total_students} élèves répartis en {num_groups} groupes de {group_size} personnes maximum.")
            
            elif action == "create_named_group":
                # Créer un groupe nommé (fonctionnalité future)
                group_name = request.form["group_name"].strip()
                if group_name:
                    return render_template("manage_groups.html", 
                                       success=True,
                                       group_name=group_name,
                                       message=f"Groupe '{group_name}' enregistré")
                    
        except Exception as e:
            return render_template("manage_groups.html", erreur=str(e))
    
    return render_template("manage_groups.html")

@app.route("/admin/access_code", methods=["GET", "POST"])
def manage_access_code():
    if not session.get("is_admin", False):
        return redirect(url_for("login"))
    
    if request.method == "POST":
        try:
            action = request.form.get("action")
            
            if action == "set_code":
                new_code = request.form.get("new_code", "").strip()
                
                # Vérifier que le code ne contient que des chiffres
                if new_code and not new_code.isdigit():
                    return render_template("access_code.html", 
                                       erreur="Le code d'accès ne doit contenir que des chiffres")
                
                set_access_code(new_code)
                
                if new_code:
                    message = f"Code d'accès défini avec succès: {new_code}"
                else:
                    message = "Code d'accès supprimé. Accès libre activé."
                
                return render_template("access_code.html", 
                                   success=True,
                                   current_code=new_code,
                                   message=message)
            
            elif action == "remove_code":
                # Supprimer le fichier de code pour activer l'accès libre
                try:
                    if os.path.exists("access_code.txt"):
                        os.remove("access_code.txt")
                    message = "Code d'accès supprimé. Accès libre activé."
                    return render_template("access_code.html", 
                                       success=True,
                                       current_code="",
                                       message=message)
                except Exception as e:
                    return render_template("access_code.html", 
                                       erreur=f"Erreur lors de la suppression du code: {str(e)}")
                    
        except Exception as e:
            return render_template("access_code.html", erreur=str(e))
    
    current_code = get_access_code()
    return render_template("access_code.html", current_code=current_code)

@app.route("/admin/planning")
def admin_planning():
    if not session.get("is_admin", False):
        return redirect(url_for("login"))
    
    # Récupérer le planning complet
    schedule = generate_schedule(START_DATE, days=30)
    
    # Récupérer le créneau actuel
    now = datetime.now()
    current_shift = None
    next_shifts = []
    
    for i, slot in enumerate(schedule):
        slot_start = datetime.fromisoformat(slot['iso'])
        slot_end = slot_start + timedelta(hours=2)
        
        if slot_start <= now < slot_end:
            current_shift = slot
        elif slot_start > now:
            next_shifts.append(slot)
            if len(next_shifts) >= 3:  # Garder seulement les 3 prochains créneaux
                break
    
    return render_template("admin_planning.html", 
                       nom=session["nom"], 
                       prenom=session["prenom"],
                       schedule=schedule,
                       current_shift=current_shift,
                       next_shifts=next_shifts)

@app.route("/admin/security")
def security():
    if not session.get("is_admin", False):
        return redirect(url_for("login"))
    
    return render_template("security.html", 
                       nom=session["nom"], 
                       prenom=session["prenom"])

@app.route("/admin/manage_students", methods=["GET", "POST"])
def manage_students():
    if not session.get("is_admin", False):
        return redirect(url_for("login"))
    
    if request.method == "POST":
        action = request.form.get("action")
        
        if action == "delete_all":
            try:
                # Supprimer le fichier Excel existant
                if os.path.exists("eleves.xlsx"):
                    os.remove("eleves.xlsx")
                
                # Créer un nouveau fichier vide avec les colonnes requises
                empty_df = pd.DataFrame(columns=['Prenoms', 'Noms', 'Groupe', 'Guerite', 'telephone'])
                empty_df.to_excel("eleves.xlsx", index=False, engine="openpyxl")
                
                return render_template("manage_students.html", 
                                   success=True,
                                   message="Liste d'élèves supprimée avec succès")
            except Exception as e:
                return render_template("manage_students.html", erreur=str(e))
        
        elif action == "upload_new":
            try:
                if 'file' not in request.files:
                    return render_template("manage_students.html", 
                                       erreur="Aucun fichier sélectionné")
                
                file = request.files['file']
                if file.filename == '':
                    return render_template("manage_students.html", 
                                       erreur="Aucun fichier sélectionné")
                
                if file and file.filename.endswith('.xlsx'):
                    # Sauvegarder le nouveau fichier
                    file.save("eleves.xlsx")
                    
                    # Organiser les groupes aléatoirement avec taille personnalisée
                    group_size = int(request.form.get("group_size", 4))
                    df = pd.read_excel("eleves.xlsx", engine="openpyxl")
                    df = organize_random_groups(df, group_size)
                    df.to_excel("eleves.xlsx", index=False, engine="openpyxl")
                    
                    total_students = len(df)
                    num_groups = df['Groupe'].nunique()
                    
                    return render_template("manage_students.html", 
                                       success=True,
                                       message=f"Nouvelle liste importée et organisée en {num_groups} groupes de {group_size} personnes maximum ({total_students} élèves au total)")
                else:
                    return render_template("manage_students.html", 
                                       erreur="Veuillez sélectionner un fichier Excel (.xlsx)")
            except Exception as e:
                return render_template("manage_students.html", erreur=str(e))
    
    return render_template("manage_students.html")

def organize_random_groups(df, group_size=None):
    """Organiser les élèves en groupes de manière aléatoire avec taille personnalisée"""
    if df.empty:
        return df
    
    # Si aucune taille n'est spécifiée, utiliser 4 par défaut
    if group_size is None:
        group_size = 4
    
    # Mélanger les élèves aléatoirement
    df_shuffled = df.sample(frac=1).reset_index(drop=True)
    
    # Assigner des groupes
    total_students = len(df_shuffled)
    num_groups = (total_students + group_size - 1) // group_size
    
    for i in range(num_groups):
        start_idx = i * group_size
        end_idx = min((i + 1) * group_size, total_students)
        
        if start_idx < total_students:
            df_shuffled.loc[start_idx:end_idx-1, 'Groupe'] = i + 1
    
    return df_shuffled

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
