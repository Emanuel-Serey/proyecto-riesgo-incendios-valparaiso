export function clasificarPrecisionGps(
  precision
) {
  const valor = Number(
    precision
  )


  if (
    !Number.isFinite(valor) ||
    valor < 0
  ) {
    return {
      nivel:
        'desconocida',

      etiqueta:
        'Precisión desconocida',

      icono:
        '?',

      aptaCorroboracion:
        false,

      descripcion:
        'No fue posible determinar la precisión de la ubicación.',

      descripcionAdmin:
        'No fue posible determinar la precisión GPS informada por el dispositivo. Este reporte no se utiliza como corroboración geográfica automática.',
    }
  }


  if (
    valor <= 100
  ) {
    return {
      nivel:
        'buena',

      etiqueta:
        'Buena precisión',

      icono:
        '✓',

      aptaCorroboracion:
        true,

      descripcion:
        'La ubicación obtenida tiene una precisión adecuada para el reporte.',

      descripcionAdmin:
        'La ubicación reportada presenta una precisión GPS adecuada.',
    }
  }


  if (
    valor <= 500
  ) {
    return {
      nivel:
        'moderada',

      etiqueta:
        'Precisión moderada',

      icono:
        '!',

      aptaCorroboracion:
        true,

      descripcion:
        'La ubicación es aproximada. Si es posible, intenta actualizarla antes de enviar.',

      descripcionAdmin:
        'La ubicación reportada tiene una precisión GPS moderada. Puede utilizarse como referencia geográfica, pero considera esta incertidumbre antes de confirmar.',
    }
  }


  return {
    nivel:
      'baja',

    etiqueta:
      'Ubicación poco precisa',

    icono:
      '!',

    aptaCorroboracion:
      false,

    descripcion:
      'La ubicación podría estar alejada del lugar real. Intenta actualizarla o seleccionar el lugar del incendio en el mapa.',

    descripcionAdmin:
      'La ubicación reportada presenta baja precisión GPS y podría estar alejada del lugar real. No se utiliza como corroboración geográfica automática.',
  }
}


export function formatearPrecisionGps(
  precision
) {
  const valor = Number(
    precision
  )


  if (
    !Number.isFinite(valor)
  ) {
    return '-'
  }


  return `${Math.round(
    valor
  )} m`
}