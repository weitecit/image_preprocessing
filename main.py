from Image_data import Relevant_metadata
from os import path, listdir
import pymongo
import os
import shutil

mongo_str = 'mongodb+srv://admin:aSAa4hwn77FX5Ueg@weitec-db-dev.glav6.mongodb.net/'
client = pymongo.MongoClient(mongo_str)
db = client['main']

def get_image_list(image_folder):
    availabe_extensions = ['png', 'jpg', 'tif', 'tiff']
    files = []
    for file in listdir(image_folder):
        if file.split('.')[-1].lower() in availabe_extensions:
            files.append(file)
    return files

def get_dataset_positions(image_folder):
    positions = []
    
    for file in get_image_list(image_folder):
        image_path = path.join(image_folder, file)
        metadata = Relevant_metadata(image_path, process_sunshine=False)

        data = tuple(reversed(metadata.position))
        positions.append(data)
    return positions


def detect_plots(image_folder):
    positions = get_dataset_positions(image_folder)

    #Find in mongo by Intersection
    geometries = [{'type': 'Point', 'coordinates': list(position)} for position in positions]
    query = {
        '$or': [
            {'geometry': {'$geoIntersects': {'$geometry': geom}}} for geom in geometries
        ]
    }
    return list(db.plots.find(query))


def detect_fields_and_divide(image_folder, out_folder):
    image_list = get_image_list(image_folder)

    for image in image_list:
        metadata = Relevant_metadata(os.path.join(image_folder, image), process_sunshine=False)
        position = tuple(reversed(metadata.position))

        result = db.plots.find_one({'geometry': {'$near': {'$geometry': {'type': 'Point', 'coordinates': position}, '$maxDistance': 100}}})
        
        if result:
            source_image = os.path.join(image_folder, image)
            new_folder_name = f'W{metadata.datetime.isocalendar()[1]}_{result['properties']['field']}_{metadata.image_type}_{len(image_list)}'
            if not os.path.exists(os.path.join(out_folder, new_folder_name)):
                os.makedirs(os.path.join(out_folder, new_folder_name))
            out_image = os.path.join(out_folder, new_folder_name, image)
            print(out_image)
            shutil.copy2(source_image, out_image)
        else:
            print(f'No plot found for {image}')



if __name__ == '__main__':
    source_folder = r"C:\Users\Daniel_Arcos\Desktop\0001"
    out_folder = r"C:\Users\Daniel_Arcos\Desktop\out_folder"

    detect_fields_and_divide(source_folder, out_folder)