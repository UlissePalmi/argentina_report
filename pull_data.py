import requests
import pandas as pd

url = "https://www.indec.gob.ar/ftp/cuadros/economia/..."  # their FTP path
df = pd.read_excel(url)