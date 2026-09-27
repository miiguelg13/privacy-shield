from pathlib import Path
from ultralytics import YOLO
import cv2
import numpy as np

CARPETA_PESOS = Path(__file__).resolve().parent.parent / 'modelos' / 'pesos'
ruta_modelo_caras = str(CARPETA_PESOS / 'caras.pt')
ruta_modelo_matriculas = str(CARPETA_PESOS / 'matriculas.pt')

modelo_caras = YOLO(ruta_modelo_caras)
modelo_matriculas = YOLO(ruta_modelo_matriculas)

def detectar(bytes_imagen, detectar_caras, detectar_matriculas):
    array = np.frombuffer(bytes_imagen, np.uint8)
    imagen = cv2.imdecode(array, cv2.IMREAD_COLOR)

    detecciones = []

    if detectar_caras:
        resultados = modelo_caras(imagen, conf=0.25, verbose=False)[0]
        for caja in resultados.boxes:
            x1, y1, x2, y2 = map(int, caja.xyxy[0].tolist())
            detecciones.append({'tipo': 'cara','bbox': [x1, y1, x2, y2],'confianza': round(float(caja.conf[0]), 3),
            })

    if detectar_matriculas:
        resultados = modelo_matriculas(imagen, conf=0.25, verbose=False)[0]
        for caja in resultados.boxes:
            x1, y1, x2, y2 = map(int, caja.xyxy[0].tolist())
            detecciones.append({'tipo': 'matricula','bbox': [x1, y1, x2, y2],'confianza': round(float(caja.conf[0]), 3),
            })

    return detecciones, imagen