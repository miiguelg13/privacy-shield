import cv2
import numpy as np

def aplicar_blur(imagen, detecciones):
    for deteccion in detecciones:
        x1, y1, x2, y2 = deteccion['bbox']
        alto, ancho = imagen.shape[:2]
        x1 = max(0, x1); y1 = max(0, y1)
        x2 = min(ancho, x2); y2 = min(alto, y2)

        centro_x = (x1 + x2) // 2
        centro_y = (y1 + y2) // 2
        radio_x = (x2 - x1) // 2
        radio_y = (y2 - y1) // 2

        if deteccion['tipo'] == 'cara':
            mascara = np.zeros(imagen.shape[:2], dtype=np.uint8)
            cv2.ellipse(mascara, (centro_x, centro_y), (radio_x, radio_y), 0, 0, 360, 255, -1)
            imagen_borrosa = cv2.GaussianBlur(imagen, (99, 99), 0)
            imagen[mascara == 255] = imagen_borrosa[mascara == 255]
        else:
            zona = imagen[y1:y2, x1:x2]
            zona_borrosa = cv2.GaussianBlur(zona, (51, 51), 0)
            imagen[y1:y2, x1:x2] = zona_borrosa

    return imagen

def aplicar_negro(imagen, detecciones):
    for det in detecciones:
        if 'bbox' not in det:
            continue
        x1, y1, x2, y2 = det['bbox']
        alto, ancho = imagen.shape[:2]
        x1 = max(0, x1); y1 = max(0, y1)
        x2 = min(ancho, x2); y2 = min(alto, y2)

        if det['tipo'] == 'cara':
            centro_x = (x1 + x2) // 2
            centro_y = (y1 + y2) // 2
            radio_x = (x2 - x1) // 2
            radio_y = (y2 - y1) // 2
            cv2.ellipse(imagen, (centro_x, centro_y), (radio_x, radio_y), 0, 0, 360, (0, 0, 0), -1)
        else:
            cv2.rectangle(imagen, (x1, y1), (x2, y2), (0, 0, 0), -1)

    return imagen
def imagen_a_bytes(imagen):
    _, buffer = cv2.imencode('.jpg', imagen)
    return buffer.tobytes()