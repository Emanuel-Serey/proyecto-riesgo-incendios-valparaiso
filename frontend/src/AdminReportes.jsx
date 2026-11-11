import {
  useEffect,
  useState,
} from 'react'

import {
  Link,
  useLocation,
} from 'react-router-dom'

import {
  clasificarPrecisionGps,
  formatearPrecisionGps,
} from './gpsUtils'

import './AdminReportes.css'
import './GpsPrecision.css'
import './Duplicados.css'
import './ReportesCercanos.css'
import './UbicacionReporte.css'


const TOKEN_KEY =
  'admin_access_token'

function formatearFechaReporte(
  fecha
) {

  if (!fecha) {
    return '-'
  }


  const valor =
    new Date(
      fecha
    )


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
      day:
        '2-digit',

      month:
        '2-digit',

      year:
        'numeric',
    }
  )

}


function formatearHoraReporte(
  fecha
) {

  if (!fecha) {
    return '-'
  }


  const valor =
    new Date(
      fecha
    )


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
      hour:
        '2-digit',

      minute:
        '2-digit',
    }
  )

}


function obtenerAntiguedadReporte(
  fecha
) {

  if (!fecha) {
    return ''
  }


  const valor =
    new Date(
      fecha
    )


  if (
    Number.isNaN(
      valor.getTime()
    )
  ) {

    return ''

  }


  const diferenciaMs =
    Date.now()
    -
    valor.getTime()


  if (
    diferenciaMs < 0
  ) {

    return 'Ahora'

  }


  const minutos =
    Math.floor(
      diferenciaMs
      /
      60000
    )


  if (
    minutos < 1
  ) {

    return 'Hace menos de 1 min'

  }


  if (
    minutos < 60
  ) {

    return `Hace ${minutos} min`

  }


  const horas =
    Math.floor(
      minutos
      /
      60
    )


  if (
    horas < 24
  ) {

    return (
      horas === 1
        ? 'Hace 1 hora'
        : `Hace ${horas} horas`
    )

  }


  const dias =
    Math.floor(
      horas
      /
      24
    )


  return (
    dias === 1
      ? 'Hace 1 día'
      : `Hace ${dias} días`
  )

}

function AdminReportes() {
  const location =
    useLocation()


  const [
    verificandoSesion,
    setVerificandoSesion
  ] = useState(true)


  const [
    autenticado,
    setAutenticado
  ] = useState(false)


  const [
    usuario,
    setUsuario
  ] = useState(null)


  const [
    username,
    setUsername
  ] = useState('admin')


  const [
    password,
    setPassword
  ] = useState('')


  const [
    pendientes,
    setPendientes
  ] = useState([])


  const [
    cargando,
    setCargando
  ] = useState(false)


  const [
    procesando,
    setProcesando
  ] = useState(null)


  const [
    error,
    setError
  ] = useState('')


  // =========================================================
  // TOKEN
  // =========================================================

  const obtenerToken = () => {

    return sessionStorage.getItem(
      TOKEN_KEY
    )

  }


  const eliminarSesion = () => {

    sessionStorage.removeItem(
      TOKEN_KEY
    )


    setAutenticado(
      false
    )


    setUsuario(
      null
    )


    setPendientes(
      []
    )

  }


  // =========================================================
  // CARGAR REPORTES
  // =========================================================

  const cargarPendientes =
    async (
      tokenRecibido = null
    ) => {

      const token =
        tokenRecibido ||
        obtenerToken()


      if (
        !token
      ) {

        eliminarSesion()

        return

      }


      setCargando(
        true
      )


      setError(
        ''
      )


      try {

        const respuesta =
          await fetch(
            '/api/reportes/pendientes',
            {
              headers: {

                Authorization:
                  `Bearer ${token}`,

              },

              cache:
                'no-store',
            }
          )


        if (
          respuesta.status ===
          401
        ) {

          eliminarSesion()


          throw new Error(
            'La sesión expiró. Inicia sesión nuevamente.'
          )

        }


        if (
          !respuesta.ok
        ) {

          let mensaje =
            'No fue posible cargar los reportes.'


          try {

            const datos =
              await respuesta.json()


            if (
              datos.detail
            ) {

              mensaje =
                datos.detail

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


        setPendientes(
          datos
        )


        setAutenticado(
          true
        )

      } catch (err) {

        setError(
          err.message ||
          'No fue posible cargar los reportes.'
        )

      } finally {

        setCargando(
          false
        )

      }

    }


  // =========================================================
  // VERIFICAR JWT
  // =========================================================

  useEffect(() => {

    if (
      location.pathname !==
      '/admin'
    ) {

      setVerificandoSesion(
        false
      )

      return

    }


    const verificarSesion =
      async () => {

        const token =
          obtenerToken()


        if (
          !token
        ) {

          setVerificandoSesion(
            false
          )

          return

        }


        try {

          const respuesta =
            await fetch(
              '/api/auth/me',
              {
                headers: {

                  Authorization:
                    `Bearer ${token}`,

                },

                cache:
                  'no-store',
              }
            )


          if (
            !respuesta.ok
          ) {

            eliminarSesion()

            return

          }


          const datos =
            await respuesta.json()


          setAutenticado(
            true
          )


          setUsuario(
            datos.username
          )


          await cargarPendientes(
            token
          )

        } catch {

          eliminarSesion()

        } finally {

          setVerificandoSesion(
            false
          )

        }

      }


    verificarSesion()

  }, [
    location.pathname
  ])


  // =========================================================
  // LOGIN
  // =========================================================

  const iniciarSesion =
    async (
      evento
    ) => {

      evento.preventDefault()


      setError(
        ''
      )


      if (
        !username.trim()
        ||
        !password
      ) {

        setError(
          'Ingresa usuario y contraseña.'
        )

        return

      }


      setCargando(
        true
      )


      try {

        const formulario =
          new URLSearchParams()


        formulario.append(
          'username',
          username.trim()
        )


        formulario.append(
          'password',
          password
        )


        const respuesta =
          await fetch(
            '/api/auth/token',
            {
              method:
                'POST',

              headers: {

                'Content-Type':
                  'application/x-www-form-urlencoded',

              },

              body:
                formulario.toString(),
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
            'No fue posible iniciar sesión.'
          )

        }


        sessionStorage.setItem(
          TOKEN_KEY,
          datos.access_token
        )


        setAutenticado(
          true
        )


        setUsuario(
          username.trim()
        )


        setPassword(
          ''
        )


        await cargarPendientes(
          datos.access_token
        )

      } catch (err) {

        eliminarSesion()


        setError(
          err.message ||
          'No fue posible iniciar sesión.'
        )

      } finally {

        setCargando(
          false
        )

      }

    }


  // =========================================================
  // CONFIRMAR / RECHAZAR
  // =========================================================

  const cambiarEstado =
    async (
      idReporte,
      accion
    ) => {

      const token =
        obtenerToken()


      if (
        !token
      ) {

        eliminarSesion()


        setError(
          'Debes iniciar sesión nuevamente.'
        )


        return

      }


      setProcesando(
        idReporte
      )


      setError(
        ''
      )


      try {

        const respuesta =
          await fetch(

            `/api/reportes/${idReporte}/${accion}`,

            {
              method:
                'PATCH',

              headers: {

                Authorization:
                  `Bearer ${token}`,

              },
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
          respuesta.status ===
          401
        ) {

          eliminarSesion()


          throw new Error(
            'La sesión expiró. Inicia sesión nuevamente.'
          )

        }


        if (
          !respuesta.ok
        ) {

          throw new Error(
            datos?.detail ||
            'No fue posible actualizar el reporte.'
          )

        }


        setPendientes(
          (
            actuales
          ) =>
            actuales.filter(
              (
                reporte
              ) =>
                reporte.id_reporte !==
                idReporte
            )
        )


        window.dispatchEvent(
          new Event(
            'reportes-actualizados'
          )
        )

      } catch (err) {

        setError(
          err.message ||
          'No fue posible actualizar el reporte.'
        )

      } finally {

        setProcesando(
          null
        )

      }

    }


  // =========================================================
  // LOGOUT
  // =========================================================

  const cerrarSesion = () => {

    eliminarSesion()


    setPassword(
      ''
    )


    setError(
      ''
    )

  }


  // =========================================================
  // SOLO /admin
  // =========================================================

  if (
    location.pathname !==
    '/admin'
  ) {

    return null

  }


  // =========================================================
  // VERIFICANDO
  // =========================================================

  if (
    verificandoSesion
  ) {

    return (

      <div className="admin-pagina">

        <div className="admin-cargando-pagina">

          <div className="admin-spinner" />

          <strong>
            Verificando sesión
          </strong>

          <span>
            Comprobando credenciales administrativas...
          </span>

        </div>

      </div>

    )

  }


  // =========================================================
  // LOGIN
  // =========================================================

  if (
    !autenticado
  ) {

    return (

      <div className="admin-login-pagina">


        <div className="admin-login-fondo">


          <div className="admin-login-marca">


            <div className="admin-logo">
              🔥
            </div>


            <p>
              Sistema inteligente de prevención
            </p>


            <h1>
              Riesgo de Incendios Forestales
            </h1>


            <span>
              Región de Valparaíso
            </span>


          </div>


          <div className="admin-login-contenedor">


            <div className="admin-login-card">


              <div className="admin-login-icono">
                🔐
              </div>


              <p className="admin-login-etiqueta">
                Área restringida
              </p>


              <h2>
                Administración
              </h2>


              <p className="admin-login-descripcion">

                Ingresa tus credenciales para
                acceder a las herramientas
                administrativas del sistema.

              </p>


              <form
                onSubmit={
                  iniciarSesion
                }
              >


                <label
                  htmlFor="admin-username"
                >
                  Usuario
                </label>


                <input
                  id="admin-username"

                  type="text"

                  value={
                    username
                  }

                  onChange={(
                    evento
                  ) =>
                    setUsername(
                      evento.target.value
                    )
                  }

                  autoComplete="username"

                  disabled={
                    cargando
                  }
                />


                <label
                  htmlFor="admin-password"
                >
                  Contraseña
                </label>


                <input
                  id="admin-password"

                  type="password"

                  value={
                    password
                  }

                  onChange={(
                    evento
                  ) =>
                    setPassword(
                      evento.target.value
                    )
                  }

                  autoComplete="current-password"

                  disabled={
                    cargando
                  }
                />


                {error && (

                  <div className="admin-login-error">

                    {error}

                  </div>

                )}


                <button
                  type="submit"

                  className="admin-login-boton"

                  disabled={
                    cargando
                  }
                >

                  {
                    cargando
                      ? 'Verificando...'
                      : 'Iniciar sesión'
                  }

                </button>


              </form>


              <Link
                to="/"

                className="admin-volver-login"
              >

                ← Volver al mapa público

              </Link>


            </div>


          </div>


        </div>


      </div>

    )

  }


  // =========================================================
  // PANEL ADMIN
  // =========================================================

  return (

    <div className="admin-pagina">


      <header className="admin-topbar">


        <div>

          <p>
            Sistema de Riesgo de Incendios
          </p>

          <h1>
            Panel administrativo
          </h1>

        </div>


        <div className="admin-usuario">


          <div className="admin-usuario-info">

            <span>
              Sesión iniciada
            </span>

            <strong>
              {usuario}
            </strong>

          </div>


          <button
            type="button"

            onClick={
              cerrarSesion
            }
          >
            Cerrar sesión
          </button>


        </div>


      </header>


      <div className="admin-layout">


        <aside className="admin-sidebar">


          <div className="admin-sidebar-titulo">
            Administración
          </div>


          <nav>

            <button
              type="button"

              className="admin-nav-item admin-nav-activo"
            >

              <span>
                🔥
              </span>

              Reportes ciudadanos

            </button>

          </nav>


          <div className="admin-sidebar-futuro">

            <span>

              Panel preparado para incorporar
              nuevas herramientas administrativas.

            </span>

          </div>


          <Link
            to="/"

            className="admin-volver-mapa"
          >
            ← Volver al mapa
          </Link>


        </aside>


        <main className="admin-main">


          <div className="admin-main-header">


            <div>

              <p className="admin-seccion-etiqueta">
                Validación ciudadana
              </p>


              <h2>
                Reportes pendientes
              </h2>


              <p className="admin-seccion-descripcion">

                Revisa la evidencia enviada por
                los ciudadanos antes de mostrar
                un reporte en el mapa público.

              </p>

            </div>


            <button
              type="button"

              className="admin-actualizar"

              onClick={() =>
                cargarPendientes()
              }

              disabled={
                cargando
              }
            >

              ↻ Actualizar

            </button>


          </div>


          <div className="admin-resumen">


            <div className="admin-resumen-card">

              <span>
                Pendientes
              </span>

              <strong>
                {
                  pendientes.length
                }
              </strong>

            </div>


            <div className="admin-resumen-card">

              <span>
                Sesión
              </span>

              <strong className="admin-sesion-activa">
                Activa
              </strong>

            </div>


            <div className="admin-resumen-card">

              <span>
                Autenticación
              </span>

              <strong className="admin-auth-label">
                OAuth2 + JWT
              </strong>

            </div>


          </div>


          {error && (

            <div className="admin-panel-error">

              {error}

            </div>

          )}


          {cargando && (

            <div className="admin-estado-vacio">

              <div className="admin-spinner" />

              <strong>
                Cargando reportes
              </strong>

            </div>

          )}


          {
            !cargando &&
            pendientes.length === 0 && (

              <div className="admin-estado-vacio">


                <div className="admin-check">
                  ✓
                </div>


                <strong>
                  No hay reportes pendientes
                </strong>


                <p>

                  Todos los reportes ciudadanos
                  han sido revisados.

                </p>


              </div>

            )
          }


          {
            !cargando &&
            pendientes.length > 0 && (

              <div className="admin-reportes-grid">


                {pendientes.map(
                  (
                    reporte
                  ) => {

                    const origenManual =
                      reporte.origen_ubicacion ===
                      'manual'


                    const tienePrecisionGps =
                      !origenManual
                      &&
                      reporte.precision_gps_m !==
                      null
                      &&
                      reporte.precision_gps_m !==
                      undefined


                    const calidadGps =
                      tienePrecisionGps
                        ? clasificarPrecisionGps(
                            reporte.precision_gps_m
                          )
                        : null


                    const cantidadCercanos =
                      Number(
                        reporte.reportes_cercanos_count ||
                        0
                      )


                    return (

                      <article
                        className="admin-reporte-card"

                        key={
                          reporte.id_reporte
                        }
                      >


                        <div className="admin-reporte-header">


                          <div>

                            <span>
                              Reporte ciudadano
                            </span>

                            <strong>

                              #

                              {
                                reporte.id_reporte
                              }

                            </strong>

                          </div>


                          <div className="admin-badge-pendiente">
                            Pendiente
                          </div>


                        </div>


                        {reporte.imagen_url ? (

                          <img
                            className="admin-reporte-imagen"

                            src={
                              `/api${reporte.imagen_url}`
                            }

                            alt={
                              `Evidencia del reporte ${
                                reporte.id_reporte
                              }`
                            }
                          />

                        ) : (

                          <div className="admin-imagen-vacia">

                            Sin fotografía

                          </div>

                        )}


                        <div className="admin-reporte-body">


                          <div className="admin-descripcion">

                            <span>
                              Descripción
                            </span>

                            <p>

                              {
                                reporte.descripcion ||
                                'Sin descripción'
                              }

                            </p>

                          </div>


                          <div className="admin-datos">


                            <div>

                              <span>
                                Detección IA
                              </span>

                              <strong>

                                {
                                  reporte.yolo_clase ||
                                  '-'
                                }

                              </strong>

                            </div>


                            <div>

                              <span>
                                Confianza
                              </span>

                              <strong>

                                {
                                  reporte.yolo_confianza !== null &&
                                  reporte.yolo_confianza !== undefined
                                    ? `${
                                        (
                                          Number(
                                            reporte.yolo_confianza
                                          )
                                          *
                                          100
                                        ).toFixed(1)
                                      }%`
                                    : '-'
                                }

                              </strong>

                            </div>


                            <div className="admin-dato">


                            <span>

                              {
                                origenManual
                                  ? 'Ubicación'
                                  : 'Precisión GPS'
                              }

                            </span>


                            {
                              origenManual
                                ? (

                                    <>

                                      <strong>
                                        Manual
                                      </strong>


                                      <div className="admin-badge-manual">

                                        Aproximada

                                      </div>

                                    </>

                                  )
                                : (

                                    <>

                                      <strong>

                                        {
                                          tienePrecisionGps
                                            ? formatearPrecisionGps(
                                                reporte.precision_gps_m
                                              )
                                            : '-'
                                        }

                                      </strong>


                                      {
                                        calidadGps && (

                                          <div
                                            className={
                                              `gps-calidad gps-calidad-${calidadGps.nivel}`
                                            }
                                          >

                                            {
                                              calidadGps.etiqueta
                                            }

                                          </div>

                                        )
                                      }

                                    </>

                                  )
                            }


                          </div>


                            <div>

                              <span>
                                Coordenadas
                              </span>

                              <strong>

                                {
                                  Number(
                                    reporte.latitud
                                  ).toFixed(4)
                                }

                                {', '}

                                {
                                  Number(
                                    reporte.longitud
                                  ).toFixed(4)
                                }

                              </strong>

                            </div>

                            <div className="admin-dato">

                              <span>
                                Fecha del reporte
                              </span>

                              <strong>

                                {
                                  formatearFechaReporte(
                                    reporte.fecha_reporte
                                  )
                                }

                              </strong>

                            </div>


                            <div className="admin-dato">

                              <span>
                                Hora
                              </span>

                              <strong>

                                {
                                  formatearHoraReporte(
                                    reporte.fecha_reporte
                                  )
                                }

                              </strong>


                              <small className="admin-antiguedad">

                                {
                                  obtenerAntiguedadReporte(
                                    reporte.fecha_reporte
                                  )
                                }

                              </small>

                            </div>


                          </div>


                          {
                            reporte.posible_duplicado && (

                              <div className="admin-duplicado-alerta">

                                <span>
                                  ⚠
                                </span>


                                <div>

                                  <strong>
                                    Posible fotografía duplicada
                                  </strong>


                                  La imagen presenta una
                                  coincidencia visual alta
                                  con el{' '}

                                  <span className="admin-duplicado-id">

                                    reporte #

                                    {
                                      reporte.reporte_duplicado_id
                                    }

                                  </span>

                                  .

                                  {' '}

                                  Este reporte no se considera
                                  una corroboración independiente
                                  del evento.

                                  {' '}

                                  Revisa ambas evidencias antes
                                  de confirmar.

                                </div>

                              </div>

                            )
                          }


                          {
                            cantidadCercanos > 0 && (

                              <div className="admin-cercania-alerta">


                                <span className="admin-cercania-icono">
                                  📍
                                </span>


                                <div className="admin-cercania-contenido">


                                  <strong>
                                    Posible mismo evento
                                  </strong>


                                  Se encontraron{' '}

                                  <b>
                                    {
                                      cantidadCercanos
                                    }
                                  </b>

                                  {' '}

                                  {
                                    cantidadCercanos === 1
                                      ? 'reporte adicional'
                                      : 'reportes adicionales'
                                  }

                                  {' '}dentro de{' '}

                                  <b>
                                    {
                                      reporte.radio_cercania_m
                                    } m
                                  </b>

                                  {' '}y una diferencia
                                  máxima de{' '}

                                  <b>
                                    {
                                      reporte.ventana_cercania_min
                                    } minutos
                                  </b>

                                  .


                                  {
                                    reporte.reportes_cercanos_ids &&
                                    reporte.reportes_cercanos_ids.length > 0 && (

                                      <span className="admin-cercania-detalle">

                                        Reportes relacionados:{' '}

                                        <span className="admin-cercania-ids">

                                          {
                                            reporte.reportes_cercanos_ids
                                              .map(
                                                id =>
                                                  `#${id}`
                                              )
                                              .join(
                                                ', '
                                              )
                                          }

                                        </span>

                                      </span>

                                    )
                                  }


                                  {
                                    reporte.distancia_reporte_cercano_m !== null &&
                                    reporte.distancia_reporte_cercano_m !== undefined && (

                                      <span className="admin-cercania-detalle">

                                        Reporte más cercano:{' '}

                                        {
                                          Math.round(
                                            Number(
                                              reporte.distancia_reporte_cercano_m
                                            )
                                          )
                                        }

                                        {' m'}

                                      </span>

                                    )
                                  }


                                </div>


                              </div>

                            )
                          }


                          {
                            origenManual && (

                              <div className="admin-aviso-manual">

                                <span>
                                  🗺
                                </span>

                                <div>

                                  <strong>
                                    Ubicación indicada manualmente
                                  </strong>

                                  <div>

                                    El ciudadano seleccionó este
                                    sector directamente en el mapa.
                                    La ubicación es aproximada,
                                    no proviene del GPS y no se
                                    utiliza como corroboración
                                    geográfica automática.

                                  </div>

                                </div>

                              </div>

                            )
                          }


                          {
                            calidadGps
                            &&
                            (
                              calidadGps.nivel ===
                              'moderada'
                              ||
                              calidadGps.nivel ===
                              'baja'
                              ||
                              calidadGps.nivel ===
                              'desconocida'
                            ) && (

                              <div
                                className={
                                  `admin-alerta-gps admin-alerta-gps-${calidadGps.nivel}`
                                }
                              >

                                <span>
                                  ⚠
                                </span>

                                <span>

                                  {
                                    calidadGps.descripcionAdmin
                                  }

                                </span>

                              </div>

                            )
                          }


                          <div className="admin-reporte-acciones">


                            <button
                              type="button"

                              className="admin-boton-rechazar"

                              disabled={
                                procesando ===
                                reporte.id_reporte
                              }

                              onClick={() =>
                                cambiarEstado(
                                  reporte.id_reporte,
                                  'rechazar'
                                )
                              }
                            >

                              Rechazar

                            </button>


                            <button
                              type="button"

                              className="admin-boton-confirmar"

                              disabled={
                                procesando ===
                                reporte.id_reporte
                              }

                              onClick={() =>
                                cambiarEstado(
                                  reporte.id_reporte,
                                  'confirmar'
                                )
                              }
                            >

                              {
                                procesando ===
                                reporte.id_reporte
                                  ? 'Procesando...'
                                  : 'Confirmar'
                              }

                            </button>


                          </div>


                        </div>


                      </article>

                    )

                  }
                )}


              </div>

            )
          }


        </main>


      </div>


    </div>

  )
}


export default AdminReportes