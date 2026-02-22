// Script commun pour la gestion de la barre de navigation

class NavigationManager {
    constructor() {
        this.sidebar = null;
        this.hamburgerBtn = null;
        this.init();
    }

    init() {
        // Attendre que le DOM soit chargé
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => this.setup());
        } else {
            this.setup();
        }
    }

    setup() {
        this.sidebar = document.getElementById('sidebar');
        this.hamburgerBtn = document.getElementById('hamburgerBtn');

        if (!this.sidebar || !this.hamburgerBtn) {
            console.warn('Éléments de navigation non trouvés');
            return;
        }

        // Attacher les événements
        this.attachEvents();
    }

    attachEvents() {
        // Bouton hamburger - SEUL ÉVÉNEMENT QUI DOIT DÉCLENCHER LE TOGGLE
        this.hamburgerBtn.addEventListener('click', (e) => {
            e.stopPropagation(); // Empêcher la propagation
            this.toggleSidebar();
        });

        // Empêcher la propagation des clics dans la sidebar
        this.sidebar.addEventListener('click', (e) => {
            e.stopPropagation();
        });

        // SUPPRIMÉ : Plus de gestion de clic extérieur pour éviter l'ouverture automatique
        // La sidebar doit rester strictement cachée par défaut
    }

    toggleSidebar() {
        // Utiliser une classe unique .sidebar-open pour plus de clarté
        if (this.sidebar.classList.contains('sidebar-open')) {
            this.sidebar.classList.remove('sidebar-open');
            this.sidebar.classList.add('collapsed');
            this.hamburgerBtn.classList.remove('active');
        } else {
            this.sidebar.classList.remove('collapsed');
            this.sidebar.classList.add('sidebar-open');
            this.hamburgerBtn.classList.add('active');
        }
    }

    // Méthodes utilitaires
    collapse() {
        this.sidebar.classList.remove('sidebar-open');
        this.sidebar.classList.add('collapsed');
        this.hamburgerBtn.classList.remove('active');
    }

    expand() {
        this.sidebar.classList.remove('collapsed');
        this.sidebar.classList.add('sidebar-open');
        this.hamburgerBtn.classList.add('active');
    }

    isCollapsed() {
        return this.sidebar.classList.contains('collapsed');
    }

    isOpen() {
        return this.sidebar.classList.contains('sidebar-open');
    }
}

// Initialiser automatiquement le gestionnaire de navigation
window.navigationManager = new NavigationManager();

// Rendre disponible globalement pour compatibilité
window.toggleSidebar = () => {
    window.navigationManager.toggleSidebar();
};

// Exporter pour les modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = NavigationManager;
}
