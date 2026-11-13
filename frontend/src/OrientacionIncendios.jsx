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

        Mantén una distancia segura y evita acercarte
        únicamente para obtener fotografías o videos.
        Si la situación representa un peligro, informa
        a CONAF o Bomberos e indica la ubicación del sector.

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

          'Evita quemas, fogatas y otras fuentes de fuego cerca de vegetación.',

          'Evita trabajos que puedan generar chispas en sectores con vegetación seca, especialmente durante jornadas de mayor riesgo.',

          'Mantén despejado el entorno de hojas, ramas secas y otros materiales que puedan facilitar la propagación del fuego.',

          'Mantente informado mediante los canales oficiales y presta atención a las condiciones del sector.',

        ]

      : [

          'Mantén una distancia segura del fuego y del humo. No te acerques únicamente para obtener fotografías o videos.',

          'Si la situación representa un peligro, informa a CONAF o Bomberos e indica la ubicación y referencias del sector.',

          'Si recibes una instrucción oficial de evacuación o un mensaje SAE, sigue las indicaciones de las autoridades.',

          'Mantente informado mediante SENAPRED y los organismos oficiales mientras la situación se encuentre activa.',

        ]


  const titulo =
    esRiesgo
      ? 'Refuerza las medidas de prevención'
      : 'Si observas humo o fuego'


  const descripcion =
    esRiesgo

      ? (
          'Las condiciones evaluadas para esta comuna corresponden a un nivel de riesgo alto. ' +
          'Esto no significa que exista un incendio activo, pero es recomendable reforzar las medidas preventivas.'
        )

      : (
          'Si efectivamente observas humo o fuego, prioriza tu seguridad ' +
          'y utiliza los canales oficiales cuando corresponda.'
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
                : 'Orientación de seguridad'
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