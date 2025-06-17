# node.py
import math

class Node:
    """
    Représente un nœud IoT (LoRa) dans la simulation, avec suivi complet des métriques de performance.
    
    Attributs :
        id (int) : Identifiant unique du nœud.
        initial_x (float), initial_y (float) : Position initiale du nœud (mètres).
        x (float), y (float) : Position courante du nœud (mètres).
        initial_sf (int), sf (int) : SF (spreading factor) initial et actuel du nœud.
        initial_tx_power (float), tx_power (float) : Puissance TX initiale et actuelle (dBm).
        energy_consumed (float) : Énergie totale consommée en transmission (Joules).
        packets_sent (int) : Nombre total de paquets émis par ce nœud.
        packets_success (int) : Nombre de paquets reçus avec succès.
        packets_collision (int) : Nombre de paquets perdus en raison de collisions.
        speed (float) : Vitesse (m/s) en cas de mobilité.
        direction (float) : Direction du déplacement (radians) en cas de mobilité.
        vx (float), vy (float) : Composantes de la vitesse en X et Y (m/s).
        last_move_time (float) : Dernier instant (s) où la position a été mise à jour (mobilité).
    """

    def __init__(self, node_id: int, x: float, y: float, sf: int, tx_power: float, channel=None):
        """
        Initialise le nœud avec ses paramètres de départ.
        
        :param node_id: Identifiant du nœud.
        :param x: Position X initiale (mètres).
        :param y: Position Y initiale (mètres).
        :param sf: Spreading Factor initial (entre 7 et 12).
        :param tx_power: Puissance d'émission initiale (dBm).
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
        
        # Énergie et compteurs de paquets
        self.energy_consumed = 0.0
        self.packets_sent = 0
        self.packets_success = 0
        self.packets_collision = 0
        
        # Paramètres de mobilité (initialement immobile)
        self.speed = 0.0       # Vitesse en m/s
        self.direction = 0.0   # Direction en radians
        self.vx = 0.0          # Vitesse en X (m/s)
        self.vy = 0.0          # Vitesse en Y (m/s)
        self.last_move_time = 0.0  # Temps du dernier déplacement (s)

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
            'energy_consumed_J': self.energy_consumed,
            'packets_sent': self.packets_sent,
            'packets_success': self.packets_success,
            'packets_collision': self.packets_collision
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

    def add_energy(self, energy_joules: float):
        """
        Ajoute de l'énergie consommée en transmission.
        
        :param energy_joules: Énergie (J) dépensée lors de l'envoi d'un paquet.
        """
        self.energy_consumed += energy_joules
