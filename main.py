import zipfile
import io
import urllib

import requests
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

EMT = 'https://opendata.emtmadrid.es/'
GENERAL = '/Datos-estaticos/Datos-generales-(1)'

def get_links(html):
    '''
    Toma como parámetros un texto HTML y devuelva un conjunto con
    todos los enlaces.
    '''
    pattern = r'href="(/getattachment/[a-zA-Z0-9-]*/trip[^"]*-csv\.aspx)"'
    html = str(urllib.request.urlopen(EMT+GENERAL).read())
    type(html)
    # Encontrar todas las coincidencias
    return re.findall(pattern, html)


class UrlEMT():
    __enlaces = {}

    def __init__(self):
       self.__enlaces = UrlEMT.select_valid_urls()

    @staticmethod
    def select_valid_urls():
       '''
       método estático que se encarga de actualizar el atributo de
       los objetos de la clase. Devuelve un conjunto de enlaces válidos.
       Si la petición al servidor de la EMT devuelve un código de
       retorno distinto de 200, la función lanza una excepción de
       tipo ConnectionError.
       '''
       links = get_links(urllib.request.urlopen(EMT+GENERAL).read())
       for link in links:
           splitted_url = link.split('_')
           UrlEMT.__enlaces[
               (int(splitted_url[1]),int(splitted_url[2]))] = link

    def get_url(self, year: int, month: int) -> str:
        """
        Devuelve el string de la URL correspondiente al mes y año proporcionados.
        
        Parámetros:
        - year (str): Año en formato de cadena (se espera '21', '22' o '23').
        - month (str): Mes en formato de cadena (entre '1' y '12').

        Retorno:
        - str: URL correspondiente al mes y año si existe.

        Excepciones:
        - ValueError: Si el año o mes no están en los rangos válidos o 
           no existe una URL para esa combinación.
        """
        try:
            # Convertir los parámetros a enteros para realizar la validación
            year_int = int(year)
            month_int = int(month)
        except ValueError:
            # Si los argumentos no se pueden convertir a entero, lanzar una excepción
            raise ValueError('''Los valores de 'year' y 'month' deben ser números 
                             enteros válidos.''')
        
        # Comprobación de rango válido para año y mes
        if year_int not in range(21, 24):
            raise ValueError("El año debe estar entre 21 y 23.")
        
        if month_int not in range(1, 13):
            raise ValueError("El mes debe estar entre 1 y 12.")
        
        try:
            return UrlEMT.__enlaces[year, month]
        except KeyError:
            # Si la combinación de año y mes no tiene un enlace 
            # registrado, lanzar excepción
            raise ValueError(f"No hay una URL disponible para el año 
                             {year} y mes {month}.")

    def get_csv(self, month: str, year: str) -> str:
        '''
        método de instancia que acepta los argumentos de tipo entero
        month y year y devuelve un fichero en formato CSV correspondiente
        al mes month y año year.
        '''
        url = self.get_url(year, month)
        try:
            r = requests.get(EMT+url)
            if r.status_code != 200:
                raise Exception("Error al descargar el archivo ZIP")
        except Exception as e:
            print(str(e))
        # Descomprimir el archivo ZIP en memoria
        with zipfile.ZipFile(io.BytesIO(r.content)) as z:
            # Listar los archivos en el ZIP
            nombres_archivos = z.namelist()
            # Extraer el CSV (suponiendo que es el primer archivo en la lista)
            with z.open(nombres_archivos[0]) as csv_file:
                # Leer el contenido del CSV en un objeto TextIO
                contenido_csv = io.StringIO(csv_file.read().decode('utf-8'))  # Convierte a string y crea un TextIO

        return contenido_csv  # Devuelve el objeto TextIO


class BiciMad():

    def __init__(self, month: int, year: int):
        '''

        '''
        self.month = month
        self.year = year
        self.__data = BiciMad.get_data(month, year)
        self.__data = self.clean()

    @staticmethod
    def get_data(month: int, year: int):
        '''
        Método estático que acepta los argumentos de tipo
        entero month y year y devuelve un objeto de
        tipo DataFrame con los datos de uso
        correspondientes al mes month y año year.
        '''
        columns_to_preserve = [ 'idBike', 'fleet', 'trip_minutes',
            'geolocation_unlock', 'address_unlock', 'unlock_date',
            'locktype', 'unlocktype', 'geolocation_lock',
            'address_lock', 'lock_date', 'station_unlock',
            'unlock_station_name','station_lock',
            'lock_station_name']

        url_manager = UrlEMT()
        tmp_csv =  url_manager.get_csv(month, year)
        df = pd.read_csv(tmp_csv, sep=';', quotechar="'")
        df['fecha'] = pd.to_datetime(df['fecha'], errors='coerce')
        df = df.set_index('fecha')
        return df[columns_to_preserve]

    @property
    def data(self):
        '''
        Método decorado con el decorador @property para acceder
        al atributo que representa los datos de uso. El atributo
        ha de llamarse igual.'''

        return self.__data

    @data.setter
    def data(self, valor):
      self._data = valor

    def clean(self):
        '''
        Método de instancia que se encarga de realizar la limpieza
        y transformación del dataframe que representa los datos.
        Modifica el dataframe y no devuelve nada. Realiza las
        siguientes tareas:
        '''
        try:
          self.__data = self.__data.replace([None, 'nan'], np.nan)
          self.__data.dropna(how='all', inplace=True)
          self.__data[['idBike', 'fleet', 'station_unlock', 'station_lock']] = (
              self.__data[['idBike', 'fleet', 'station_unlock', 'station_lock']].astype(str))
        except Exception as e:
          exc_type, exc_value, exc_traceback = sys.exc_info()
          print("Tipo de excepción:", exc_type.__name__)
          print("Mensaje de la excepción:", exc_value)



    def __str__(self):
        print(self.data)