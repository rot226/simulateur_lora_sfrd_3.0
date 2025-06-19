# node.py
import math

# Typical operating voltage (V)
VOLTAGE_V = 3.3
# Default currents (A) based on Semtech datasheets
SLEEP_CURRENT_A = 1e-6      # 1 µA in sleep
RX_CURRENT_A = 11e-3        # ~11 mA in RX
PROCESS_CURRENT_A = 5e-3    # ~5 mA for MCU processing
RX_WINDOW_DURATION = 0.1    # duration of RX windows in seconds

# Approximate FLoRa profile values. These numbers are loosely based on
# typical SX127x characteristics used by the FLoRa model. They allow the
# simulator to more closely match the energy behaviour of FLoRa without
# depending on the OMNeT++ code.
FLO_RA_PROFILE = {
    'voltage_v': 3.3,
    'sleep_current_a': 1e-6,
    'rx_current_a': 11e-3,
    'process_current_a': 2e-3,  # microcontroller processing
    'rx_window_duration': 1.0,
    # TX current by power level in dBm
    'tx_currents_a': {
        2: 24e-3,
        5: 30e-3,
        8: 35e-3,
        11: 44e-3,
        14: 87e-3,
        17: 120e-3,
        20: 150e-3,
    },
}

class Node:
    """
    Représente un nœud IoT (LoRa) dans la simulation, avec suivi complet des métriques de performance.
    
    Attributs :
        id (int) : Identifiant unique du nœud.
        initial_x (float), initial_y (float) : Position initiale du nœud (mètres).
        x (float), y (float) : Position courante du nœud (mètres).
        initial_sf (int), sf (int) : SF (spreading factor) initial et actuel du nœud.
        initial_tx_power (float), tx_power (float) : Puissance TX initiale et actuelle (dBm).
        energy_consumed (float) : Énergie totale consommée (toutes activités, Joules).
        energy_tx (float) : Énergie dépensée lors des transmissions.
        energy_rx (float) : Énergie dépensée en réception.
        energy_sleep (float) : Énergie dépensée en veille.
        energy_processing (float) : Énergie dépensée en traitement.
        packets_sent (int) : Nombre total de paquets émis par ce nœud.
        packets_success (int) : Nombre de paquets reçus avec succès.
        packets_collision (int) : Nombre de paquets perdus en raison de collisions.
        speed (float) : Vitesse (m/s) en cas de mobilité.
        direction (float) : Direction du déplacement (radians) en cas de mobilité.
        vx (float), vy (float) : Composantes de la vitesse en X et Y (m/s).
        last_move_time (float) : Dernier instant (s) où la position a été mise à jour (mobilité).
    """

    def __init__(self, node_id: int, x: float, y: float, sf: int, tx_power: float,
                 channel=None, devaddr: int | None = None, class_type: str = 'A',
                 profile: str | dict | None = None):
        """
        Initialise le nœud avec ses paramètres de départ. Le paramètre
        ``profile`` permet d'appliquer les valeurs d'énergie d'un profil
        spécifique (par ex. ``"flora"``) ou un dictionnaire personnalisé.
        
        :param node_id: Identifiant du nœud.
        :param x: Position X initiale (mètres).
        :param y: Position Y initiale (mètres).
        :param sf: Spreading Factor initial (entre 7 et 12).
        :param tx_power: Puissance d'émission initiale (dBm).
        :param profile: Nom du profil d'énergie à utiliser ou dictionnaire
            personnalisé. ``None`` applique les constantes par défaut.
        """
        # Identité et paramètres initiaux
        self.id = node_id
        self.initial_x = x
        self.initial_y = y
        self.x = x
        self.y = y
        self.initial_sf = sf
        self.sf = sf
        self.initial_tx_power = tx_power
        self.tx_power = tx_power
        # Canal radio attribué (peut être modifié par le simulateur)
        self.channel = channel

        # --------------------------------------------------------------
        # Energy profile configuration
        # --------------------------------------------------------------
        if profile == 'flora':
            p = FLO_RA_PROFILE
        elif isinstance(profile, dict):
            p = {**FLO_RA_PROFILE, **profile}
        else:
            p = {
                'voltage_v': VOLTAGE_V,
                'sleep_current_a': SLEEP_CURRENT_A,
                'rx_current_a': RX_CURRENT_A,
                'process_current_a': PROCESS_CURRENT_A,
                'rx_window_duration': RX_WINDOW_DURATION,
                'tx_currents_a': None,
            }

        self.voltage_v = p['voltage_v']
        self.sleep_current_a = p['sleep_current_a']
        self.rx_current_a = p['rx_current_a']
        self.process_current_a = p['process_current_a']
        self.rx_window_duration = p['rx_window_duration']
        self.tx_currents = p['tx_currents_a']
        
        # Énergie et compteurs de paquets
        self.energy_consumed = 0.0
        self.energy_tx = 0.0
        self.energy_rx = 0.0
        self.energy_sleep = 0.0
        self.energy_processing = 0.0
        self.packets_sent = 0
        self.packets_success = 0
        self.packets_collision = 0
        
        # Paramètres de mobilité (initialement immobile)
        self.speed = 0.0       # Vitesse en m/s
        self.direction = 0.0   # Direction en radians
        self.vx = 0.0          # Vitesse en X (m/s)
        self.vy = 0.0          # Vitesse en Y (m/s)
        self.last_move_time = 0.0  # Temps du dernier déplacement (s)
        self.path = None
        self.path_progress = 0.0
        self.path_duration = 0.0

        # LoRaWAN specific parameters
        self.devaddr = devaddr if devaddr is not None else node_id
        self.fcnt_up = 0
        self.fcnt_down = 0
        self.class_type = class_type
        self.awaiting_ack = False
        self.pending_mac_cmd = None
        self.need_downlink_ack = False

        # Additional state used by the simulator
        self.history: list[dict] = []
        self.in_transmission: bool = False
        self.current_end_time: float | None = None
        self.last_rssi: float | None = None
        self.last_snr: float | None = None
        self.downlink_pending: int = 0
        self.acks_received: int = 0

        # Energy accounting state
        self.last_state_time = 0.0
        self.state = 'sleep'

    def distance_to(self, other) -> float:
        """
        Calcule la distance euclidienne (mètres) entre ce nœud et un autre objet possédant 
        des attributs x et y (par exemple une passerelle).
        
        :param other: Objet avec attributs x et y.
        :return: Distance euclidienne (mètres).
        """
        dx = self.x - other.x
        dy = self.y - other.y
        return math.hypot(dx, dy)

    def __repr__(self):
        """
        Représentation en chaîne pour débogage, affichant l'ID, la position et le SF actuel.
        """
        return (f"Node(id={self.id}, pos=({self.x:.1f},{self.y:.1f}), "
                f"SF={self.sf}, TxPower={self.tx_power:.1f} dBm)")

    def to_dict(self) -> dict:
        """
        Retourne les données finales du nœud sous forme de dictionnaire, prêt pour 
        l'export en DataFrame/CSV. 
        Les positions finales et valeurs finales de SF/TxPower sont les valeurs courantes.
        """
        return {
            'node_id': self.id,
            'initial_x': self.initial_x,
            'initial_y': self.initial_y,
            'final_x': self.x,
            'final_y': self.y,
            'initial_sf': self.initial_sf,
            'final_sf': self.sf,
            'initial_tx_power': self.initial_tx_power,
            'final_tx_power': self.tx_power,
            'energy_tx_J': self.energy_tx,
            'energy_rx_J': self.energy_rx,
            'energy_sleep_J': self.energy_sleep,
            'energy_processing_J': self.energy_processing,
            'energy_consumed_J': self.energy_consumed,
            'packets_sent': self.packets_sent,
            'packets_success': self.packets_success,
            'packets_collision': self.packets_collision,
            'downlink_pending': self.downlink_pending,
            'acks_received': self.acks_received
        }

    def increment_sent(self):
        """Incrémente le compteur de paquets envoyés."""
        self.packets_sent += 1

    def increment_success(self):
        """Incrémente le compteur de paquets transmis avec succès."""
        self.packets_success += 1

    def increment_collision(self):
        """Incrémente le compteur de paquets perdus en collision."""
        self.packets_collision += 1

    # ------------------------------------------------------------------
    # PDR utilities
    # ------------------------------------------------------------------

    @property
    def pdr(self) -> float:
        """Retourne le PDR global de ce nœud."""
        return self.packets_success / self.packets_sent if self.packets_sent > 0 else 0.0

    @property
    def recent_pdr(self) -> float:
        """PDR calculé sur l'historique glissant."""
        total = len(self.history)
        if total == 0:
            return 0.0
        success = sum(1 for e in self.history if e.get('delivered'))
        return success / total

    def add_energy(self, energy_joules: float, state: str = "tx"):
        """Ajoute de l'énergie consommée pour un état donné."""
        self.energy_consumed += energy_joules
        if state == "tx":
            self.energy_tx += energy_joules
        elif state == "rx":
            self.energy_rx += energy_joules
        elif state == "sleep":
            self.energy_sleep += energy_joules
        elif state == "processing":
            self.energy_processing += energy_joules

    def consume_until(self, current_time: float) -> None:
        """Accumulates energy from ``last_state_time`` up to ``current_time``."""
        dt = current_time - self.last_state_time
        if dt <= 0:
            self.last_state_time = current_time
            return
        if self.state == "sleep":
            self.add_energy(self.sleep_current_a * self.voltage_v * dt, "sleep")
        elif self.state == "rx":
            self.add_energy(self.rx_current_a * self.voltage_v * dt, "rx")
        elif self.state == "processing":
            self.add_energy(self.process_current_a * self.voltage_v * dt, "processing")
        self.last_state_time = current_time

    # --------------------------------------------------------------
    # Energy helpers
    # --------------------------------------------------------------
    def tx_current(self, tx_power_dbm: float) -> float:
        """Return the transmit current for the given power in dBm."""
        if self.tx_currents:
            key = int(round(tx_power_dbm))
            if key in self.tx_currents:
                return self.tx_currents[key]
            closest = min(self.tx_currents.keys(), key=lambda k: abs(k - key))
            return self.tx_currents[closest]
        p_mw = 10 ** (tx_power_dbm / 10.0)
        return p_mw / (self.voltage_v * 1000.0)

    # ------------------------------------------------------------------
    # LoRaWAN helper methods
    # ------------------------------------------------------------------
    def prepare_uplink(self, payload: bytes, confirmed: bool = False):
        """Build an uplink LoRaWAN frame and increment the counter."""
        from .lorawan import LoRaWANFrame

        if self.pending_mac_cmd:
            payload = self.pending_mac_cmd + payload
            self.pending_mac_cmd = None

        mhdr = 0x40 if not confirmed else 0x80
        fctrl = 0x20 if self.need_downlink_ack else 0
        frame = LoRaWANFrame(
            mhdr=mhdr, fctrl=fctrl, fcnt=self.fcnt_up, payload=payload, confirmed=confirmed
        )
        self.fcnt_up += 1
        if confirmed:
            self.awaiting_ack = True
        self.need_downlink_ack = False
        return frame

    def handle_downlink(self, frame):
        """Process a received downlink frame."""
        from .lorawan import (
            LinkADRReq,
            LinkADRAns,
            LinkCheckReq,
            LinkCheckAns,
            DeviceTimeReq,
            DeviceTimeAns,
            DR_TO_SF,
            TX_POWER_INDEX_TO_DBM,
        )

        self.fcnt_down = frame.fcnt + 1
        if frame.confirmed:
            self.awaiting_ack = False
            self.acks_received += 1

        if frame.fctrl & 0x20:
            self.need_downlink_ack = True

        self.downlink_pending = max(0, self.downlink_pending - 1)

        if isinstance(frame.payload, bytes):
            if len(frame.payload) >= 5 and frame.payload[0] == 0x03:
                try:
                    req = LinkADRReq.from_bytes(frame.payload[:5])
                    self.sf = DR_TO_SF.get(req.datarate, self.sf)
                    self.tx_power = TX_POWER_INDEX_TO_DBM.get(req.tx_power, self.tx_power)
                    self.pending_mac_cmd = LinkADRAns().to_bytes()
                except Exception:
                    pass
            elif frame.payload == LinkCheckReq().to_bytes():
                self.pending_mac_cmd = LinkCheckAns(margin=255, gw_cnt=1).to_bytes()
            elif frame.payload == DeviceTimeReq().to_bytes():
                self.pending_mac_cmd = DeviceTimeAns(int(self.fcnt_up)).to_bytes()
            elif frame.payload.startswith(b"ADR:"):
                try:
                    _, sf_str, pwr_str = frame.payload.decode().split(":")
                    self.sf = int(sf_str)
                    self.tx_power = float(pwr_str)
                except Exception:
                    pass

    def schedule_receive_windows(self, end_time: float):
        """Return RX1 and RX2 times for the last uplink."""
        from .lorawan import compute_rx1, compute_rx2

        return compute_rx1(end_time), compute_rx2(end_time)
