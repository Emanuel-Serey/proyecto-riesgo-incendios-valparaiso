import {
  useEffect,
  useState,
} from 'react'

import './ImagenAmpliable.css'


const SELECTOR_IMAGEN = [
  '.admin-reporte-imagen',
  '.reporte-popup-imagen',
].join(', ')


function ImagenAmpliable() {

  const [
    imagenAbierta,
    setImagenAbierta
  ] = useState(null)


  // =========================================================
  // ABRIR IMAGEN DESDE CUALQUIER REPORTE
  // =========================================================

  useEffect(() => {

    const manejarClick =
      evento => {

        if (
          !(
            evento.target
            instanceof
            Element
          )
        ) {

          return

        }


        const imagen =
          evento.target.closest(
            SELECTOR_IMAGEN
          )


        if (
          !imagen
          ||
          !(
            imagen
            instanceof
            HTMLImageElement
          )
        ) {

          return

        }


        evento.preventDefault()

        evento.stopPropagation()


        setImagenAbierta({

          src:
            imagen.src,

          alt:
            imagen.alt ||
            'Evidencia del reporte ciudadano',

        })

      }


    document.addEventListener(
      'click',
      manejarClick
    )


    return () => {

      document.removeEventListener(
        'click',
        manejarClick
      )

    }

  }, [])


  // =========================================================
  // CERRAR CON ESC
  // =========================================================

  useEffect(() => {

    const manejarTeclado =
      evento => {

        if (
          evento.key ===
          'Escape'
        ) {

          setImagenAbierta(
            null
          )

        }

      }


    document.addEventListener(
      'keydown',
      manejarTeclado
    )


    return () => {

      document.removeEventListener(
        'keydown',
        manejarTeclado
      )

    }

  }, [])


  // =========================================================
  // BLOQUEAR SCROLL AL ABRIR
  // =========================================================

  useEffect(() => {

    if (
      !imagenAbierta
    ) {

      return undefined

    }


    const overflowAnterior =
      document.body.style.overflow


    document.body.style.overflow =
      'hidden'


    return () => {

      document.body.style.overflow =
        overflowAnterior

    }

  }, [
    imagenAbierta
  ])


  // =========================================================
  // CERRAR
  // =========================================================

  const cerrarImagen = () => {

    setImagenAbierta(
      null
    )

  }


  // =========================================================
  // SIN IMAGEN ABIERTA
  // =========================================================

  if (
    !imagenAbierta
  ) {

    return null

  }


  // =========================================================
  // VISOR
  // =========================================================

  return (

    <div
      className="visor-imagen-fondo"

      role="dialog"

      aria-modal="true"

      aria-label="Imagen ampliada del reporte"

      onMouseDown={
        evento => {

          if (
            evento.target ===
            evento.currentTarget
          ) {

            cerrarImagen()

          }

        }
      }
    >


      <button
        type="button"

        className="visor-imagen-cerrar"

        onClick={
          cerrarImagen
        }

        aria-label="Cerrar imagen ampliada"

        title="Cerrar"
      >

        ×

      </button>


      <div
        className="visor-imagen-contenido"

        onMouseDown={
          evento => {

            evento.stopPropagation()

          }
        }
      >


        <img
          src={
            imagenAbierta.src
          }

          alt={
            imagenAbierta.alt
          }
        />


      </div>


      <div className="visor-imagen-ayuda">

        Presiona Esc o haz clic fuera de la imagen para cerrar

      </div>


    </div>

  )

}


export default ImagenAmpliable