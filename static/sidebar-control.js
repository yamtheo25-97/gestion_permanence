// Contrôle universel de la sidebar pour toutes les pages

class SidebarController {
    constructor() {
        this.isCollapsed = true;
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
            console.warn('Sidebar ou bouton hamburger non trouvé');
            return;
        }

        // S'assurer que la sidebar est rétractée au chargement
        this.ensureCollapsed();
        
        // Attacher les événements
        this.attachEvents();
        
        console.log('Contrôleur de sidebar initialisé');
    }

    ensureCollapsed() {
        if (!this.sidebar.classList.contains('collapsed')) {
            this.sidebar.classList.add('collapsed');
            this.hamburgerBtn.classList.add('active');
            this.isCollapsed = true;
        }
    }

    attachEvents() {
        // Bouton hamburger
        this.hamburgerBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            this.toggle();
        });

        // Clic à l'extérieur pour fermer
        document.addEventListener('click', (e) => {
            if (!this.isCollapsed && 
                !this.sidebar.contains(e.target) && 
                !this.hamburgerBtn.contains(e.target)) {
                this.collapse();
            }
        });

        // Empêcher la propagation depuis la sidebar
        this.sidebar.addEventListener('click', (e) => {
            e.stopPropagation();
        });

        // Gestion du clavier (ESC pour fermer)
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && !this.isCollapsed) {
                this.collapse();
            }
        });
    }

    toggle() {
        if (this.isCollapsed) {
            this.expand();
        } else {
            this.collapse();
        }
    }

    expand() {
        this.sidebar.classList.remove('collapsed');
        this.hamburgerBtn.classList.remove('active');
        this.isCollapsed = false;
    }

    collapse() {
        this.sidebar.classList.add('collapsed');
        this.hamburgerBtn.classList.add('active');
        this.isCollapsed = true;
    }

    // Méthodes utilitaires
    getState() {
        return {
            isCollapsed: this.isCollapsed,
            sidebar: this.sidebar,
            hamburgerBtn: this.hamburgerBtn
        };
    }

    forceCollapse() {
        this.collapse();
    }

    forceExpand() {
        this.expand();
    }
}

// Créer l'instance globale
window.sidebarController = new SidebarController();

// Fonctions globales pour compatibilité
window.toggleSidebar = () => window.sidebarController.toggle();
window.collapseSidebar = () => window.sidebarController.collapse();
window.expandSidebar = () => window.sidebarController.expand();

// Export pour les modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = SidebarController;
}
