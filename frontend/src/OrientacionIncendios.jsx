import './OrientacionIncendios.css'


const CANALES_PRINCIPALES = [
  {
    nombre:
      'CONAF',

    numero:
      '130',

    descripcion:
      'Incendios forestales',

    icono:
      '🌲',
  },

  {
    nombre:
      'Bomberos',

    numero:
      '132',

    descripcion:
      'Emergencias',

    icono:
      '🚒',
  },
]


const CANALES_ADICIONALES = [
  {
    nombre:
      'Carabineros',

    numero:
      '133',

    descripcion:
      'Emergencias',

    icono:
      '🚓',
  },

  {
    nombre:
      'PDI',

    numero:
      '134',

    descripcion:
      'Emergencias',

    icono:
      '🛡️',
  },
]


function CanalOficial({
  nombre,
  numero,
  descripcion,
  icono,
}) {

  return (

    <div
      className="orientacion-canal orientacion-canal-estatico"

      title={
        `Teléfono de emergencia ${numero}`
      }
    >

      <span className="orientacion-canal-icono">

        {icono}

      </span>


      <span className="orientacion-canal-contenido">

        <span className="orientacion-canal-organismo">

          {nombre}

        </span>


        <strong>

          {numero}

        </strong>


        <small>

          {descripcion}

        </small>

      </span>

    </div>

  )

}


function OrientacionCompacta() {

  return (

    <section className="orientacion-compacta-simple">


      <div className="orientacion-compacta-titulo">

        <span>
          🔥
        </span>


        <div>

          <strong>
            Si observas humo o fuego
          </strong>


          <small>
            Prioriza tu seguridad y utiliza los canales oficiales.
          </small>

        </div>

      </div>


      <div className="orientacion-mensaje-rapido">

        Mantente alejado del avance del fuego y del humo.
        No te acerques únicamente para obtener fotografías
        o videos. Avisa lo antes posible a CONAF o Bomberos
        e indica la ubicación del sector. Si recibes un
        mensaje SAE o una instrucción de evacuación,
        evacúa de inmediato y sigue las indicaciones
        de las autoridades.

      </div>


      <div className="orientacion-compacta-telefonos">


        <div>

          <span>
            🌲
          </span>


          <span>

            <small>
              CONAF
            </small>

            <strong>
              130
            </strong>

          </span>

        </div>


        <div>

          <span>
            🚒
          </span>


          <span>

            <small>
              Bomberos
            </small>

            <strong>
              132
            </strong>

          </span>

        </div>


      </div>


      <a
        className="orientacion-compacta-senapred"

        href="https://www.senapred.cl/incendios-forestales/"

        target="_blank"

        rel="noreferrer"
      >

        <span>
          ⚠️ SENAPRED
        </span>


        <span>
          Información oficial ↗
        </span>

      </a>


    </section>

  )

}


function OrientacionIncendios({
  contexto,
  nivelRiesgo = null,
  compacto = false,
}) {

  const esRiesgo =
    contexto ===
    'riesgo'


  const esReporte =
    contexto ===
    'reporte'


  if (
    esRiesgo
    &&
    nivelRiesgo !==
    'Alto'
  ) {

    return null

  }


  if (
    !esRiesgo
    &&
    !esReporte
  ) {

    return null

  }


  if (
    compacto
  ) {

    return (
      <OrientacionCompacta />
    )

  }


  const recomendaciones =
    esRiesgo

      ? [

          'Revisa con tu hogar las vías de evacuación y considera una ruta alternativa por si una salida queda bloqueada.',

          'Mantén el teléfono cargado y permanece atento a información oficial y mensajes del Sistema de Alerta de Emergencia (SAE).',

          'Ten preparado un kit básico con agua, documentos importantes, medicamentos, linterna y cargador portátil.',

          'Si vives cerca de vegetación, mantén despejados techos, canaletas y el entorno inmediato de hojas, ramas y otros materiales que puedan arder.',

        ]

      : [

          'Aléjate del avance del fuego y del humo. No te acerques únicamente para obtener fotografías o videos.',

          'Avisa lo antes posible a CONAF o Bomberos e indica la ubicación y referencias que permitan llegar al sector.',

          'Si recibes un mensaje SAE o una instrucción de evacuación, evacúa de inmediato y sigue las indicaciones de las autoridades.',

          'Mantente informado mediante SENAPRED y otros canales oficiales mientras la emergencia se encuentre activa.',

        ]


  const titulo =
    esRiesgo
      ? 'Prepárate ante condiciones de riesgo alto'
      : 'Si observas humo o fuego'


  const descripcion =
    esRiesgo

      ? (
          'El nivel de riesgo evaluado para esta comuna es alto. ' +
          'Estas medidas pueden ayudarte a estar mejor preparado.'
        )

      : (
          'Prioriza tu seguridad y utiliza los canales oficiales ' +
          'si existe una emergencia activa.'
        )


  return (

    <section
      className={
        `orientacion-incendios ${
          esRiesgo
            ? 'orientacion-riesgo'
            : 'orientacion-reporte'
        }`
      }
    >


      <div className="orientacion-cabecera">


        <div className="orientacion-icono">

          {
            esRiesgo
              ? '⚠️'
              : '🔥'
          }

        </div>


        <div>

          <span className="orientacion-etiqueta">

            {
              esRiesgo
                ? 'Recomendaciones preventivas'
                : 'Información de emergencia'
            }

          </span>


          <h3>

            {titulo}

          </h3>


          <p>

            {descripcion}

          </p>

        </div>


      </div>


      <ul className="orientacion-recomendaciones">

        {
          recomendaciones.map(
            recomendacion => (

              <li
                key={
                  recomendacion
                }
              >

                {recomendacion}

              </li>

            )
          )
        }

      </ul>


      <div className="orientacion-canales">


        <div className="orientacion-canales-titulo">

          Canales oficiales

        </div>


        <div className="orientacion-canales-grid">

          {
            CANALES_PRINCIPALES.map(
              canal => (

                <CanalOficial
                  key={
                    canal.numero
                  }

                  {...canal}
                />

              )
            )
          }


          {
            CANALES_ADICIONALES.map(
              canal => (

                <CanalOficial
                  key={
                    canal.numero
                  }

                  {...canal}
                />

              )
            )
          }

        </div>


        <a
          className="orientacion-senapred"

          href="https://www.senapred.cl/incendios-forestales/"

          target="_blank"

          rel="noreferrer"
        >

          <span>
            ⚠️
          </span>


          <span>

            <strong>
              SENAPRED
            </strong>

            <small>
              Ver información y recomendaciones oficiales
            </small>

          </span>


          <span className="orientacion-enlace-icono">
            ↗
          </span>

        </a>


      </div>


      <div className="orientacion-nota">

        {
          esRiesgo
            ? (
                'La predicción de riesgo de esta plataforma no constituye una alerta oficial de emergencia.'
              )
            : (
                'El reporte realizado en esta plataforma no reemplaza la comunicación con los organismos oficiales de emergencia.'
              )
        }

      </div>


    </section>

  )

}


export default OrientacionIncendios