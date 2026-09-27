import easyocr
import cv2
import numpy as np
import re

lector_ocr = easyocr.Reader(['es', 'en'], gpu=True)

PATRONES = {
    'dni':                 r'\b\d{8}[\s\-]?[A-Za-z]\b',
    'nie':                 r'\b[XYZxyz][\s\-]?\d{7}[\s\-]?[A-Za-z]\b',
    'pasaporte_es':        r'\b[A-Z]{3}\s?\d{6}\b',
    'iban_es':             r'(?:IBAN\s*:?\s*)?ES\d{2}(?:[\s\-]?\d{4}){5}',
    'tarjeta':             r'\b\d{4}[\s.\-]?\d{4}[\s.\-]?\d{4}[\s.\-]?\d{4}\b',
    'tarjeta_amex':        r'\b\d{4}[\s.\-]?\d{6}[\s.\-]?\d{5}\b',
    'ccc':                 r'\b\d{4}[\s\-]?\d{4}[\s\-]?\d{2}[\s\-]?\d{10}\b',
    'telefono_es':         r'(?:(?:\+|00)?\s*34[\s.\-]*)?\(?[6789]\d{2}\)?[\s.\-]*\d{3}[\s.\-]*\d{3}',
    'email':               r'[a-zA-Z0-9._%+\-]+\s*@\s*[a-zA-Z0-9.\-]+\s*\.\s*[a-zA-Z]{2,}',
    'url':                 r'(?:https?://)?(?:www\.)?[a-zA-Z0-9\-]+\.[a-zA-Z]{2,}(?:/[\w./\-?=&%#]*)?',
    'seguridad_social_es': r'\b\d{2}[\s/\-]\d{8}[\s/\-]\d{2}\b',
    'codigo_postal_es':    r'(?:CP|C\.P\.|codigo\s*postal)[\s:.\-]*((?:0[1-9]|[1-4]\d|5[0-2])\d{3})',
}


def normalizar_texto(texto):
    resultado = texto
    resultado = re.sub(r'(?<=\d)o(?=\d)', '0', resultado)
    resultado = re.sub(r'(?<=\d)o(?=\s)', '0', resultado)
    resultado = re.sub(r'(?<=\s)o(?=\d)', '0', resultado)
    resultado = re.sub(r'(?<=\d)l(?=\d)', '1', resultado)
    resultado = re.sub(r'(\d{8})4[,\.]?\s*$', r'\1A', resultado)
    resultado = resultado.rstrip(',').rstrip('.')
    return resultado


def bbox_completo(coordenadas):
    x1 = int(min(p[0] for p in coordenadas))
    y1 = int(min(p[1] for p in coordenadas))
    x2 = int(max(p[0] for p in coordenadas))
    y2 = int(max(p[1] for p in coordenadas))
    return [x1, y1, x2, y2]


def calcular_sub_bbox(coordenadas, texto_completo, inicio_match, fin_match):
    if not texto_completo or len(texto_completo) == 0:
        return bbox_completo(coordenadas)

    x1_total, y1_total, x2_total, y2_total = bbox_completo(coordenadas)
    ancho_total = x2_total - x1_total
    longitud = len(texto_completo)

    proporcion_inicio = inicio_match / longitud
    proporcion_fin = fin_match / longitud

    x1_match = x1_total + proporcion_inicio * ancho_total
    x2_match = x1_total + proporcion_fin * ancho_total

    margen = max(2, ancho_total * 0.015)
    x1_match = max(x1_total, x1_match - margen)
    x2_match = min(x2_total, x2_match + margen)

    return [int(x1_match), int(y1_total), int(x2_match), int(y2_total)]


def buscar_dni_con_espacios(texto):
    patron_permisivo = r'\d(?:[\s\-]*\d){7}[\s\-]?[A-Za-z]\b'
    return re.search(patron_permisivo, texto)


def detectar_texto_sensible(bytes_imagen):
    textos_encontrados = lector_ocr.readtext(bytes_imagen)

    array = np.frombuffer(bytes_imagen, np.uint8)
    imagen = cv2.imdecode(array, cv2.IMREAD_COLOR)

    for i, (coordenadas, texto, confianza) in enumerate(textos_encontrados):
        print(f'[{round(confianza,2)}] "{texto}"')

    detecciones_texto = []
    indices_usados = set()

    for i in range(len(textos_encontrados)):
        if i in indices_usados:
            continue

        coords_i, texto_i, conf_i = textos_encontrados[i]
        texto_i_norm = normalizar_texto(texto_i).strip().rstrip(':').strip()

        if not re.search(r'(ES\d|IBAN)', texto_i_norm, re.IGNORECASE):
            continue

        fragmentos = [(coords_i, texto_i_norm, conf_i)]
        for j in range(i + 1, min(i + 8, len(textos_encontrados))):
            if j in indices_usados:
                break
            coords_j, texto_j, conf_j = textos_encontrados[j]
            texto_j_norm = normalizar_texto(texto_j)
            fragmentos.append((coords_j, texto_j_norm, conf_j))

            texto_hasta_aqui = ' '.join(f[1] for f in fragmentos)
            texto_sin_espacios = re.sub(r'\s', '', texto_hasta_aqui)
            if re.search(PATRONES['iban_es'], texto_hasta_aqui, re.IGNORECASE) or \
               re.search(r'ES\d{20}', texto_sin_espacios, re.IGNORECASE):
                break

        texto_combinado = ' '.join(f[1] for f in fragmentos)
        texto_sin_espacios = re.sub(r'\s', '', texto_combinado)

        match_iban = re.search(PATRONES['iban_es'], texto_combinado, re.IGNORECASE)
        match_compacto = re.search(r'ES\d{20}', texto_sin_espacios, re.IGNORECASE)

        if not (match_iban or match_compacto):
            continue

        sub_bboxes = []

        if match_iban:
            inicio_match = match_iban.start()
            fin_match = match_iban.end()

            posicion_actual = 0
            for (coords_f, texto_f, _) in fragmentos:
                inicio_frag = posicion_actual
                fin_frag = posicion_actual + len(texto_f)

                solape_inicio = max(inicio_match, inicio_frag)
                solape_fin = min(fin_match, fin_frag)

                if solape_fin > solape_inicio:
                    inicio_local = solape_inicio - inicio_frag
                    fin_local = solape_fin - inicio_frag
                    sub_bboxes.append(
                        calcular_sub_bbox(coords_f, texto_f, inicio_local, fin_local)
                    )

                posicion_actual = fin_frag + 1
        else:
            for (coords_f, _, _) in fragmentos:
                sub_bboxes.append(bbox_completo(coords_f))

        if sub_bboxes:
            x1 = min(b[0] for b in sub_bboxes)
            y1 = min(b[1] for b in sub_bboxes)
            x2 = max(b[2] for b in sub_bboxes)
            y2 = max(b[3] for b in sub_bboxes)

            detecciones_texto.append({
                'tipo': 'iban',
                'texto': texto_combinado,
                'bbox': [x1, y1, x2, y2],
                'confianza': 0.9,
            })
            for k in range(i, i + len(fragmentos)):
                indices_usados.add(k)


    for i in range(len(textos_encontrados)):
        if i in indices_usados:
            continue

        coords_i, texto_i, conf_i = textos_encontrados[i]
        texto_i_norm = normalizar_texto(texto_i)

        if not re.search(r'\bDNI\b', texto_i_norm, re.IGNORECASE):
            continue

        match_dni = buscar_dni_con_espacios(texto_i_norm)

        if match_dni:
            bbox = calcular_sub_bbox(coords_i, texto_i_norm, match_dni.start(), match_dni.end())
            detecciones_texto.append({
                'tipo': 'dni',
                'texto': texto_i_norm[match_dni.start():match_dni.end()],
                'bbox': bbox,
                'confianza': round(float(conf_i), 3),
            })
            indices_usados.add(i)
            continue

        for j in range(i + 1, min(i + 4, len(textos_encontrados))):
            if j in indices_usados:
                break
            coords_j, texto_j, conf_j = textos_encontrados[j]
            texto_j_norm = normalizar_texto(texto_j)

            match_numero = buscar_dni_con_espacios(texto_j_norm)
            if match_numero:
                bbox = calcular_sub_bbox(coords_j, texto_j_norm, match_numero.start(), match_numero.end())
                detecciones_texto.append({
                    'tipo': 'dni',
                    'texto': texto_j_norm[match_numero.start():match_numero.end()],
                    'bbox': bbox,
                    'confianza': round(float(conf_j), 3),
                })
                indices_usados.add(i)
                indices_usados.add(j)
                break

    for i, (coordenadas, texto, confianza) in enumerate(textos_encontrados):
        if i in indices_usados:
            continue
        if confianza < 0.3:
            continue

        texto_normalizado = normalizar_texto(texto)

        for nombre_patron, patron in PATRONES.items():
            if nombre_patron == 'iban_es':
                continue

            match = re.search(patron, texto_normalizado, re.IGNORECASE)
            if not match:
                continue

            bbox = calcular_sub_bbox(coordenadas, texto_normalizado, match.start(), match.end())

            detecciones_texto.append({
                'tipo': nombre_patron,
                'texto': texto_normalizado[match.start():match.end()],
                'bbox': bbox,
                'confianza': round(float(confianza), 3),
            })
            indices_usados.add(i)
            break

    return detecciones_texto, imagen


def redactar_texto(imagen, detecciones_texto):
    for deteccion in detecciones_texto:
        x1, y1, x2, y2 = deteccion['bbox']
        cv2.rectangle(imagen, (x1, y1), (x2, y2), (0, 0, 0), -1)
    return imagen