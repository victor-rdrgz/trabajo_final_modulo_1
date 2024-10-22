import re
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
    """
    Toma como parámetro un texto HTML y devuelve un conjunto con 
    todos los enlaces que coincidan con el patrón definido.

    Parámetros:
    - html (str): El contenido HTML de una página como una cadena.

    Retorno:
    - set: Un conjunto que contiene todos los enlaces encontrados en el HTML.

    Ejemplos:
    >>> html_example = '''
    ... <a href="/geta...71a0b925/trips_22_02_February-csv.aspx">Download</a>
    ... <a href="/geta...j8h0b925/trips_23_02_February-csv.aspx">Download</a>
    ... <a href="/geta...c71a0b925/trips_23_01_February-csv.aspx">Download</a>
    ... '''
    >>> get_links(html_example)
    {'/getattachment/1234/trip-data-csv.aspx',
    '/getattachment/5678/trip-data-csv.aspx'}

    >>> html_example_empty = '<html><body>No links here</body></html>'
    >>> get_links(html_example_empty)
    set()

    >>> get_links(1234)
    Traceback (most recent call last):
    ...
    TypeError: El argumento 'html' debe ser una cadena de texto.
    """
    # Verificar que el argumento html sea de tipo str
    if not isinstance(html, str):
        raise TypeError("El argumento 'html' debe ser una cadena de texto.")
    # Encontrar todas las coincidencias del patrón en el HTML
    pattern = r'href="(/getattachment/[a-zA-Z0-9-]*/trip[^"]*-csv\.aspx)"'
    return list(set(re.findall(pattern, html)))
    

class UrlEMT():
    __enlaces = {}
   
    def __init__(self):
       __enlaces = UrlEMT.select_valid_urls()
   
    @staticmethod
    def select_valid_urls():
        '''
        método estático que se encarga de actualizar el atributo de
        los objetos de la clase. Devuelve un conjunto de enlaces válidos.
        Si la petición al servidor de la EMT devuelve un código de 
        retorno distinto de 200, la función lanza una excepción de 
        tipo ConnectionError.
        '''
        try:
            # Realizar la solicitud HTTP y verificar el código de estado
            r = urllib.request.urlopen(EMT + GENERAL)
            if r.getcode() != 200:
                print(
                    f"Error al conectar con el servidor: código {r.getcode()}")
                
            # Obtener los enlaces válidos del HTML
            links = get_links(r.read().decode("utf-8"))

            # Actualizar el atributo __enlaces con los enlaces obtenidos
            for link in links:
                splitted_url = link.split('_')
                
                # Se asume que el formato del enlace es 
                # '/getattachment/{id}/{mes}/{nombre}'
                if len(splitted_url) >= 3:
                    UrlEMT.__enlaces[
                        int(splitted_url[1]), int(splitted_url[2])] = link

        except urllib.error.URLError as e:
            raise ConnectionError(
                f"Error al intentar conectar con el servidor: {e}")
           
    def get_url(self, year: int, month: int) -> str:
        """
        Devuelve el string de la URL correspondiente 
        al mes y año proporcionados.
        
        Parámetros:
        - year (str): Año en formato de cadena (se espera '21', '22' o '23').
        - month (str): Mes en formato de cadena (entre '1' y '12').

        Retorno:
        - str: URL correspondiente al mes y año si existe.

        Excepciones:
        - ValueError: Si el año o mes no están en los rangos válidos o 
            no existe una URL para esa combinación.
        """
        
        # Comprobación de rango válido para año y mes
        if month not in range(1, 13):
            raise ValueError("El año debe estar entre 21 y 23.")
        
        if year not in range(21, 24):
            raise ValueError("El mes debe estar entre 1 y 12.")
        
        try:
            return UrlEMT.__enlaces[year, month]
        except KeyError:
            # Si la combinación de año y mes no tiene un enlace 
            # registrado, lanzar excepción
            print(
                f"No hay una URL disponible para el año {year} y mes {month}.")

    def get_csv(self, month: int, year: int) -> str:
        '''
        método de instancia que acepta los argumentos de tipo entero 
        month y year y devuelve un fichero en formato CSV correspondiente 
        al mes month y año year.
        '''
        url = EMT + self.get_url(year, month)
        try:
            r = requests.get(url)
            # Levanta una excepción si el código HTTP no es 200
            r.raise_for_status()
        except requests.exceptions.RequestException as e:
            raise ConnectionError(f"Error al descargar el archivo ZIP: {e}")
        try:
            # Descomprimir el archivo ZIP en memoria
            with zipfile.ZipFile(io.BytesIO(r.content)) as z:
                # Listar los archivos en el ZIP
                nombres_archivos = z.namelist()
                if not nombres_archivos:
                    raise FileNotFoundError(
                        "No se encontró ningún archivo en el ZIP")
                # Extraer el CSV
                with z.open(nombres_archivos[0]) as csv_file:
                    # Leer el contenido del CSV en un objeto TextIO
                    contenido_csv = io.StringIO(
                        csv_file.read().decode('utf-8'))  
                    # Convierte a string y crea un TextIO
        except zipfile.BadZipFile as e:
            print(f"El archivo descargado no es un ZIP válido: {e}") 
        return contenido_csv  # Devuelve el objeto TextIO


    def __str__(self):
        print(UrlEMT.__enlaces)    
    
    
class BiciMad():
    month = 0
    year = 0
    csv = ''
    data = np.nan
    
    def __init__(self, month: int, year: int):
        '''
        
        '''
        self.month = month
        self.year = year
        self.__data = BiciMad.get_data(month, year)
        self.clean()
    
    @staticmethod    
    def get_data(month: int, year: int):
        '''
        Método estático que acepta los argumentos de tipo entero 
        month y year y devuelve un objeto de tipo DataFrame 
        con los datos de uso correspondientes al mes y año indicados.
        
        Parámetros:
        - month (int): Mes como número entero (1-12).
        - year (int): Año como número entero (por ejemplo, 2023).
        
        Retorno:
        - pd.DataFrame: DataFrame que contiene los datos filtrados.

        Excepciones:
        - ValueError: Si el mes o año no son válidos.
        - KeyError: Si alguna de las columnas especificadas
                    no existe en el DataFrame.
        '''
        # Comprobación de rango válido para año y mes
        if month not in range(1, 13):
            raise ValueError("El año debe estar entre 21 y 23.")
        if year not in range(21, 24):
            raise ValueError("El mes debe estar entre 1 y 12.")
        
        columns_to_preserve = [ 'idBike', 'fleet', 'trip_minutes',
            'geolocation_unlock', 'address_unlock', 'unlock_date',
            'locktype', 'unlocktype', 'geolocation_lock', 
            'address_lock', 'lock_date', 'station_unlock',
            'unlock_station_name','station_lock', 
            'lock_station_name']
        
        url_manager = UrlEMT()
        try:
            # Obtener el CSV y convertirlo en un DataFrame
            df = pd.read_csv(
                url_manager.get_csv(month, year), sep=';', quotechar="'")
        except Exception as e:
            raise ConnectionError(f"Error al obtener datos desde la URL: {e}")
        
        # Convertir la columna 'fecha' a datetime y establecerla como índice
        df['fecha'] = pd.to_datetime(df['fecha'], errors='coerce')
        df.set_index('fecha', inplace=True)
        # Filtrar el DataFrame para conservar solo las columnas deseadas
        try:
            return df[columns_to_preserve]
        except KeyError as e:
            missing_columns = [
                col for col in columns_to_preserve if col not in df.columns]
            raise KeyError(f"Faltan las siguientes columnas en el DataFrame:
                           {', '.join(missing_columns)}") from e
    
    @property
    def data(self):
        '''
        Método decorado con el decorador @property para acceder 
        al atributo que representa los datos de uso. El atributo
        ha de llamarse igual.
        
        Retorno:
        - Los datos almacenados en el atributo privado __data.
        '''        
        return self.__data
    
    
    def clean(self):
        '''
        Método de instancia que se encarga de realizar la limpieza
        y transformación del dataframe que representa los datos.
        Modifica el dataframe y no devuelve nada. Realiza las 
        siguientes tareas:
        '''
        # Reemplazar None y NaN por np.nan
        self.__data.replace([None, 'nan'], np.nan, inplace=True)
        # Eliminar filas donde todos los elementos son NaN
        self.__data.dropna(how='all', inplace=True)
        # Convertir columnas a tipo string
        columns_to_convert = [
            'idBike', 'fleet', 'station_unlock', 'station_lock']
        self.__data[columns_to_convert] = self.__data[
            columns_to_convert].astype(str)
        
    
    def __str__(self):
        print(self.data) 