// Sonnerie + bouton arrêter
let son = new Audio("/static/sounds/alarm.wav");
let alerteActive = false;

function demarrerAlerte() {
    if (!alerteActive) {
        son.loop = true;
        son.play();
        alerteActive = true;
        document.getElementById("btnStop").style.display = "inline-block";
    }
}

function arreterAlerte() {
    son.pause();
    son.currentTime = 0;
    alerteActive = false;
    document.getElementById("btnStop").style.display = "none";
}
