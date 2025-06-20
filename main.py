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

def get_image_list(image_folder):
    available_extensions = ['png', 'jpg', 'tif', 'tiff']
    files = []
    for file in os.listdir(image_folder):
        if file.split('.')[-1].lower() in available_extensions:
            files.append(file)
    return files

def get_dataset_positions(image_folder):
    positions = []
    
    for file in get_image_list(image_folder):
        image_path = os.path.join(image_folder, file)
        metadata = Relevant_metadata(image_path, process_sunshine=False)

        data = metadata.position
        positions.append(data)
    return positions

def get_dataset_gdf(image_folder:str)->gpd.GeoDataFrame:
    points = []
    metadata_list = []

    for file in get_image_list(image_folder):
        image_path = os.path.join(image_folder, file)
        metadata = Relevant_metadata(image_path, process_sunshine=False)

        data = metadata.position
        points.append(Point(data[0], data[1]))
        metadata_list.append(metadata.as_dict())

    gdf = gpd.GeoDataFrame(metadata_list,geometry=points, crs="epsg:4326")
    return gdf

def detect_plots(image_folder)->list[dict]:
    positions = get_dataset_positions(image_folder)

    #Find in mongo by Intersection
    geometries = [{'type': 'Point', 'coordinates': list(position)} for position in positions]
    query = {
        '$or': [
            {'geometry': {'$geoIntersects': {'$geometry': geom}}} for geom in geometries
        ]
    }
    return list(db.plots.find(query))


def detect_fields_and_divide(image_folder:str, out_folder:str, buffer_size:float=50)->list:
    image_list = get_image_list(image_folder)

    #get plots as gdf
    plots_list = detect_plots(image_folder)
    properties = [x['properties'] for x in plots_list]
    geometries = [shape(x['geometry']) for x in plots_list]

    gdf = gpd.GeoDataFrame(properties,  geometry=geometries, crs="epsg:4326")
    tr_gdf = gdf.to_crs(epsg=3857).buffer(buffer_size)

    print(f'Detected fields: {gdf["field"].unique()}')

    tr = Transformer.from_crs("epsg:4326", "epsg:3857", always_xy=True)

    images_out_of_bounds = []
    out_folders = set()
    for image in image_list:
        metadata = Relevant_metadata(os.path.join(image_folder, image), process_sunshine=False)
        position = metadata.position

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
            source_image = os.path.join(image_folder, image)
            new_folder_name = f'W{metadata.datetime.isocalendar()[1]}_{field}_{metadata.image_type}_{len(image_list)}'
            out_folders.add(new_folder_name)
            if not os.path.exists(os.path.join(out_folder, new_folder_name)):
                os.makedirs(os.path.join(out_folder, new_folder_name))
            out_image = os.path.join(out_folder, new_folder_name, image)
            shutil.copy2(source_image, out_image)

    print(f'Images out of bounds: {len(images_out_of_bounds)}')
    return out_folders

def fields_and_cluster_division(image_folder:str, out_folder:str, buffer_size:float=50, max_images:int=1000):
    sub_folders = detect_fields_and_divide(image_folder, out_folder, buffer_size)
    #TODO optimizar: en imágenes multiespectrales, trabajar solo con una sola banda
    #TODO optimizar: obtiene las posiciones en varias ocasiones
    for sub in sub_folders:
        print(f'Processing: {sub}')
        image_list = get_image_list(os.path.join(out_folder, sub))
        positions = get_dataset_positions(os.path.join(out_folder, sub))
        clustering = full_clustering(positions, max_images=max_images)
        total_arr = np.column_stack((clustering, image_list))
        
        for cluster in np.unique(clustering[:, 2]):
            cluster_arr = total_arr[clustering[:, 2] == cluster]
            cluster_folder = os.path.join(out_folder, sub, f'Cluster_{int(cluster)}')
            #move images
            os.makedirs(cluster_folder, exist_ok=True)
            for image in cluster_arr[:, 3]:
                in_image = os.path.join(out_folder, sub, image)
                out_image = os.path.join(out_folder, sub, cluster_folder, image)
                os.replace(in_image, out_image)
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



if __name__ == '__main__':
    source_folder = r"C:\Users\Daniel_Arcos\Desktop\DJI_202506091548_174_Agricultura-agriauto-cabrera"
    out_folder = r"C:\Users\Daniel_Arcos\Desktop\out_folder"

    detect_fields_and_divide(source_folder, out_folder)