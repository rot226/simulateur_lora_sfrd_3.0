import logging

logger = logging.getLogger(__name__)

class NetworkServer:
    """Représente le serveur de réseau LoRa (collecte des paquets reçus)."""
    def __init__(self):
        """Initialise le serveur réseau."""
        # Ensemble des identifiants d'événements déjà reçus (pour éviter les doublons)
        self.received_events = set()
        # Stockage optionnel d'infos sur les réceptions (par ex : via quelle passerelle)
        self.event_gateway = {}
        # Compteur de paquets reçus
        self.packets_received = 0
        # Indicateur ADR serveur
        self.adr_enabled = False
        # Références pour ADR serveur
        self.nodes = []
        self.gateways = []
        self.channel = None

    # ------------------------------------------------------------------
    # Downlink management
    # ------------------------------------------------------------------
    def send_downlink(
        self,
        node,
        payload: bytes = b"",
        confirmed: bool = False,
        adr_command: tuple[int, float] | None = None,
    ):
        """Queue a downlink frame for a node via the first gateway."""
        from .lorawan import (
            LoRaWANFrame,
            LinkADRReq,
            SF_TO_DR,
            DBM_TO_TX_POWER_INDEX,
        )

        gw = self.gateways[0] if self.gateways else None
        if gw is None:
            return
        frame = LoRaWANFrame(
            mhdr=0x60, fctrl=0, fcnt=node.fcnt_down, payload=payload, confirmed=confirmed
        )
        if adr_command:
            sf, power = adr_command
            dr = SF_TO_DR.get(sf, 5)
            p_idx = DBM_TO_TX_POWER_INDEX.get(int(power), 0)
            frame.payload = LinkADRReq(dr, p_idx).to_bytes()
        node.fcnt_down += 1
        gw.buffer_downlink(node.id, frame)
        try:
            node.downlink_pending += 1
        except AttributeError:
            pass

    def receive(self, event_id: int, node_id: int, gateway_id: int, rssi: float | None = None):
        """
        Traite la réception d'un paquet par le serveur.
        Évite de compter deux fois le même paquet s'il arrive via plusieurs passerelles.
        :param event_id: Identifiant unique de l'événement de transmission du paquet.
        :param node_id: Identifiant du nœud source.
        :param gateway_id: Identifiant de la passerelle ayant reçu le paquet.
        :param rssi: RSSI mesuré par la passerelle pour ce paquet (optionnel).
        """
        if event_id in self.received_events:
            # Doublon (déjà reçu via une autre passerelle)
            logger.debug(f"NetworkServer: duplicate packet event {event_id} from node {node_id} (ignored).")
            return
        # Nouveau paquet reçu
        self.received_events.add(event_id)
        self.event_gateway[event_id] = gateway_id
        self.packets_received += 1
        logger.debug(f"NetworkServer: packet event {event_id} from node {node_id} received via gateway {gateway_id}.")

        # Appliquer ADR au niveau serveur si activé
        if self.adr_enabled and rssi is not None:
            from .lorawan import SF_TO_DR, DBM_TO_TX_POWER_INDEX, LinkADRReq

            node = next((n for n in self.nodes if n.id == node_id), None)
            if node:
                new_sf = node.sf
                if rssi > -120 and node.sf > 7:
                    new_sf -= 1
                elif rssi < -120 and node.sf < 12:
                    new_sf += 1
                if new_sf != node.sf:
                    dr = SF_TO_DR.get(new_sf, SF_TO_DR.get(node.sf, 5))
                    p_idx = DBM_TO_TX_POWER_INDEX.get(int(node.tx_power), 0)
                    down = LinkADRReq(dr, p_idx).to_bytes()
                    self.send_downlink(node, down)
