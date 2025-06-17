import argparse
import csv
import random
import logging

# Configuration du logger pour afficher les informations
logging.basicConfig(level=logging.INFO, format='%(message)s')

def simulate(nodes, gateways, area, mode, interval, steps):
    """Exécute une simulation LoRa simplifiée et retourne les métriques."""
    # Initialisation des compteurs
    total_transmissions = 0
    collisions = 0
    delivered = 0
    energy_consumed = 0.0
    delays = []  # stockera le délai de chaque paquet livré

    # Génération des instants d'émission pour chaque nœud
    send_times = {node: [] for node in range(nodes)}
    for node in range(nodes):
        if mode.lower() == "periodic":
            t = 0
            while t < steps:
                send_times[node].append(t)
                t += interval
        else:  # mode "Random"
            # Émission aléatoire avec probabilité 1/interval à chaque pas de temps
            for t in range(steps):
                if random.random() < 1.0/interval:
                    send_times[node].append(t)

    # Simulation pas à pas
    for t in range(steps):
        transmitting_nodes = [node for node, times in send_times.items() if t in times]
        nb_tx = len(transmitting_nodes)
        if nb_tx > 0:
            total_transmissions += nb_tx
            if nb_tx == 1:
                # Un seul nœud émet à ce pas -> succès
                delivered += 1
                energy_consumed += 1.0  # consommation d'énergie d'une transmission
                delays.append(0)  # délai nul (livraison immédiate)
            else:
                # Plusieurs émettent -> collision pour tous ces paquets
                collisions += nb_tx  # on compte chaque paquet perdu comme collision
                energy_consumed += nb_tx * 1.0  # chaque nœud a tout de même dépensé de l'énergie

    # Calcul des métriques finales
    pdr = (delivered / total_transmissions) * 100 if total_transmissions > 0 else 0
    avg_delay = (sum(delays) / len(delays)) if delays else 0

    return delivered, collisions, pdr, energy_consumed, avg_delay

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Simulateur LoRa – Mode CLI")
    parser.add_argument("--nodes", type=int, default=10, help="Nombre de nœuds")
    parser.add_argument("--gateways", type=int, default=1, help="Nombre de gateways")
    parser.add_argument("--area", type=int, default=1000, help="Taille de l'aire de simulation (côté du carré)")
    parser.add_argument("--mode", choices=["Random", "Periodic"], default="Random", help="Mode de transmission")
    parser.add_argument("--interval", type=int, default=10, help="Intervalle moyen ou fixe entre transmissions")
    parser.add_argument("--steps", type=int, default=100, help="Nombre de pas de temps de la simulation")
    parser.add_argument("--output", type=str, help="Fichier CSV pour sauvegarder les résultats (optionnel)")
    args = parser.parse_args()

    logging.info(f"Simulation d'un réseau LoRa : {args.nodes} nœuds, {args.gateways} gateways, "
                 f"aire={args.area}m, mode={args.mode}, intervalle={args.interval}, steps={args.steps}")
    delivered, collisions, pdr, energy, avg_delay = simulate(
        args.nodes, args.gateways, args.area, args.mode, args.interval, args.steps
    )
    logging.info(f"Résultats : PDR={pdr:.2f}% , Paquets livrés={delivered}, Collisions={collisions}, "
                 f"Énergie consommée={energy:.1f} unités, Délai moyen={avg_delay:.2f} unités de temps")

    # Sauvegarde des résultats dans un CSV si demandé
    if args.output:
        with open(args.output, mode='w', newline='') as f:
            writer = csv.writer(f)
            # En-tête
            writer.writerow(["nodes", "gateways", "area", "mode", "interval", "steps",
                             "delivered", "collisions", "PDR(%)", "energy", "avg_delay"])
            # Données
            writer.writerow([args.nodes, args.gateways, args.area, args.mode, args.interval, args.steps,
                             delivered, collisions, f"{pdr:.2f}", f"{energy:.1f}", f"{avg_delay:.2f}"])
        logging.info(f"Résultats enregistrés dans {args.output}")
