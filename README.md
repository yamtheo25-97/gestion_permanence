# Programme de Permanence

Application Flask pour gérer des permanences/rotations avec système d'alerte et d'alarme.

## Fonctionnalités

- **Authentification** : Connexion avec nom et prénom
- **Gestion de permanence** : Ajout de numéro de téléphone
- **Planification** : Génération automatique de rotations (2h par créneau, 6h–18h, sur 4 jours+)
- **Rotation des groupes** : Support des groupes avec rotation de guérite (Nord/Sud) en interne
- **Alertes** : Notifications 30 minutes avant un créneau avec modal et alarme sonore
- **Tableau de bord** : Affichage de la rotation actuelle/prochaine et des alertes utilisateur
- **Menu planning** : Vue détaillée du planning avec mise à jour auto (polling)

## Structure du projet

```
.
├── app.py                    # Application Flask principale
├── eleves.xlsx              # Base de données élèves/groupes
├── alertes.xlsx             # Fichier alertes (optionnel)
├── requirements.txt         # Dépendances Python
├── .gitignore              # Configuration git
├── static/
│   ├── style.css           # Styles CSS
│   └── alertes.js          # Scripts alertes (optionnel)
└── templates/
    ├── login.html          # Page de connexion
    ├── add_phone.html      # Ajout numéro téléphone
    ├── dashboard.html      # Tableau de bord
    ├── menu.html           # Page planning
    └── ...
```

## Installation

### Pré-requis
- Python 3.12+
- pip

### Setup

1. Clonez ou téléchargez le projet :
   ```bash
   git clone https://github.com/<votre-username>/gestion_permanence_python.git
   cd gestion_permanence_python
   ```

2. Créez et activez un environnement virtuel :
   ```bash
   python -m venv .venv
   .venv\Scripts\activate  # Windows
   # ou
   source .venv/bin/activate  # macOS/Linux
   ```

3. Installez les dépendances :
   ```bash
   pip install -r requirements.txt
   ```

## Utilisation

Lancez l'application Flask en mode développement :
```bash
python app.py
```

Accédez à `http://localhost:5000` dans votre navigateur.

### Flux utilisateur

1. **Login** : Entrez votre nom et prénom (basé sur `eleves.xlsx`)
2. **Ajouter téléphone** : Entrez votre numéro de téléphone
3. **Menu / Planning** : Consulter la rotation pour les 4 prochains jours
4. **Tableau de bord** : Voir les alertes et la rotation actuelle + alerte sonore 30min avant

## Configuration

Les données sont stockées dans des fichiers Excel :
- **eleves.xlsx** : Colonnes requises : `Noms`, `Prenoms`, `Groupe`, `Guerite`, `telephone`
- **alertes.xlsx** : Colonnes requises : `Noms`, `Prenoms`, `Message`, `Date`, `Type`

Les rotations commencent demain à 6h00 et couvrent 4 jours par défaut (extensible).

## Routes principales

- `GET /` : Connexion
- `POST /` : Validation login
- `GET /add_phone` : Formulaire numéro téléphone
- `GET /menu` : Page planning
- `GET /menu/data` : Données planning (JSON, polling)
- `GET /current-shift` : Créneau actuel/prochain (JSON)
- `GET /alert-check` : Vérification alerte 30min (JSON)
- `GET /dashboard` : Tableau de bord
- `GET /logout` : Déconnexion

## Licences & Crédits

Projet interne de gestion de permanence — 2026.

## Support

Pour toute question ou problème, consultez le code dans `app.py` ou les templates.
