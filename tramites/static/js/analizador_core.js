// Funciones puras del analizador de requisitos (reutilizables y testeables en Node).

export const MS_PER_DAY = 1000 * 60 * 60 * 24;

export function parseISODate(value) {
  if (!value) {
    return null;
  }
  const [yearStr, monthStr, dayStr] = value.split("-");
  const year = Number(yearStr);
  const month = Number(monthStr);
  const day = Number(dayStr);
  if (!Number.isFinite(year) || !Number.isFinite(month) || !Number.isFinite(day)) {
    return null;
  }
  return new Date(Date.UTC(year, month - 1, day));
}

export function addYears(date, years) {
  const clone = new Date(date.getTime());
  clone.setUTCFullYear(clone.getUTCFullYear() + years);
  return clone;
}

export function addDays(date, days) {
  const clone = new Date(date.getTime());
  clone.setUTCDate(clone.getUTCDate() + days);
  return clone;
}

export function calculateInclusiveDays(startDate, endDate) {
  if (!(startDate instanceof Date) || !(endDate instanceof Date)) {
    return 0;
  }
  const diff = endDate.getTime() - startDate.getTime();
  if (diff < 0) {
    return 0;
  }
  return Math.floor(diff / MS_PER_DAY) + 1;
}

export function calculateValidDays(startDate, endDate, ingresoDate) {
  if (!(startDate instanceof Date) || !(endDate instanceof Date) || !(ingresoDate instanceof Date)) {
    return 0;
  }
  if (endDate < ingresoDate) {
    return 0;
  }
  const effectiveStart = startDate <= ingresoDate ? addDays(ingresoDate, 1) : startDate;
  if (effectiveStart > endDate) {
    return 0;
  }
  return calculateInclusiveDays(effectiveStart, endDate);
}

export function daysBetween(start, end) {
  if (!(start instanceof Date) || !(end instanceof Date)) {
    return 0;
  }
  const diff = end.getTime() - start.getTime();
  return diff <= 0 ? 0 : Math.ceil(diff / MS_PER_DAY);
}

export function pluralize(word, value) {
  return Math.abs(value) === 1 ? word : `${word}s`;
}

export function describeDuration(start, end) {
  if (!(start instanceof Date) || !(end instanceof Date)) {
    return "0 días";
  }
  let years = end.getUTCFullYear() - start.getUTCFullYear();
  let months = end.getUTCMonth() - start.getUTCMonth();
  let days = end.getUTCDate() - start.getUTCDate();
  if (days < 0) {
    months -= 1;
    const prevMonthIndex = (end.getUTCMonth() - 1 + 12) % 12;
    const prevYear = end.getUTCMonth() === 0 ? end.getUTCFullYear() - 1 : end.getUTCFullYear();
    days += daysInMonth(prevYear, prevMonthIndex);
  }
  if (months < 0) {
    years -= 1;
    months += 12;
  }
  const parts = [];
  if (years > 0) {
    parts.push(`${years} ${pluralize("año", years)}`);
  }
  if (months > 0) {
    parts.push(`${months} ${pluralize("mes", months)}`);
  }
  if (!parts.length) {
    parts.push(`${Math.max(days, 0)} ${pluralize("día", Math.max(days, 0))}`);
  }
  return parts.join(" y ");
}

function daysInMonth(year, monthIndex) {
  const date = new Date(Date.UTC(year, monthIndex + 1, 0));
  return date.getUTCDate();
}

export function evaluateYearsRequirement(ingresoDate, analisisDate, minYearsRequired) {
  if (!ingresoDate || !analisisDate) {
    return {
      ready: false,
      valid: false,
      badgeClass: "badge--warning",
      badgeText: "Pendiente",
      description: "Captura la fecha de ingreso y la fecha de análisis.",
    };
  }
  if (analisisDate < ingresoDate) {
    return {
      ready: false,
      valid: false,
      badgeClass: "badge--danger",
      badgeText: "Inconsistente",
      description: "La fecha de análisis no puede ser anterior a la fecha de ingreso.",
    };
  }
  const minDate = addYears(ingresoDate, minYearsRequired);
  const valid = analisisDate >= minDate;
  const pendingDays = daysBetween(analisisDate, minDate);
  const description = valid
    ? `Cumple: ${describeDuration(ingresoDate, analisisDate)} de servicio.`
    : `Faltan ${pendingDays} ${pluralize("día", pendingDays)} para llegar al mínimo.`;
  return {
    ready: true,
    valid,
    badgeClass: valid ? "badge--success" : "badge--danger",
    badgeText: valid ? "Cumple" : "No cumple",
    description,
  };
}

export function evaluateLicensesRequirement(ingresoDate, licencias, requiredDays) {
  if (!ingresoDate) {
    return {
      ready: false,
      valid: false,
      validDays: 0,
      badgeClass: "badge--warning",
      badgeText: "Pendiente",
      description: "Captura la fecha de ingreso para validar los días de licencia.",
    };
  }
  const validDays = licencias.reduce((total, licencia) => {
    const startDate = parseISODate(licencia.start);
    const endDate = parseISODate(licencia.end);
    return total + calculateValidDays(startDate, endDate, ingresoDate);
  }, 0);
  const valid = validDays >= requiredDays && licencias.length > 0;
  let description;
  if (!licencias.length) {
    description = "No hay licencias capturadas.";
  } else if (valid) {
    description = `Cumple con ${validDays} ${pluralize("día", validDays)} válidos.`;
  } else {
    const remaining = Math.max(requiredDays - validDays, 0);
    description = `Faltan ${remaining} ${pluralize("día", remaining)} válidos.`;
  }
  return {
    ready: licencias.length > 0,
    valid,
    validDays,
    badgeClass: !licencias.length ? "badge--warning" : valid ? "badge--success" : "badge--danger",
    badgeText: !licencias.length ? "Pendiente" : valid ? "Cumple" : "No cumple",
    description,
  };
}

export function buildLicenseStatus(startDate, endDate, ingresoDate) {
  if (!(startDate instanceof Date) || !(endDate instanceof Date)) {
    return {
      badge: "badge--danger",
      label: "Error",
      detail: "Fechas incompletas.",
    };
  }
  if (!(ingresoDate instanceof Date)) {
    return {
      badge: "badge--warning",
      label: "Pendiente",
      detail: "Ingresa la fecha de ingreso para validar.",
    };
  }
  if (endDate < ingresoDate) {
    return {
      badge: "badge--danger",
      label: "No válido",
      detail: "Todo el periodo es anterior a la fecha de ingreso.",
    };
  }
  if (startDate <= ingresoDate && endDate >= ingresoDate) {
    return {
      badge: "badge--warning",
      label: "Parcial",
      detail: "Solo se contabilizan los días posteriores a la fecha de ingreso.",
    };
  }
  return {
    badge: "badge--success",
    label: "Válido",
    detail: "El periodo completo ocurre después de la fecha de ingreso.",
  };
}
