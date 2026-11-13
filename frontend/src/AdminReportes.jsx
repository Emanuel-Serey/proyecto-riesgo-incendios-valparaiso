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


function formatearComprobacion(
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

      second:
        '2-digit',
    }
  )

}


function formatearPromedioHoras(
  horas
) {

  if (
    horas ===
    null
  ) {

    return '-'
  }


  if (
    horas <
    1
  ) {

    return (
      `${Math.round(
        horas * 60
      )} min`
    )
  }


  return (
    `${horas.toFixed(1)} h`
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
    activos,
    setActivos
  ] = useState([])


  const [
    historial,
    setHistorial
  ] = useState([])


  const [
    vista,
    setVista
  ] = useState(
    'pendientes'
  )


  const [
    filtroHistorial,
    setFiltroHistorial
  ] = useState(
    'todos'
  )


  const [
    estadoSistema,
    setEstadoSistema
  ] = useState(null)


  const [
    cargandoSistema,
    setCargandoSistema
  ] = useState(false)


  const [
    errorSistema,
    setErrorSistema
  ] = useState('')


  const [
    estadisticasRiesgo,
    setEstadisticasRiesgo
  ] = useState(null)


  const [
    cargandoEstadisticasRiesgo,
    setCargandoEstadisticasRiesgo
  ] = useState(false)


  const [
    errorEstadisticasRiesgo,
    setErrorEstadisticasRiesgo
  ] = useState('')


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


    setActivos(
      []
    )


    setHistorial(
      []
    )


    setEstadoSistema(
      null
    )


    setEstadisticasRiesgo(
      null
    )


    setErrorEstadisticasRiesgo(
      ''
    )


    setCargandoEstadisticasRiesgo(
      false
    )

  }


  // =========================================================
  // PENDIENTES
  // =========================================================

  const cargarPendientes =
    async (
      tokenRecibido = null
    ) => {

      const token =
        tokenRecibido ||
        obtenerToken()


      if (!token) {
        eliminarSesion()
        return
      }


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
          'La sesión expiró.'
        )
      }


      if (
        !respuesta.ok
      ) {

        const datos =
          await respuesta.json()


        throw new Error(
          datos.detail ||
          'No fue posible cargar los reportes pendientes.'
        )
      }


      setPendientes(
        await respuesta.json()
      )

  }


  // =========================================================
  // ACTIVOS
  // =========================================================

  const cargarActivos =
    async (
      tokenRecibido = null
    ) => {

      const token =
        tokenRecibido ||
        obtenerToken()


      if (!token) {
        eliminarSesion()
        return
      }


      const respuesta =
        await fetch(
          '/api/admin/reportes/confirmados',
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
          'La sesión expiró.'
        )
      }


      if (
        !respuesta.ok
      ) {

        const datos =
          await respuesta.json()


        throw new Error(
          datos.detail ||
          'No fue posible cargar los reportes activos.'
        )
      }


      setActivos(
        await respuesta.json()
      )

  }


  // =========================================================
  // HISTORIAL
  // =========================================================

  const cargarHistorial =
    async (
      tokenRecibido = null
    ) => {

      const token =
        tokenRecibido ||
        obtenerToken()


      if (!token) {
        eliminarSesion()
        return
      }


      const respuesta =
        await fetch(
          '/api/admin/reportes/historial',
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
          'La sesión expiró.'
        )
      }


      if (
        !respuesta.ok
      ) {

        const datos =
          await respuesta.json()


        throw new Error(
          datos.detail ||
          'No fue posible cargar el historial.'
        )
      }


      setHistorial(
        await respuesta.json()
      )

  }


  // =========================================================
  // ESTADO DEL SISTEMA
  // =========================================================

  const cargarEstadoSistema =
    async (
      tokenRecibido = null
    ) => {

      const token =
        tokenRecibido ||
        obtenerToken()


      if (!token) {
        eliminarSesion()
        return
      }


      setCargandoSistema(
        true
      )


      setErrorSistema(
        ''
      )


      try {

        const respuesta =
          await fetch(
            '/api/admin/system/status',
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
            'La sesión expiró.'
          )
        }


        if (
          !respuesta.ok
        ) {

          const datos =
            await respuesta.json()


          throw new Error(
            datos.detail ||
            'No fue posible comprobar el sistema.'
          )
        }


        setEstadoSistema(
          await respuesta.json()
        )


      } catch (err) {

        setErrorSistema(
          err.message ||
          'No fue posible comprobar el sistema.'
        )

      } finally {

        setCargandoSistema(
          false
        )

      }

    }


  // =========================================================
  // ESTADISTICAS DE RIESGO
  // =========================================================

  const cargarEstadisticasRiesgo =
    async (
      tokenRecibido = null
    ) => {

      const token =
        tokenRecibido ||
        obtenerToken()


      if (!token) {
        eliminarSesion()
        return
      }


      setCargandoEstadisticasRiesgo(
        true
      )


      setErrorEstadisticasRiesgo(
        ''
      )


      try {

        const respuesta =
          await fetch(
            '/api/admin/riesgo/estadisticas',
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
            'La sesión expiró.'
          )
        }


        if (
          !respuesta.ok
        ) {

          const datos =
            await respuesta.json()


          throw new Error(
            datos.detail ||
            'No fue posible cargar las estadísticas de riesgo.'
          )
        }


        setEstadisticasRiesgo(
          await respuesta.json()
        )


      } catch (err) {

        setErrorEstadisticasRiesgo(
          err.message ||
          'No fue posible cargar las estadísticas de riesgo.'
        )

      } finally {

        setCargandoEstadisticasRiesgo(
          false
        )

      }

    }


  // =========================================================
  // CARGAR REPORTES
  // =========================================================

  const cargarTodosReportes =
    async (
      token
    ) => {

      await Promise.all([

        cargarPendientes(
          token
        ),

        cargarActivos(
          token
        ),

        cargarHistorial(
          token
        ),

      ])

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


        if (!token) {

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


          await cargarTodosReportes(
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

        const datos =
          await respuesta.json()


        if (
          !respuesta.ok
        ) {

          throw new Error(
            datos.detail ||
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


        await cargarTodosReportes(
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


      if (!token) {
        eliminarSesion()
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


        const datos =
          await respuesta.json()


        if (
          !respuesta.ok
        ) {

          throw new Error(
            datos.detail ||
            'No fue posible actualizar el reporte.'
          )
        }


        await cargarTodosReportes(
          token
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
  // RESOLVER
  // =========================================================

  const resolverReporte =
    async (
      idReporte
    ) => {

      const token =
        obtenerToken()


      if (!token) {
        eliminarSesion()
        return
      }


      setProcesando(
        idReporte
      )


      try {

        const respuesta =
          await fetch(
            `/api/reportes/${idReporte}/resolver`,
            {
              method:
                'PATCH',

              headers: {
                Authorization:
                  `Bearer ${token}`,
              },
            }
          )


        const datos =
          await respuesta.json()


        if (
          !respuesta.ok
        ) {

          throw new Error(
            datos.detail ||
            'No fue posible resolver el reporte.'
          )
        }


        await cargarTodosReportes(
          token
        )


        window.dispatchEvent(
          new Event(
            'reportes-actualizados'
          )
        )


      } catch (err) {

        setError(
          err.message ||
          'No fue posible resolver el reporte.'
        )

      } finally {

        setProcesando(
          null
        )

      }

    }


  // =========================================================
  // ACTUALIZAR
  // =========================================================

  const actualizarVista =
    async () => {

      if (
        vista ===
        'sistema'
      ) {

        await cargarEstadoSistema()

        return
      }


      if (
        vista ===
        'analisis'
      ) {

        setCargando(
          true
        )


        try {

          await Promise.all([

            cargarTodosReportes(
              obtenerToken()
            ),

            cargarEstadisticasRiesgo(),

          ])

        } finally {

          setCargando(
            false
          )

        }


        return

      }


      setCargando(
        true
      )


      try {

        await cargarTodosReportes(
          obtenerToken()
        )

      } finally {

        setCargando(
          false
        )

      }

    }


  const abrirSistema = () => {

    setVista(
      'sistema'
    )


    cargarEstadoSistema()

  }


  const abrirAnalisis = () => {

    setVista(
      'analisis'
    )


    cargarEstadisticasRiesgo()

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
  // MÉTRICAS
  // =========================================================

  const resueltos =
    historial.filter(
      reporte =>
        reporte.estado ===
        'resuelto'
    )


  const rechazados =
    historial.filter(
      reporte =>
        reporte.estado ===
        'rechazado'
    )


  const todosReportes = [

    ...pendientes,

    ...activos,

    ...historial,

  ]


  const totalReportes =
    todosReportes.length


  const confirmadosHistoricos =
    activos.length
    +
    resueltos.length


  const decisiones =
    confirmadosHistoricos
    +
    rechazados.length


  const tasaConfirmacion =
    decisiones >
    0

      ? (
          confirmadosHistoricos
          /
          decisiones
          *
          100
        )

      : 0


  const totalGps =
    todosReportes.filter(
      reporte =>
        reporte.origen_ubicacion ===
        'gps'
    ).length


  const totalManual =
    todosReportes.filter(
      reporte =>
        reporte.origen_ubicacion ===
        'manual'
    ).length


  const totalDuplicados =
    todosReportes.filter(
      reporte =>
        reporte.posible_duplicado
    ).length


  const deteccionesHumo =
    todosReportes.filter(
      reporte =>
        reporte.yolo_clase ===
        'smoke'
    ).length


  const deteccionesFuego =
    todosReportes.filter(
      reporte =>
        reporte.yolo_clase ===
        'fire'
    ).length


  const tiemposResolucion =
    resueltos
      .filter(
        reporte =>
          reporte.fecha_validacion
          &&
          reporte.fecha_resolucion
      )
      .map(
        reporte => {

          const inicio =
            new Date(
              reporte.fecha_validacion
            ).getTime()


          const fin =
            new Date(
              reporte.fecha_resolucion
            ).getTime()


          return (
            fin - inicio
          ) / 3600000

        }
      )
      .filter(
        valor =>
          Number.isFinite(
            valor
          )
          &&
          valor >=
          0
      )


  const promedioResolucion =
    tiemposResolucion.length >
    0

      ? (
          tiemposResolucion.reduce(
            (
              total,
              valor
            ) =>
              total +
              valor,
            0
          )
          /
          tiemposResolucion.length
        )

      : null


  const porcentaje =
    cantidad => {

      if (
        totalReportes ===
        0
      ) {

        return 0
      }


      return (
        cantidad
        /
        totalReportes
        *
        100
      )

    }


  // =========================================================
  // HISTORIAL
  // =========================================================

  const historialFiltrado =
    historial.filter(
      reporte => {

        if (
          filtroHistorial ===
          'todos'
        ) {

          return true
        }


        return (
          reporte.estado ===
          filtroHistorial
        )

      }
    )


  // =========================================================
  // RUTA
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

                <label>
                  Usuario
                </label>


                <input
                  type="text"

                  value={
                    username
                  }

                  onChange={
                    evento =>
                      setUsername(
                        evento.target.value
                      )
                  }
                />


                <label>
                  Contraseña
                </label>


                <input
                  type="password"

                  value={
                    password
                  }

                  onChange={
                    evento =>
                      setPassword(
                        evento.target.value
                      )
                  }
                />


                {
                  error && (

                    <div className="admin-login-error">
                      {error}
                    </div>

                  )
                }


                <button
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
  // PANEL
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


          <div className="admin-sidebar-grupo">

            <div className="admin-sidebar-grupo-titulo">
              Reportes ciudadanos
            </div>


            <button
              className={
                `admin-nav-item ${
                  vista ===
                  'pendientes'
                    ? 'admin-nav-activo'
                    : ''
                }`
              }

              onClick={() =>
                setVista(
                  'pendientes'
                )
              }
            >

              🔥 Pendientes

              <b className="admin-nav-contador">
                {pendientes.length}
              </b>

            </button>


            <button
              className={
                `admin-nav-item ${
                  vista ===
                  'activos'
                    ? 'admin-nav-activo'
                    : ''
                }`
              }

              onClick={() =>
                setVista(
                  'activos'
                )
              }
            >

              📍 Reportes activos

              <b className="admin-nav-contador">
                {activos.length}
              </b>

            </button>


            <button
              className={
                `admin-nav-item ${
                  vista ===
                  'historial'
                    ? 'admin-nav-activo'
                    : ''
                }`
              }

              onClick={() =>
                setVista(
                  'historial'
                )
              }
            >

              🕘 Historial

              <b className="admin-nav-contador">
                {historial.length}
              </b>

            </button>

          </div>


          <div className="admin-sidebar-grupo">

            <div className="admin-sidebar-grupo-titulo">
              Sistema
            </div>


            <button
              className={
                `admin-nav-item ${
                  vista ===
                  'sistema'
                    ? 'admin-nav-activo'
                    : ''
                }`
              }

              onClick={
                abrirSistema
              }
            >

              ⚙ Estado del sistema

            </button>

          </div>


          <div className="admin-sidebar-grupo">

            <div className="admin-sidebar-grupo-titulo">
              Análisis
            </div>


            <button
              className={
                `admin-nav-item ${
                  vista ===
                  'analisis'
                    ? 'admin-nav-activo'
                    : ''
                }`
              }

              onClick={
                abrirAnalisis
              }
            >

              📊 Estadísticas

            </button>

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

                {
                  vista ===
                  'pendientes'
                    ? 'Validación ciudadana'
                    : vista ===
                      'activos'
                        ? 'Seguimiento de reportes'
                        : vista ===
                          'historial'
                            ? 'Registro histórico'
                            : vista ===
                              'sistema'
                                ? 'Infraestructura'
                                : 'Análisis del sistema'
                }

              </p>


              <h2>

                {
                  vista ===
                  'pendientes'
                    ? 'Reportes pendientes'
                    : vista ===
                      'activos'
                        ? 'Reportes activos'
                        : vista ===
                          'historial'
                            ? 'Historial de reportes'
                            : vista ===
                              'sistema'
                                ? 'Estado del sistema'
                                : 'Estadísticas'
                }

              </h2>


              <p className="admin-seccion-descripcion">

                {
                  vista ===
                  'pendientes'
                    ? 'Revisa la evidencia antes de publicar un reporte en el mapa.'
                    : vista ===
                      'activos'
                        ? 'Reportes actualmente visibles como llamas en el mapa público.'
                        : vista ===
                          'historial'
                            ? 'Consulta reportes resueltos y rechazados.'
                            : vista ===
                              'sistema'
                                ? 'Supervisa servicios, base de datos y modelos de inteligencia artificial.'
                                : 'Resumen estadístico de reportes ciudadanos y uso del sistema de riesgo.'
                }

              </p>

            </div>


            <button
              className="admin-actualizar"
              onClick={
                actualizarVista
              }
            >

              ↻ Actualizar

            </button>


          </div>


          {
            (
              vista ===
              'pendientes'
              ||
              vista ===
              'activos'
              ||
              vista ===
              'historial'
            )
            && (

              <div className="admin-resumen">


                <div className="admin-resumen-card">

                  <span>
                    Pendientes
                  </span>

                  <strong>
                    {pendientes.length}
                  </strong>

                </div>


                <div className="admin-resumen-card">

                  <span>
                    Activos en mapa
                  </span>

                  <strong>
                    {activos.length}
                  </strong>

                </div>


                <div className="admin-resumen-card">

                  <span>
                    Historial
                  </span>

                  <strong>
                    {historial.length}
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


              </div>

            )
          }


          {
            error && (

              <div className="admin-panel-error">
                {error}
              </div>

            )
          }


          {/* =================================================
              PENDIENTES
              ================================================= */}

          {
            vista ===
            'pendientes'
            &&
            (

              <div className="admin-reportes-grid">

                {
                  pendientes.map(
                    reporte => {

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
                                #{reporte.id_reporte}
                              </strong>

                            </div>


                            <div className="admin-badge-pendiente">
                              Pendiente
                            </div>

                          </div>


                          <img
                            className="admin-reporte-imagen"

                            src={
                              `/api${reporte.imagen_url}`
                            }

                            alt="Evidencia"
                          />


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
                                  {reporte.yolo_clase || '-'}
                                </strong>

                              </div>


                              <div>

                                <span>
                                  Confianza
                                </span>

                                <strong>

                                  {
                                    reporte.yolo_confianza !==
                                    null

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


                              <div>

                                <span>
                                  {
                                    origenManual
                                      ? 'Ubicación'
                                      : 'Precisión GPS'
                                  }
                                </span>

                                <strong>

                                  {
                                    origenManual
                                      ? 'Manual · aproximada'
                                      : tienePrecisionGps
                                        ? formatearPrecisionGps(
                                            reporte.precision_gps_m
                                          )
                                        : '-'
                                  }

                                </strong>

                                {
                                  calidadGps && (

                                    <small className="admin-antiguedad">
                                      {calidadGps.etiqueta}
                                    </small>

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


                              <div>

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


                              <div>

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

                                  ⚠

                                  <div>

                                    <strong>
                                      Posible fotografía duplicada
                                    </strong>

                                    Coincidencia visual con el reporte
                                    {' #'}

                                    {
                                      reporte.reporte_duplicado_id
                                    }

                                    .

                                  </div>

                                </div>

                              )
                            }


                            {
                              origenManual && (

                                <div className="admin-aviso-manual">

                                  🗺

                                  <div>

                                    <strong>
                                      Ubicación indicada manualmente
                                    </strong>

                                    El punto es aproximado y no
                                    proviene del GPS.

                                  </div>

                                </div>

                              )
                            }


                            {
                              calidadGps
                              &&
                              calidadGps.nivel !==
                              'buena'
                              && (

                                <div className="admin-alerta-gps">

                                  ⚠

                                  {
                                    calidadGps.descripcionAdmin
                                  }

                                </div>

                              )
                            }


                            <div className="admin-reporte-acciones">


                              <button
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

                                Confirmar

                              </button>


                            </div>


                          </div>


                        </article>

                      )

                    }
                  )
                }


              </div>

            )
          }


          {/* =================================================
              ACTIVOS
              ================================================= */}

          {
            vista ===
            'activos'
            && (

              <div className="admin-reportes-grid">

                {
                  activos.map(
                    reporte => (

                      <article
                        className="admin-reporte-card admin-reporte-activo"

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
                              #{reporte.id_reporte}
                            </strong>

                          </div>

                          <div className="admin-badge-activo">
                            Activo en mapa
                          </div>

                        </div>


                        <img
                          className="admin-reporte-imagen"

                          src={
                            `/api${reporte.imagen_url}`
                          }

                          alt="Evidencia"
                        />


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
                                {reporte.yolo_clase || '-'}
                              </strong>

                            </div>


                            <div>

                              <span>
                                Confianza
                              </span>

                              <strong>

                                {
                                  reporte.yolo_confianza !==
                                  null

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


                            <div>

                              <span>
                                Ubicación
                              </span>

                              <strong>

                                {
                                  reporte.origen_ubicacion ===
                                  'manual'
                                    ? 'Manual · aproximada'
                                    : 'GPS'
                                }

                              </strong>

                            </div>


                            <div>

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


                            <div>

                              <span>
                                Validado
                              </span>

                              <strong>

                                {
                                  formatearFechaReporte(
                                    reporte.fecha_validacion
                                  )
                                }

                              </strong>

                            </div>


                          </div>


                          <div className="admin-activo-aviso">

                            🔥

                            <div>

                              <strong>
                                Visible en el mapa público
                              </strong>

                              Marca como resuelto cuando el
                              evento ya no corresponda mostrarse.

                            </div>

                          </div>


                          <div className="admin-reporte-acciones admin-reporte-acciones-unica">

                            <button
                              className="admin-boton-resolver"

                              onClick={() =>
                                resolverReporte(
                                  reporte.id_reporte
                                )
                              }
                            >

                              ✓ Marcar como resuelto

                            </button>

                          </div>


                        </div>


                      </article>

                    )
                  )
                }


              </div>

            )
          }


          {/* =================================================
              HISTORIAL
              ================================================= */}

          {
            vista ===
            'historial'
            && (

              <>

                <div className="admin-historial-filtros">


                  <button
                    className={
                      filtroHistorial ===
                      'todos'
                        ? 'admin-filtro-activo'
                        : ''
                    }

                    onClick={() =>
                      setFiltroHistorial(
                        'todos'
                      )
                    }
                  >

                    Todos
                    <span>
                      {historial.length}
                    </span>

                  </button>


                  <button
                    className={
                      filtroHistorial ===
                      'resuelto'
                        ? 'admin-filtro-activo'
                        : ''
                    }

                    onClick={() =>
                      setFiltroHistorial(
                        'resuelto'
                      )
                    }
                  >

                    Resueltos
                    <span>
                      {resueltos.length}
                    </span>

                  </button>


                  <button
                    className={
                      filtroHistorial ===
                      'rechazado'
                        ? 'admin-filtro-activo'
                        : ''
                    }

                    onClick={() =>
                      setFiltroHistorial(
                        'rechazado'
                      )
                    }
                  >

                    Rechazados
                    <span>
                      {rechazados.length}
                    </span>

                  </button>


                </div>


                <div className="admin-reportes-grid">


                  {
                    historialFiltrado.map(

                      reporte => {

                        const resuelto =
                          reporte.estado ===
                          'resuelto'


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
                                  #{reporte.id_reporte}
                                </strong>

                              </div>


                              <div
                                className={
                                  resuelto
                                    ? 'admin-badge-resuelto'
                                    : 'admin-badge-rechazado'
                                }
                              >

                                {
                                  resuelto
                                    ? 'Resuelto'
                                    : 'Rechazado'
                                }

                              </div>


                            </div>


                            <img
                              className="admin-reporte-imagen"

                              src={
                                `/api${reporte.imagen_url}`
                              }

                              alt="Evidencia"
                            />


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
                                    {reporte.yolo_clase || '-'}
                                  </strong>

                                </div>


                                <div>

                                  <span>
                                    Confianza
                                  </span>

                                  <strong>

                                    {
                                      reporte.yolo_confianza !==
                                      null

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


                                <div>

                                  <span>
                                    Ubicación
                                  </span>

                                  <strong>

                                    {
                                      reporte.origen_ubicacion ===
                                      'manual'
                                        ? 'Manual · aproximada'
                                        : 'GPS'
                                    }

                                  </strong>

                                </div>


                                <div>

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


                                <div>

                                  <span>
                                    Cierre
                                  </span>

                                  <strong>

                                    {
                                      resuelto
                                        ? formatearFechaReporte(
                                            reporte.fecha_resolucion
                                          )
                                        : 'Rechazado'
                                    }

                                  </strong>

                                </div>


                              </div>


                            </div>


                          </article>

                        )

                      }
                    )
                  }


                </div>


              </>

            )
          }


          {/* =================================================
              ESTADO DEL SISTEMA
              ================================================= */}

          {
            vista ===
            'sistema'
            && (

              <>

                <div className="admin-system-general">


                  <div>

                    <span>
                      Estado general
                    </span>

                    <strong
                      className={
                        estadoSistema?.status ===
                        'ok'
                          ? 'admin-status-ok-text'
                          : 'admin-status-error-text'
                      }
                    >

                      {
                        cargandoSistema
                          ? 'Comprobando...'
                          : estadoSistema?.status ===
                            'ok'
                              ? '● Sistema operativo'
                              : '● Sistema con incidencias'
                      }

                    </strong>

                  </div>


                  <div>

                    <span>
                      Última comprobación
                    </span>

                    <strong>

                      {
                        formatearComprobacion(
                          estadoSistema?.checked_at
                        )
                      }

                    </strong>

                  </div>


                </div>


                {
                  errorSistema && (

                    <div className="admin-panel-error">
                      {errorSistema}
                    </div>

                  )
                }


                <h3 className="admin-subtitulo">
                  Servicios
                </h3>


                <div className="admin-system-grid">


                  {
                    Object.values(
                      estadoSistema?.services ||
                      {}
                    ).map(
                      servicio => (

                        <div
                          className="admin-system-card"
                          key={
                            servicio.name
                          }
                        >

                          <div className="admin-system-card-header">

                            <span className="admin-system-icon">
                              ⚙
                            </span>


                            <span
                              className={
                                servicio.status ===
                                'ok'
                                  ? 'admin-status-dot admin-status-ok'
                                  : 'admin-status-dot admin-status-error'
                              }
                            />

                          </div>


                          <strong>
                            {servicio.name}
                          </strong>


                          <p>
                            {servicio.description}
                          </p>


                          <span
                            className={
                              servicio.status ===
                              'ok'
                                ? 'admin-system-operativo'
                                : 'admin-system-no-disponible'
                            }
                          >

                            {
                              servicio.status ===
                              'ok'
                                ? 'Operativo'
                                : 'No disponible'
                            }

                          </span>


                        </div>

                      )
                    )
                  }


                </div>


                <h3 className="admin-subtitulo admin-subtitulo-separado">
                  Modelos de inteligencia artificial
                </h3>


                <div className="admin-model-grid">


                  {
                    Object.values(
                      estadoSistema?.models ||
                      {}
                    ).map(
                      modelo => (

                        <div
                          className="admin-model-card"
                          key={
                            modelo.name
                          }
                        >


                          <div className="admin-model-icon">
                            🤖
                          </div>


                          <div className="admin-model-info">

                            <span>
                              Modelo
                            </span>

                            <strong>
                              {modelo.name}
                            </strong>

                            <b>
                              {modelo.technology}
                            </b>

                            <p>
                              {modelo.description}
                            </p>

                          </div>


                          <div
                            className={
                              modelo.status ===
                              'ok'
                                ? 'admin-model-status admin-model-ok'
                                : 'admin-model-status admin-model-error'
                            }
                          >

                            {
                              modelo.status ===
                              'ok'
                                ? '● Disponible'
                                : '● No disponible'
                            }

                          </div>


                        </div>

                      )
                    )
                  }


                </div>


              </>

            )
          }


          {/* =================================================
              ANÁLISIS
              ================================================= */}

          {
            vista ===
            'analisis'
            && (

              <>

                <div className="admin-analisis-seccion">

                  <h3>
                    Uso del sistema de riesgo
                  </h3>


                  {
                    errorEstadisticasRiesgo && (

                      <div className="admin-panel-error">
                        {errorEstadisticasRiesgo}
                      </div>

                    )
                  }


                  {
                    cargandoEstadisticasRiesgo
                    &&
                    !estadisticasRiesgo
                      ? (

                        <p>
                          Cargando estadísticas...
                        </p>

                      )
                      : (

                        <div className="admin-analisis-grid">


                          <div className="admin-analisis-card">

                            <span>
                              Consultas realizadas
                            </span>

                            <strong>
                              {
                                estadisticasRiesgo
                                  ?.consultas_total
                                ??
                                0
                              }
                            </strong>

                            <p>
                              Consultas territoriales de usuarios
                            </p>

                          </div>


                          <div className="admin-analisis-card">

                            <span>
                              Consultas de hoy
                            </span>

                            <strong>
                              {
                                estadisticasRiesgo
                                  ?.consultas_hoy
                                ??
                                0
                              }
                            </strong>

                            <p>
                              Consultas realizadas durante el día
                            </p>

                          </div>


                          <div className="admin-analisis-card">

                            <span>
                              Inferencias registradas
                            </span>

                            <strong>
                              {
                                estadisticasRiesgo
                                  ?.inferencias_total
                                ??
                                0
                              }
                            </strong>

                            <p>
                              Resultados almacenados del modelo de riesgo
                            </p>

                          </div>


                          <div className="admin-analisis-card">

                            <span>
                              Comuna más consultada
                            </span>

                            <strong>
                              {
                                estadisticasRiesgo
                                  ?.comuna_mas_consultada
                                ||
                                '-'
                              }
                            </strong>

                            <p>
                              {
                                estadisticasRiesgo
                                  ?.comuna_mas_consultada
                                  ? `${
                                      estadisticasRiesgo
                                        .comuna_mas_consultada_total
                                    } consulta${
                                      estadisticasRiesgo
                                        .comuna_mas_consultada_total ===
                                      1
                                        ? ''
                                        : 's'
                                    }`
                                  : 'Sin consultas registradas'
                              }
                            </p>

                          </div>


                        </div>

                      )
                  }

                </div>


                <div className="admin-analisis-grid">


                  <div className="admin-analisis-card">

                    <span>
                      Reportes recibidos
                    </span>

                    <strong>
                      {totalReportes}
                    </strong>

                    <p>
                      Total registrado en el sistema
                    </p>

                  </div>


                  <div className="admin-analisis-card">

                    <span>
                      Confirmados
                    </span>

                    <strong>
                      {confirmadosHistoricos}
                    </strong>

                    <p>
                      Activos + resueltos
                    </p>

                  </div>


                  <div className="admin-analisis-card">

                    <span>
                      Rechazados
                    </span>

                    <strong>
                      {rechazados.length}
                    </strong>

                    <p>
                      No publicados en el mapa
                    </p>

                  </div>


                  <div className="admin-analisis-card">

                    <span>
                      Tasa de confirmación
                    </span>

                    <strong>
                      {tasaConfirmacion.toFixed(1)}%
                    </strong>

                    <p>
                      Sobre reportes ya decididos
                    </p>

                  </div>


                  <div className="admin-analisis-card">

                    <span>
                      Tiempo medio de cierre
                    </span>

                    <strong>
                      {
                        formatearPromedioHoras(
                          promedioResolucion
                        )
                      }
                    </strong>

                    <p>
                      Desde validación hasta resolución
                    </p>

                  </div>


                  <div className="admin-analisis-card">

                    <span>
                      Posibles duplicados
                    </span>

                    <strong>
                      {totalDuplicados}
                    </strong>

                    <p>
                      Detectados mediante pHash
                    </p>

                  </div>


                </div>


                <div className="admin-analisis-seccion">


                  <h3>
                    Estado de los reportes
                  </h3>


                  <div className="admin-barra-fila">

                    <span>
                      Pendientes
                    </span>

                    <div className="admin-barra-track">

                      <div
                        className="admin-barra-fill"
                        style={{
                          width:
                            `${porcentaje(
                              pendientes.length
                            )}%`
                        }}
                      />

                    </div>

                    <b>
                      {pendientes.length}
                    </b>

                  </div>


                  <div className="admin-barra-fila">

                    <span>
                      Activos
                    </span>

                    <div className="admin-barra-track">

                      <div
                        className="admin-barra-fill"
                        style={{
                          width:
                            `${porcentaje(
                              activos.length
                            )}%`
                        }}
                      />

                    </div>

                    <b>
                      {activos.length}
                    </b>

                  </div>


                  <div className="admin-barra-fila">

                    <span>
                      Resueltos
                    </span>

                    <div className="admin-barra-track">

                      <div
                        className="admin-barra-fill"
                        style={{
                          width:
                            `${porcentaje(
                              resueltos.length
                            )}%`
                        }}
                      />

                    </div>

                    <b>
                      {resueltos.length}
                    </b>

                  </div>


                  <div className="admin-barra-fila">

                    <span>
                      Rechazados
                    </span>

                    <div className="admin-barra-track">

                      <div
                        className="admin-barra-fill"
                        style={{
                          width:
                            `${porcentaje(
                              rechazados.length
                            )}%`
                        }}
                      />

                    </div>

                    <b>
                      {rechazados.length}
                    </b>

                  </div>


                </div>


                <div className="admin-analisis-doble">


                  <div className="admin-analisis-seccion">

                    <h3>
                      Origen de ubicación
                    </h3>


                    <div className="admin-analisis-detalle">

                      <span>
                        GPS
                      </span>

                      <strong>
                        {totalGps}
                      </strong>

                    </div>


                    <div className="admin-analisis-detalle">

                      <span>
                        Selección manual
                      </span>

                      <strong>
                        {totalManual}
                      </strong>

                    </div>


                  </div>


                  <div className="admin-analisis-seccion">

                    <h3>
                      Detección mediante IA
                    </h3>


                    <div className="admin-analisis-detalle">

                      <span>
                        Humo detectado
                      </span>

                      <strong>
                        {deteccionesHumo}
                      </strong>

                    </div>


                    <div className="admin-analisis-detalle">

                      <span>
                        Fuego detectado
                      </span>

                      <strong>
                        {deteccionesFuego}
                      </strong>

                    </div>


                  </div>


                </div>


              </>

            )
          }


        </main>


      </div>


    </div>

  )
}

export default AdminReportes
