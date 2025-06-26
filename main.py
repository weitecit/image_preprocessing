from image_data import Relevant_metadata
import pymongo
import os
import shutil
import geopandas as gpd
from shapely.geometry import shape, Point
from pyproj import Transformer
from clustering import full_clustering
import numpy as np

mongo_str = 'mongodb+srv://admin:aSAa4hwn77FX5Ueg@weitec-db-dev.glav6.mongodb.net/'
client = pymongo.MongoClient(mongo_str)
db = client['main']

available_extensions = ['png', 'jpg', 'tif', 'tiff']
omited_folders = ['.thumb']

def retrieve_all_files(root_folder):
    for root, dirs, files in os.walk(root_folder):
        for archivo in files:
            ruta_archivo = os.path.join(root, archivo)
            ruta_nueva = os.path.join(root_folder, archivo)
            os.replace(ruta_archivo, ruta_nueva)
        if root != root_folder:
            try:
                os.rmdir(root)
                print(f"Carpeta '{root}' borrada")
            except OSError as e:
                print(f"No se pudo borrar la carpeta '{root}': {e}")

def get_image_list(image_folder:str)->list[str]:
    available_extensions = ['png', 'jpg', 'tif', 'tiff']
    files = []
    for file in os.listdir(image_folder):
        if file.split('.')[-1].lower() in available_extensions:
            files.append(file)
    return files
def get_image_paths(root_folder:str)->list[str]:
    image_list =[]

    for root, dirs, files in os.walk(root_folder, topdown=False):
        if any(omit in root for omit in omited_folders):
            continue

        for archivo in files:
            if archivo.split('.')[-1].lower() not in available_extensions:
                continue
            image_list.append(os.path.join(root, archivo))
    return image_list

def get_dataset_positions(image_folder:str)->list[tuple]:
    positions = []
    
    for file in get_image_paths(image_folder):
        metadata = Relevant_metadata(file, process_sunshine=False)

        data = metadata.position
        positions.append(data)
    return positions

def get_dataset_gdf(image_folder:str)->gpd.GeoDataFrame:
    points = []
    metadata_list = []

    for file in get_image_paths(image_folder):
        metadata = Relevant_metadata(file, process_sunshine=False)

        data = metadata.position
        points.append(Point(data[0], data[1]))
        metadata_list.append(metadata.as_dict())

    gdf = gpd.GeoDataFrame(metadata_list,geometry=points, crs="epsg:4326")
    return gdf

def detect_plots(positions:list[tuple])->list[dict]:

    #Find in mongo by Intersection
    geometries = [{'type': 'Point', 'coordinates': list(position)} for position in positions]
    query = {
        '$or': [
            {'geometry': {'$geoIntersects': {'$geometry': geom}}} for geom in geometries
        ]
    }
    return list(db.plots.find(query))


def detect_fields_and_divide(image_folder:str, out_folder:str, buffer_size:float=50, positions:list[tuple]=None)->list:
    image_list = get_image_paths(image_folder)

    #get plots as gdf
    if positions is None:
        positions = get_dataset_positions(image_folder)

    plots_list = detect_plots(positions)
    properties = [x['properties'] for x in plots_list]
    geometries = [shape(x['geometry']) for x in plots_list]

    gdf = gpd.GeoDataFrame(properties,  geometry=geometries, crs="epsg:4326")
    tr_gdf = gdf.to_crs(epsg=3857).buffer(buffer_size)

    print(f'Detected fields: {gdf["field"].unique()}')

    tr = Transformer.from_crs("epsg:4326", "epsg:3857", always_xy=True)

    images_out_of_bounds = []
    out_folders = set()
    for image in image_list:
        metadata = Relevant_metadata(image, process_sunshine=False)
        position = metadata.position
        image_name = os.path.basename(image)

        #tranform coordinates and intersect
        x, y = tr.transform(position[0], position[1])
        tr_point = Point(x, y)
       
        mask = tr_gdf.intersects(tr_point)
        detected_fields_in_point = gdf[mask]['field'].unique()
        
        if len(detected_fields_in_point) == 0:
            images_out_of_bounds.append(image)
            continue

        #copy to folder
        for field in detected_fields_in_point:
            new_folder_name = f'W{metadata.datetime.isocalendar()[1]}_{field}_{metadata.image_type}_{len(image_list)}'
            out_folders.add(new_folder_name)
            if not os.path.exists(os.path.join(out_folder, new_folder_name)):
                os.makedirs(os.path.join(out_folder, new_folder_name))
            
            try:
                out_image = os.path.join(out_folder, new_folder_name, image_name)
                shutil.copy2(image, out_image)
            except PermissionError as e:
                print(f"No se pudo copiar la imagen '{image}': {e}")
                print(out_image)
                continue

    print(f'Images out of bounds: {len(images_out_of_bounds)}')
    return out_folders

def fields_and_cluster_division(image_folder:str, out_folder:str, buffer_size:float=50, max_images:int=1000):
    """
    Processes images by detecting fields, dividing them into clusters, and organizing them into subdirectories.

    This function first detects fields within the images and divides the images 
    into subdirectories based on these fields. It then performs clustering on 
    the images within each subdirectory and further organizes them into 
    clusters. The clustered images are moved into corresponding cluster 
    subdirectories.

    Args:
        image_folder (str): Path to the folder containing the images to process.
        out_folder (str): Path to the folder where the output subdirectories 
                          and clustered images will be saved.
        buffer_size (float, optional): Buffer size used during field detection. 
                                       Defaults to 50.
        max_images (int, optional): Maximum number of images allowed in each 
                                    cluster. Defaults to 1000.

    Returns:
        None
    """

    sub_folders = detect_fields_and_divide(image_folder, out_folder, buffer_size)
    #TODO optimizar: en imágenes multiespectrales, trabajar solo con una sola banda
    #TODO optimizar: obtiene las posiciones en varias ocasiones
    for sub in sub_folders:
        print(f'Processing: {sub}')
        image_list = get_image_paths(os.path.join(out_folder, sub))
        print(f'Images: {len(image_list)}')
        positions = get_dataset_positions(os.path.join(out_folder, sub))
        clustering = full_clustering(positions, max_images=max_images)
        total_arr = np.column_stack((clustering, image_list))
        
        for cluster in np.unique(clustering[:, 2]):
            cluster_arr = total_arr[clustering[:, 2] == cluster]
            cluster_folder = os.path.join(out_folder, sub, f'Cluster_{int(cluster)}')
            #move images
            os.makedirs(cluster_folder, exist_ok=True)
            for image in cluster_arr[:, 3]:
                image_name = os.path.basename(image)
                out_image = os.path.join(out_folder, sub, cluster_folder, image_name)
                os.replace(image, out_image)
    print('DONE')


def select_unique_multispectral_images(image_list):
    main_names = []
    last_name = ""
    for image in image_list:
        unique_name = "_".join(image.split('_')[:-1])
        if unique_name != last_name:
            last_name = unique_name
            main_names.append(image)

    return main_names

def flat_folder_structure(directory:str, omited_folders:list=['.thumbs'])->None:

    for root, dirs, files in os.walk(directory, topdown=False):
        #check if in omited folders
        if any(omit in root for omit in omited_folders):
            continue
        
        #move files
        for archivo in files:
            ruta_archivo = os.path.join(root, archivo)
            ruta_nueva = os.path.join(directory, archivo)
            os.replace(ruta_archivo, ruta_nueva)
        #delete empty folders
        if root != directory:
            try:
                os.rmdir(root)
                print(f"Carpeta '{root}' borrada")
            except OSError as e:
                print(f"No se pudo borrar la carpeta '{root}': {e}")

if __name__ == '__main__':
    import sys
    fields_and_cluster_division(sys.argv[1], sys.argv[2])