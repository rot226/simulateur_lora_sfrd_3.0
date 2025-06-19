#!/usr/bin/env python3
"""Analyse simple des fichiers CSV générés par le simulateur."""
import sys
import pandas as pd
import matplotlib.pyplot as plt

if len(sys.argv) < 2:
    print("Usage: python analyse_resultats.py fichier1.csv [fichier2.csv ...]")
    sys.exit(1)

dfs = [pd.read_csv(f) for f in sys.argv[1:]]
results = pd.concat(dfs, ignore_index=True)

# Conversion des colonnes numériques
results['PDR(%)'] = results['PDR(%)'].astype(float)
results['energy'] = results['energy'].astype(float)

print(results)
print(f"PDR moyen: {results['PDR(%)'].mean():.2f}%")

plt.figure()
results.plot(x='nodes', y='PDR(%)', kind='bar')
plt.ylabel('PDR (%)')
plt.title('Taux de livraison par nombre de noeuds')
plt.tight_layout()
plt.savefig('pdr_par_nodes.png')
print("Graphique enregistré dans pdr_par_nodes.png")

