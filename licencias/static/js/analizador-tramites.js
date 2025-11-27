const MS_PER_DAY = 1000 * 60 * 60 * 24;
const BADGE_VARIANTS = ["badge--success", "badge--warning", "badge--danger", "badge--neutral", "badge--gold"];

document.addEventListener("DOMContentLoaded", () => {
  initCollapsibles();
  initCollapsibleShortcuts();
  initNormativityModal();
  const root = document.getElementById("eligibility-tool");
  if (!root) {
    return;
  }

  const minYears = Number(root.dataset.minYears || "15");
  const ingresoInput = document.getElementById("fecha-ingreso");
  const analisisInput = document.getElementById("fecha-analisis");
  const regimenSelect = document.getElementById("regimen-licencia");
  const form = document.getElementById("licencia-form");
  const inicioInput = document.getElementById("licencia-inicio");
  const finInput = document.getElementById("licencia-fin");
  const diasInput = document.getElementById("licencia-dias");
  const guardarBtn = document.getElementById("guardar-licencia");
  const cancelarBtn = document.getElementById("cancelar-edicion");
  const limpiarBtn = document.getElementById("limpiar-licencias");
  const feedbackBox = document.getElementById("licencia-feedback");
  const licenciasBody = document.getElementById("licencias-tbody");
  const totalDiasEl = root.querySelector("[data-total-dias]");
  const requiredDaysEl = root.querySelector("[data-required-days]");
  const validDaysIndicatorEl = root.querySelector("[data-valid-days-indicator]");
  const remainingDaysEls = root.querySelectorAll("[data-remaining-days]");
  const finalAlert = document.getElementById("resultado-final");

  const requirementNodes = {
    years: root.querySelector('[data-requirement="years"]'),
    licenses: root.querySelector('[data-requirement="licenses"]'),
  };

  const state = {
    licencias: [],
    editingId: null,
  };

  form?.addEventListener("submit", (event) => {
    event.preventDefault();
    hideFeedback();
    const startValue = inicioInput?.value || "";
    const endValue = finInput?.value || "";
    const startDate = parseISODate(startValue);
    const endDate = parseISODate(endValue);
    if (!startDate || !endDate) {
      showFeedback("Completa las dos fechas de la licencia.");
      return;
    }
    if (endDate < startDate) {
      showFeedback("La fecha de término no puede ser anterior a la de inicio.");
      return;
    }
    if (state.editingId) {
      const idx = state.licencias.findIndex((item) => item.id === state.editingId);
      if (idx !== -1) {
        state.licencias[idx] = {
          ...state.licencias[idx],
          start: startValue,
          end: endValue,
        };
      }
    } else {
      state.licencias.push({
        id: generateId(),
        start: startValue,
        end: endValue,
      });
    }
    state.licencias.sort((a, b) => a.start.localeCompare(b.start));
    resetForm();
    renderLicencias();
    updateSummary();
  });

  limpiarBtn?.addEventListener("click", () => {
    if (!state.licencias.length) {
      return;
    }
    const shouldClear = window.confirm("¿Deseas eliminar todas las licencias capturadas?");
    if (!shouldClear) {
      return;
    }
    state.licencias = [];
    resetForm();
    renderLicencias();
    updateSummary();
  });

  cancelarBtn?.addEventListener("click", () => {
    resetForm();
  });

  licenciasBody?.addEventListener("click", (event) => {
    const button = event.target instanceof HTMLElement ? event.target.closest("button[data-action]") : null;
    if (!button) {
      return;
    }
    const { action, id } = button.dataset;
    if (!id) {
      return;
    }
    if (action === "edit") {
      startEditing(id);
    } else if (action === "delete") {
      deleteLicense(id);
    }
  });

  [inicioInput, finInput].forEach((input) => {
    input?.addEventListener("change", updateDiasPreview);
  });

  ingresoInput?.addEventListener("change", () => {
    renderLicencias();
    updateSummary();
  });
  analisisInput?.addEventListener("change", updateSummary);
  regimenSelect?.addEventListener("change", updateSummary);

  function renderLicencias() {
    if (!licenciasBody) {
      return;
    }
    licenciasBody.innerHTML = "";
    if (!state.licencias.length) {
      const row = document.createElement("tr");
      row.className = "table__empty";
      const cell = document.createElement("td");
      cell.colSpan = 4;
      cell.textContent = "Agrega la primera licencia para iniciar los cálculos.";
      row.appendChild(cell);
      licenciasBody.appendChild(row);
      return;
    }
    const ingresoDate = parseISODate(ingresoInput?.value || "");
    const fragment = document.createDocumentFragment();
    state.licencias.forEach((licencia) => {
      const startDate = parseISODate(licencia.start);
      const endDate = parseISODate(licencia.end);
      const row = document.createElement("tr");
      const periodoCell = document.createElement("td");
      periodoCell.innerHTML = `
        <span class="table__primary">Del ${formatDate(startDate)}</span>
        <span class="table__secondary">al ${formatDate(endDate)}</span>
      `;
      const diasCell = document.createElement("td");
      const totalDays = calculateInclusiveDays(startDate, endDate);
      const validDays = ingresoDate ? calculateValidDays(startDate, endDate, ingresoDate) : 0;
      const validLabel = ingresoDate
        ? `${validDays} ${pluralize("día", validDays)} válidos`
        : "Ingresa la fecha de ingreso para validar";
      diasCell.innerHTML = `
        <span class="table__primary">${totalDays} ${pluralize("día", totalDays)}</span>
        <span class="table__secondary">${validLabel}</span>
      `;

      const statusCell = document.createElement("td");
      const statusInfo = buildLicenseStatus(startDate, endDate, ingresoDate);
      const badge = document.createElement("span");
      badge.className = `badge ${statusInfo.badge}`;
      badge.textContent = statusInfo.label;
      const statusText = document.createElement("span");
      statusText.className = "table__secondary";
      statusText.textContent = statusInfo.detail;
      statusCell.appendChild(badge);
      statusCell.appendChild(statusText);

      const actionsCell = document.createElement("td");
      actionsCell.innerHTML = `
        <div class="table-actions">
          <button type="button" class="btn btn--ghost btn--sm" data-action="edit" data-id="${licencia.id}">Editar</button>
          <button type="button" class="btn btn--ghost btn--sm" data-action="delete" data-id="${licencia.id}">Eliminar</button>
        </div>
      `;

      row.appendChild(periodoCell);
      row.appendChild(diasCell);
      row.appendChild(statusCell);
      row.appendChild(actionsCell);
      fragment.appendChild(row);
    });
    licenciasBody.appendChild(fragment);
  }

  function startEditing(id) {
    const licencia = state.licencias.find((item) => item.id === id);
    if (!licencia || !inicioInput || !finInput || !guardarBtn || !cancelarBtn) {
      return;
    }
    state.editingId = id;
    inicioInput.value = licencia.start;
    finInput.value = licencia.end;
    guardarBtn.textContent = "Guardar cambios";
    cancelarBtn.hidden = false;
    updateDiasPreview();
    inicioInput.focus();
  }

  function deleteLicense(id) {
    const licencia = state.licencias.find((item) => item.id === id);
    if (!licencia) {
      return;
    }
    const ok = window.confirm("¿Eliminar esta licencia médica?");
    if (!ok) {
      return;
    }
    state.licencias = state.licencias.filter((item) => item.id !== id);
    if (state.editingId === id) {
      resetForm();
    }
    renderLicencias();
    updateSummary();
  }

  function resetForm() {
    form?.reset();
    if (diasInput) {
      diasInput.value = "0";
    }
    state.editingId = null;
    if (guardarBtn) {
      guardarBtn.textContent = "Agregar licencia";
    }
    if (cancelarBtn) {
      cancelarBtn.hidden = true;
    }
    hideFeedback();
  }

  function updateDiasPreview() {
    if (!inicioInput || !finInput || !diasInput) {
      return;
    }
    const start = parseISODate(inicioInput.value);
    const end = parseISODate(finInput.value);
    if (!start || !end) {
      diasInput.value = "0";
      return;
    }
    const diff = calculateInclusiveDays(start, end);
    diasInput.value = String(diff);
  }

  function updateSummary() {
    const ingresoDate = parseISODate(ingresoInput?.value || "");
    const analisisDate = parseISODate(analisisInput?.value || "");
    const requiredDays = getRequiredDays();
    if (requiredDaysEl) {
      requiredDaysEl.textContent = `Meta actual: ${requiredDays} ${pluralize("día", requiredDays)} requeridos`;
    }
    const yearsResult = evaluateYearsRequirement(ingresoDate, analisisDate, minYears);
    applyRequirementStatus("years", yearsResult);

    const licensesResult = evaluateLicensesRequirement(ingresoDate, state.licencias, requiredDays);
    applyRequirementStatus("licenses", licensesResult);
    if (totalDiasEl) {
      totalDiasEl.textContent = `Total válido: ${licensesResult.validDays} ${pluralize("día", licensesResult.validDays)}`;
    }
    if (validDaysIndicatorEl) {
      validDaysIndicatorEl.textContent = `${licensesResult.validDays} / ${requiredDays} ${pluralize("día", requiredDays)} válidos`;
    }
    if (remainingDaysEls.length) {
      const remaining = Math.max(requiredDays - licensesResult.validDays, 0);
      let remainingMessage = "Captura la fecha de ingreso para calcular los días restantes.";
      if (ingresoDate instanceof Date) {
        if (!state.licencias.length) {
          remainingMessage = `Faltan ${requiredDays} ${pluralize("día", requiredDays)} por acreditar.`;
        } else if (licensesResult.valid) {
          remainingMessage = `Meta alcanzada: ${licensesResult.validDays} ${pluralize("día", licensesResult.validDays)} válidos.`;
        } else {
          remainingMessage = `Faltan ${remaining} ${pluralize("día", remaining)} válidos.`;
        }
      }
      remainingDaysEls.forEach((element) => {
        element.textContent = remainingMessage;
      });
    }
    updateFinalAlert(yearsResult, licensesResult);
  }

  function applyRequirementStatus(key, result) {
    const node = requirementNodes[key];
    if (!node) {
      return;
    }
    const badge = node.querySelector("[data-status-pill]");
    const text = node.querySelector("[data-status-text]");
    if (badge) {
      badge.textContent = result.badgeText;
      badge.classList.remove(...BADGE_VARIANTS);
      if (result.badgeClass) {
        badge.classList.add(result.badgeClass);
      }
    }
    if (text) {
      text.textContent = result.description;
    }
  }

  function updateFinalAlert(yearsResult, licensesResult) {
    if (!finalAlert) {
      return;
    }
    finalAlert.classList.remove("alert--success", "alert--danger", "alert--warning");
    if (!yearsResult.ready || !licensesResult.ready) {
      finalAlert.classList.add("alert--warning");
      finalAlert.textContent = "Captura todos los datos para determinar si el trámite es aprobado.";
      return;
    }
    if (yearsResult.valid && licensesResult.valid) {
      finalAlert.classList.add("alert--success");
      finalAlert.textContent = "Aprobado: ambos requisitos se cumplen.";
    } else {
      finalAlert.classList.add("alert--danger");
      const missing = [];
      if (!yearsResult.valid) {
        missing.push("15 años de servicio");
      }
      if (!licensesResult.valid) {
        missing.push("los días de licencia requeridos");
      }
      finalAlert.textContent = `No aprobado: falta cumplir ${missing.join(" y ")}.`;
    }
  }

  function evaluateYearsRequirement(ingresoDate, analisisDate, minYearsRequired) {
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

  function evaluateLicensesRequirement(ingresoDate, licencias, requiredDays) {
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

  function buildLicenseStatus(startDate, endDate, ingresoDate) {
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

  function calculateInclusiveDays(startDate, endDate) {
    if (!(startDate instanceof Date) || !(endDate instanceof Date)) {
      return 0;
    }
    const diff = endDate.getTime() - startDate.getTime();
    if (diff < 0) {
      return 0;
    }
    return Math.floor(diff / MS_PER_DAY) + 1;
  }

  function calculateValidDays(startDate, endDate, ingresoDate) {
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

  function addYears(date, years) {
    const clone = new Date(date.getTime());
    clone.setUTCFullYear(clone.getUTCFullYear() + years);
    return clone;
  }

  function addDays(date, days) {
    const clone = new Date(date.getTime());
    clone.setUTCDate(clone.getUTCDate() + days);
    return clone;
  }

  function describeDuration(start, end) {
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

  function daysBetween(start, end) {
    if (!(start instanceof Date) || !(end instanceof Date)) {
      return 0;
    }
    const diff = end.getTime() - start.getTime();
    return diff <= 0 ? 0 : Math.ceil(diff / MS_PER_DAY);
  }

  function getRequiredDays() {
    if (!regimenSelect) {
      return 60;
    }
    const selected = regimenSelect.options[regimenSelect.selectedIndex];
    const datasetValue = selected?.dataset?.requiredDays;
    return Number(datasetValue || "60");
  }

  function generateId() {
    return `${Date.now().toString(36)}-${Math.random().toString(16).slice(2)}`;
  }

  function showFeedback(message) {
    if (!feedbackBox) {
      return;
    }
    feedbackBox.textContent = message;
    feedbackBox.hidden = false;
  }

  function hideFeedback() {
    if (!feedbackBox) {
      return;
    }
    feedbackBox.hidden = true;
    feedbackBox.textContent = "";
  }

  function parseISODate(value) {
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

  function formatDate(date) {
    if (!(date instanceof Date)) {
      return "Fecha inválida";
    }
    const day = String(date.getUTCDate()).padStart(2, "0");
    const month = String(date.getUTCMonth() + 1).padStart(2, "0");
    const year = date.getUTCFullYear();
    return `${day}/${month}/${year}`;
  }

  function pluralize(word, value) {
    return Math.abs(value) === 1 ? word : `${word}s`;
  }

  // Inicializar vista
  renderLicencias();
  updateSummary();
});

function initCollapsibles() {
  const sections = document.querySelectorAll("[data-collapsible]");
  sections.forEach((section, index) => {
    const content = section.querySelector("[data-collapsible-content]");
    const toggle = section.querySelector("[data-collapsible-toggle]");
    if (!content || !toggle) {
      return;
    }
    const showLabel = toggle.dataset.labelShow || "Mostrar";
    const hideLabel = toggle.dataset.labelHide || "Ocultar";
    if (!content.id) {
      const baseId = section.id || `collapsible-${index + 1}`;
      content.id = `${baseId}-content`;
    }
    toggle.setAttribute("aria-controls", content.id);

    const applyState = (isOpen) => {
      const openState = Boolean(isOpen);
      content.hidden = !openState;
      toggle.textContent = openState ? hideLabel : showLabel;
      toggle.setAttribute("aria-expanded", String(openState));
      content.setAttribute("aria-hidden", String(!openState));
      section.classList.toggle("is-open", openState);
    };

    const defaultState = section.dataset.collapsibleDefault === "open";
    applyState(defaultState);
    section._setCollapsibleState = applyState;

    toggle.addEventListener("click", () => {
      applyState(content.hidden);
    });
  });
}

function initCollapsibleShortcuts() {
  const triggers = document.querySelectorAll("[data-open-collapsible]");
  if (!triggers.length) {
    return;
  }
  triggers.forEach((trigger) => {
    trigger.addEventListener("click", () => {
      const selector = trigger.dataset.openCollapsible;
      if (!selector) {
        return;
      }
      const target = document.querySelector(selector);
      if (!target) {
        return;
      }
      const setState = target._setCollapsibleState;
      const content = target.querySelector("[data-collapsible-content]");
      if (typeof setState === "function" && content?.hidden) {
        setState(true);
      }
      target.scrollIntoView({ behavior: "smooth", block: "start" });
    });
  });
}

function initNormativityModal() {
  const modal = document.getElementById("normatividad-modal");
  const triggers = document.querySelectorAll("[data-norm-template]");
  if (!modal || !triggers.length) {
    return;
  }
  const titleEl = modal.querySelector("[data-modal-title]");
  const bodyEl = modal.querySelector("[data-modal-body]");
  const overlay = modal.querySelector(".modal-overlay");
  const closeButtons = modal.querySelectorAll("[data-modal-close]");
  if (!titleEl || !bodyEl) {
    return;
  }

  const templateMap = new Map();
  document.querySelectorAll("template[data-norm-detail]").forEach((templateEl) => {
    if (templateEl.id) {
      templateMap.set(templateEl.id, templateEl.innerHTML.trim());
    }
  });
  if (!templateMap.size) {
    return;
  }

  const openModal = (title, templateId) => {
    const html = templateMap.get(templateId);
    if (!html) {
      return;
    }
    titleEl.textContent = title || "Detalle normativo";
    bodyEl.innerHTML = html;
    modal.hidden = false;
    modal.classList.add("is-open");
    window.setTimeout(() => {
      const focusTarget = modal.querySelector("[data-modal-close]");
      focusTarget?.focus();
    }, 40);
  };

  const closeModal = () => {
    modal.classList.remove("is-open");
    modal.hidden = true;
    bodyEl.innerHTML = "";
  };

  closeButtons.forEach((button) => {
    button.addEventListener("click", closeModal);
  });
  overlay?.addEventListener("click", closeModal);
  modal.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      event.preventDefault();
      closeModal();
    }
  });

  triggers.forEach((trigger) => {
    trigger.addEventListener("click", () => {
      const templateId = trigger.dataset.normTemplate;
      if (!templateId) {
        return;
      }
      const explicitTitle = trigger.dataset.normTitle || trigger.textContent?.trim();
      openModal(explicitTitle, templateId);
    });
  });
}
