from pathlib import Path
import cv2
import numpy as np
import subprocess
import os
import tempfile
from ultralytics import YOLO
from boxmot.trackers.bytetrack.bytetrack import ByteTrack

CARPETA_PESOS = Path(__file__).resolve().parent.parent / 'modelos' / 'pesos'
ruta_modelo_caras = str(CARPETA_PESOS / 'caras.pt')
ruta_modelo_matriculas = str(CARPETA_PESOS / 'matriculas.pt')

modelo_caras = YOLO(ruta_modelo_caras)
modelo_matriculas = YOLO(ruta_modelo_matriculas)


CONF_CARAS = 0.12
CONF_MATRICULAS = 0.20
IMGSZ = 1280
TAMANO_BATCH = 4


def crear_tracker(fps_video=30):
    """
    ByteTrack configurado para mantener tracks vivos el mayor tiempo posible.
    track_buffer = 3 segundos para sobrevivir a oclusiones largas.
    Umbrales bajos para aceptar detecciones de baja confianza.
    """
    buffer_frames = max(60, int(fps_video * 3))
    return ByteTrack(
        track_high_thresh=0.25,
        track_low_thresh=0.05,
        new_track_thresh=0.30,
        track_buffer=buffer_frames,
        match_thresh=0.85,
        frame_rate=max(1, int(fps_video)),
    )


def expandir_bbox(x1, y1, x2, y2, factor, ancho_img, alto_img):
    """Expande un bbox manteniendo el centro, limitado a las dimensiones de la imagen."""
    ancho = x2 - x1
    alto = y2 - y1
    diff_x = int((ancho * (factor - 1)) / 2)
    diff_y = int((alto * (factor - 1)) / 2)
    return (
        max(0, x1 - diff_x),
        max(0, y1 - diff_y),
        min(ancho_img, x2 + diff_x),
        min(alto_img, y2 + diff_y),
    )


def aplicar_blur_eliptico(imagen, x1, y1, x2, y2):
    alto, ancho = imagen.shape[:2]
    ancho_cara = x2 - x1
    alto_cara = y2 - y1
    area_cara = ancho_cara * alto_cara
    area_imagen = ancho * alto
    proporcion = area_cara / area_imagen

    if proporcion > 0.15:
        margen_porcentaje = 0.10
    elif proporcion > 0.05:
        margen_porcentaje = 0.25
    elif proporcion > 0.01:
        margen_porcentaje = 0.40
    else:
        margen_porcentaje = 0.55

    margen_x = int(ancho_cara * margen_porcentaje)
    margen_y = int(alto_cara * margen_porcentaje)
    x1 = max(0, x1 - margen_x)
    y1 = max(0, y1 - margen_y)
    x2 = min(ancho, x2 + margen_x)
    y2 = min(alto, y2 + margen_y)

    radio_x = (x2 - x1) // 2
    radio_y = (y2 - y1) // 2
    zona = imagen[y1:y2, x1:x2]
    if zona.size == 0:
        return imagen

    mascara = np.zeros(zona.shape[:2], dtype=np.uint8)
    cv2.ellipse(mascara, (radio_x, radio_y), (radio_x, radio_y), 0, 0, 360, 255, -1)
    zona_borrosa = cv2.GaussianBlur(zona, (199, 199), 0)
    zona_final = np.where(mascara[:, :, np.newaxis] == 255, zona_borrosa, zona)
    imagen[y1:y2, x1:x2] = zona_final
    return imagen


def aplicar_blur_rectangular(imagen, x1, y1, x2, y2):
    alto, ancho = imagen.shape[:2]
    margen_x = int((x2 - x1) * 0.2)
    margen_y = int((y2 - y1) * 0.2)
    x1 = max(0, x1 - margen_x)
    y1 = max(0, y1 - margen_y)
    x2 = min(ancho, x2 + margen_x)
    y2 = min(alto, y2 + margen_y)
    zona = imagen[y1:y2, x1:x2]
    if zona.size == 0:
        return imagen
    zona_borrosa = cv2.GaussianBlur(zona, (151, 151), 0)
    imagen[y1:y2, x1:x2] = zona_borrosa
    return imagen


def aplicar_negro_eliptico(imagen, x1, y1, x2, y2):
    alto, ancho = imagen.shape[:2]
    ancho_cara = x2 - x1
    alto_cara = y2 - y1
    area_cara = ancho_cara * alto_cara
    area_imagen = ancho * alto
    proporcion = area_cara / area_imagen

    if proporcion > 0.15:
        margen_porcentaje = 0.10
    elif proporcion > 0.05:
        margen_porcentaje = 0.25
    elif proporcion > 0.01:
        margen_porcentaje = 0.40
    else:
        margen_porcentaje = 0.55

    margen_x = int(ancho_cara * margen_porcentaje)
    margen_y = int(alto_cara * margen_porcentaje)
    x1 = max(0, x1 - margen_x)
    y1 = max(0, y1 - margen_y)
    x2 = min(ancho, x2 + margen_x)
    y2 = min(alto, y2 + margen_y)

    centro_x = (x1 + x2) // 2
    centro_y = (y1 + y2) // 2
    radio_x = (x2 - x1) // 2
    radio_y = (y2 - y1) // 2
    cv2.ellipse(imagen, (centro_x, centro_y), (radio_x, radio_y), 0, 0, 360, (0, 0, 0), -1)
    return imagen


def aplicar_negro_rectangular(imagen, x1, y1, x2, y2):
    alto, ancho = imagen.shape[:2]
    margen_x = int((x2 - x1) * 0.2)
    margen_y = int((y2 - y1) * 0.2)
    x1 = max(0, x1 - margen_x)
    y1 = max(0, y1 - margen_y)
    x2 = min(ancho, x2 + margen_x)
    y2 = min(alto, y2 + margen_y)
    cv2.rectangle(imagen, (x1, y1), (x2, y2), (0, 0, 0), -1)
    return imagen


def obtener_fps(ruta_video):
    comando = [
        'ffprobe', '-v', 'error',
        '-select_streams', 'v:0',
        '-show_entries', 'stream=r_frame_rate',
        '-of', 'default=noprint_wrappers=1:nokey=1',
        ruta_video
    ]
    resultado = subprocess.run(comando, capture_output=True, text=True)
    fps_raw = resultado.stdout.strip()
    if '/' in fps_raw:
        num, den = fps_raw.split('/')
        return round(int(num) / int(den), 2)
    return float(fps_raw) if fps_raw else 25.0


def detectar_corte_camara(frame_anterior, frame_actual, umbral=45.0):
    if frame_anterior is None:
        return False
    diferencia = cv2.absdiff(frame_anterior, frame_actual)
    return diferencia.mean() > umbral


def segundos_a_tiempo(segundos):
    minutos = int(segundos // 60)
    segs = int(segundos % 60)
    return f'{minutos:02d}:{segs:02d}'


def bbox_solapa_con_excluidas(x1, y1, x2, y2, bboxes_excluidas, umbral_iou=0.3):
    for bex in bboxes_excluidas:
        bx1, by1, bx2, by2 = bex
        ix1 = max(x1, bx1)
        iy1 = max(y1, by1)
        ix2 = min(x2, bx2)
        iy2 = min(y2, by2)
        if ix2 <= ix1 or iy2 <= iy1:
            continue
        area_interseccion = (ix2 - ix1) * (iy2 - iy1)
        area_bbox = (x2 - x1) * (y2 - y1)
        iou = area_interseccion / area_bbox if area_bbox > 0 else 0
        if iou >= umbral_iou:
            return True
    return False


def procesar_video(bytes_video, detectar_caras, detectar_matriculas, bboxes_excluidas=None, modo='blur', progreso=None):
    try:
        import torch
        if torch.cuda.is_available():
            torch.zeros(1).cuda()
    except Exception:
        pass

    if bboxes_excluidas is None:
        bboxes_excluidas = []

    with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as f:
        f.write(bytes_video)
        ruta_entrada = f.name

    ruta_salida = ruta_entrada.replace('.mp4', '_anonimizado.mp4')
    carpeta_frames = tempfile.mkdtemp()
    carpeta_resultado = tempfile.mkdtemp()

    try:
        # PASO 1: extraemos los frames
        subprocess.run([
            'ffmpeg', '-i', ruta_entrada,
            '-q:v', '2',
            os.path.join(carpeta_frames, 'frame_%05d.jpg'),
            '-y'
        ], check=True, capture_output=True)

        frames = sorted([f for f in os.listdir(carpeta_frames) if f.endswith('.jpg')])
        if not frames:
            raise ValueError('No se pudieron extraer frames del video')

        total_frames = len(frames)
        print(f'Frames extraidos: {total_frames}')

        if progreso is not None:
            progreso['total_frames'] = total_frames
            progreso['frame_actual'] = 0

        fps = obtener_fps(ruta_entrada)
        print(f'FPS: {fps}')

        # PASO 2: inicializamos los trackers
        tracker_caras = crear_tracker(fps) if detectar_caras else None
        tracker_matriculas = crear_tracker(fps) if detectar_matriculas else None

        frame_anterior = None
        timeline = []
        ids_caras_registrados = set()
        ids_matriculas_registrados = set()

        ultimas_posiciones_caras = {}
        frames_sin_deteccion_caras = {}
        max_frames_memoria = max(3, int(fps * 0.1))
        factor_expansion_por_frame = 0.02
        factor_expansion_max = 1.15

        frame_contador = 0
        batches = [frames[i:i + TAMANO_BATCH] for i in range(0, len(frames), TAMANO_BATCH)]

        for batch in batches:
            imagenes_batch = []
            nombres_batch = []
            for nombre_frame in batch:
                ruta_frame = os.path.join(carpeta_frames, nombre_frame)
                imagen = cv2.imread(ruta_frame)
                imagenes_batch.append(imagen)
                nombres_batch.append(nombre_frame)

            if detectar_caras and tracker_caras is not None:
                resultados_batch = modelo_caras(
                    imagenes_batch,
                    conf=CONF_CARAS,
                    iou=0.45,
                    imgsz=IMGSZ,
                    verbose=False
                )
            else:
                resultados_batch = [None] * len(imagenes_batch)

            if detectar_matriculas and tracker_matriculas is not None:
                resultados_batch_mat = modelo_matriculas(
                    imagenes_batch,
                    conf=CONF_MATRICULAS,
                    iou=0.45,
                    imgsz=IMGSZ,
                    verbose=False
                )
            else:
                resultados_batch_mat = [None] * len(imagenes_batch)

            for idx, (nombre_frame, imagen) in enumerate(zip(nombres_batch, imagenes_batch)):
                frame_contador += 1
                if progreso is not None:
                    progreso['frame_actual'] = frame_contador

                alto, ancho = imagen.shape[:2]

                if detectar_corte_camara(frame_anterior, imagen):
                    print(f'Corte de camara detectado en {nombre_frame}')
                    ultimas_posiciones_caras.clear()
                    frames_sin_deteccion_caras.clear()
                    if detectar_caras:
                        tracker_caras = crear_tracker(fps)
                    if detectar_matriculas:
                        tracker_matriculas = crear_tracker(fps)

                frame_anterior = imagen.copy()
                numero_frame = frames.index(nombre_frame)
                segundo_actual = numero_frame / fps

                if detectar_caras and tracker_caras is not None and resultados_batch[idx] is not None:
                    resultado = resultados_batch[idx]
                    detecciones_numpy = []
                    for caja in resultado.boxes:
                        x1, y1, x2, y2 = map(int, caja.xyxy[0].tolist())
                        confianza = float(caja.conf[0])
                        detecciones_numpy.append([x1, y1, x2, y2, confianza, 0])

                    if detecciones_numpy:
                        dets = np.array(detecciones_numpy, dtype=np.float32)
                    else:
                        dets = np.empty((0, 6), dtype=np.float32)

                    tracks = tracker_caras.update(dets, imagen)

                    ids_activos = set()
                    for track in tracks:
                        x1, y1, x2, y2, track_id = int(track[0]), int(track[1]), int(track[2]), int(track[3]), int(track[4])
                        x1 = max(0, x1); y1 = max(0, y1)
                        x2 = min(ancho, x2); y2 = min(alto, y2)
                        ids_activos.add(track_id)
                        ultimas_posiciones_caras[track_id] = (x1, y1, x2, y2)
                        frames_sin_deteccion_caras[track_id] = 0

                        if track_id not in ids_caras_registrados:
                            ids_caras_registrados.add(track_id)
                            ventana = int(segundo_actual / 5) * 5
                            entrada = next((e for e in timeline if e['segundo'] == ventana and e['tipo'] == 'cara'), None)
                            if entrada:
                                entrada['cantidad'] += 1
                            else:
                                timeline.append({
                                    'tipo': 'cara',
                                    'tiempo': segundos_a_tiempo(ventana),
                                    'segundo': float(ventana),
                                    'cantidad': 1,
                                })

                    # Persistencia: tracks que no aparecen este frame
                    for tid in list(frames_sin_deteccion_caras.keys()):
                        if tid not in ids_activos:
                            frames_sin_deteccion_caras[tid] += 1
                            if frames_sin_deteccion_caras[tid] > max_frames_memoria:
                                del frames_sin_deteccion_caras[tid]
                                if tid in ultimas_posiciones_caras:
                                    del ultimas_posiciones_caras[tid]

                    for tid, (x1, y1, x2, y2) in ultimas_posiciones_caras.items():
                        frames_perdido = frames_sin_deteccion_caras.get(tid, 0)
                        if frames_perdido > 0:
                            factor = min(factor_expansion_max, 1 + frames_perdido * factor_expansion_por_frame)
                            x1, y1, x2, y2 = expandir_bbox(x1, y1, x2, y2, factor, ancho, alto)

                        if not bbox_solapa_con_excluidas(x1, y1, x2, y2, bboxes_excluidas):
                            if modo == 'negro':
                                imagen = aplicar_negro_eliptico(imagen, x1, y1, x2, y2)
                            else:
                                imagen = aplicar_blur_eliptico(imagen, x1, y1, x2, y2)

                if detectar_matriculas and tracker_matriculas is not None and resultados_batch_mat[idx] is not None:
                    resultado_mat = resultados_batch_mat[idx]
                    detecciones_numpy = []
                    for caja in resultado_mat.boxes:
                        x1, y1, x2, y2 = map(int, caja.xyxy[0].tolist())
                        confianza = float(caja.conf[0])
                        detecciones_numpy.append([x1, y1, x2, y2, confianza, 0])

                    if detecciones_numpy:
                        dets = np.array(detecciones_numpy, dtype=np.float32)
                    else:
                        dets = np.empty((0, 6), dtype=np.float32)

                    tracks = tracker_matriculas.update(dets, imagen)

                    for track in tracks:
                        x1, y1, x2, y2 = int(track[0]), int(track[1]), int(track[2]), int(track[3])
                        track_id_mat = int(track[4])
                        x1 = max(0, x1); y1 = max(0, y1)
                        x2 = min(ancho, x2); y2 = min(alto, y2)

                        if track_id_mat not in ids_matriculas_registrados:
                            ids_matriculas_registrados.add(track_id_mat)
                            ventana = int(segundo_actual / 5) * 5
                            entrada = next((e for e in timeline if e['segundo'] == ventana and e['tipo'] == 'matricula'), None)
                            if entrada:
                                entrada['cantidad'] += 1
                            else:
                                timeline.append({
                                    'tipo': 'matricula',
                                    'tiempo': segundos_a_tiempo(ventana),
                                    'segundo': float(ventana),
                                    'cantidad': 1,
                                })

                        if modo == 'negro':
                            imagen = aplicar_negro_rectangular(imagen, x1, y1, x2, y2)
                        else:
                            imagen = aplicar_blur_rectangular(imagen, x1, y1, x2, y2)

                ruta_frame_resultado = os.path.join(carpeta_resultado, nombre_frame)
                cv2.imwrite(ruta_frame_resultado, imagen)
                print(f'Frame procesado: {nombre_frame}')

        # PASO 4: reensamblamos el video con audio
        subprocess.run([
            'ffmpeg',
            '-framerate', str(fps),
            '-i', os.path.join(carpeta_resultado, 'frame_%05d.jpg'),
            '-i', ruta_entrada,
            '-c:v', 'libx264',
            '-c:a', 'aac',
            '-map', '0:v:0',
            '-map', '1:a:0?',
            '-pix_fmt', 'yuv420p',
            ruta_salida, '-y'
        ], check=True, capture_output=True)

        with open(ruta_salida, 'rb') as f:
            bytes_resultado = f.read()

        total_detecciones = len(ids_caras_registrados) + len(ids_matriculas_registrados)

        if total_detecciones == 0:
            nivel_riesgo = 'bajo'
        elif total_detecciones <= 3:
            nivel_riesgo = 'medio'
        else:
            nivel_riesgo = 'alto'

        timeline.sort(key=lambda x: x['segundo'])

        return bytes_resultado, total_detecciones, nivel_riesgo, timeline

    finally:
        for frame in os.listdir(carpeta_frames):
            os.remove(os.path.join(carpeta_frames, frame))
        os.rmdir(carpeta_frames)

        for frame in os.listdir(carpeta_resultado):
            os.remove(os.path.join(carpeta_resultado, frame))
        os.rmdir(carpeta_resultado)

        if os.path.exists(ruta_entrada):
            os.remove(ruta_entrada)
        if os.path.exists(ruta_salida):
            os.remove(ruta_salida)
