from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
import json
import asyncio
import time

from detector import detectar
from ocr import detectar_texto_sensible, redactar_texto
from video import procesar_video, bbox_solapa_con_excluidas
from detector import detectar, modelo_caras, modelo_matriculas
from anonimizador import aplicar_blur, imagen_a_bytes, aplicar_negro


import tempfile
import os
import base64
import cv2
import numpy as np
import subprocess


progreso_videos = {}

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=['http://localhost:5173', 'http://localhost:3000'],
    allow_methods=['*'],
    allow_headers=['*'],
    expose_headers=['X-Total', 'X-Riesgo', 'X-Timeline', 'X-Detecciones', 'X-Tiempo'],
)

@app.get('/')
def inicio():
    return {'mensaje': 'Privacy Shield API funcionando'}

@app.post('/api/analizar')
async def analizar(
    archivo: UploadFile = File(...),
    caras: bool = True,
    matriculas: bool = True,
    texto: bool = False,
    modo: str = 'blur',
    bboxes_excluidas: str = '',
):
    inicio = time.time()
    if not archivo.content_type.startswith('image/'):
        raise HTTPException(400, 'El archivo debe ser una imagen')
    bytes_imagen = await archivo.read()
    detecciones, imagen = detectar(bytes_imagen, caras, matriculas)
    if bboxes_excluidas:
        try:
            lista_bboxes = json.loads(bboxes_excluidas)
            if lista_bboxes:
                detecciones = [
                    d for d in detecciones
                    if d['tipo'] != 'cara' or not bbox_solapa_con_excluidas(
                        d['bbox'][0], d['bbox'][1], d['bbox'][2], d['bbox'][3], lista_bboxes
                    )
                ]
        except Exception:
            pass
    detecciones_texto = []
    if texto:
        print('OCR activado, procesando...')
        detecciones_texto, imagen = detectar_texto_sensible(bytes_imagen)
        print(f'Textos detectados: {len(detecciones_texto)}')
        for d in detecciones_texto:
            print(f'  {d}')
        imagen = redactar_texto(imagen, detecciones_texto)
    if modo == 'blur':
        imagen = aplicar_blur(imagen, detecciones)
    else:
        imagen = aplicar_negro(imagen, detecciones)
    bytes_resultado = imagen_a_bytes(imagen)

    todas_detecciones = detecciones + detecciones_texto
    total = len(todas_detecciones)

    if total == 0:
        nivel_riesgo = 'bajo'
    elif total <= 3:
        nivel_riesgo = 'medio'
    else:
        nivel_riesgo = 'alto'

    tiempo_procesado = round(time.time() - inicio, 2)

    return Response(
        content=bytes_resultado,
        media_type='image/jpeg',
        headers={
            'X-Detecciones': json.dumps(todas_detecciones),
            'X-Riesgo': nivel_riesgo,
            'X-Total': str(total),
            'X-Tiempo': str(tiempo_procesado),
        }
    )

@app.post('/api/imagen/preview')
async def preview_imagen(archivo: UploadFile = File(...)):
    bytes_imagen = await archivo.read()
    array = np.frombuffer(bytes_imagen, np.uint8)
    imagen = cv2.imdecode(array, cv2.IMREAD_COLOR)

    resultados = modelo_caras(imagen, conf=0.25, verbose=False)[0]

    caras_detectadas = []
    for i, caja in enumerate(resultados.boxes):
        x1, y1, x2, y2 = map(int, caja.xyxy[0].tolist())
        confianza = round(float(caja.conf[0]), 3)
        cv2.rectangle(imagen, (x1, y1), (x2, y2), (0, 200, 100), 2)
        cv2.putText(imagen, str(i + 1), (x1, y1 - 8),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 200, 100), 2)
        caras_detectadas.append({
            'id_cara': i + 1,
            'bbox': [x1, y1, x2, y2],
            'confianza': confianza,
        })

    _, buffer = cv2.imencode('.jpg', imagen)
    imagen_base64 = base64.b64encode(buffer).decode('utf-8')

    return {
        'imagen_preview': imagen_base64,
        'caras': caras_detectadas,
        'total_caras': len(caras_detectadas),
    }


@app.post('/api/analizar/video')
async def analizar_video(
    archivo: UploadFile = File(...),
    caras: bool = True,
    matriculas: bool = True,
    bboxes_excluidas: str = '',
    modo: str = 'blur',
    job_id: str = '',
):
    inicio = time.time()
    bytes_video = await archivo.read()

    lista_bboxes_excluidas = []
    if bboxes_excluidas:
        try:
            lista_bboxes_excluidas = json.loads(bboxes_excluidas)
        except:
            lista_bboxes_excluidas = []

    progreso_actual = {'frame_actual': 0, 'total_frames': 0}
    if job_id:
        progreso_videos[job_id] = progreso_actual

    try:
        bytes_resultado, total, nivel_riesgo, timeline = await asyncio.to_thread(
            procesar_video,
            bytes_video, caras, matriculas,
            bboxes_excluidas=lista_bboxes_excluidas,
            modo=modo,
            progreso=progreso_actual,
        )
    except Exception as error:
        import traceback
        traceback.print_exc()
        raise HTTPException(500, f'Error procesando video: {str(error)}')
    finally:
        if job_id and job_id in progreso_videos:
            del progreso_videos[job_id]

    tiempo_procesado = round(time.time() - inicio, 2)

    return Response(
        content=bytes_resultado,
        media_type='video/mp4',
        headers={
            'X-Total': str(total),
            'X-Riesgo': nivel_riesgo,
            'X-Timeline': json.dumps(timeline),
            'X-Tiempo': str(tiempo_procesado),
        }
    )


@app.get('/api/video/progreso')
async def obtener_progreso_video(job_id: str):
    """Endpoint de polling: devuelve el frame actual y el total para el job dado."""
    if job_id not in progreso_videos:
        return {'frame_actual': 0, 'total_frames': 0}
    return progreso_videos[job_id]



@app.post('/api/video/preview')
async def preview_video(
    archivo: UploadFile = File(...),
    segundo: float = 0.0,
    offset: int = 0,
):
    bytes_video = await archivo.read()

    with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as f:
        f.write(bytes_video)
        ruta_temp = f.name

    try:
        import subprocess
        ruta_frame = ruta_temp.replace('.mp4', '_preview.jpg')
        subprocess.run([
            'ffmpeg', '-i', ruta_temp,
            '-ss', str(segundo),
            '-vframes', '1',
            ruta_frame, '-y'
        ], check=True, capture_output=True)

        imagen = cv2.imread(ruta_frame)
        resultados = modelo_caras(imagen, conf=0.25, verbose=False)[0]

        caras_detectadas = []
        for i, caja in enumerate(resultados.boxes):
            x1, y1, x2, y2 = map(int, caja.xyxy[0].tolist())
            confianza = round(float(caja.conf[0]), 3)

            id_cara = offset + i + 1

            cv2.rectangle(imagen, (x1, y1), (x2, y2), (0, 200, 100), 2)
            cv2.putText(imagen, str(id_cara), (x1, y1 - 8),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 200, 100), 2)

            caras_detectadas.append({
                'id_cara': id_cara,
                'bbox': [x1, y1, x2, y2],
                'confianza': confianza,
            })

        _, buffer = cv2.imencode('.jpg', imagen)
        imagen_base64 = base64.b64encode(buffer).decode('utf-8')

        return {
            'imagen_preview': imagen_base64,
            'caras': caras_detectadas,
            'total_caras': len(caras_detectadas),
        }

    finally:
        if os.path.exists(ruta_temp):
            os.remove(ruta_temp)
        if os.path.exists(ruta_frame):
            os.remove(ruta_frame)


@app.post('/api/directo/frame')
async def procesar_frame_directo(
    archivo: UploadFile = File(...),
    caras: bool = True,
    matriculas: bool = True,
    bboxes_excluidas: str = '',
):
    bytes_frame = await archivo.read()

    nparr = np.frombuffer(bytes_frame, np.uint8)
    imagen = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    alto_orig, ancho_orig = imagen.shape[:2]
    escala = min(1.0, 640 / ancho_orig)
    if escala < 1.0:
        nuevo_ancho = int(ancho_orig * escala)
        nuevo_alto = int(alto_orig * escala)
        imagen = cv2.resize(imagen, (nuevo_ancho, nuevo_alto))

    if imagen is None:
        raise HTTPException(400, 'Frame invalido')

    alto, ancho = imagen.shape[:2]

    lista_bboxes = []
    if bboxes_excluidas:
        try:
            lista_bboxes = json.loads(bboxes_excluidas)
        except Exception:
            lista_bboxes = []

    if caras:
        resultados = modelo_caras(imagen, conf=0.35, verbose=False)[0]
        for caja in resultados.boxes:
            x1, y1, x2, y2 = map(int, caja.xyxy[0].tolist())
            x1 = max(0, x1); y1 = max(0, y1)
            x2 = min(ancho, x2); y2 = min(alto, y2)

            if lista_bboxes and bbox_solapa_con_excluidas(x1, y1, x2, y2, lista_bboxes):
                continue

            centro_x = (x1 + x2) // 2
            centro_y = (y1 + y2) // 2
            radio_x = (x2 - x1) // 2
            radio_y = (y2 - y1) // 2
            cv2.ellipse(imagen, (centro_x, centro_y), (radio_x, radio_y), 0, 0, 360, (0, 0, 0), -1)


    if matriculas:
        resultados_mat = modelo_matriculas(imagen, conf=0.35, verbose=False)[0]
        for caja in resultados_mat.boxes:
            x1, y1, x2, y2 = map(int, caja.xyxy[0].tolist())
            x1 = max(0, x1); y1 = max(0, y1)
            x2 = min(ancho, x2); y2 = min(alto, y2)
 
            margen_x = int((x2 - x1) * 0.2)
            margen_y = int((y2 - y1) * 0.2)
            x1 = max(0, x1 - margen_x)
            y1 = max(0, y1 - margen_y)
            x2 = min(ancho, x2 + margen_x)
            y2 = min(alto, y2 + margen_y)
            cv2.rectangle(imagen, (x1, y1), (x2, y2), (0, 0, 0), -1)

            

    _, buffer = cv2.imencode('.jpg', imagen, [cv2.IMWRITE_JPEG_QUALITY, 80])
    imagen_base64 = base64.b64encode(buffer).decode('utf-8')

    return {'frame': imagen_base64}
