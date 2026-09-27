const btnTema = document.getElementById('btnTema')
const textoTema = document.getElementById('textoTema')
const iconoTema = document.querySelector('.icono-tema')
let temaActual = 'oscuro'

btnTema.addEventListener('click', function() {
    temaActual = temaActual === 'oscuro' ? 'claro' : 'oscuro'
    document.documentElement.setAttribute('data-tema', temaActual)
    textoTema.textContent = temaActual === 'oscuro' ? 'Oscuro' : 'Claro'
    // Cambiar icono sol/luna
    if (temaActual === 'claro') {
        iconoTema.innerHTML = '<circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/>'
    } else {
        iconoTema.innerHTML = '<path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>'
    }
})

document.querySelectorAll('.pestana').forEach(function(pestana) {
    pestana.addEventListener('click', function() {
        document.querySelectorAll('.pestana').forEach(p => p.classList.remove('activa'))
        document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('activa'))
        pestana.classList.add('activa')
        document.getElementById('tab-' + pestana.dataset.tab).classList.add('activa')
        if (pestana.dataset.tab !== 'directo' && streamActivo) {
            pararDirecto()
        }
    })
})

function segundosAFormato(segundos) {
    const mins = Math.floor(segundos / 60)
    const segs = Math.floor(segundos % 60)
    return `${String(mins).padStart(2, '0')}:${String(segs).padStart(2, '0')}`
}

function formatearTiempo(segundos) {
    const total = parseFloat(segundos)
    if (isNaN(total)) return '?'
    const segs_redondeado = Math.round(total)
    if (segs_redondeado < 60) return `${segs_redondeado}s`
    const minutos = Math.floor(segs_redondeado / 60)
    const restante = segs_redondeado % 60
    return `${minutos}m ${restante}s`
}

function crearInputArchivo(accept, callback) {
    const input = document.createElement('input')
    input.type = 'file'
    input.accept = accept
    input.style.display = 'none'
    input.addEventListener('change', function(e) {
        const archivo = e.target.files[0]
        if (archivo) callback(archivo)
    })
    document.body.appendChild(input)
    return input
}

function iniciarContador(elementoId) {
    let segundos = 0
    const el = document.getElementById(elementoId)
    el.textContent = formatearTiempo(0)
    const intervalo = setInterval(function() {
        segundos++
        el.textContent = formatearTiempo(segundos)
    }, 1000)
    return intervalo
}

function pararContador(intervalo) {
    clearInterval(intervalo)
}

let archivoImagen = null
let carasExcluidasImagen = new Set()
let carasDetectadasImagen = []
let intervaloImagen = null

const zonaSubidaImagen = document.getElementById('zonaSubidaImagen')

function mostrarPreviaImagen(archivo) {
    archivoImagen = archivo
    const tamano = (archivo.size / 1024 / 1024).toFixed(1)
    zonaSubidaImagen.innerHTML = `
        <div style="display:flex; flex-direction:column; align-items:center; gap:6px;">
            <span style="font-size:14px; font-weight:600; color:var(--text-primary);">${archivo.name}</span>
            <span style="font-size:12px; color:var(--text-muted);">${tamano} MB</span>
        </div>
    `
    const panel = document.getElementById('panelArchivoImagen')
    panel.innerHTML = `
        <button id="btnCambiarImagen" class="btn-secundario">Cambiar</button>
        <button id="btnEliminarImagen" class="btn-secundario" style="color:var(--danger); border-color:var(--danger);">Eliminar</button>
    `
    panel.style.display = 'flex'
    panel.classList.remove('oculto')

    document.getElementById('btnEliminarImagen').addEventListener('click', limpiarImagen)
    document.getElementById('btnCambiarImagen').addEventListener('click', function() {
        crearInputArchivo('image/*', mostrarPreviaImagen).click()
    })

    document.getElementById('btnAnalizarImagen').disabled = false
    document.getElementById('resultadoImagen').classList.add('oculto')
    document.getElementById('btnDescargarImagen').classList.add('oculto')
    document.getElementById('btnReporteImagen').classList.add('oculto')
    carasExcluidasImagen = new Set()
    carasDetectadasImagen = []
    cargarPreviewCarasImagen(archivo)
}

function limpiarImagen() {
    archivoImagen = null
    carasExcluidasImagen = new Set()
    carasDetectadasImagen = []
    document.getElementById('selectorCarasImagen').classList.add('oculto')
    zonaSubidaImagen.innerHTML = '<p>Arrastra una imagen aquí o haz clic para seleccionar</p>'
    const panel = document.getElementById('panelArchivoImagen')
    panel.innerHTML = ''
    panel.classList.add('oculto')
    document.getElementById('btnAnalizarImagen').disabled = true
    document.getElementById('resultadoImagen').classList.add('oculto')
    document.getElementById('btnDescargarImagen').classList.add('oculto')
    document.getElementById('btnReporteImagen').classList.add('oculto')
}

async function cargarPreviewCarasImagen(archivo) {
    const selectorEl = document.getElementById('selectorCarasImagen')
    const previstaEl = document.getElementById('imagenPreviewSelector')
    const listaEl = document.getElementById('listaCarasImagen')

    selectorEl.classList.remove('oculto')
    listaEl.innerHTML = '<p style="font-size:12px; color:var(--text-muted);">Analizando caras...</p>'
    previstaEl.style.opacity = '0.4'

    const formulario = new FormData()
    formulario.append('archivo', archivo)

    try {
        const respuesta = await fetch('http://localhost:8000/api/imagen/preview', {
            method: 'POST', body: formulario
        })
        const datos = await respuesta.json()

        carasDetectadasImagen = datos.caras
        previstaEl.src = 'data:image/jpeg;base64,' + datos.imagen_preview
        previstaEl.style.opacity = '1'

        listaEl.innerHTML = ''
        if (datos.total_caras === 0) {
            listaEl.innerHTML = '<p style="font-size:12px; color:var(--text-muted);">No se detectaron caras.</p>'
        } else {
            datos.caras.forEach(function(cara) {
                const item = document.createElement('div')
                item.className = 'cara-item'
                item.innerHTML = `
                    <span class="cara-numero">${cara.id_cara}</span>
                    <span>Cara ${cara.id_cara}</span>
                    <span style="margin-left:auto; font-size:11px; color:var(--text-muted)">${Math.round(cara.confianza * 100)}%</span>
                `
                item.addEventListener('click', function() {
                    if (carasExcluidasImagen.has(cara.id_cara)) {
                        carasExcluidasImagen.delete(cara.id_cara)
                        item.classList.remove('excluida')
                        item.querySelector('span:nth-child(2)').textContent = `Cara ${cara.id_cara}`
                    } else {
                        carasExcluidasImagen.add(cara.id_cara)
                        item.classList.add('excluida')
                        item.querySelector('span:nth-child(2)').textContent = 'No censurar'
                    }
                })
                listaEl.appendChild(item)
            })
        }
    } catch (error) {
        listaEl.innerHTML = '<p style="font-size:12px; color:var(--danger);">Error al cargar el preview.</p>'
    }
}

zonaSubidaImagen.addEventListener('click', function() {
    crearInputArchivo('image/*', mostrarPreviaImagen).click()
})
zonaSubidaImagen.addEventListener('dragover', function(e) { e.preventDefault(); zonaSubidaImagen.style.borderColor = 'var(--accent)' })
zonaSubidaImagen.addEventListener('dragleave', function() { zonaSubidaImagen.style.borderColor = '' })
zonaSubidaImagen.addEventListener('drop', function(e) {
    e.preventDefault()
    zonaSubidaImagen.style.borderColor = ''
    const archivo = e.dataTransfer.files[0]
    if (archivo && archivo.type.startsWith('image/')) mostrarPreviaImagen(archivo)
})

document.getElementById('btnAnalizarImagen').addEventListener('click', async function() {
    if (!archivoImagen) return

    const cargando = document.getElementById('cargandoImagen')
    cargando.classList.remove('oculto')
    document.getElementById('btnAnalizarImagen').disabled = true
    document.getElementById('resultadoImagen').classList.add('oculto')
    intervaloImagen = iniciarContador('contadorTiempoImagen')

    const formulario = new FormData()
    formulario.append('archivo', archivoImagen)

    const caras = document.getElementById('checkCarasImagen').checked
    const matriculas = document.getElementById('checkMatriculasImagen').checked
    const texto = document.getElementById('checkTextoImagen').checked
    const modo = document.querySelector('input[name="modoImagen"]:checked').value

    const bboxExcluidasImagen = carasDetectadasImagen
        .filter(c => carasExcluidasImagen.has(c.id_cara))
        .map(c => c.bbox)

    let url = `http://localhost:8000/api/analizar?caras=${caras}&matriculas=${matriculas}&texto=${texto}&modo=${modo}`
    if (bboxExcluidasImagen.length > 0) {
        url += `&bboxes_excluidas=${encodeURIComponent(JSON.stringify(bboxExcluidasImagen))}`
    }

    try {
        const respuesta = await fetch(url, { method: 'POST', body: formulario })
        pararContador(intervaloImagen)

        const total = respuesta.headers.get('X-Total')
        const riesgo = respuesta.headers.get('X-Riesgo')
        const tiempo = respuesta.headers.get('X-Tiempo')
        const detecciones = JSON.parse(respuesta.headers.get('X-Detecciones') || '[]')
        const blob = await respuesta.blob()
        const urlResultado = URL.createObjectURL(blob)

        document.getElementById('statCarasImagen').textContent = detecciones.filter(d => d.tipo === 'cara').length
        document.getElementById('statMatriculasImagen').textContent = detecciones.filter(d => d.tipo === 'matricula').length
        document.getElementById('statTextosImagen').textContent = detecciones.filter(d => !['cara','matricula'].includes(d.tipo)).length
        document.getElementById('statTiempoImagen').textContent = formatearTiempo(tiempo)

        const tarjetaRiesgo = document.getElementById('statRiesgoImagen')
        tarjetaRiesgo.className = `stat-item stat-riesgo riesgo-${riesgo}`
        document.getElementById('valorRiesgoImagen').textContent = riesgo

        document.getElementById('imagenOriginal').src = URL.createObjectURL(archivoImagen)
        document.getElementById('imagenResultado').src = urlResultado

        const btnDesc = document.getElementById('btnDescargarImagen')
        btnDesc.href = urlResultado
        btnDesc.download = 'imagen_anonimizada.jpg'
        btnDesc.classList.remove('oculto')
        document.getElementById('btnReporteImagen').classList.remove('oculto')

        const lista = document.getElementById('listaDeteccionesImagen')
        lista.innerHTML = ''
        if (detecciones.length === 0) {
            lista.innerHTML = '<p style="font-size:13px; color:var(--text-muted); grid-column:1/-1;">No se detectaron datos sensibles.</p>'
        } else {
            detecciones.forEach(function(det) {
                const item = document.createElement('div')
                item.className = 'deteccion-item'
                item.innerHTML = `<span class="tipo-etiqueta">${det.tipo}</span><span class="tiempo-evento">${det.confianza}</span>`
                lista.appendChild(item)
            })
        }

        const resultado = document.getElementById('resultadoImagen')
        resultado.classList.remove('oculto')
        requestAnimationFrame(() => resultado.classList.add('visible'))

    } catch (error) {
        pararContador(intervaloImagen)
        alert('Error al conectar con el servidor.')
    }

    cargando.classList.add('oculto')
    document.getElementById('btnAnalizarImagen').disabled = false
})

let archivoVideo = null
let carasExcluidas = new Set()
let carasDetectadas = []  // Acumula caras de todas las escenas visitadas
let contadorIdCaras = 0   // Contador global; se resetea solo con video nuevo
let intervaloVideo = null

const zonaSubidaVideo = document.getElementById('zonaSubidaVideo')
const selectorCaras = document.getElementById('selectorCaras')
const sliderSegundo = document.getElementById('sliderSegundo')
const labelSegundoActual = document.getElementById('labelSegundoActual')
const labelSegundoTotal = document.getElementById('labelSegundoTotal')
const imagenPreview = document.getElementById('imagenPreview')
const listaCaras = document.getElementById('listaCaras')

function mostrarPreviaVideo(archivo) {
    archivoVideo = archivo
    carasExcluidas = new Set()
    carasDetectadas = []
    contadorIdCaras = 0
    const tamano = (archivo.size / 1024 / 1024).toFixed(1)
    zonaSubidaVideo.innerHTML = `
        <div style="display:flex; flex-direction:column; align-items:center; gap:6px;">
            <span style="font-size:14px; font-weight:600; color:var(--text-primary);">${archivo.name}</span>
            <span style="font-size:12px; color:var(--text-muted);">${tamano} MB</span>
        </div>
    `
    const panel = document.getElementById('panelArchivoVideo')
    panel.innerHTML = `
        <button id="btnCambiarVideo" class="btn-secundario">Cambiar</button>
        <button id="btnEliminarVideo" class="btn-secundario" style="color:var(--danger); border-color:var(--danger);">Eliminar</button>
    `
    panel.style.display = 'flex'
    panel.classList.remove('oculto')

    document.getElementById('btnEliminarVideo').addEventListener('click', limpiarVideo)
    document.getElementById('btnCambiarVideo').addEventListener('click', function() {
        crearInputArchivo('video/*', mostrarPreviaVideo).click()
    })

    selectorCaras.classList.remove('oculto')
    inicializarSlider(archivo)
    cargarFrameCaras(0)

    document.getElementById('btnAnalizarVideo').disabled = false
    document.getElementById('resultadoVideo').classList.add('oculto')
    document.getElementById('btnDescargarVideo').classList.add('oculto')
}

function limpiarVideo() {
    archivoVideo = null
    carasExcluidas = new Set()
    carasDetectadas = []
    contadorIdCaras = 0
    selectorCaras.classList.add('oculto')
    zonaSubidaVideo.innerHTML = '<p>Arrastra un vídeo aquí o haz clic para seleccionar</p>'
    const panel = document.getElementById('panelArchivoVideo')
    panel.innerHTML = ''
    panel.classList.add('oculto')
    document.getElementById('btnAnalizarVideo').disabled = true
    document.getElementById('resultadoVideo').classList.add('oculto')
    document.getElementById('btnDescargarVideo').classList.add('oculto')
}

zonaSubidaVideo.addEventListener('click', function() {
    crearInputArchivo('video/*', mostrarPreviaVideo).click()
})
zonaSubidaVideo.addEventListener('dragover', function(e) { e.preventDefault(); zonaSubidaVideo.style.borderColor = 'var(--accent)' })
zonaSubidaVideo.addEventListener('dragleave', function() { zonaSubidaVideo.style.borderColor = '' })
zonaSubidaVideo.addEventListener('drop', function(e) {
    e.preventDefault()
    zonaSubidaVideo.style.borderColor = ''
    const archivo = e.dataTransfer.files[0]
    if (archivo && archivo.type.startsWith('video/')) mostrarPreviaVideo(archivo)
})

async function inicializarSlider(archivo) {
    const urlLocal = URL.createObjectURL(archivo)
    const videoTemp = document.createElement('video')
    videoTemp.src = urlLocal
    await new Promise(function(resolve) {
        videoTemp.addEventListener('loadedmetadata', function() {
            const duracion = Math.floor(videoTemp.duration)
            sliderSegundo.max = duracion
            sliderSegundo.value = 0
            labelSegundoTotal.textContent = segundosAFormato(duracion)
            labelSegundoActual.textContent = '00:00'
            resolve()
        })
    })
}

sliderSegundo.addEventListener('input', function() {
    labelSegundoActual.textContent = segundosAFormato(parseInt(sliderSegundo.value))
})

sliderSegundo.addEventListener('change', function() {
    cargarFrameCaras(parseInt(sliderSegundo.value))
})

async function cargarFrameCaras(segundo) {
    const scrollY = window.scrollY
    listaCaras.innerHTML = '<p style="font-size:12px; color:var(--text-muted);">Analizando frame...</p>'
    imagenPreview.style.opacity = '0.4'

    const formulario = new FormData()
    formulario.append('archivo', archivoVideo)

    try {
        const url = `http://localhost:8000/api/video/preview?segundo=${segundo}&offset=${contadorIdCaras}`
        const respuesta = await fetch(url, {
            method: 'POST', body: formulario
        })
        const datos = await respuesta.json()

        carasDetectadas = carasDetectadas.concat(datos.caras)
        contadorIdCaras += datos.caras.length

        imagenPreview.src = 'data:image/jpeg;base64,' + datos.imagen_preview
        imagenPreview.style.opacity = '1'

        listaCaras.innerHTML = ''
        if (datos.total_caras === 0) {
            listaCaras.innerHTML = '<p style="font-size:12px; color:var(--text-muted);">No se detectaron caras en este frame.</p>'
        } else {
            datos.caras.forEach(function(cara) {
                const item = document.createElement('div')
                item.className = 'cara-item'
                if (carasExcluidas.has(cara.id_cara)) {
                    item.classList.add('excluida')
                }
                const textoEstado = carasExcluidas.has(cara.id_cara) ? 'No censurar' : `ID Cara ${cara.id_cara}`
                item.innerHTML = `
                    <span class="cara-numero">${cara.id_cara}</span>
                    <span>${textoEstado}</span>
                    <span style="margin-left:auto; font-size:11px; color:var(--text-muted)">${Math.round(cara.confianza * 100)}%</span>
                `
                item.addEventListener('click', function() {
                    if (carasExcluidas.has(cara.id_cara)) {
                        carasExcluidas.delete(cara.id_cara)
                        item.classList.remove('excluida')
                        item.querySelector('span:nth-child(2)').textContent = `ID Cara ${cara.id_cara}`
                    } else {
                        carasExcluidas.add(cara.id_cara)
                        item.classList.add('excluida')
                        item.querySelector('span:nth-child(2)').textContent = 'No censurar'
                    }
                })
                listaCaras.appendChild(item)
            })
        }
    } catch (error) {
        listaCaras.innerHTML = '<p style="font-size:12px; color:var(--danger);">Error al cargar el frame.</p>'
    }
    window.scrollTo({ top: scrollY, behavior: 'instant' })
}

document.getElementById('btnAnalizarVideo').addEventListener('click', async function() {
    if (!archivoVideo) return

    const cargando = document.getElementById('cargandoVideo')
    cargando.classList.remove('oculto')
    document.getElementById('textoCargandoVideo').textContent = 'Procesando vídeo... esto puede tardar varios minutos'
    document.getElementById('btnAnalizarVideo').disabled = true
    document.getElementById('resultadoVideo').classList.add('oculto')

    const barraFill = document.getElementById('barraVideoFill')
    const contadorFrames = document.getElementById('contadorFramesVideo')
    barraFill.classList.remove('progreso-real')
    barraFill.style.width = ''
    contadorFrames.textContent = 'Preparando...'

    const formulario = new FormData()
    formulario.append('archivo', archivoVideo)

    const caras = document.getElementById('checkCarasVideo').checked
    const matriculas = document.getElementById('checkMatriculasVideo').checked
    const modo = document.querySelector('input[name="modoVideo"]:checked').value
    const bboxExcluidas = carasDetectadas.filter(c => carasExcluidas.has(c.id_cara)).map(c => c.bbox)

    // Generamos un job_id unico para esta peticion
    const jobId = 'job_' + Date.now()

    let url = `http://localhost:8000/api/analizar/video?caras=${caras}&matriculas=${matriculas}&modo=${modo}&job_id=${jobId}`
    if (bboxExcluidas.length > 0) {
        url += `&bboxes_excluidas=${encodeURIComponent(JSON.stringify(bboxExcluidas))}`
    }

    // Polling de progreso cada 600ms
    const intervaloPoll = setInterval(async function() {
        try {
            const respPoll = await fetch(`http://localhost:8000/api/video/progreso?job_id=${jobId}`)
            const prog = await respPoll.json()
            if (prog.total_frames > 0) {
                const porcentaje = Math.round((prog.frame_actual / prog.total_frames) * 100)
                barraFill.classList.add('progreso-real')
                barraFill.style.width = porcentaje + '%'
                contadorFrames.textContent = `Frame ${prog.frame_actual} de ${prog.total_frames}`
            }
        } catch (e) {}
    }, 600)

    try {
        const respuesta = await fetch(url, { method: 'POST', body: formulario })
        clearInterval(intervaloPoll)
        barraFill.classList.add('progreso-real')
        barraFill.style.width = '100%'

        const total = respuesta.headers.get('X-Total')
        const riesgo = respuesta.headers.get('X-Riesgo')
        const tiempo = respuesta.headers.get('X-Tiempo')
        const timeline = JSON.parse(respuesta.headers.get('X-Timeline') || '[]')
        const blob = await respuesta.blob()
        const urlResultado = URL.createObjectURL(blob)

        const totalCaras = timeline
            .filter(e => e.tipo === 'cara')
            .reduce((suma, e) => suma + e.cantidad, 0)
        const totalMatriculas = timeline
            .filter(e => e.tipo === 'matricula')
            .reduce((suma, e) => suma + e.cantidad, 0)

        document.getElementById('statCarasVideo').textContent = totalCaras
        document.getElementById('statMatriculasVideo').textContent = totalMatriculas
        document.getElementById('statTiempoVideo').textContent = formatearTiempo(tiempo)

        // Tarjeta de riesgo
        const tarjetaRiesgo = document.getElementById('statRiesgoVideo')
        tarjetaRiesgo.className = `stat-item stat-riesgo riesgo-${riesgo}`
        document.getElementById('valorRiesgoVideo').textContent = riesgo

        document.getElementById('videoOriginal').src = URL.createObjectURL(archivoVideo)
        document.getElementById('videoResultado').src = urlResultado

        const btnDesc = document.getElementById('btnDescargarVideo')
        btnDesc.href = urlResultado
        btnDesc.download = 'video_anonimizado.mp4'
        btnDesc.classList.remove('oculto')

        const lista = document.getElementById('listaDeteccionesVideo')
        lista.innerHTML = ''
        if (timeline.length === 0) {
            lista.innerHTML = '<p style="font-size:13px; color:var(--text-muted); grid-column:1/-1;">No se detectaron incidencias.</p>'
        } else {
            timeline.forEach(function(evento) {
                const item = document.createElement('div')
                item.className = 'deteccion-item'
                item.style.cursor = 'pointer'
                item.innerHTML = `<span class="tipo-etiqueta">${evento.tipo}</span><span>×${evento.cantidad}</span><span class="tiempo-evento">${evento.tiempo}</span>`
                item.addEventListener('click', function() {
                    document.getElementById('videoResultado').currentTime = evento.segundo
                    document.getElementById('videoResultado').play()
                })
                lista.appendChild(item)
            })
        }

        const resultado = document.getElementById('resultadoVideo')
        resultado.classList.remove('oculto')
        requestAnimationFrame(() => resultado.classList.add('visible'))

    } catch (error) {
        clearInterval(intervaloPoll)
        barraFill.classList.remove('progreso-real')
        barraFill.style.width = ''
        alert('Error al conectar con el servidor.')
    }

    cargando.classList.add('oculto')
    barraFill.classList.remove('progreso-real')
    barraFill.style.width = ''
    contadorFrames.textContent = 'Preparando...'
    document.getElementById('btnAnalizarVideo').disabled = false
})

let streamActivo = false
let streamWebcam = null
let intervaloDirecto = null
let carasExcluidasDirecto = new Set()
let carasDetectadasDirecto = []
let bboxesExcluidasDirecto = []

const videoWebcam = document.getElementById('videoWebcam')
const frameDirecto = document.getElementById('frameDirecto')
const canvasCaptura = document.getElementById('canvasCaptura')
const fpsDirecto = document.getElementById('fpsDirecto')
const btnIniciarDirecto = document.getElementById('btnIniciarDirecto')
const btnPararDirecto = document.getElementById('btnPararDirecto')
const directoContenido = document.getElementById('directoContenido')

btnIniciarDirecto.addEventListener('click', async function() {
    try {
        streamWebcam = await navigator.mediaDevices.getUserMedia({ video: true })
        videoWebcam.srcObject = streamWebcam
        streamActivo = true
        btnIniciarDirecto.classList.add('oculto')
        btnPararDirecto.classList.remove('oculto')
        document.getElementById('btnSeleccionarCarasDirecto').classList.remove('oculto')
        directoContenido.classList.remove('oculto')
        procesarDirecto()
    } catch (error) {
        alert('No se pudo acceder a la webcam. Asegúrate de dar permisos.')
    }
})

btnPararDirecto.addEventListener('click', pararDirecto)

function pararDirecto() {
    streamActivo = false
    if (streamWebcam) {
        streamWebcam.getTracks().forEach(track => track.stop())
        streamWebcam = null
    }
    clearTimeout(intervaloDirecto)
    videoWebcam.srcObject = null
    btnIniciarDirecto.classList.remove('oculto')
    btnPararDirecto.classList.add('oculto')
    document.getElementById('btnSeleccionarCarasDirecto').classList.add('oculto')
    document.getElementById('selectorCarasDirecto').classList.add('oculto')
    directoContenido.classList.add('oculto')
    frameDirecto.src = ''
    carasExcluidasDirecto = new Set()
    carasDetectadasDirecto = []
    bboxesExcluidasDirecto = []
}

document.getElementById('btnSeleccionarCarasDirecto').addEventListener('click', capturarYSeleccionarCarasDirecto)
document.getElementById('btnRefrescarDirecto').addEventListener('click', capturarYSeleccionarCarasDirecto)

async function capturarYSeleccionarCarasDirecto() {
    if (!streamActivo || videoWebcam.videoWidth === 0) return

    const selectorEl = document.getElementById('selectorCarasDirecto')
    const previstaEl = document.getElementById('imagenPreviewDirecto')
    const listaEl = document.getElementById('listaCarasDirecto')

    // Capturamos el frame actual de la webcam
    const anchoCaptura = 640
    const altoCaptura = Math.round(videoWebcam.videoHeight * (anchoCaptura / videoWebcam.videoWidth))
    const canvasTemp = document.createElement('canvas')
    canvasTemp.width = anchoCaptura
    canvasTemp.height = altoCaptura
    canvasTemp.getContext('2d').drawImage(videoWebcam, 0, 0, anchoCaptura, altoCaptura)

    selectorEl.classList.remove('oculto')
    listaEl.innerHTML = '<p style="font-size:12px; color:var(--text-muted);">Analizando caras...</p>'
    previstaEl.style.opacity = '0.4'

    canvasTemp.toBlob(async function(blob) {
        const formulario = new FormData()
        formulario.append('archivo', blob, 'captura.jpg')

        try {
            const respuesta = await fetch('http://localhost:8000/api/imagen/preview', {
                method: 'POST', body: formulario
            })
            const datos = await respuesta.json()

            carasDetectadasDirecto = datos.caras
            carasExcluidasDirecto = new Set()
            bboxesExcluidasDirecto = []

            previstaEl.src = 'data:image/jpeg;base64,' + datos.imagen_preview
            previstaEl.style.opacity = '1'

            listaEl.innerHTML = ''
            if (datos.total_caras === 0) {
                listaEl.innerHTML = '<p style="font-size:12px; color:var(--text-muted);">No se detectaron caras en este momento.</p>'
            } else {
                datos.caras.forEach(function(cara) {
                    const item = document.createElement('div')
                    item.className = 'cara-item'
                    item.innerHTML = `
                        <span class="cara-numero">${cara.id_cara}</span>
                        <span>Cara ${cara.id_cara}</span>
                        <span style="margin-left:auto; font-size:11px; color:var(--text-muted)">${Math.round(cara.confianza * 100)}%</span>
                    `
                    item.addEventListener('click', function() {
                        if (carasExcluidasDirecto.has(cara.id_cara)) {
                            carasExcluidasDirecto.delete(cara.id_cara)
                            item.classList.remove('excluida')
                            item.querySelector('span:nth-child(2)').textContent = `Cara ${cara.id_cara}`
                        } else {
                            carasExcluidasDirecto.add(cara.id_cara)
                            item.classList.add('excluida')
                            item.querySelector('span:nth-child(2)').textContent = 'No censurar'
                        }
                        // Actualizar las bboxes excluidas activas
                        bboxesExcluidasDirecto = carasDetectadasDirecto
                            .filter(c => carasExcluidasDirecto.has(c.id_cara))
                            .map(c => c.bbox)
                    })
                    listaEl.appendChild(item)
                })
            }
        } catch (error) {
            listaEl.innerHTML = '<p style="font-size:12px; color:var(--danger);">Error al analizar el frame.</p>'
        }
    }, 'image/jpeg', 0.8)
}

async function procesarDirecto() {
    if (!streamActivo) return

    if (videoWebcam.videoWidth === 0 || videoWebcam.videoHeight === 0) {
        intervaloDirecto = setTimeout(procesarDirecto, 200)
        return
    }

    const caras = document.getElementById('checkCarasDirecto').checked
    const matriculas = document.getElementById('checkMatriculasDirecto').checked

    const anchoEnvio = 640
    const altoEnvio = Math.round(videoWebcam.videoHeight * (anchoEnvio / videoWebcam.videoWidth))
    canvasCaptura.width = anchoEnvio
    canvasCaptura.height = altoEnvio
    const ctx = canvasCaptura.getContext('2d')
    ctx.drawImage(videoWebcam, 0, 0, anchoEnvio, altoEnvio)

    canvasCaptura.toBlob(async function(blob) {
        if (!blob || !streamActivo) return

        const formulario = new FormData()
        formulario.append('archivo', blob, 'frame.jpg')

        const inicio = Date.now()
        let urlDirecto = `http://localhost:8000/api/directo/frame?caras=${caras}&matriculas=${matriculas}`
        if (bboxesExcluidasDirecto.length > 0) {
            urlDirecto += `&bboxes_excluidas=${encodeURIComponent(JSON.stringify(bboxesExcluidasDirecto))}`
        }
        fetch(urlDirecto, {
            method: 'POST',
            body: formulario
        }).then(function(respuesta) {
            if (respuesta.ok) {
                respuesta.json().then(function(datos) {
                    const tardo = Date.now() - inicio
                    frameDirecto.src = 'data:image/jpeg;base64,' + datos.frame
                    fpsDirecto.textContent = `Latencia: ${tardo}ms`
                })
            }
        }).catch(function() {})

    }, 'image/jpeg', 0.6)

    if (streamActivo) {
        intervaloDirecto = setTimeout(procesarDirecto, 100)
    }
}
