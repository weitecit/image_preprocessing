from sklearn.cluster import AgglomerativeClustering, SpectralClustering
import numpy as np
import matplotlib.pyplot as plt
from matplotlib import colormaps

cmap = colormaps['viridis']

def agglomerative_clustering(positions:list[tuple], distance_threshold:float=0.001)->list[tuple]:
    #transformar en un formato apto para sklearn
    X = np.array(positions)

    #aplicar algoritmo de agrupamiento
    model = AgglomerativeClustering(n_clusters=None, distance_threshold=distance_threshold, linkage='single')
    model.fit_predict(X)

    new_positions = np.column_stack((X, model.labels_))
    return new_positions


def spectral_clustering(positions:list[tuple], n_clusters:int=2)->list[tuple]:
    #transformar en un formato apto para sklearn
    X = np.array(positions)

    #aplicar algoritmo de agrupamiento
    model = SpectralClustering(n_clusters=n_clusters, n_neighbors=10, affinity='nearest_neighbors')
    model.fit_predict(X)

    new_positions = np.column_stack((X, model.labels_))
    return new_positions

def plot_map(positions:list[tuple], labels:list)->None:
    for u in np.unique(labels):
        plt.scatter(positions[labels == u, 0], positions[labels == u, 1], marker='o', label=f"Cluster {u}")
    plt.legend()
    plt.plot()