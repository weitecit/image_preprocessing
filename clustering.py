from sklearn.cluster import AgglomerativeClustering, SpectralClustering
import numpy as np
import matplotlib.pyplot as plt
import math

def agglomerative_clustering(positions:list[tuple], distance_threshold:float=0.0008)->list[tuple]:
    X = np.array(positions)

    model = AgglomerativeClustering(n_clusters=None, distance_threshold=distance_threshold, linkage='single')
    model.fit_predict(X)

    new_positions = np.column_stack((X, model.labels_))
    return new_positions


def spectral_clustering(positions:list[tuple], n_clusters:int=2)->list[tuple]:
    X = np.array(positions)

    model = SpectralClustering(n_clusters=n_clusters, n_neighbors=10, affinity='nearest_neighbors')
    model.fit_predict(X)

    new_positions = np.column_stack((X, model.labels_))
    return new_positions

def plot_map(positions:list[tuple[2]], labels:list)->None:
    for u in np.unique(labels):
        plt.scatter(positions[labels == u, 0], positions[labels == u, 1], marker='o', label=f"Cluster {u}")
    plt.legend()
    plt.plot()

def full_clustering(positions:list[tuple], distance_threshold:float=0.0009, max_images:int=1000)->list[tuple[3]]:
    first_clustering = agglomerative_clustering(positions, distance_threshold)
    max_label = np.max(first_clustering[:, 2])

    # Get the unique labels and their counts
    #ejemplo de salida: (array([0, 1], dtype=int32), array([291, 613]))
    unique_labels = np.unique(first_clustering[:, 2], return_counts=True)

    excessive_position_labels = unique_labels[0][unique_labels[1] > max_images]
    #TODO hacer print de los cluster que no necesitan ser divididos

    for e_label in excessive_position_labels:
        positions = first_clustering[first_clustering[:, 2] == e_label]
        positions = positions[:, :2]
        n_clusters = math.ceil(len(positions) / max_images)
        print(f'Cluster {e_label}: {len(positions)} positions -> {n_clusters} splits')
        second_clustering = spectral_clustering(positions, n_clusters)

        #new unique indexing
        second_clustering[:,2] += max_label + 1
        max_label += len(np.unique(second_clustering[:, 2]))

        for u in np.unique(second_clustering[:, 2]):
            print(f'\tCluster {u}: {len(second_clustering[second_clustering[:, 2] == u])}')
        
        #add to the first clustering
        first_clustering[first_clustering[:, 2] == e_label, 2] = second_clustering[:, 2]
    
    return first_clustering