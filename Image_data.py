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
        with open(path, 'rb') as f:
            self.exif = exifread.process_file(f, details=False)
            self.xmp = get_xmp(f)

        #relevant metadata
        self.camera_model = str(self.exif['Image Model'])
        self.exposure_time = float_value(self.exif['EXIF ExposureTime'])
        self.f_number = float_value(self.exif['EXIF FNumber'])
        self.iso = float_value(self.exif['EXIF ISOSpeedRatings'])
        self.position = get_gps_values(self.exif)
        self.altitude = float_value(self.exif['GPS GPSAltitude'])
        self.datetime = datetime.strptime(str(self.exif['EXIF DateTimeOriginal']), "%Y:%m:%d %H:%M:%S")
        self.image_type = get_image_type(self.camera_model)

        if(self.camera_model=='Sequoia'):
            self.model = self.xmp['Camera:SensorModel']['rdf:Seq']['rdf:li'].split(',')
            self.model = [float(x) for x in self.model]

            self.sunshine = None
            if process_sunshine:
                self.sunshine = get_sunshine(self.xmp)


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
    latitude_values = float_values(exif['GPS GPSLatitude'])
    longitude_values = float_values(exif['GPS GPSLongitude'])

    latitude = latitude_values[0]+latitude_values[1]/60+latitude_values[2]/3600
    if str(exif['GPS GPSLatitudeRef']) == 'S' or str(exif['GPS GPSLatitudeRef']) == 'South':
        latitude = -latitude

    longitude = longitude_values[0]+longitude_values[1]/60+longitude_values[2]/3600
    if str(exif['GPS GPSLongitudeRef']) == 'W' or str(exif['GPS GPSLongitudeRef']) == 'West':
        longitude = -longitude

    return latitude, longitude

def get_image_type(camera_model):

    if camera_model in multispectral_cameras:
        return 'Multispectral'
    elif camera_model in RGB_cameras:
        return 'RGB'
    else:
        return 'Unknown'