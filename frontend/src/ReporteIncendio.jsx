import {
  useEffect,
  useRef,
  useState,
} from 'react'

import L from 'leaflet'

import {
  CircleMarker,
  GeoJSON,
  MapContainer,
  TileLayer,
} from 'react-leaflet'

import {
  clasificarPrecisionGps,
  formatearPrecisionGps,
} from './gpsUtils'

import OrientacionIncendios from './OrientacionIncendios'

import './GpsPrecision.css'
import './Duplicados.css'
import './UbicacionReporte.css'


const MAX_IMAGEN_MB = 10

const TIPOS_PERMITIDOS = [
  'image/jpeg',
  'image/png',
  'image/webp',
]


// =========================================================
// MAPA DE SELECCIÓN MANUAL
// =========================================================

function MapaUbicacionManual({
  geojson,
  ubicacion,
  onSeleccionar,
}) {

  const capaRegion =
    L.geoJSON(
      geojson
    )


  const limitesRegion =
    capaRegion.getBounds()


  const limitesNavegacion =
    limitesRegion.pad(
      0.12
    )


  const configurarRegion = (
    feature,
    layer
  ) => {

    layer.on(
      'click',
      (
        evento
      ) => {

        onSeleccionar(
          evento.latlng
        )

      }
    )

  }


  return (

    <div className="mapa-ubicacion-manual">

      <MapContainer
        bounds={
          limitesRegion
        }

        boundsOptions={{
          padding: [
            15,
            15,
          ],
        }}

        maxBounds={
          limitesNavegacion
        }

        maxBoundsViscosity={
          1.0
        }

        minZoom={
          7
        }

        maxZoom={
          17
        }

        scrollWheelZoom={
          true
        }

        zoomControl={
          true
        }
      >

        <TileLayer
          attribution={
            '&copy; OpenStreetMap contributors'
          }

          url={
            'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png'
          }
        />


        <GeoJSON
          data={
            geojson
          }

          onEachFeature={
            configurarRegion
          }

          style={{
            color:
              '#2563eb',

            weight:
              2,

            fillColor:
              '#60a5fa',

            fillOpacity:
              0.16,
          }}
        />


        {ubicacion && (

          <CircleMarker
            center={[
              ubicacion.latitud,
              ubicacion.longitud,
            ]}

            radius={
              8
            }

            pathOptions={{
              color:
                '#991b1b',

              weight:
                2,

              fillColor:
                '#ef4444',

              fillOpacity:
                1,
            }}
          />

        )}


      </MapContainer>

    </div>

  )

}


// =========================================================
// COMPONENTE PRINCIPAL
// =========================================================

function ReporteIncendio() {
  const [
    abierto,
    setAbierto
  ] = useState(false)


  const [
    modoUbicacion,
    setModoUbicacion
  ] = useState('gps')


  const [
    buscandoUbicacion,
    setBuscandoUbicacion
  ] = useState(false)


  const [
    ubicacion,
    setUbicacion
  ] = useState(null)


  const [
    errorUbicacion,
    setErrorUbicacion
  ] = useState('')


  const [
    regionGeoJson,
    setRegionGeoJson
  ] = useState(null)


  const [
    cargandoRegion,
    setCargandoRegion
  ] = useState(false)


  const [
    imagen,
    setImagen
  ] = useState(null)


  const [
    vistaPrevia,
    setVistaPrevia
  ] = useState(null)


  const [
    descripcion,
    setDescripcion
  ] = useState('')


  const [
    enviando,
    setEnviando
  ] = useState(false)


  const [
    error,
    setError
  ] = useState('')


  const [
    resultado,
    setResultado
  ] = useState(null)


  const inputImagenRef =
    useRef(null)


  // =========================================================
  // CARGAR REGIÓN
  // =========================================================

  useEffect(() => {

    if (
      modoUbicacion !==
      'manual'
    ) {

      return

    }


    if (
      regionGeoJson
    ) {

      return

    }


    let activo =
      true


    const cargarRegion =
      async () => {

        setCargandoRegion(
          true
        )


        try {

          const respuesta =
            await fetch(
              '/data/region_valparaiso.geojson'
            )


          if (
            !respuesta.ok
          ) {

            throw new Error()

          }


          const datos =
            await respuesta.json()


          if (
            activo
          ) {

            setRegionGeoJson(
              datos
            )

          }

        } catch {

          if (
            activo
          ) {

            setErrorUbicacion(
              'No fue posible cargar el mapa de la Región de Valparaíso.'
            )

          }

        } finally {

          if (
            activo
          ) {

            setCargandoRegion(
              false
            )

          }

        }

      }


    cargarRegion()


    return () => {

      activo =
        false

    }

  }, [
    modoUbicacion,
    regionGeoJson,
  ])


  // =========================================================
  // PREVIEW
  // =========================================================

  useEffect(() => {

    return () => {

      if (
        vistaPrevia
      ) {

        URL.revokeObjectURL(
          vistaPrevia
        )

      }

    }

  }, [
    vistaPrevia
  ])


  // =========================================================
  // GPS
  // =========================================================

  const obtenerUbicacion = () => {

    setModoUbicacion(
      'gps'
    )


    setUbicacion(
      null
    )


    setErrorUbicacion(
      ''
    )


    if (
      !navigator.geolocation
    ) {

      setErrorUbicacion(
        'Tu navegador no permite obtener la ubicación.'
      )

      return

    }


    setBuscandoUbicacion(
      true
    )


    navigator.geolocation.getCurrentPosition(

      (
        posicion
      ) => {

        setUbicacion({

          latitud:
            posicion.coords.latitude,

          longitud:
            posicion.coords.longitude,

          precision:
            posicion.coords.accuracy,

          origen:
            'gps',

        })


        setBuscandoUbicacion(
          false
        )

      },


      (
        errorGeolocalizacion
      ) => {

        setBuscandoUbicacion(
          false
        )


        let mensaje =
          'No fue posible obtener tu ubicación.'


        if (
          errorGeolocalizacion.code ===
          errorGeolocalizacion.PERMISSION_DENIED
        ) {

          mensaje =
            'Debes permitir el acceso a tu ubicación o seleccionar el lugar manualmente en el mapa.'

        }


        if (
          errorGeolocalizacion.code ===
          errorGeolocalizacion.POSITION_UNAVAILABLE
        ) {

          mensaje =
            'La ubicación no está disponible en este momento.'

        }


        if (
          errorGeolocalizacion.code ===
          errorGeolocalizacion.TIMEOUT
        ) {

          mensaje =
            'La solicitud de ubicación tardó demasiado. Intenta nuevamente.'

        }


        setErrorUbicacion(
          mensaje
        )

      },


      {
        enableHighAccuracy:
          true,

        timeout:
          15000,

        maximumAge:
          0,
      }

    )

  }


  // =========================================================
  // UBICACIÓN MANUAL
  // =========================================================

  const activarUbicacionManual = () => {

    setModoUbicacion(
      'manual'
    )


    setUbicacion(
      null
    )


    setBuscandoUbicacion(
      false
    )


    setErrorUbicacion(
      ''
    )

  }


  const seleccionarPuntoManual = (
    latlng
  ) => {

    setUbicacion({

      latitud:
        latlng.lat,

      longitud:
        latlng.lng,

      precision:
        null,

      origen:
        'manual',

    })


    setErrorUbicacion(
      ''
    )

  }


  // =========================================================
  // ABRIR / CERRAR
  // =========================================================

  const abrirFormulario = () => {

    setAbierto(
      true
    )


    setResultado(
      null
    )


    setError(
      ''
    )


    obtenerUbicacion()

  }


  const limpiarFormulario = () => {

    if (
      vistaPrevia
    ) {

      URL.revokeObjectURL(
        vistaPrevia
      )

    }


    setModoUbicacion(
      'gps'
    )


    setImagen(
      null
    )


    setVistaPrevia(
      null
    )


    setDescripcion(
      ''
    )


    setResultado(
      null
    )


    setError(
      ''
    )


    setUbicacion(
      null
    )


    setErrorUbicacion(
      ''
    )


    if (
      inputImagenRef.current
    ) {

      inputImagenRef.current.value =
        ''

    }

  }


  const cerrarFormulario = () => {

    if (
      enviando
    ) {

      return

    }


    limpiarFormulario()


    setAbierto(
      false
    )

  }


  const crearOtroReporte = () => {

    limpiarFormulario()


    obtenerUbicacion()

  }


  // =========================================================
  // IMAGEN
  // =========================================================

  const seleccionarImagen = (
    evento
  ) => {

    setError(
      ''
    )


    const archivo =
      evento.target.files?.[0]


    if (
      !archivo
    ) {

      return

    }


    if (
      !TIPOS_PERMITIDOS.includes(
        archivo.type
      )
    ) {

      setError(
        'La fotografía debe ser JPG, PNG o WebP.'
      )


      evento.target.value =
        ''


      return

    }


    if (
      archivo.size
      >
      MAX_IMAGEN_MB
      *
      1024
      *
      1024
    ) {

      setError(
        `La fotografía no puede superar ${MAX_IMAGEN_MB} MB.`
      )


      evento.target.value =
        ''


      return

    }


    if (
      vistaPrevia
    ) {

      URL.revokeObjectURL(
        vistaPrevia
      )

    }


    setImagen(
      archivo
    )


    setVistaPrevia(
      URL.createObjectURL(
        archivo
      )
    )

  }


  // =========================================================
  // ENVIAR
  // =========================================================

  const enviarReporte =
    async (
      evento
    ) => {

      evento.preventDefault()


      setError(
        ''
      )


      if (
        !ubicacion
      ) {

        setError(
          'Debes indicar la ubicación del posible incendio.'
        )


        return

      }


      if (
        !imagen
      ) {

        setError(
          'Debes adjuntar una fotografía.'
        )


        return

      }


      setEnviando(
        true
      )


      try {

        const formulario =
          new FormData()


        formulario.append(
          'latitud',
          String(
            ubicacion.latitud
          )
        )


        formulario.append(
          'longitud',
          String(
            ubicacion.longitud
          )
        )


        if (
          ubicacion.origen ===
          'gps'
          &&
          ubicacion.precision !==
          null
        ) {

          formulario.append(
            'precision_gps_m',
            String(
              ubicacion.precision
            )
          )

        }


        formulario.append(
          'imagen',
          imagen
        )


        if (
          descripcion.trim()
        ) {

          formulario.append(
            'descripcion',
            descripcion.trim()
          )

        }


        const respuesta =
          await fetch(
            '/api/reportes',
            {
              method:
                'POST',

              body:
                formulario,
            }
          )


        let datos = null


        try {

          datos =
            await respuesta.json()

        } catch {

          datos = null

        }


        if (
          !respuesta.ok
        ) {

          throw new Error(
            datos?.detail ||
            'No fue posible enviar el reporte.'
          )

        }


        setResultado(
          datos
        )

      } catch (err) {

        setError(
          err.message ||
          'No fue posible enviar el reporte.'
        )

      } finally {

        setEnviando(
          false
        )

      }

    }


  const calidadGps = (

    ubicacion &&
    ubicacion.origen ===
    'gps'

      ? clasificarPrecisionGps(
          ubicacion.precision
        )

      : null

  )


  // =========================================================
  // UI
  // =========================================================

  return (
    <>

      <button
        className="boton-reportar-incendio"

        type="button"

        onClick={
          abrirFormulario
        }
      >

        <span>
          🔥
        </span>

        Reportar posible incendio

      </button>


      {abierto && (

        <div
          className="reporte-modal-fondo"

          onMouseDown={(
            evento
          ) => {

            if (
              evento.target ===
              evento.currentTarget
            ) {

              cerrarFormulario()

            }

          }}
        >

          <div className="reporte-modal">


            <div className="reporte-modal-header">

              <div>

                <p>
                  Red de detección comunitaria
                </p>

                <h2>
                  Reportar posible incendio
                </h2>

              </div>


              <button
                type="button"

                className="reporte-cerrar"

                onClick={
                  cerrarFormulario
                }

                aria-label="Cerrar"
              >
                ×
              </button>

            </div>


            {!resultado && (

              <form
                className="reporte-formulario"

                onSubmit={
                  enviarReporte
                }
              >


                <div className="reporte-aviso">

                  <strong>
                    Importante
                  </strong>


                  <span>

                    Esta herramienta permite
                    reportar indicios de fuego
                    o humo. No reemplaza los
                    canales oficiales de
                    emergencia.

                  </span>

                </div>


                <OrientacionIncendios
                  contexto="reporte"

                  compacto
                />


                {/* =================================================
                    UBICACIÓN
                    ================================================= */}

                <div className="reporte-campo">


                  <label>
                    Ubicación del posible incendio
                  </label>


                  <div className="ubicacion-opciones">


                    <button
                      type="button"

                      className={
                        `ubicacion-opcion ${
                          modoUbicacion ===
                          'gps'
                            ? 'ubicacion-opcion-activa'
                            : ''
                        }`
                      }

                      onClick={
                        obtenerUbicacion
                      }
                    >

                      📍 Usar mi ubicación

                    </button>


                    <button
                      type="button"

                      className={
                        `ubicacion-opcion ${
                          modoUbicacion ===
                          'manual'
                            ? 'ubicacion-opcion-activa'
                            : ''
                        }`
                      }

                      onClick={
                        activarUbicacionManual
                      }
                    >

                      🗺 Seleccionar en el mapa

                    </button>


                  </div>


                  {
                    modoUbicacion ===
                    'gps' && (

                      <>

                        {buscandoUbicacion && (

                          <div className="ubicacion-pendiente">

                            Obteniendo tu ubicación...

                          </div>

                        )}


                        {
                          !buscandoUbicacion &&
                          ubicacion &&
                          calidadGps && (

                            <>

                              <div
                                className={
                                  `ubicacion-correcta ubicacion-${calidadGps.nivel}`
                                }
                              >

                                <div className="ubicacion-icono">

                                  {
                                    calidadGps.icono
                                  }

                                </div>


                                <div>

                                  <strong>
                                    Ubicación obtenida
                                  </strong>


                                  <span>

                                    Precisión aproximada:{' '}

                                    {
                                      formatearPrecisionGps(
                                        ubicacion.precision
                                      )
                                    }

                                  </span>


                                  <div
                                    className={
                                      `gps-calidad gps-calidad-${calidadGps.nivel}`
                                    }
                                  >

                                    {
                                      calidadGps.etiqueta
                                    }

                                  </div>

                                </div>

                              </div>


                              {
                                (
                                  calidadGps.nivel ===
                                  'moderada'
                                  ||
                                  calidadGps.nivel ===
                                  'baja'
                                ) && (

                                  <div
                                    className={
                                      `gps-advertencia gps-advertencia-${calidadGps.nivel}`
                                    }
                                  >

                                    {
                                      calidadGps.descripcion
                                    }

                                  </div>

                                )
                              }

                            </>

                          )
                        }


                        {
                          !buscandoUbicacion &&
                          !ubicacion &&
                          errorUbicacion && (

                            <div className="reporte-error">

                              {
                                errorUbicacion
                              }

                            </div>

                          )
                        }

                      </>

                    )
                  }


                  {
                    modoUbicacion ===
                    'manual' && (

                      <>

                        <div className="ubicacion-manual-info">

                          Selecciona el sector donde
                          observas fuego o humo.


                          <span className="ubicacion-manual-ayuda">

                            El mapa está limitado a la
                            Región de Valparaíso. No necesitas
                            indicar una dirección exacta:
                            marca el sector aproximado.

                          </span>

                        </div>


                        {cargandoRegion && (

                          <div className="ubicacion-pendiente">

                            Cargando mapa...

                          </div>

                        )}


                        {
                          !cargandoRegion &&
                          regionGeoJson && (

                            <MapaUbicacionManual
                              geojson={
                                regionGeoJson
                              }

                              ubicacion={
                                ubicacion
                              }

                              onSeleccionar={
                                seleccionarPuntoManual
                              }
                            />

                          )
                        }


                        {
                          errorUbicacion && (

                            <div className="reporte-error">

                              {
                                errorUbicacion
                              }

                            </div>

                          )
                        }


                        {
                          ubicacion &&
                          ubicacion.origen ===
                          'manual' && (

                            <div className="ubicacion-manual-seleccionada">

                              <strong>
                                ✓ Ubicación aproximada seleccionada
                              </strong>


                              <span className="ubicacion-manual-coordenadas">

                                {
                                  Number(
                                    ubicacion.latitud
                                  ).toFixed(5)
                                }

                                {', '}

                                {
                                  Number(
                                    ubicacion.longitud
                                  ).toFixed(5)
                                }

                              </span>


                              <p>

                                Esta ubicación fue indicada
                                manualmente y será presentada
                                al administrador como aproximada.

                              </p>

                            </div>

                          )
                        }

                      </>

                    )
                  }


                </div>


                {/* =================================================
                    FOTOGRAFÍA
                    ================================================= */}

                <div className="reporte-campo">


                  <label>
                    Fotografía
                  </label>


                  <input
                    ref={
                      inputImagenRef
                    }

                    className="input-imagen-oculto"

                    id="imagen-reporte"

                    type="file"

                    accept={
                      'image/jpeg,image/png,image/webp'
                    }

                    capture="environment"

                    onChange={
                      seleccionarImagen
                    }
                  />


                  <label
                    htmlFor="imagen-reporte"

                    className="selector-imagen"
                  >

                    {vistaPrevia ? (

                      <img
                        src={
                          vistaPrevia
                        }

                        alt="Fotografía seleccionada"
                      />

                    ) : (

                      <div className="selector-imagen-vacio">

                        <span>
                          📷
                        </span>


                        <strong>
                          Tomar o seleccionar fotografía
                        </strong>


                        <small>
                          JPG, PNG o WebP · máximo 10 MB
                        </small>

                      </div>

                    )}

                  </label>


                </div>


                {/* =================================================
                    DESCRIPCIÓN
                    ================================================= */}

                <div className="reporte-campo">


                  <label
                    htmlFor="descripcion-reporte"
                  >

                    Descripción

                    <span>
                      opcional
                    </span>

                  </label>


                  <textarea
                    id="descripcion-reporte"

                    maxLength={
                      500
                    }

                    value={
                      descripcion
                    }

                    onChange={(
                      evento
                    ) =>
                      setDescripcion(
                        evento.target.value
                      )
                    }

                    placeholder={
                      'Ej.: Se observa una columna de humo cerca de una zona de vegetación.'
                    }
                  />


                  <span className="contador-caracteres">

                    {
                      descripcion.length
                    }

                    /500

                  </span>


                </div>


                {error && (

                  <div className="reporte-error">

                    {error}

                  </div>

                )}


                {enviando && (

                  <div className="reporte-analizando">

                    <div className="spinner-reporte" />


                    <div>

                      <strong>
                        Analizando fotografía...
                      </strong>


                      <span>

                        La IA está buscando indicios
                        de fuego o humo.

                      </span>

                    </div>

                  </div>

                )}


                <button
                  type="submit"

                  className="boton-enviar-reporte"

                  disabled={
                    enviando
                    ||
                    !ubicacion
                    ||
                    !imagen
                  }
                >

                  {
                    enviando
                      ? 'Analizando...'
                      : 'Enviar reporte'
                  }

                </button>


              </form>

            )}


            {/* =================================================
                RESULTADO
                ================================================= */}

            {resultado && (

              <div className="resultado-reporte">


                <div
                  className={
                    `resultado-reporte-icono ${
                      resultado.yolo_detectado
                        ? 'resultado-aceptado'
                        : 'resultado-rechazado'
                    }`
                  }
                >

                  {
                    resultado.yolo_detectado
                      ? '✓'
                      : '×'
                  }

                </div>


                <h3>

                  {
                    resultado.yolo_detectado
                      ? 'Reporte recibido'
                      : 'No se detectaron indicios'
                  }

                </h3>


                <p>

                  {
                    resultado.yolo_detectado
                      ? (
                          'La imagen contiene indicios compatibles con fuego o humo. ' +
                          'El reporte quedó pendiente de validación.'
                        )
                      : (
                          'La IA no detectó fuego ni humo en la fotografía. ' +
                          'El reporte no fue enviado a validación.'
                        )
                  }

                </p>


                {
                  resultado.posible_duplicado && (

                    <div className="reporte-duplicado-aviso">

                      <strong>
                        ⚠ Posible fotografía duplicada
                      </strong>


                      La fotografía es muy similar
                      a otra imagen registrada
                      anteriormente. El reporte se
                      enviará igualmente para
                      revisión del administrador.

                    </div>

                  )
                }


                <div className="resultado-reporte-info">


                  <div>

                    <span>
                      Estado
                    </span>


                    <strong>

                      {
                        resultado.yolo_detectado
                          ? 'Pendiente de validación'
                          : 'Rechazado'
                      }

                    </strong>

                  </div>


                  <div>

                    <span>
                      Detección IA
                    </span>


                    <strong>

                      {
                        resultado.yolo_clase ||
                        'Sin detección'
                      }

                    </strong>

                  </div>


                  {
                    resultado.yolo_confianza !== null &&
                    resultado.yolo_confianza !== undefined && (

                      <div>

                        <span>
                          Confianza
                        </span>


                        <strong>

                          {
                            (
                              Number(
                                resultado.yolo_confianza
                              )
                              *
                              100
                            ).toFixed(1)
                          }

                          %

                        </strong>

                      </div>

                    )
                  }


                  <div>

                    <span>
                      Ubicación
                    </span>


                    <strong>

                      {
                        resultado.origen_ubicacion ===
                        'manual'

                          ? 'Seleccionada manualmente · aproximada'

                          : `${
                              formatearPrecisionGps(
                                resultado.precision_gps_m
                              )
                            } · GPS`
                      }

                    </strong>

                  </div>


                </div>


                <OrientacionIncendios
                  contexto="reporte"
                />


                <button
                  type="button"

                  className="boton-nuevo-reporte"

                  onClick={
                    crearOtroReporte
                  }
                >

                  Crear otro reporte

                </button>


                <button
                  type="button"

                  className="boton-cerrar-resultado"

                  onClick={
                    cerrarFormulario
                  }
                >

                  Cerrar

                </button>


              </div>

            )}


          </div>

        </div>

      )}

    </>
  )

}


export default ReporteIncendio