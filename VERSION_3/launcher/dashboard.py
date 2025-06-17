import os
import sys

import panel as pn
import pandas as pd
import plotly.graph_objects as go

# Assurer la résolution correcte des imports quel que soit le répertoire
# depuis lequel ce fichier est exécuté. On ajoute le dossier parent
# (celui contenant le paquet ``launcher``) au ``sys.path`` s'il n'y est pas
# déjà. Ainsi, ``from launcher.simulator`` fonctionnera aussi avec la
# commande ``panel serve dashboard.py`` exécutée depuis ce dossier.
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from launcher.simulator import Simulator
import numpy as np
import time

# --- Initialisation Panel ---
pn.extension('plotly')
# Définition du titre de la page via le document Bokeh directement
pn.state.curdoc.title = "Simulateur LoRa"

# --- Variables globales ---
sim = None
sim_callback = None
mobility_callback = None
chrono_callback = None
start_time = None
elapsed_time = 0

# --- Widgets de configuration ---
num_nodes_input = pn.widgets.IntInput(name="Nombre de nœuds", value=20, step=1, start=1)
num_gateways_input = pn.widgets.IntInput(name="Nombre de passerelles", value=1, step=1, start=1)
area_input = pn.widgets.FloatInput(name="Taille de l'aire (m)", value=1000.0, step=100.0, start=100.0)
mode_select = pn.widgets.RadioButtonGroup(name="Mode d'émission", options=['Aléatoire', 'Périodique'], value='Aléatoire')
interval_input = pn.widgets.FloatInput(name="Intervalle moyen (s)", value=30.0, step=1.0, start=0.1)
packets_input = pn.widgets.IntInput(name="Nombre de paquets (0=infin)", value=0, step=1, start=0)
adr_node_checkbox = pn.widgets.Checkbox(name="ADR nœud", value=False)
adr_server_checkbox = pn.widgets.Checkbox(name="ADR serveur", value=False)

# --- Widget pour activer/désactiver la mobilité des nœuds ---
mobility_checkbox = pn.widgets.Checkbox(name="Activer la mobilité des nœuds", value=False)

# --- Boutons de contrôle ---
start_button = pn.widgets.Button(name="Lancer la simulation", button_type="success")
stop_button = pn.widgets.Button(name="Arrêter la simulation", button_type="warning", disabled=True)

# --- Nouveau bouton d'export et message d'état ---
export_button = pn.widgets.Button(name="Exporter résultats (dossier courant)", button_type="primary", disabled=True)
export_message = pn.pane.HTML("Clique sur Exporter pour générer le fichier CSV après la simulation.")

# --- Indicateurs de métriques ---
pdr_indicator = pn.indicators.Number(name="PDR", value=0, format="{value:.1%}")
collisions_indicator = pn.indicators.Number(name="Collisions", value=0, format="{value:d}")
energy_indicator = pn.indicators.Number(name="Énergie Tx (J)", value=0.0, format="{value:.3f}")
delay_indicator = pn.indicators.Number(name="Délai moyen (s)", value=0.0, format="{value:.3f}")

# --- Chronomètre ---
chrono_indicator = pn.indicators.Number(name="Durée simulation (s)", value=0, format="{value:.1f}")


# --- Pane pour la carte des nœuds/passerelles ---
map_pane = pn.pane.Plotly(height=500, sizing_mode='stretch_width')

# --- Pane pour l'histogramme SF ---
sf_hist_pane = pn.pane.Plotly(height=250, sizing_mode='stretch_width')

# --- Fonctions de mobilité ---
def initialize_node_velocities(nodes, vmax=2.0):
    for node in nodes:
        node.vx = (np.random.rand() * 2 - 1) * vmax
        node.vy = (np.random.rand() * 2 - 1) * vmax

def move_nodes(nodes, area_size, dt=10.0):
    for node in nodes:
        node.x += node.vx * dt
        node.y += node.vy * dt
        if node.x < 0:
            node.x = -node.x
            node.vx = -node.vx
        if node.x > area_size:
            node.x = 2 * area_size - node.x
            node.vx = -node.vx
        if node.y < 0:
            node.y = -node.y
            node.vy = -node.vy
        if node.y > area_size:
            node.y = 2 * area_size - node.y
            node.vy = -node.vy

# --- Mise à jour de la carte ---
def update_map():
    global sim
    if sim is None:
        return
    fig = go.Figure()
    x_nodes = [node.x for node in sim.nodes]
    y_nodes = [node.y for node in sim.nodes]
    node_ids = [str(node.id) for node in sim.nodes]
    fig.add_scatter(x=x_nodes, y=y_nodes, mode='markers+text', name='Nœuds',
                    text=node_ids, textposition='top center',
                    marker=dict(symbol='circle', color='blue', size=8))
    x_gw = [gw.x for gw in sim.gateways]
    y_gw = [gw.y for gw in sim.gateways]
    fig.add_scatter(x=x_gw, y=y_gw, mode='markers', name='Passerelles',
                    marker=dict(symbol='star', color='red', size=10, line=dict(width=1, color='black')))
    area = area_input.value
    fig.update_layout(
        title="Position des nœuds et passerelles",
        xaxis_title="X (m)", yaxis_title="Y (m)",
        xaxis_range=[0, area], yaxis_range=[0, area],
        yaxis=dict(scaleanchor="x", scaleratio=1)
    )
    map_pane.object = fig

# --- Callback pour changer le label de l'intervalle selon le mode d'émission ---
def on_mode_change(event):
    if event.new == 'Aléatoire':
        interval_input.name = "Intervalle moyen (s)"
    else:
        interval_input.name = "Période (s)"

mode_select.param.watch(on_mode_change, 'value')

# --- Callback mobilité ---
def periodic_mobility_update():
    global sim
    if sim is not None and mobility_checkbox.value:
        move_nodes(sim.nodes, area_input.value, dt=10.0)
        update_map()

# --- Callback chrono ---
def periodic_chrono_update():
    global chrono_indicator, start_time, elapsed_time
    if start_time is not None:
        elapsed_time = time.time() - start_time
        chrono_indicator.value = elapsed_time

# --- Callback étape de simulation ---
def step_simulation():
    if sim is None:
        return
    cont = sim.step()
    metrics = sim.get_metrics()
    pdr_indicator.value = metrics['PDR']
    collisions_indicator.value = metrics['collisions']
    energy_indicator.value = metrics['energy_J']
    delay_indicator.value = metrics['avg_delay_s']
    sf_dist = metrics['sf_distribution']
    sf_fig = go.Figure(
        data=[go.Bar(x=[f"SF{sf}" for sf in sf_dist.keys()], y=list(sf_dist.values()))]
    )
    sf_fig.update_layout(title="Répartition des SF par nœud", xaxis_title="SF", yaxis_title="Nombre de nœuds")
    sf_hist_pane.object = sf_fig
    update_map()
    if not cont:
        on_stop(None)
        return

# --- Bouton "Lancer la simulation" ---
def on_start(event):
    global sim, sim_callback, start_time, chrono_callback, elapsed_time, mobility_callback
    elapsed_time = 0

    # Arrêter toutes les callbacks au cas où
    if sim_callback:
        sim_callback.stop()
        sim_callback = None
    if mobility_callback:
        mobility_callback.stop()
        mobility_callback = None
    if chrono_callback:
        chrono_callback.stop()
        chrono_callback = None

    sim = Simulator(
        num_nodes=int(num_nodes_input.value),
        num_gateways=int(num_gateways_input.value),
        area_size=float(area_input.value),
        transmission_mode='Random' if mode_select.value == 'Aléatoire' else 'Periodic',
        packet_interval=float(interval_input.value),
        packets_to_send=int(packets_input.value),
        adr_node=adr_node_checkbox.value,
        adr_server=adr_server_checkbox.value,
        mobility=mobility_checkbox.value
    )

    if mobility_checkbox.value:
        initialize_node_velocities(sim.nodes)
        mobility_callback = pn.state.add_periodic_callback(periodic_mobility_update, period=10000, timeout=None)
    start_time = time.time()
    chrono_callback = pn.state.add_periodic_callback(periodic_chrono_update, period=100, timeout=None)

    update_map()
    pdr_indicator.value = 0
    collisions_indicator.value = 0
    energy_indicator.value = 0
    delay_indicator.value = 0
    chrono_indicator.value = 0
    sf_counts = {sf: sum(1 for node in sim.nodes if node.sf == sf) for sf in range(7, 13)}
    sf_fig = go.Figure(data=[go.Bar(x=[f"SF{sf}" for sf in sf_counts.keys()], y=list(sf_counts.values()))])
    sf_fig.update_layout(title="Répartition des SF par nœud", xaxis_title="SF", yaxis_title="Nombre de nœuds")
    sf_hist_pane.object = sf_fig
    num_nodes_input.disabled = True
    num_gateways_input.disabled = True
    area_input.disabled = True
    mode_select.disabled = True
    interval_input.disabled = True
    packets_input.disabled = True
    adr_node_checkbox.disabled = True
    adr_server_checkbox.disabled = True
    mobility_checkbox.disabled = True
    start_button.disabled = True
    stop_button.disabled = False
    export_button.disabled = True
    export_message.object = "Clique sur Exporter pour générer le fichier CSV après la simulation."

    sim.running = True
    sim_callback = pn.state.add_periodic_callback(step_simulation, period=100, timeout=None)

# --- Bouton "Arrêter la simulation" ---
def on_stop(event):
    global sim, sim_callback, mobility_callback, chrono_callback, start_time
    if sim is None or not sim.running:
        return

    sim.running = False
    if sim_callback:
        sim_callback.stop()
        sim_callback = None
    if mobility_callback:
        mobility_callback.stop()
        mobility_callback = None
    if chrono_callback:
        chrono_callback.stop()
        chrono_callback = None

    num_nodes_input.disabled = False
    num_gateways_input.disabled = False
    area_input.disabled = False
    mode_select.disabled = False
    interval_input.disabled = False
    packets_input.disabled = False
    adr_node_checkbox.disabled = False
    adr_server_checkbox.disabled = False
    mobility_checkbox.disabled = False
    start_button.disabled = False
    stop_button.disabled = True
    export_button.disabled = False

    start_time = None
    export_message.object = "✅ Simulation terminée. Tu peux exporter les résultats."

# --- Export CSV local : Méthode universelle ---
def exporter_csv(event=None):
    global sim
    if sim is not None:
        try:
            df = sim.get_events_dataframe()
            if df.empty:
                export_message.object = "⚠️ Aucune donnée à exporter !"
                return
            # Nom de fichier unique avec date et heure
            timestamp = time.strftime("%Y-%m-%d_%H-%M-%S")
            chemin = os.path.join(os.getcwd(), f"resultats_simulation_{timestamp}.csv")
            df.to_csv(chemin, index=False, encoding="utf-8")
            export_message.object = f"✅ Résultats exportés : <b>{chemin}</b><br>(Ouvre-le avec Excel ou pandas)"
            try:
                os.startfile(os.getcwd())
            except Exception:
                pass
        except Exception as e:
            export_message.object = f"❌ Erreur lors de l'export : {e}"
    else:
        export_message.object = "⚠️ Lance la simulation d'abord !"

export_button.on_click(exporter_csv)

# --- Case à cocher mobilité : pour mobilité à chaud, hors simulation ---
def on_mobility_toggle(event):
    global sim, mobility_callback
    if sim and sim.running:
        if event.new:
            initialize_node_velocities(sim.nodes)
            if not mobility_callback:
                mobility_callback = pn.state.add_periodic_callback(periodic_mobility_update, period=10000, timeout=None)
        else:
            if mobility_callback:
                mobility_callback.stop()
                mobility_callback = None
        sim.mobility_enabled = event.new

mobility_checkbox.param.watch(on_mobility_toggle, 'value')

# --- Associer les callbacks aux boutons ---
start_button.on_click(on_start)
stop_button.on_click(on_stop)

# --- Mise en page du dashboard ---
controls = pn.WidgetBox(
    num_nodes_input, num_gateways_input, area_input, mode_select, interval_input, packets_input,
    adr_node_checkbox, adr_server_checkbox, mobility_checkbox,
    pn.Row(start_button, stop_button, export_button),  # Ajout du bouton export ici
    export_message  # Message d'état export
)

metrics_col = pn.Column(
    chrono_indicator,
    pdr_indicator,
    collisions_indicator,
    energy_indicator,
    delay_indicator,
)

dashboard = pn.Column(
    controls,
    pn.Row(map_pane, metrics_col, sizing_mode='stretch_width'),
    sf_hist_pane,
)
dashboard.servable(title="Simulateur LoRa")
