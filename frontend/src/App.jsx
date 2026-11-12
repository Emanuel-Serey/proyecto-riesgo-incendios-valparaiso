import { useEffect, useRef, useState } from 'react'
import L from 'leaflet'

import {
  GeoJSON,
  MapContainer,
  Marker,
  Popup,
  TileLayer,
  ZoomControl,
  useMap,
} from 'react-leaflet'

import './App.css'

import AdminReportes from './AdminReportes'
import ReporteIncendio from './ReporteIncendio'
import OrientacionIncendios from './OrientacionIncendios'


const COMUNAS = [
  'Algarrobo',
  'Cabildo',
  'Calle Larga',
  'Cartagena',
  'Casablanca',
  'Catemu',
  'Concón',
  'El Quisco',
  'El Tabo',
  'Hijuelas',
  'La Calera',
  'La Cruz',
  'La Ligua',
  'Limache',
  'Llaillay',
  'Los Andes',
  'Nogales',
  'Olmué',
  'Panquehue',
  'Papudo',
  'Petorca',
  'Puchuncaví',
  'Putaendo',
  'Quillota',
  'Quilpué',
  'Quintero',
  'Rinconada',
  'San Antonio',
  'San Esteban',
  'San Felipe',
  'Santa María',
  'Santo Domingo',
  'Valparaíso',
  'Villa Alemana',
  'Viña del Mar',
  'Zapallar',
]


const iconoIncendio = L.divIcon({
  className: 'marcador-incendio',

  html: `
    <div class="marcador-incendio-icono">
      🔥
    </div>
  `,

  iconSize: [42, 42],
  iconAnchor: [21, 21],
  popupAnchor: [0, -20],
})


function ConfigurarMapa({
  regionGeojson
}) {
  const map = useMap()


  useEffect(() => {
    if (!regionGeojson) {
      return
    }


    const capa =
      L.geoJSON(
        regionGeojson
      )

    const bounds =
      capa.getBounds()


    if (!bounds.isValid()) {
      return
    }


    map.setView(
      [-32.9, -71.15],
      9,
      {
        animate: false,
      }
    )


    map.setMinZoom(9)


    const limites =
      bounds.pad(0.08)


    map.setMaxBounds(
      limites
    )

  }, [
    regionGeojson,
    map
  ])


  return null
}


function formatearFechaReportePublico(
  fecha
) {
  if (!fecha) {
    return '-'
  }


  const valor =
    new Date(fecha)


  if (
    Number.isNaN(
      valor.getTime()
    )
  ) {
    return '-'
  }


  return valor.toLocaleDateString(
    'es-CL',
    {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      timeZone: 'America/Santiago',
    }
  )
}


function formatearHoraReportePublico(
  fecha
) {
  if (!fecha) {
    return '-'
  }


  const valor =
    new Date(fecha)


  if (
    Number.isNaN(
      valor.getTime()
    )
  ) {
    return '-'
  }


  return valor.toLocaleTimeString(
    'es-CL',
    {
      hour: '2-digit',
      minute: '2-digit',
      hour12: false,
      timeZone: 'America/Santiago',
    }
  )
}


function antiguedadReportePublico(
  fecha
) {
  if (!fecha) {
    return ''
  }


  const valor =
    new Date(fecha)


  if (
    Number.isNaN(
      valor.getTime()
    )
  ) {
    return ''
  }


  const diferencia =
    Date.now() -
    valor.getTime()


  const minutos =
    Math.floor(
      diferencia / 60000
    )


  if (minutos < 1) {
    return 'Hace menos de 1 min'
  }


  if (minutos < 60) {
    return `Hace ${minutos} min`
  }


  const horas =
    Math.floor(
      minutos / 60
    )


  if (horas < 24) {
    return horas === 1
      ? 'Hace 1 hora'
      : `Hace ${horas} horas`
  }


  const dias =
    Math.floor(
      horas / 24
    )


  return dias === 1
    ? 'Hace 1 día'
    : `Hace ${dias} días`
}


function App() {
  const [
    estadoSistema,
    setEstadoSistema
  ] = useState(
    'verificando'
  )


  const [
    comuna,
    setComuna
  ] = useState(
    'Valparaíso'
  )


  const [
    resultado,
    setResultado
  ] = useState(null)


  const [
    comunasGeojson,
    setComunasGeojson
  ] = useState(null)


  const [
    regionGeojson,
    setRegionGeojson
  ] = useState(null)


  const [
    mascaraGeojson,
    setMascaraGeojson
  ] = useState(null)


  const [
    reportesConfirmados,
    setReportesConfirmados
  ] = useState([])


  const [
    cargando,
    setCargando
  ] = useState(false)


  const [
    error,
    setError
  ] = useState('')


  const geoJsonRef =
    useRef()


  // =========================================================
  // CARTOGRAFÍA
  // =========================================================

  useEffect(() => {

    const cargarCartografia =
      async () => {

        try {
          const [
            respuestaComunas,
            respuestaRegion,
            respuestaMascara,
          ] = await Promise.all([
            fetch(
              '/data/comunas_valparaiso.geojson'
            ),

            fetch(
              '/data/region_valparaiso.geojson'
            ),

            fetch(
              '/data/mascara_valparaiso.geojson'
            ),
          ])


          if (
            !respuestaComunas.ok ||
            !respuestaRegion.ok ||
            !respuestaMascara.ok
          ) {
            throw new Error(
              'No fue posible cargar la cartografía'
            )
          }


          const [
            comunas,
            region,
            mascara,
          ] = await Promise.all([
            respuestaComunas.json(),
            respuestaRegion.json(),
            respuestaMascara.json(),
          ])


          setComunasGeojson(
            comunas
          )


          setRegionGeojson(
            region
          )


          setMascaraGeojson(
            mascara
          )

        } catch (err) {

          setError(
            err.message
          )

        }

      }


    cargarCartografia()

  }, [])


  // =========================================================
  // ESTADO GENERAL
  // =========================================================

  useEffect(() => {
    let activo = true


    const verificarSistema =
      async () => {

        try {
          const respuesta =
            await fetch(
              '/api/health/system',
              {
                cache:
                  'no-store',
              }
            )


          const datos =
            await respuesta.json()


          if (!activo) {
            return
          }


          if (
            datos.status ===
            'ok'
          ) {

            setEstadoSistema(
              'operativo'
            )

          } else {

            setEstadoSistema(
              'degradado'
            )

          }

        } catch {

          if (activo) {

            setEstadoSistema(
              'desconectado'
            )

          }

        }

      }


    verificarSistema()


    const intervalo =
      setInterval(
        verificarSistema,
        30000
      )


    return () => {

      activo = false


      clearInterval(
        intervalo
      )

    }

  }, [])


  // =========================================================
  // REPORTES CONFIRMADOS
  // =========================================================

  useEffect(() => {
    let activo = true


    const cargarReportes =
      async () => {

        try {
          const respuesta =
            await fetch(
              '/api/reportes/confirmados',
              {
                cache:
                  'no-store',
              }
            )


          if (!respuesta.ok) {

            throw new Error(
              'No fue posible cargar los reportes'
            )

          }


          const datos =
            await respuesta.json()


          if (activo) {

            setReportesConfirmados(
              datos
            )

          }

        } catch {

          if (activo) {

            setReportesConfirmados(
              []
            )

          }

        }

      }


    cargarReportes()


    const intervalo =
      setInterval(
        cargarReportes,
        30000
      )


    window.addEventListener(
      'reportes-actualizados',
      cargarReportes
    )


    return () => {

      activo = false


      clearInterval(
        intervalo
      )


      window.removeEventListener(
        'reportes-actualizados',
        cargarReportes
      )

    }

  }, [])


  // =========================================================
  // CONSULTA DE RIESGO
  // =========================================================

  const consultarRiesgo =
    async (
      comunaSeleccionada =
        comuna
    ) => {

      setCargando(true)

      setError('')


      try {

        const respuesta =
          await fetch(
            `/api/riesgo/${
              encodeURIComponent(
                comunaSeleccionada
              )
            }`
          )


        if (!respuesta.ok) {

          let mensaje =
            'No fue posible consultar el riesgo'


          try {

            const detalle =
              await respuesta.json()


            if (
              detalle.detail
            ) {

              mensaje =
                detalle.detail

            }

          } catch {

            // Mensaje genérico.

          }


          throw new Error(
            mensaje
          )

        }


        const datos =
          await respuesta.json()


        setComuna(
          comunaSeleccionada
        )


        setResultado(
          datos
        )

      } catch (err) {

        setResultado(null)


        setError(
          err.message
        )

      } finally {

        setCargando(false)

      }

    }


  // =========================================================
  // COLORES
  // =========================================================

  const obtenerColor = (
    nombreComuna
  ) => {

    if (
      !resultado ||
      resultado.comuna !==
        nombreComuna
    ) {

      return '#e2e8f0'

    }


    switch (
      resultado.nivel_riesgo
    ) {

      case 'Bajo':
        return '#16a34a'


      case 'Medio':
        return '#f59e0b'


      case 'Alto':
        return '#dc2626'


      default:
        return '#e2e8f0'

    }

  }


  const estiloComuna = (
    feature
  ) => ({
    color: '#475569',

    weight: 1.25,

    fillColor:
      obtenerColor(
        feature.properties.comuna
      ),

    fillOpacity: 0.7,
  })


  const estiloMascara = {
    color:
      'transparent',

    weight: 0,

    fillColor:
      '#334155',

    fillOpacity:
      0.26,
  }


  const onEachFeature = (
    feature,
    layer
  ) => {

    const nombreComuna =
      feature.properties.comuna


    layer.bindTooltip(
      nombreComuna,
      {
        sticky: true,
        direction: 'top',
      }
    )


    layer.on({

      click: () => {

        setComuna(
          nombreComuna
        )


        consultarRiesgo(
          nombreComuna
        )

      },


      mouseover: (
        evento
      ) => {

        evento.target.setStyle({
          weight: 2.5,

          color:
            '#111827',

          fillOpacity:
            0.85,
        })

      },


      mouseout: (
        evento
      ) => {

        if (
          geoJsonRef.current
        ) {

          geoJsonRef.current.resetStyle(
            evento.target
          )

        }

      },

    })

  }


  // =========================================================
  // UTILIDADES
  // =========================================================

  const claseRiesgo =
    resultado
      ? `riesgo riesgo-${resultado.nivel_riesgo.toLowerCase()}`
      : 'riesgo riesgo-sin-datos'


  const formatearNumero = (
    valor,
    decimales = 1
  ) => {

    if (
      valor === null ||
      valor === undefined
    ) {

      return '-'

    }


    return Number(
      valor
    ).toFixed(
      decimales
    )

  }


  const convertirNudosAKmh = (
    nudos
  ) => {

    if (
      nudos === null ||
      nudos === undefined
    ) {

      return null

    }


    return (
      Number(nudos) *
      1.852
    )

  }


  const obtenerTextoDireccion = (
    direccion
  ) => {

    if (
      direccion ===
      'aumenta'
    ) {

      return (
        'Contribuye a una evaluación de mayor riesgo'
      )

    }


    if (
      direccion ===
      'reduce'
    ) {

      return (
        'Contribuye a una evaluación de menor riesgo'
      )

    }


    return (
      'Tiene una influencia neutra en esta evaluación'
    )

  }


  const obtenerSimboloDireccion = (
    direccion
  ) => {

    if (
      direccion ===
      'aumenta'
    ) {

      return '↑'

    }


    if (
      direccion ===
      'reduce'
    ) {

      return '↓'

    }


    return '•'

  }


  // =========================================================
  // UI
  // =========================================================

  return (

    <div className="app">


      <header className="header">

        <div>

          <p className="eyebrow">
            Sistema inteligente de prevención
          </p>


          <h1>
            Riesgo de Incendios Forestales
          </h1>


          <p>
            Región de Valparaíso
          </p>

        </div>


        <div
          className={
            `estado-sistema estado-${estadoSistema}`
          }
        >

          <span className="estado-dot" />


          {
            estadoSistema ===
            'operativo' &&
            'Sistema operativo'
          }


          {
            estadoSistema ===
            'degradado' &&
            'Servicio parcialmente disponible'
          }


          {
            estadoSistema ===
            'desconectado' &&
            'Servicio no disponible'
          }


          {
            estadoSistema ===
            'verificando' &&
            'Verificando sistema...'
          }

        </div>

      </header>


      <main className="contenido">


        <section className="mapa-contenedor">


          <MapContainer
            key="mapa-valparaiso-v8"

            center={[
              -32.9,
              -71.15
            ]}

            zoom={9}

            minZoom={9}

            maxZoom={14}

            zoomControl={false}

            maxBoundsViscosity={1.0}

            worldCopyJump={false}

            className="mapa"
          >


            <TileLayer
              attribution={
                '&copy; OpenStreetMap contributors'
              }

              url={
                'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png'
              }

              noWrap={true}
            />


            {mascaraGeojson && (

              <GeoJSON
                data={
                  mascaraGeojson
                }

                style={
                  estiloMascara
                }

                interactive={
                  false
                }
              />

            )}


            {comunasGeojson && (

              <GeoJSON
                key={
                  resultado
                    ? `${
                        resultado.comuna
                      }-${
                        resultado.nivel_riesgo
                      }`
                    : 'sin-riesgo'
                }

                ref={
                  geoJsonRef
                }

                data={
                  comunasGeojson
                }

                style={
                  estiloComuna
                }

                onEachFeature={
                  onEachFeature
                }
              />

            )}


            {reportesConfirmados.map(
              (
                reporte
              ) => (

                <Marker
                  key={
                    reporte.id_reporte
                  }

                  position={[
                    Number(
                      reporte.latitud
                    ),

                    Number(
                      reporte.longitud
                    ),
                  ]}

                  icon={
                    iconoIncendio
                  }
                >

                  <Popup
                    minWidth={280}
                    maxWidth={320}
                  >

                    <div className="reporte-popup-publico">


                      <div className="reporte-popup-titulo">

                        🔥 Reporte ciudadano validado

                      </div>


                      {reporte.imagen_url && (

                        <img
                          className="reporte-popup-imagen"

                          src={
                            `/api${reporte.imagen_url}`
                          }

                          alt="Evidencia del reporte ciudadano"
                        />

                      )}


                      <div className="reporte-popup-descripcion">

                        <span>
                          Descripción enviada por el ciudadano
                        </span>


                        <p>

                          {
                            reporte.descripcion ||
                            'El ciudadano no agregó una descripción.'
                          }

                        </p>

                      </div>


                      <div className="reporte-popup-datos">


                        <div>

                          <span>
                            Fecha
                          </span>

                          <strong>

                            {
                              formatearFechaReportePublico(
                                reporte.fecha_reporte
                              )
                            }

                          </strong>

                        </div>


                        <div>

                          <span>
                            Hora
                          </span>

                          <strong>

                            {
                              formatearHoraReportePublico(
                                reporte.fecha_reporte
                              )
                            }

                          </strong>


                          <small>

                            {
                              antiguedadReportePublico(
                                reporte.fecha_reporte
                              )
                            }

                          </small>

                        </div>


                      </div>


                      <div className="reporte-popup-revisado">

                        <span>
                          ✓
                        </span>

                        Reporte revisado

                      </div>


                      <div className="reporte-popup-aviso">

                        Este reporte fue enviado por un
                        ciudadano y revisado dentro de la
                        plataforma. No corresponde a una
                        confirmación oficial de emergencia.

                      </div>


                      <OrientacionIncendios
                        contexto="reporte"
                        compacto
                      />


                    </div>

                  </Popup>

                </Marker>

              )
            )}


            {regionGeojson && (

              <ConfigurarMapa
                regionGeojson={
                  regionGeojson
                }
              />

            )}


            <ZoomControl
              position="bottomleft"
            />


          </MapContainer>


          <ReporteIncendio />


          <AdminReportes />


          <div className="mapa-etiqueta">

            Área continental analizada

            <span>
              Región de Valparaíso
            </span>

          </div>


          <div className="leyenda-mapa">


            <div className="leyenda-titulo">
              Nivel de riesgo
            </div>


            <div className="leyenda-item">

              <span className="leyenda-color leyenda-bajo" />

              Bajo

            </div>


            <div className="leyenda-item">

              <span className="leyenda-color leyenda-medio" />

              Medio

            </div>


            <div className="leyenda-item">

              <span className="leyenda-color leyenda-alto" />

              Alto

            </div>


            <div className="leyenda-item">

              <span className="leyenda-color leyenda-sin-evaluar" />

              Sin evaluar

            </div>


            <div className="leyenda-separador" />


            <div className="leyenda-item">

              <span className="leyenda-incendio">
                🔥
              </span>

              Reporte validado

            </div>

          </div>

        </section>


        <aside className="panel">


          <div>

            <p className="panel-etiqueta">
              Consulta territorial
            </p>


            <h2>
              Evaluar riesgo
            </h2>

          </div>


          <label htmlFor="comuna">
            Comuna
          </label>


          <select
            id="comuna"

            value={comuna}

            onChange={(
              evento
            ) => {

              setComuna(
                evento.target.value
              )


              setResultado(
                null
              )


              setError(
                ''
              )

            }}
          >

            {COMUNAS.map(
              (
                nombre
              ) => (

                <option
                  key={
                    nombre
                  }

                  value={
                    nombre
                  }
                >

                  {nombre}

                </option>

              )
            )}

          </select>


          <button
            onClick={() =>
              consultarRiesgo()
            }

            disabled={
              cargando
            }
          >

            {
              cargando
                ? 'Analizando...'
                : 'Consultar riesgo'
            }

          </button>


          {error && (

            <div className="mensaje-error">
              {error}
            </div>

          )}


          {
            !resultado &&
            !error && (

              <div className="estado-inicial">

                Selecciona una comuna en el mapa
                o en la lista para consultar su
                nivel de riesgo.

              </div>

            )
          }


          {resultado && (

            <div className="resultado">


              <div className={claseRiesgo}>

                <span>
                  Nivel de riesgo
                </span>


                <strong>
                  {
                    resultado.nivel_riesgo
                  }
                </strong>


                <div className="indice-riesgo">

                  <span>

                    Índice de riesgo:{' '}

                    {
                      formatearNumero(
                        resultado.score_modelo,
                        3
                      )
                    }

                  </span>


                  <span
                    className="info-indice"

                    title={
                      'El índice resume la evaluación del sistema. ' +
                      'No representa una probabilidad exacta de que ocurra un incendio.'
                    }
                  >
                    i
                  </span>

                </div>

              </div>


              <OrientacionIncendios
                contexto="riesgo"

                nivelRiesgo={
                  resultado.nivel_riesgo
                }
              />


              <div className="datos-grid">


                <article>

                  <span>
                    Temperatura media
                  </span>


                  <strong>

                    {
                      formatearNumero(
                        resultado.temperatura_media,
                        1
                      )
                    }

                    {' °C'}

                  </strong>


                  <small>
                    Día anterior
                  </small>

                </article>


                <article>

                  <span>
                    Humedad media
                  </span>


                  <strong>

                    {
                      formatearNumero(
                        resultado.humedad_media,
                        1
                      )
                    }

                    {' %'}

                  </strong>


                  <small>
                    Día anterior
                  </small>

                </article>


                <article>

                  <span>
                    Viento medio
                  </span>


                  <strong>

                    {
                      formatearNumero(
                        convertirNudosAKmh(
                          resultado.viento_medio
                        ),
                        1
                      )
                    }

                    {' km/h'}

                  </strong>


                  <small>
                    Día anterior
                  </small>

                </article>


                <article>

                  <span>
                    Cobertura vegetal
                  </span>


                  <strong>
                    {
                      resultado.vegetacion_cobertura
                    }
                  </strong>


                  <small>
                    Predominante
                  </small>

                </article>


              </div>


              <div className="dato-historico">

                <span>
                  Promedio histórico anual
                </span>


                <strong>

                  {
                    formatearNumero(
                      resultado.incendios_historicos,
                      1
                    )
                  }

                  {' incendios/año'}

                </strong>

              </div>


              {
                resultado.factores_principales &&
                resultado.factores_principales.length > 0 && (

                  <div className="factores">


                    <div className="factores-titulo">

                      Factores que influyen en esta evaluación

                    </div>


                    <div className="factores-lista">

                      {
                        resultado.factores_principales.map(
                          (
                            factor
                          ) => (

                            <div
                              className={
                                `factor factor-${factor.direccion}`
                              }

                              key={
                                factor.variable
                              }
                            >

                              <div className="factor-icono">

                                {
                                  obtenerSimboloDireccion(
                                    factor.direccion
                                  )
                                }

                              </div>


                              <div className="factor-contenido">

                                <strong>
                                  {
                                    factor.nombre
                                  }
                                </strong>


                                <span>

                                  {
                                    obtenerTextoDireccion(
                                      factor.direccion
                                    )
                                  }

                                </span>

                              </div>

                            </div>

                          )
                        )
                      }

                    </div>


                    <div className="factores-nota">

                      Se muestran los factores
                      con mayor influencia en la
                      evaluación actual.

                    </div>

                  </div>

                )
              }


              <div className="fechas">

                <span>

                  Fecha evaluada:{' '}

                  <b>
                    {
                      resultado.fecha_prediccion
                    }
                  </b>

                </span>


                <span>

                  Meteorología utilizada:{' '}

                  <b>
                    {
                      resultado.fecha_meteorologia
                    }
                  </b>

                </span>

              </div>


              <div className="nota-metodologica">

                Las variables meteorológicas
                corresponden al promedio del día
                calendario anterior.

              </div>


            </div>

          )}


        </aside>

      </main>

    </div>

  )

}


export default App