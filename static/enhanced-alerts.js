// Système d'alertes amélioré pour le programme de permanence

class EnhancedAlertSystem {
    constructor() {
        this.audioContext = null;
        this.isAudioEnabled = true;
        this.isNotificationEnabled = true;
        this.alertHistory = [];
        this.checkInterval = 30000; // 30 secondes
        this.lastCheckTime = null;
        
        this.init();
    }

    init() {
        // Initialiser le contexte audio pour une meilleure gestion du son
        try {
            window.AudioContext = window.AudioContext || window.webkitAudioContext;
            this.audioContext = new AudioContext();
        } catch (e) {
            console.warn('AudioContext non supporté:', e);
        }

        // Demander la permission pour les notifications
        this.requestNotificationPermission();
        
        // Démarrer la vérification périodique
        this.startPeriodicCheck();
        
        // Enregistrer les événements de visibilité de la page
        document.addEventListener('visibilitychange', () => this.handleVisibilityChange());
        
        console.log('Système d\'alertes amélioré initialisé');
    }

    async requestNotificationPermission() {
        if ('Notification' in window && Notification.permission === 'default') {
            const permission = await Notification.requestPermission();
            this.isNotificationEnabled = permission === 'granted';
            return permission;
        }
        return Notification.permission;
    }

    async startPeriodicCheck() {
        // Vérifier immédiatement
        await this.checkAlerts();
        
        // Puis vérifier périodiquement
        setInterval(async () => {
            if (!document.hidden) {
                await this.checkAlerts();
            }
        }, this.checkInterval);
    }

    async checkAlerts() {
        try {
            const response = await fetch('/enhanced-alert-check');
            const data = await response.json();
            
            this.lastCheckTime = new Date();
            
            if (data.should_alert && this.isAudioEnabled) {
                await this.playEnhancedAlert(data);
            }
            
            // Mettre à jour l'interface si nécessaire
            this.updateAlertStatus(data);
            
        } catch (error) {
            console.error('Erreur lors de la vérification des alertes:', error);
        }
    }

    async playEnhancedAlert(alertData) {
        try {
            // Jouer le son d'alarme
            await this.playAlarmSound();
            
            // Afficher la notification de navigateur
            if (this.isNotificationEnabled && alertData.user_logged_in) {
                this.showBrowserNotification(alertData);
            }
            
            // Ajouter à l'historique
            this.addToHistory(alertData, 'ALERT');
            
        } catch (error) {
            console.error('Erreur lors de la lecture de l\'alerte:', error);
        }
    }

    async playAlarmSound() {
        return new Promise((resolve, reject) => {
            try {
                const audio = new Audio('/static/alarm.wav');
                
                audio.addEventListener('ended', () => {
                    resolve();
                }, { once: true });
                
                audio.addEventListener('error', (e) => {
                    console.error('Erreur audio:', e);
                    reject(e);
                }, { once: true });
                
                // Démarrer l'audio
                audio.play().catch(e => {
                    console.warn('Erreur lecture audio:', e);
                    resolve(); // Continuer même si le son échoue
                });
                
            } catch (error) {
                reject(error);
            }
        });
    }

    showBrowserNotification(alertData) {
        if ('Notification' in window && Notification.permission === 'granted') {
            const notification = new Notification('ALERTE DE PERMANENCE', {
                body: `Bonjour ${alertData.user_name}, votre service commence dans 30 minutes!`,
                icon: '/static/logo_douanes.png',
                badge: '/static/logo_douanes.png',
                tag: 'permanence-alert',
                requireInteraction: true,
                silent: false
            });
            
            // Fermer automatiquement après 10 secondes
            setTimeout(() => {
                notification.close();
            }, 10000);
            
            // Gérer le clic sur la notification
            notification.onclick = () => {
                window.focus();
                notification.close();
            };
        }
    }

    addToHistory(alertData, type) {
        const entry = {
            timestamp: new Date().toISOString(),
            type: type,
            data: alertData,
            user: alertData.user_name || 'Inconnu'
        };
        
        this.alertHistory.unshift(entry);
        
        // Limiter l'historique à 50 entrées
        if (this.alertHistory.length > 50) {
            this.alertHistory = this.alertHistory.slice(0, 50);
        }
        
        // Sauvegarder dans le localStorage
        try {
            localStorage.setItem('alertHistory', JSON.stringify(this.alertHistory));
        } catch (e) {
            console.warn('Impossible de sauvegarder l\'historique:', e);
        }
    }

    updateAlertStatus(alertData) {
        // Mettre à jour les indicateurs visuels si nécessaire
        const statusIndicator = document.getElementById('alertStatus');
        if (statusIndicator) {
            if (alertData.should_alert) {
                statusIndicator.className = 'alert-active';
                statusIndicator.textContent = 'ALERTE ACTIVE';
            } else {
                statusIndicator.className = 'alert-inactive';
                statusIndicator.textContent = 'Aucune alerte';
            }
        }
    }

    handleVisibilityChange() {
        if (document.hidden) {
            // La page est cachée, vérifier moins fréquemment
            this.checkInterval = 60000; // 1 minute
        } else {
            // La page est visible, vérifier plus fréquemment
            this.checkInterval = 30000; // 30 secondes
        }
    }

    // Méthodes utilitaires
    getAlertHistory() {
        return this.alertHistory;
    }

    clearHistory() {
        this.alertHistory = [];
        try {
            localStorage.removeItem('alertHistory');
        } catch (e) {
            console.warn('Impossible de supprimer l\'historique:', e);
        }
    }

    setAudioEnabled(enabled) {
        this.isAudioEnabled = enabled;
    }

    setNotificationEnabled(enabled) {
        this.isNotificationEnabled = enabled;
    }

    async testSystem() {
        console.log('Test du système d\'alerte...');
        
        // Tester le son
        try {
            await this.playAlarmSound();
            console.log('✅ Test audio réussi');
        } catch (error) {
            console.error('❌ Test audio échoué:', error);
        }
        
        // Tester la notification
        try {
            this.showBrowserNotification({
                user_name: 'Utilisateur Test',
                should_alert: true
            });
            console.log('✅ Test notification réussi');
        } catch (error) {
            console.error('❌ Test notification échoué:', error);
        }
    }
}

// Initialiser le système quand le DOM est chargé
document.addEventListener('DOMContentLoaded', function() {
    window.enhancedAlertSystem = new EnhancedAlertSystem();
    
    // Rendre disponible globalement
    window.testAlert = () => window.enhancedAlertSystem.testSystem();
    window.clearAlertHistory = () => window.enhancedAlertSystem.clearHistory();
    
    console.log('Système d\'alertes amélioré chargé et prêt');
});
