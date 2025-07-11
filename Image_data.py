import exifread
import xmltodict as x2d
import base64
import struct
import numpy as np
from datetime import datetime

multispectral_cameras = ['Sequoia']
RGB_cameras = ['ZH20T']

class Relevant_metadata:
    def __init__(self, path, process_sunshine=True):
        self.path = path
        self.exif = {}
        self.xmp = {}
        try:
            with open(path, 'rb') as f:
                self.exif = exifread.process_file(f, details=False) or {}
                self.xmp = get_xmp(f)
        except Exception as e:
            print(f"Error processing file {self.path}: {e}")
            # Initialize exif and xmp as empty to prevent further errors
            self.exif = {}
            self.xmp = {}

        #relevant metadata
        try:
            self.camera_model = str(self.exif.get('Image Model', 'Unknown'))
            self.exposure_time = float_value(self.exif.get('EXIF ExposureTime')) if self.exif.get('EXIF ExposureTime') else None
            self.f_number = float_value(self.exif.get('EXIF FNumber')) if self.exif.get('EXIF FNumber') else None
            self.iso = float_value(self.exif.get('EXIF ISOSpeedRatings')) if self.exif.get('EXIF ISOSpeedRatings') else None
            
            # Handle GPS data with checks
            self.position = get_gps_values(self.exif) if self.exif else (0.0, 0.0)
            self.altitude = float_value(self.exif.get('GPS GPSAltitude')) if self.exif and self.exif.get('GPS GPSAltitude') else None
            self.datetime = None
            if self.exif.get('EXIF DateTimeOriginal'):
                try:
                    self.datetime = datetime.strptime(str(self.exif['EXIF DateTimeOriginal']), "%Y:%m:%d %H:%M:%S")
                except ValueError:
                    print(f"Warning: Malformed DateTimeOriginal in {self.path}")
                    self.datetime = None # Handle cases where datetime string is malformed

            self.image_type = get_image_type(self.camera_model)

            self.sunshine = None
            self.model = None
            if(self.camera_model=='Sequoia'):
                # Ensure 'Camera:SensorModel' exists before accessing
                if self.xmp and 'Camera:SensorModel' in self.xmp and 'rdf:Seq' in self.xmp['Camera:SensorModel'] and \
                   'rdf:li' in self.xmp['Camera:SensorModel']['rdf:Seq']:
                    self.model = self.xmp['Camera:SensorModel']['rdf:Seq']['rdf:li'].split(',')
                    self.model = [float(x) for x in self.model]

                if process_sunshine:
                    self.sunshine = get_sunshine(self.xmp)
        except KeyError as ke:
            print(f"KeyError: Missing EXIF tag '{ke}' in file: {self.path}")
            # Set default values for all attributes to prevent further errors
            self.camera_model = 'Unknown'
            self.exposure_time = None
            self.f_number = None
            self.iso = None
            self.position = None
            self.altitude = None  # Ensure altitude is set even in error cases
            self.datetime = None
            self.image_type = 'Unknown'
            self.sunshine = None
            self.model = None
        except Exception as e:
            print(f"An unexpected error occurred while processing EXIF data for {self.path}: {e}")
            # Set default values for all attributes
            self.camera_model = 'Unknown'
            self.exposure_time = None
            self.f_number = None
            self.iso = None
            self.position = None
            self.altitude = None  # Ensure altitude is set even in error cases
            self.datetime = None
            self.image_type = 'Unknown'
            self.sunshine = None
            self.model = None
    def as_dict(self):
        return {
            'camera_model': self.camera_model,
            'exposure_time': self.exposure_time,
            'f_number': self.f_number,
            'iso': self.iso,
            'position': self.position,
            'altitude': self.altitude,
            'datetime': self.datetime,
            'image_type': self.image_type,
            'sunshine': self.sunshine,
            'path': self.path,
            'image_type': self.image_type,
            'model': self.model
        }
def get_xmp(file):
    img_bytes = file.read()
    xmp_start = img_bytes.find(b'<x:xmpmeta')
    xmp_end = img_bytes.find(b'</x:xmpmeta')

    if xmp_start < xmp_end:
        xmp_str = img_bytes[xmp_start:xmp_end + 12].decode('utf8')
        xdict = x2d.parse(xmp_str)

        xdict = xdict.get('x:xmpmeta', {})
        xdict = xdict.get('rdf:RDF', {})
        xdict = xdict.get('rdf:Description', {})
        if isinstance(xdict, list):
            return xdict[0]
        else:
            return [xdict][0]
    else:
        return []

def float_values(tag):
    if isinstance(tag.values, list):
        result = []
        for v in tag.values:
            if isinstance(v, int):
                result.append(float(v))
            elif isinstance(v, tuple) and len(v) == 1 and isinstance(v[0], float):
                result.append(v[0])
            elif v.den != 0:
                result.append(float(v.num) / float(v.den))
            else:
                result.append(None)
        return result
    elif hasattr(tag.values, 'den'):
        return [float(tag.values.num) / float(tag.values.den) if tag.values.den != 0 else None]
    else:
        return [None]

def float_value(tag):
    v = float_values(tag)
    if len(v) > 0:
        return v[0]
    
def get_sunshine(xmp, fmt="<QHHHHfffQHHHHfffQHHHHfffQHHHHfffQHHHHfffQHHHHfff"):
    try:
        Irr = xmp['Camera:IrradianceList']
        byteIrr = base64.b64decode(Irr)
        boxIrr = struct.unpack_from(fmt, byteIrr)
    
        current_mean= sum(np.asarray(boxIrr)[1:48:8])/6
        return current_mean
    except Exception as e:
        print("Error in get_sunshine", e)
        return None
    
def get_gps_values(exif):
    # Ensure all necessary GPS tags exist before processing
    if exif and exif.get('GPS GPSLatitude') and exif.get('GPS GPSLongitude') and \
       exif.get('GPS GPSLatitudeRef') and exif.get('GPS GPSLongitudeRef'):
        latitude_values = float_values(exif['GPS GPSLatitude'])
        longitude_values = float_values(exif['GPS GPSLongitude'])

        latitude = latitude_values[0]+latitude_values[1]/60+latitude_values[2]/3600
        if str(exif['GPS GPSLatitudeRef']) == 'S' or str(exif['GPS GPSLatitudeRef']) == 'South':
            latitude = -latitude

        longitude = longitude_values[0]+longitude_values[1]/60+longitude_values[2]/3600
        if str(exif['GPS GPSLongitudeRef']) == 'W' or str(exif['GPS GPSLongitudeRef']) == 'West':
            longitude = -longitude

        return (longitude, latitude)
    else:
        return (0.0, 0.0)  # Return default coordinates instead of None

def get_image_type(camera_model):

    if camera_model in multispectral_cameras:
        return 'Multispectral'
    elif camera_model in RGB_cameras:
        return 'RGB'
    else:
        return 'Unknown'