(() => {
  "use strict";

  document.addEventListener("DOMContentLoaded", () => {
    const initializers = [
      ["initTabs", initTabs],
      ["initCasoInternoForm", initCasoInternoForm],
      ["initFilterToggle", initFilterToggle],
      ["initTramiteCasoDetail", initTramiteCasoDetail],
      ["initEstatusCrudUnified", initEstatusCrudUnified],
      ["initTerminoCalculators", initTerminoCalculators],
      ["initFuncionDisplays", initFuncionDisplays],
      ["initSortableTables", initSortableTables],
      ["initIncidenciasSections", initIncidenciasSections],
      ["initPlantillasSearch", initPlantillasSearch],
      ["initTrabajadorLookup", initTrabajadorLookup],
      ["initPrefijoOficioMulti", initPrefijoOficioMulti],
      ["initTrabajadorPicker", initTrabajadorPicker],
      ["initTrabajadoresCaso", initTrabajadoresCaso],
      ["initTrabajadorQuickFill", initTrabajadorQuickFill],
      ["initTrabajadorSelectors", initTrabajadorSelectors],
      ["initBulkCasoActions", initBulkCasoActions],
      ["initInboxEnhancements", initInboxEnhancements],
      ["initSimpleModals", initSimpleModals],
      ["initDuplicadosPreview", initDuplicadosPreview],
      ["initFolioGenerador", initFolioGenerador],
      ["initFolioGeneradorCampos", initFolioGeneradorCampos],
      ["initFolioBuscar", initFolioBuscar],
      ["initPrefijoFolioCrud", initPrefijoFolioCrud],
      ["initFolioCopy", initFolioCopy],
      ["initPdfFileValidation", initPdfFileValidation],
      ["initConvertirCasoConfirmations", initConvertirCasoConfirmations],
      ["initCasoDestinoSearch", initCasoDestinoSearch],
      ["initToggleSections", initToggleSections],
      ["initSelectTypeahead", initSelectTypeahead],
    ];
    initializers.forEach(([name, initFn]) => {
      try {
        initFn();
      } catch (error) {
        console.error(`[app.js] ${name} failed`, error);
      }
    });
  });

  const INITIALS_SKIP = new Set(["DE", "DEL", "LA", "LAS", "LOS", "Y"]);

  const buildInitials = (value) => {
    const cleaned = (value || "").trim();
    if (!cleaned) return "";
    const parts = cleaned.split(/\s+/).filter(Boolean);
    const filtered = parts.filter(
      (part) => !INITIALS_SKIP.has(part.toUpperCase()),
    );
    const source = filtered.length ? filtered : parts;
    return source.map((part) => part[0].toUpperCase()).join("");
  };

  const setInputValue = (input, value) => {
    if (!input) return;
    input.value = value;
    input.dispatchEvent(new Event("input", { bubbles: true }));
    input.dispatchEvent(new Event("change", { bubbles: true }));
  };

  const initializedGenericCrudKeys = new Set();

  const queryByNameSuffix = (scope, suffix, fallbackSelector = "") => {
    if (!scope || !suffix) {
      return null;
    }
    const byPrefixedName = scope.querySelector(`[name$="-${suffix}"]`);
    if (byPrefixedName) return byPrefixedName;
    const byExactName = scope.querySelector(`[name="${suffix}"]`);
    if (byExactName) return byExactName;
    const byLooseSuffix = scope.querySelector(`[name$="${suffix}"]`);
    if (byLooseSuffix) return byLooseSuffix;
    if (fallbackSelector) {
      return scope.querySelector(fallbackSelector);
    }
    return null;
  };

  function initTabs() {
    const tabButtons = document.querySelectorAll(".tab-link[data-tab-target]");
    if (!tabButtons.length) {
      return;
    }
    const panels = document.querySelectorAll(".tab-panel[data-tab-panel]");

    const activateTab = (targetKey) => {
      tabButtons.forEach((button) => {
        const isActive = button.dataset.tabTarget === targetKey;
        button.classList.toggle("is-active", isActive);
        button.setAttribute("aria-selected", String(isActive));
        button.setAttribute("tabindex", isActive ? "0" : "-1");
      });
      panels.forEach((panel) => {
        const isActive = panel.dataset.tabPanel === targetKey;
        panel.classList.toggle("is-active", isActive);
        panel.hidden = !isActive;
      });
    };

    tabButtons.forEach((button) => {
      if (!button.hasAttribute("tabindex")) {
        button.setAttribute(
          "tabindex",
          button.classList.contains("is-active") ? "0" : "-1",
        );
      }
      button.addEventListener("click", () => {
        activateTab(button.dataset.tabTarget);
      });
      button.addEventListener("keydown", (event) => {
        if (event.key !== "ArrowRight" && event.key !== "ArrowLeft") {
          return;
        }
        event.preventDefault();
        const direction = event.key === "ArrowRight" ? 1 : -1;
        const buttons = Array.from(tabButtons);
        const currentIndex = buttons.indexOf(button);
        const nextIndex = (currentIndex + direction + buttons.length) % buttons.length;
        const nextButton = buttons[nextIndex];
        nextButton.focus();
        activateTab(nextButton.dataset.tabTarget);
      });
    });
  }

  function initTerminoCalculators() {
    const calculateDiff = (value) => {
      if (!value) return null;
      const target = new Date(`${value}T00:00:00`);
      const today = new Date();
      const todayMidnight = new Date(today.getFullYear(), today.getMonth(), today.getDate());
      const diffMs = target - todayMidnight;
      return Math.round(diffMs / (1000 * 60 * 60 * 24));
    };

    const bindCalculator = (inputSelector, outputSelector) => {
      const inputs = document.querySelectorAll(inputSelector);
      inputs.forEach((input) => {
        const output = input
          .closest("section, form")
          ?.querySelector(outputSelector) || document.querySelector(outputSelector);
        if (!output) return;
        const update = () => {
          const diffDays = calculateDiff(input.value);
          if (diffDays === null || Number.isNaN(diffDays)) {
            output.textContent = "—";
            output.dataset.delta = "";
            return;
          }
          const absDiff = Math.abs(diffDays);
          const suffix = absDiff === 1 ? "día" : "días";
          output.textContent =
            diffDays >= 0 ? `${diffDays} ${suffix} restantes` : `Vencido hace ${absDiff} ${suffix}`;
          output.dataset.delta = diffDays;
        };
        input.addEventListener("change", update);
        input.addEventListener("input", update);
        update();
      });
    };

    // Caso principal
    bindCalculator("#id_fecha_termino", "[data-termino-dias-caso]");
    // Trámite asociado (prefijo en modal)
    bindCalculator("#id_tramite_caso-fecha_termino", "[data-termino-dias-tramite]");
    // Trámite asociado standalone (sin prefijo)
    bindCalculator("#id_fecha_termino", "[data-termino-dias-tramite]");
  }

  function initIncidenciasSections() {
    const sections = document.querySelectorAll("[data-incidencias]");
    if (!sections.length) {
      return;
    }
    const core = window.AnalizadorCore || {};
    const parseISODate =
      core.parseISODate ||
      ((value) => {
        if (!value) return null;
        const date = new Date(`${value}T00:00:00Z`);
        return Number.isNaN(date.getTime()) ? null : date;
      });
    const addDays =
      core.addDays ||
      ((date, days) => {
        const clone = new Date(date.getTime());
        clone.setUTCDate(clone.getUTCDate() + days);
        return clone;
      });
    const calculateInclusiveDays =
      core.calculateInclusiveDays ||
      ((start, end) => {
        if (!(start instanceof Date) || !(end instanceof Date)) return 0;
        const diff = end.getTime() - start.getTime();
        if (diff < 0) return 0;
        return Math.floor(diff / (1000 * 60 * 60 * 24)) + 1;
      });
    const formatISO = (date) => {
      if (!(date instanceof Date)) return "";
      const year = date.getUTCFullYear();
      const month = `${date.getUTCMonth() + 1}`.padStart(2, "0");
      const day = `${date.getUTCDate()}`.padStart(2, "0");
      return `${year}-${month}-${day}`;
    };
    const hasValue = (el) => {
      if (!el) return false;
      return (el.value || "").toString().trim() !== "";
    };
    const parseJsonArray = (value) => {
      if (!value) return [];
      try {
        const parsed = JSON.parse(value);
        return Array.isArray(parsed) ? parsed : [];
      } catch (_err) {
        return [];
      }
    };
    const toSafeInt = (value) => {
      const parsed = Number.parseInt(String(value || "").trim(), 10);
      return Number.isFinite(parsed) ? parsed : null;
    };
    const makeRangeId = () =>
      `rango:${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

    sections.forEach((section) => {
      const toggle = section.querySelector("[data-incidencias-toggle]");
      const clearBtn = section.querySelector("[data-incidencias-clear]");
      const body = section.querySelector("[data-incidencias-body]");
      const summary = section.querySelector("[data-incidencias-summary]");
      const nombreInput = section.querySelector('input[name$="incidencia_nombre_docente"]');
      const workerSelect = section.querySelector("[data-incidencia-worker-select]");
      const requiresWorkerSelection = Boolean(workerSelect);
      const afiliacionSelect = section.querySelector('[name$="incidencia_afiliacion"]');
      const inicioInput = section.querySelector('input[name$="incidencia_fecha_inicio"]');
      const terminoInput = section.querySelector('input[name$="incidencia_fecha_termino"]');
      const diasInput = section.querySelector('input[name$="incidencia_dias_otorgados"]');
      const rangosHidden = section.querySelector('input[name$="rangos_fechas_adicionales"]');
      const rangosRows = section.querySelector("[data-rangos-fechas-rows]");
      const rangoAddBtn = section.querySelector("[data-rango-fecha-add]");
      const rangoModal = section.querySelector("[data-rango-fecha-modal]");

      if (!afiliacionSelect && !inicioInput && !terminoInput && !diasInput) {
        return;
      }

      const normalizeRanges = (items) =>
        (Array.isArray(items) ? items : [])
          .filter((item) => item && typeof item === "object")
          .map((item) => ({
            id: String(item.id || makeRangeId()),
            trabajador_nombre: String(item.trabajador_nombre || "").trim(),
            incidencia_afiliacion: String(item.incidencia_afiliacion || "").trim().toUpperCase(),
            incidencia_fecha_inicio: String(item.incidencia_fecha_inicio || "").trim(),
            incidencia_fecha_termino: String(item.incidencia_fecha_termino || "").trim(),
            incidencia_dias_otorgados: item.incidencia_dias_otorgados || "",
          }))
          .filter(
            (item) =>
              item.trabajador_nombre &&
              (item.incidencia_afiliacion ||
                item.incidencia_fecha_inicio ||
                item.incidencia_fecha_termino ||
                item.incidencia_dias_otorgados),
          );

      let rangosAdicionales = normalizeRanges(parseJsonArray(rangosHidden?.value || ""));
      let currentRangeId = "";

      const setCollapsed = (collapsed) => {
        if (body) {
          if (collapsed) {
            body.hidden = true;
          } else {
            body.hidden = false;
            body.removeAttribute("hidden");
          }
        }
        if (toggle) {
          toggle.textContent = collapsed ? "Mostrar" : "Ocultar";
        }
      };

      const syncPrimaryWorker = () => {
        if (!requiresWorkerSelection) return;
        if (!nombreInput) return;
        const selected = (workerSelect?.value || "").trim();
        setInputValue(nombreInput, selected);
      };

      const setFieldsEnabled = (enabled) => {
        [afiliacionSelect, inicioInput, terminoInput, diasInput].forEach((input) => {
          if (!input) return;
          input.disabled = !enabled;
        });
      };

      const lockFields = (afiliacion) => {
        if (afiliacion === "IMSS") {
          if (terminoInput) terminoInput.setAttribute("disabled", "disabled");
          if (diasInput) diasInput.removeAttribute("disabled");
        } else if (afiliacion === "ISSSTE") {
          if (diasInput) diasInput.setAttribute("disabled", "disabled");
          if (terminoInput) terminoInput.removeAttribute("disabled");
        } else {
          if (terminoInput) terminoInput.removeAttribute("disabled");
          if (diasInput) diasInput.removeAttribute("disabled");
        }
      };

      const persistRangos = () => {
        if (!rangosHidden) return;
        rangosHidden.value = JSON.stringify(rangosAdicionales);
      };

      const closeRangoModal = () => {
        if (!rangoModal) return;
        const form = rangoModal.querySelector("[data-rango-fecha-form]");
        const message = rangoModal.querySelector("[data-rango-fecha-message]");
        currentRangeId = "";
        if (form) {
          if (typeof form.reset === "function") {
            form.reset();
          } else {
            form
              .querySelectorAll("input, select, textarea")
              .forEach((input) => {
                if (input.type === "checkbox" || input.type === "radio") {
                  input.checked = false;
                } else {
                  input.value = "";
                }
              });
          }
        }
        if (message) {
          message.textContent = "";
          message.className = "modal-message";
          message.style.display = "none";
        }
        rangoModal.hidden = true;
      };

      const renderRangos = () => {
        if (!rangosRows) return;
        rangosRows.innerHTML = "";
        if (!rangosAdicionales.length) {
          const row = document.createElement("tr");
          row.className = "table__empty-row";
          row.innerHTML =
            '<td colspan="6" class="table__empty">No hay rangos de fechas adicionales.</td>';
          rangosRows.appendChild(row);
          return;
        }
        rangosAdicionales.forEach((rango) => {
          const row = document.createElement("tr");
          row.innerHTML = `
            <td>${rango.trabajador_nombre || "-"}</td>
            <td>${rango.incidencia_afiliacion || "-"}</td>
            <td>${rango.incidencia_fecha_inicio || "-"}</td>
            <td>${rango.incidencia_fecha_termino || "-"}</td>
            <td>${rango.incidencia_dias_otorgados || "-"}</td>
            <td class="table-actions">
              <button type="button" class="table-actions__link" data-rango-fecha-edit data-rango-fecha-id="${rango.id || ""}">Editar</button>
              <button type="button" class="table-actions__link table-actions__link--danger" data-rango-fecha-delete data-rango-fecha-id="${rango.id || ""}">Eliminar</button>
            </td>
          `;
          rangosRows.appendChild(row);
        });
      };

      const upsertRango = (record) => {
        if (!record) return;
        const idx = rangosAdicionales.findIndex((item) => item.id === record.id);
        if (idx >= 0) {
          rangosAdicionales[idx] = record;
        } else {
          rangosAdicionales.push(record);
        }
        persistRangos();
        renderRangos();
      };

      const openRangoModal = (record = null) => {
        if (!rangoModal) return;
        const form = rangoModal.querySelector("[data-rango-fecha-form]");
        const title = rangoModal.querySelector("[data-rango-fecha-title]");
        const message = rangoModal.querySelector("[data-rango-fecha-message]");
        if (!form) return;
        const worker = form.querySelector("[data-rango-fechas-worker-select]");
        const afiliacion = form.querySelector("[data-rango-fecha-afiliacion]");
        const inicio = form.querySelector("[data-rango-fecha-inicio]");
        const termino = form.querySelector("[data-rango-fecha-termino]");
        const dias = form.querySelector("[data-rango-fecha-dias]");
        currentRangeId = record?.id || "";
        if (title) {
          title.textContent = record ? "Editar rango de fechas" : "Agregar rango de fechas";
        }
        if (message) {
          message.textContent = "";
          message.className = "modal-message";
          message.style.display = "none";
        }
        if (worker) {
          if (record?.trabajador_nombre) {
            worker.value = record.trabajador_nombre;
          } else if (worker.options.length === 2) {
            worker.value = worker.options[1].value;
          } else {
            worker.value = "";
          }
        }
        if (afiliacion) afiliacion.value = record?.incidencia_afiliacion || "";
        if (inicio) inicio.value = record?.incidencia_fecha_inicio || "";
        if (termino) termino.value = record?.incidencia_fecha_termino || "";
        if (dias) dias.value = record?.incidencia_dias_otorgados || "";
        rangoModal.hidden = false;
      };

      const computeRange = (payload) => {
        const afiliacion = (payload.incidencia_afiliacion || "").toUpperCase();
        const inicioDate = parseISODate(payload.incidencia_fecha_inicio || "");
        const terminoDate = parseISODate(payload.incidencia_fecha_termino || "");
        const diasValue = toSafeInt(payload.incidencia_dias_otorgados);
        if (!payload.trabajador_nombre) {
          return { error: "Selecciona un trabajador válido." };
        }
        if (!afiliacion) {
          return { error: "Selecciona la afiliación." };
        }
        if (!inicioDate) {
          return { error: "Captura la fecha de inicio." };
        }
        if (afiliacion === "ISSSTE") {
          if (!terminoDate) {
            return { error: "Captura la fecha de término." };
          }
          if (terminoDate < inicioDate) {
            return { error: "La fecha de término no puede ser anterior a la de inicio." };
          }
          return {
            incidencia_afiliacion: "ISSSTE",
            incidencia_fecha_inicio: formatISO(inicioDate),
            incidencia_fecha_termino: formatISO(terminoDate),
            incidencia_dias_otorgados: calculateInclusiveDays(inicioDate, terminoDate),
          };
        }
        if (afiliacion === "IMSS") {
          if (!diasValue || diasValue <= 0) {
            return { error: "Ingresa días otorgados mayores a cero." };
          }
          const terminoCalculado = addDays(inicioDate, diasValue - 1);
          return {
            incidencia_afiliacion: "IMSS",
            incidencia_fecha_inicio: formatISO(inicioDate),
            incidencia_fecha_termino: formatISO(terminoCalculado),
            incidencia_dias_otorgados: diasValue,
          };
        }
        return { error: "Selecciona IMSS o ISSSTE." };
      };

      const resetFields = () => {
        [inicioInput, terminoInput, diasInput, afiliacionSelect].forEach((input) => {
          if (input) {
            input.value = "";
          }
        });
        if (workerSelect) {
          workerSelect.value = "";
        }
        if (nombreInput && requiresWorkerSelection) {
          setInputValue(nombreInput, "");
        }
        rangosAdicionales = [];
        persistRangos();
        renderRangos();
        lockFields("");
        setFieldsEnabled(false);
        setCollapsed(true);
        if (summary) {
          summary.textContent = requiresWorkerSelection
            ? "Selecciona un trabajador para activar el rango principal."
            : "Completa afiliación y fechas para calcular el rango principal.";
        }
      };

      const update = () => {
        const workerName = requiresWorkerSelection
          ? (workerSelect?.value || nombreInput?.value || "").trim()
          : (nombreInput?.value || "").trim();
        const hasWorker = requiresWorkerSelection ? Boolean(workerName) : true;
        if (requiresWorkerSelection && hasWorker && nombreInput && nombreInput.value !== workerName) {
          setInputValue(nombreInput, workerName);
        } else if (requiresWorkerSelection && !hasWorker && nombreInput && nombreInput.value) {
          setInputValue(nombreInput, "");
        }
        setFieldsEnabled(hasWorker);
        const afiliacion = (afiliacionSelect?.value || "").toUpperCase();
        const inicioDate = parseISODate(inicioInput?.value || "");
        const terminoDate = parseISODate(terminoInput?.value || "");
        const diasValue = diasInput && hasValue(diasInput) ? Number(diasInput.value) : null;
        const hasMainData =
          hasValue(afiliacionSelect) ||
          hasValue(inicioInput) ||
          hasValue(terminoInput) ||
          hasValue(diasInput);
        const hasAny = hasMainData || rangosAdicionales.length > 0;
        setCollapsed(!hasAny && (!requiresWorkerSelection || !hasWorker));
        if (hasWorker) {
          lockFields(afiliacion);
        }

        if (!summary) {
          return;
        }
        if (requiresWorkerSelection && !hasWorker) {
          summary.textContent = "Selecciona un trabajador para activar el rango principal.";
          return;
        }
        if (!hasMainData) {
          summary.textContent = "Completa afiliación y fechas para calcular el rango principal.";
          return;
        }
        if (!afiliacion) {
          summary.textContent = "Selecciona afiliación (IMSS/ISSSTE) para aplicar las reglas.";
          return;
        }
        if (!inicioInput?.value) {
          summary.textContent = "Captura la fecha de inicio para calcular días o la fecha de término.";
          return;
        }

        if (afiliacion === "ISSSTE") {
          if (!terminoInput?.value) {
            summary.textContent = "Captura la fecha de término para calcular los días naturales.";
            if (diasInput) diasInput.value = "";
            return;
          }
          if (terminoDate && inicioDate && terminoDate < inicioDate) {
            summary.textContent = "La fecha de término no puede ser anterior a la de inicio.";
            if (diasInput) diasInput.value = "";
            return;
          }
          const calculated = calculateInclusiveDays(inicioDate, terminoDate);
          if (diasInput) {
            diasInput.value = calculated || "";
            diasInput.setAttribute("disabled", "disabled");
          }
          summary.textContent =
            calculated > 0
              ? `${calculated} día${calculated === 1 ? "" : "s"} naturales entre las fechas.`
              : "Confirma que las fechas sean correctas para calcular los días otorgados.";
        } else if (afiliacion === "IMSS") {
          if (diasValue && diasValue > 0 && inicioDate) {
            const endDate = addDays(inicioDate, diasValue - 1);
            if (terminoInput) {
              terminoInput.value = formatISO(endDate);
              terminoInput.setAttribute("disabled", "disabled");
            }
            summary.textContent = `Fecha de término calculada: ${terminoInput?.value || ""} (${diasValue} día${
              diasValue === 1 ? "" : "s"
            } naturales).`;
          } else {
            summary.textContent = "Ingresa los días otorgados para calcular la fecha de término.";
            if (terminoInput) terminoInput.value = "";
          }
        } else {
          summary.textContent = "Selecciona IMSS o ISSSTE para activar el cálculo.";
        }
      };

      if (rangosRows) {
        rangosRows.addEventListener("click", (event) => {
          const editBtn = event.target.closest("[data-rango-fecha-edit]");
          if (editBtn) {
            const rangeId = editBtn.dataset.rangoFechaId || "";
            const record = rangosAdicionales.find((item) => item.id === rangeId);
            openRangoModal(record || null);
            return;
          }
          const deleteBtn = event.target.closest("[data-rango-fecha-delete]");
          if (!deleteBtn) return;
          const rangeId = deleteBtn.dataset.rangoFechaId || "";
          rangosAdicionales = rangosAdicionales.filter((item) => item.id !== rangeId);
          persistRangos();
          renderRangos();
          update();
        });
      }

      if (rangoAddBtn) {
        rangoAddBtn.addEventListener("click", () => {
          openRangoModal();
        });
      }

      if (rangoModal) {
        const closeButtons = rangoModal.querySelectorAll("[data-rango-fecha-close]");
        closeButtons.forEach((btn) => btn.addEventListener("click", closeRangoModal));
        const modalForm = rangoModal.querySelector("[data-rango-fecha-form]");
        if (modalForm) {
          const handleSave = (event) => {
            event.preventDefault();
            const workerInput = modalForm.querySelector("[data-rango-fechas-worker-select]");
            const afiliacionInput = modalForm.querySelector("[data-rango-fecha-afiliacion]");
            const inicioModalInput = modalForm.querySelector("[data-rango-fecha-inicio]");
            const terminoModalInput = modalForm.querySelector("[data-rango-fecha-termino]");
            const diasModalInput = modalForm.querySelector("[data-rango-fecha-dias]");
            const message = rangoModal.querySelector("[data-rango-fecha-message]");

            const payload = {
              trabajador_nombre: (workerInput?.value || "").trim(),
              incidencia_afiliacion: (afiliacionInput?.value || "").trim().toUpperCase(),
              incidencia_fecha_inicio: (inicioModalInput?.value || "").trim(),
              incidencia_fecha_termino: (terminoModalInput?.value || "").trim(),
              incidencia_dias_otorgados: (diasModalInput?.value || "").trim(),
            };
            const computed = computeRange(payload);
            if (computed.error) {
              if (message) {
                message.textContent = computed.error;
                message.className = "modal-message error";
                message.style.display = "block";
              }
              return;
            }
            upsertRango({
              id: currentRangeId || makeRangeId(),
              trabajador_nombre: payload.trabajador_nombre,
              ...computed,
            });
            closeRangoModal();
            update();
          };
          modalForm.addEventListener("submit", handleSave);
          const saveButton = modalForm.querySelector("[data-rango-fecha-save]");
          if (saveButton) {
            saveButton.addEventListener("click", handleSave);
          }
        }
      }

      toggle?.addEventListener("click", (event) => {
        event.preventDefault();
        const collapsed = body ? body.hidden : true;
        setCollapsed(!collapsed);
      });
      clearBtn?.addEventListener("click", resetFields);
      [workerSelect, afiliacionSelect, inicioInput, terminoInput, diasInput].forEach((input) => {
        input?.addEventListener("change", update);
        input?.addEventListener("input", update);
      });
      persistRangos();
      renderRangos();
      if (requiresWorkerSelection && workerSelect && workerSelect.options.length === 2 && !workerSelect.value) {
        workerSelect.value = workerSelect.options[1].value;
      }
      syncPrimaryWorker();
      update();
    });
  }

  function initPlantillasSearch() {
    const form = document.querySelector("[data-plantillas-search]");
    if (!form) {
      return;
    }
    const targetSelector = form.dataset.plantillasTarget;
    const indicatorSelector = form.dataset.plantillasIndicator;
    let target = targetSelector ? document.querySelector(targetSelector) : null;
    const indicator = indicatorSelector ? document.querySelector(indicatorSelector) : null;
    const inputs = form.querySelectorAll("input[name]");
    if (!target || !inputs.length) {
      return;
    }

    let timeoutId = null;
    let activeController = null;

    const serializeForm = () => {
      const params = new URLSearchParams();
      inputs.forEach((input) => {
        if (!input.name) return;
        params.set(input.name, input.value || "");
      });
      params.set("partial", "1");
      return params.toString();
    };

    const setLoading = (isLoading) => {
      if (!indicator) return;
      indicator.style.display = isLoading ? "block" : "none";
    };

    const fetchResults = () => {
      if (activeController) {
        activeController.abort();
      }
      activeController = new AbortController();
      setLoading(true);

      const url = `${form.action}?${serializeForm()}`;
      fetch(url, {
        method: "GET",
        headers: { "HX-Request": "true" },
        signal: activeController.signal,
      })
        .then((response) => {
          if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
          }
          return response.text();
        })
        .then((html) => {
          const parser = new DOMParser();
          const doc = parser.parseFromString(html, "text/html");
          const newTarget = targetSelector ? doc.querySelector(targetSelector) : null;
          if (!newTarget) {
            throw new Error("No se encontró el contenedor de resultados.");
          }
          target.replaceWith(newTarget);
          target = newTarget;
        })
        .catch((error) => {
          if (error.name !== "AbortError") {
            console.error("Error cargando plantillas:", error);
          }
        })
        .finally(() => {
          setLoading(false);
        });
    };

    const scheduleFetch = () => {
      if (timeoutId) {
        clearTimeout(timeoutId);
      }
      timeoutId = setTimeout(fetchResults, 350);
    };

    inputs.forEach((input) => {
      input.addEventListener("input", scheduleFetch);
      input.addEventListener("change", scheduleFetch);
      input.addEventListener("search", scheduleFetch);
    });
  }

  function initTrabajadorLookup() {
    const inputs = Array.from(document.querySelectorAll("[data-trabajador-lookup]"));
    if (!inputs.length) {
      const fallbackInput = document.querySelector("#id_trabajador_principal_nombre");
      if (fallbackInput) {
        inputs.push(fallbackInput);
      }
    }
    if (!inputs.length) {
      return;
    }
    inputs.forEach((targetInput) => {
      const form =
        targetInput.closest("form") ||
        document.querySelector("[data-caso-interno-form]") ||
        document.querySelector("form");
      const datalistId = targetInput.getAttribute("list");
      const datalist = datalistId ? document.getElementById(datalistId) : null;
      const hiddenField =
        form?.querySelector("[data-trabajador-id]") ||
        form?.querySelector("#id_trabajador_principal") ||
        document.querySelector("[data-trabajador-id]") ||
        document.querySelector("#id_trabajador_principal");
      const correoField = document.querySelector("[data-trabajador-correo]");
      const celularField = document.querySelector("[data-trabajador-celular]");
      const sistemaField = document.querySelector("[data-trabajador-sistema]");
      const lookupUrl =
        targetInput.dataset.lookupUrl || form?.dataset.empleadoLookup || "";
      if (!datalist || !hiddenField || !lookupUrl) {
        return;
      }

      const map = new Map();
      const localCatalogOptions = new Map();
      let timeoutId = null;
      let activeController = null;

      const clearHiddenSelection = () => {
        hiddenField.value = "";
      };

      const buildWorkerLabel = (item) => {
        const labelParts = [item?.nombre, item?.rfc, item?.curp].filter(Boolean);
        return labelParts.join(" · ");
      };

      const upsertDatalistOption = (label, id) => {
        if (!label || !id) {
          return;
        }
        map.set(label, String(id));
        const existing = Array.from(datalist.options).find((option) => option.value === label);
        if (existing) {
          return;
        }
        const option = document.createElement("option");
        option.value = label;
        datalist.appendChild(option);
      };

      const renderOptions = (results) => {
        datalist.innerHTML = "";
        map.clear();
        localCatalogOptions.forEach((storedId, storedLabel) => {
          upsertDatalistOption(storedLabel, storedId);
        });
        results.forEach((item) => {
          const label = buildWorkerLabel(item);
          const id = String(item?.id || "");
          upsertDatalistOption(label, id);
        });
      };

      const fetchSuggestions = () => {
        const query = targetInput.value.trim();
        if (query.length < 2) {
          renderOptions([]);
          return;
        }
        if (activeController) {
          activeController.abort();
        }
        activeController = new AbortController();
        const url = `${lookupUrl}?q=${encodeURIComponent(query)}`;
        fetch(url, { signal: activeController.signal })
          .then((response) => {
            if (!response.ok) {
              throw new Error(`HTTP ${response.status}`);
            }
            return response.json();
          })
          .then((data) => {
            renderOptions(data.results || []);
          })
          .catch((error) => {
            if (error.name !== "AbortError") {
              console.error("Error buscando trabajadores:", error);
            }
          });
      };

      const scheduleFetch = () => {
        if (timeoutId) {
          clearTimeout(timeoutId);
        }
        timeoutId = setTimeout(fetchSuggestions, 300);
      };

      const fetchDetalle = (id) => {
        if (!id) {
          return;
        }
        fetch(`${lookupUrl}?id=${encodeURIComponent(id)}`)
          .then((response) => {
            if (!response.ok) {
              throw new Error(`HTTP ${response.status}`);
            }
            return response.json();
          })
          .then((data) => {
            if (correoField && !correoField.value) {
              correoField.value = data.correo || "";
            }
            if (celularField && !celularField.value) {
              celularField.value = data.celular || "";
            }
            if (sistemaField && !sistemaField.value) {
              sistemaField.value = data.sistema || "";
            }
            document.dispatchEvent(
              new CustomEvent("trabajador:detalle", { detail: data }),
            );
          })
          .catch((error) => {
            console.error("Error consultando trabajador:", error);
          });
      };

      const applySelection = () => {
        const typedValue = targetInput.value.trim();
        const selectedId = map.get(typedValue);
        if (!selectedId) {
          if (!typedValue) {
            clearHiddenSelection();
          }
          return;
        }
        hiddenField.value = selectedId;
        document.dispatchEvent(
          new CustomEvent("trabajador:seleccion", { detail: { id: selectedId } }),
        );
        fetchDetalle(selectedId);
      };

      targetInput.addEventListener("input", () => {
        clearHiddenSelection();
        scheduleFetch();
      });
      targetInput.addEventListener("change", applySelection);
      targetInput.addEventListener("blur", applySelection);

      document.addEventListener("trabajador:catalogo-add", (event) => {
        const data = event.detail || {};
        const workerId = String(data.id || "").trim();
        if (!workerId || workerId.startsWith("manual:")) {
          return;
        }
        const label = buildWorkerLabel(data);
        if (!label) {
          return;
        }
        localCatalogOptions.set(label, workerId);
        upsertDatalistOption(label, workerId);
      });
    });
  }

  function initPrefijoOficioMulti() {
    const scopes = document.querySelectorAll("[data-prefijo-scope]");
    if (!scopes.length) {
      return;
    }
    const modal = document.getElementById("prefijo-oficio-modal");
    const form = document.getElementById("prefijo-oficio-form");
    if (!modal || !form) {
      return;
    }
    const modalTitle = modal.querySelector("[data-modal-title]");
    const modalMessage = modal.querySelector("[data-modal-message]");
    const saveBtn = form.querySelector("[data-prefijo-oficio-save]");
    const closeBtns = modal.querySelectorAll("[data-modal-close]");
    const datalist = document.getElementById("prefijo-oficio-options-licencias");
    const apiBase = "/api/prefijos-oficio/";
    let currentMode = "create";
    let selectedId = null;
    let activeScope = null;

    const getScopeElements = (scope) => ({
      select: scope.querySelector("[data-prefijo-select]"),
      input: scope.querySelector("[data-prefijo-input]"),
      openBtn: scope.querySelector("[data-prefijo-open]"),
      editBtn: scope.querySelector("[data-prefijo-edit]"),
      deleteBtn: scope.querySelector("[data-prefijo-delete]"),
    });

    const updateAllSelects = (callback) => {
      scopes.forEach((scope) => {
        const { select } = getScopeElements(scope);
        if (select) {
          callback(select);
        }
      });
    };

    const addOption = (select, data) => {
      const option = document.createElement("option");
      option.value = data.id;
      option.textContent = data.nombre;
      select.appendChild(option);
      select.value = data.id;
    };

    const updateOption = (select, data) => {
      const option = select.querySelector(`option[value="${data.id}"]`);
      if (option) {
        option.textContent = data.nombre;
      }
    };

    const removeOption = (select, id) => {
      const option = select.querySelector(`option[value="${id}"]`);
      if (option) {
        option.remove();
      }
      if (select.value === String(id)) {
        select.value = "";
      }
    };

    const upsertDatalistOption = (value) => {
      if (!datalist || !value) {
        return;
      }
      const existing = Array.from(datalist.children).find((opt) => opt.value === value);
      if (existing) {
        return;
      }
      const option = document.createElement("option");
      option.value = value;
      datalist.appendChild(option);
    };

    const removeDatalistOption = (value) => {
      if (!datalist) {
        return;
      }
      const option = Array.from(datalist.children).find((opt) => opt.value === value);
      if (option) {
        option.remove();
      }
    };

    const showMessage = (message, isError = false) => {
      if (modalMessage) {
        modalMessage.textContent = message;
        modalMessage.className = isError ? "modal-message error" : "modal-message success";
        modalMessage.style.display = isError || message ? "block" : "none";
      }
    };

    const closeModal = () => {
      modal.hidden = true;
      form.reset();
      if (modalMessage) {
        modalMessage.style.display = "none";
        modalMessage.className = "modal-message";
      }
    };

    const openModalForCreate = (scope) => {
      activeScope = scope;
      currentMode = "create";
      if (modalTitle) {
        modalTitle.textContent = "Agregar prefijo de oficio";
      }
      const nombreInput = form.querySelector("#prefijo-oficio-nombre");
      if (nombreInput) {
        nombreInput.required = true;
        nombreInput.value = "";
        nombreInput.focus();
      }
      const fieldset = form.querySelector("#prefijo-oficio-fields");
      if (fieldset) {
        fieldset.style.display = "block";
      }
      if (saveBtn) {
        saveBtn.textContent = "Guardar";
        saveBtn.classList.remove("btn--danger");
        saveBtn.classList.add("btn--primary");
      }
      modal.hidden = false;
    };

    const openModalForEdit = (scope) => {
      const { select } = getScopeElements(scope);
      selectedId = parseInt(select?.value, 10);
      if (!selectedId) {
        showMessage("Selecciona un prefijo primero.", true);
        return;
      }
      activeScope = scope;
      currentMode = "edit";
      if (modalTitle) {
        modalTitle.textContent = "Editar prefijo de oficio";
      }
      const fieldset = form.querySelector("#prefijo-oficio-fields");
      if (fieldset) {
        fieldset.style.display = "block";
      }
      if (saveBtn) {
        saveBtn.textContent = "Guardar";
        saveBtn.classList.remove("btn--danger");
        saveBtn.classList.add("btn--primary");
      }
      fetch(`${apiBase}${selectedId}/`, {
        headers: { "X-Requested-With": "XMLHttpRequest" },
      })
        .then((response) => {
          if (!response.ok) throw new Error("No se pudo cargar el prefijo");
          return response.json();
        })
        .then((data) => {
          form.querySelector("#prefijo-oficio-nombre").value = data.nombre || "";
          form.querySelector("#prefijo-oficio-descripcion").value = data.descripcion || "";
          if (modalMessage) {
            modalMessage.style.display = "none";
          }
          modal.hidden = false;
        })
        .catch((error) => {
          showMessage(`Error: ${error.message}`, true);
        });
    };

    const openModalForDelete = (scope) => {
      const { select } = getScopeElements(scope);
      selectedId = parseInt(select?.value, 10);
      if (!selectedId) {
        showMessage("Selecciona un prefijo primero.", true);
        return;
      }
      activeScope = scope;
      currentMode = "delete";
      if (modalTitle) {
        modalTitle.textContent = "Eliminar prefijo de oficio";
      }
      const fieldset = form.querySelector("#prefijo-oficio-fields");
      if (fieldset) {
        fieldset.style.display = "none";
      }
      const nombreInput = form.querySelector("#prefijo-oficio-nombre");
      if (nombreInput) {
        nombreInput.required = false;
      }
      if (saveBtn) {
        saveBtn.textContent = "Eliminar";
        saveBtn.classList.remove("btn--primary");
        saveBtn.classList.add("btn--danger");
      }
      if (modalMessage) {
        modalMessage.textContent = "¿Estás seguro de que deseas eliminar este prefijo? Esta acción no se puede deshacer.";
        modalMessage.className = "modal-message";
        modalMessage.style.display = "block";
      }
      modal.hidden = false;
    };

    const createPrefix = async (data) => {
      const response = await fetch(apiBase, {
        method: "POST",
        headers: defaultHeaders(),
        body: JSON.stringify(data),
      });
      if (!response.ok) {
        const errorData = await response.json();
        const errorMessage = extractErrorMessage(errorData) || "Error al crear el prefijo.";
        showMessage(errorMessage, true);
        return;
      }
      const created = await response.json();
      updateAllSelects((select) => addOption(select, created));
      upsertDatalistOption(created.nombre);
      const { input } = activeScope ? getScopeElements(activeScope) : {};
      if (input) {
        input.value = created.nombre;
      }
      showMessage("Prefijo creado exitosamente.");
      setTimeout(closeModal, 800);
    };

    const updatePrefix = async (id, data) => {
      const response = await fetch(`${apiBase}${id}/`, {
        method: "PATCH",
        headers: defaultHeaders(),
        body: JSON.stringify(data),
      });
      if (!response.ok) {
        const errorData = await response.json();
        const errorMessage = extractErrorMessage(errorData) || "Error al actualizar el prefijo.";
        showMessage(errorMessage, true);
        return;
      }
      const updated = await response.json();
      updateAllSelects((select) => updateOption(select, updated));
      upsertDatalistOption(updated.nombre);
      const { select, input } = activeScope ? getScopeElements(activeScope) : {};
      if (select && select.value === String(updated.id) && input) {
        input.value = updated.nombre;
      }
      showMessage("Prefijo actualizado exitosamente.");
      setTimeout(closeModal, 800);
    };

    const deletePrefix = async (id) => {
      const response = await fetch(`${apiBase}${id}/`, {
        method: "DELETE",
        headers: defaultHeaders(),
      });
      if (!response.ok) {
        const errorData = await response.json();
        const errorMessage = extractErrorMessage(errorData) || "Error al eliminar el prefijo.";
        showMessage(errorMessage, true);
        return;
      }
      let optionLabel = "";
      updateAllSelects((select) => {
        const option = select.querySelector(`option[value="${id}"]`);
        if (option && !optionLabel) {
          optionLabel = option.textContent || "";
        }
        removeOption(select, id);
      });
      if (optionLabel) {
        removeDatalistOption(optionLabel);
      }
      const { input } = activeScope ? getScopeElements(activeScope) : {};
      if (input && optionLabel && input.value === optionLabel) {
        input.value = "";
      }
      showMessage("Prefijo eliminado.");
      setTimeout(closeModal, 800);
    };

    const submitForm = async (event) => {
      event.preventDefault();
      if (currentMode === "delete") {
        await deletePrefix(selectedId);
        return;
      }
      const nombreInput = form.querySelector("#prefijo-oficio-nombre");
      if (!nombreInput.value.trim()) {
        showMessage("El prefijo es obligatorio.", true);
        nombreInput.focus();
        return;
      }
      const data = {
        nombre: nombreInput.value.trim(),
        descripcion: form.querySelector("#prefijo-oficio-descripcion").value.trim(),
      };
      if (currentMode === "create") {
        await createPrefix(data);
      } else if (currentMode === "edit") {
        await updatePrefix(selectedId, data);
      }
    };

    scopes.forEach((scope) => {
      const { select, input, openBtn, editBtn, deleteBtn } = getScopeElements(scope);
      if (select && input) {
        select.addEventListener("change", () => {
          const selected = select.selectedOptions[0];
          if (selected && selected.textContent) {
            input.value = selected.textContent;
            input.focus();
          }
        });
      }
      if (openBtn) {
        openBtn.addEventListener("click", () => openModalForCreate(scope));
      }
      if (editBtn) {
        editBtn.addEventListener("click", () => openModalForEdit(scope));
      }
      if (deleteBtn) {
        deleteBtn.addEventListener("click", () => openModalForDelete(scope));
      }
    });

    if (saveBtn) {
      form.addEventListener("submit", submitForm);
    }
    closeBtns.forEach((btn) => btn.addEventListener("click", closeModal));
  }

  function initTrabajadorPicker() {
    const openBtn = document.querySelector("[data-empleado-picker-open]");
    const modal = document.getElementById("empleado-picker-modal");
    const body = modal ? modal.querySelector("[data-empleado-picker-body]") : null;
    const closeBtns = modal ? modal.querySelectorAll("[data-empleado-picker-close]") : [];
    const input = document.querySelector("[data-trabajador-lookup]");
    const fallbackInput = document.querySelector("#id_trabajador_principal_nombre");
    const targetInput = input || fallbackInput;
    const form =
      targetInput?.closest("form") ||
      document.querySelector("[data-caso-interno-form]") ||
      document.querySelector("form");
    const hiddenField =
      document.querySelector("[data-trabajador-id]") ||
      form?.querySelector("#id_trabajador_principal");
    const correoField = document.querySelector("[data-trabajador-correo]");
    const celularField = document.querySelector("[data-trabajador-celular]");
    const sistemaField = document.querySelector("[data-trabajador-sistema]");
    const lookupUrl = targetInput
      ? targetInput.dataset.lookupUrl || form?.dataset.empleadoLookup || ""
      : "";
    const pickerUrl = targetInput
      ? targetInput.dataset.empleadoPickerUrl || form?.dataset.empleadoPicker || ""
      : "";
    if (!openBtn || !modal || !body || !targetInput || !hiddenField || !lookupUrl || !pickerUrl) {
      return;
    }

    let activeController = null;

    const closeModal = () => {
      modal.hidden = true;
    };

    const fetchDetalle = (id) => {
      if (!id) {
        return;
      }
      fetch(`${lookupUrl}?id=${encodeURIComponent(id)}`)
        .then((response) => {
          if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
          }
          return response.json();
        })
        .then((data) => {
          hiddenField.value = data.id || "";
          targetInput.value = data.nombre || "";
          if (correoField) correoField.value = data.correo || "";
          if (celularField) celularField.value = data.celular || "";
          if (sistemaField) sistemaField.value = data.sistema || "";
          document.dispatchEvent(
            new CustomEvent("trabajador:detalle", { detail: data }),
          );
        })
        .catch((error) => {
          console.error("Error consultando trabajador:", error);
        });
    };

    let searchTimeout = null;

    const escapeHtml = (value) =>
      String(value)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#39;");

    const highlightText = (text, query) => {
      if (!query) {
        return escapeHtml(text);
      }
      const safeText = escapeHtml(text);
      const escapedQuery = query.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
      const regex = new RegExp(escapedQuery, "gi");
      return safeText.replace(regex, (match) => `<mark class="result-highlight">${match}</mark>`);
    };

    const applyHighlights = () => {
      const query = targetInput ? targetInput.value : "";
      const cells = body.querySelectorAll("[data-highlight]");
      cells.forEach((cell) => {
        const raw = cell.dataset.highlight || "";
        cell.innerHTML = highlightText(raw, query.trim());
      });
    };

    const bindPickerEvents = () => {
      const form = body.querySelector("[data-empleado-picker-form]");
      const searchInput = form ? form.querySelector("input[name='q']") : null;
      const buttons = body.querySelectorAll("[data-empleado-select]");
      const editButtons = body.querySelectorAll("[data-empleado-edit]");
      const deleteButtons = body.querySelectorAll("[data-empleado-delete]");
      const backBtn = body.querySelector("[data-empleado-picker-back]");
      buttons.forEach((btn) => {
        btn.addEventListener("click", () => {
          const id = btn.dataset.empleadoId;
          fetchDetalle(id);
          closeModal();
        });
      });
      editButtons.forEach((btn) => {
        btn.addEventListener("click", () => {
          const url = btn.dataset.empleadoEditUrl;
          if (url) {
            loadPicker(url, true);
          }
        });
      });
      deleteButtons.forEach((btn) => {
        btn.addEventListener("click", () => {
          const url = btn.dataset.empleadoDeleteUrl;
          if (url) {
            loadPicker(url, true);
          }
        });
      });
      if (backBtn) {
        backBtn.addEventListener("click", () => loadPicker());
      }
      if (searchInput) {
        const scheduleFetch = () => {
          if (searchTimeout) {
            clearTimeout(searchTimeout);
          }
          const query = searchInput.value;
          searchTimeout = setTimeout(() => loadPicker(query), 300);
        };
        searchInput.addEventListener("input", scheduleFetch);
        searchInput.addEventListener("search", scheduleFetch);
        searchInput.addEventListener("change", scheduleFetch);
      }
      if (form && !searchInput) {
        form.addEventListener("submit", (event) => {
          event.preventDefault();
          const url = form.getAttribute("action") || window.location.href;
          const formData = new FormData(form);
          fetch(url, {
            method: "POST",
            headers: { "X-Requested-With": "XMLHttpRequest", "X-CSRFToken": getCsrfToken() },
            body: formData,
          })
            .then((response) => {
              if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
              }
              return response.text();
            })
            .then((html) => {
              body.innerHTML = html;
              bindPickerEvents();
            })
            .catch((error) => {
              console.error("Error guardando trabajador:", error);
            });
        });
      }
      applyHighlights();
    };

    const buildPickerUrl = (query = "") => {
      try {
        const url = new URL(pickerUrl, window.location.origin);
        if (query) {
          url.searchParams.set("q", query);
        }
        return url.toString();
      } catch (_err) {
        if (!query) return pickerUrl;
        return `${pickerUrl}?q=${encodeURIComponent(query)}`;
      }
    };

    const loadPicker = (query = "", isUrl = false) => {
      if (activeController) {
        activeController.abort();
      }
      activeController = new AbortController();
      const url = isUrl ? query : buildPickerUrl(query);
      if (!isUrl) {
        const results = body.querySelector("[data-empleado-picker-results]");
        if (results) {
          results.innerHTML = "<p class=\"text-muted\">Cargando trabajadores...</p>";
        }
      } else {
        body.innerHTML = "<p class=\"text-muted\">Cargando trabajadores...</p>";
      }
      fetch(url, { signal: activeController.signal })
        .then((response) => {
          if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
          }
          return response.text();
        })
        .then((html) => {
          if (isUrl) {
            body.innerHTML = html;
            bindPickerEvents();
            return;
          }
          const parser = new DOMParser();
          const doc = parser.parseFromString(html, "text/html");
          const nextResults = doc.querySelector("[data-empleado-picker-results]");
          const currentResults = body.querySelector("[data-empleado-picker-results]");
          if (nextResults && currentResults) {
            currentResults.replaceWith(nextResults);
          } else {
            body.innerHTML = html;
          }
          bindPickerEvents();
        })
        .catch((error) => {
          if (error.name !== "AbortError") {
            body.innerHTML = "<p class=\"text-muted\">No se pudieron cargar los trabajadores.</p>";
            console.error("Error cargando trabajadores:", error);
          }
        });
    };

    openBtn.addEventListener("click", () => {
      modal.hidden = false;
      loadPicker();
    });
    closeBtns.forEach((btn) => btn.addEventListener("click", closeModal));
  }

  function initTrabajadoresCaso() {
    const forms = document.querySelectorAll(
      "[data-caso-interno-form], [data-tramite-caso-form]",
    );
    if (!forms.length) {
      return;
    }
    forms.forEach((form) => {
      const isCaseForm = form.matches("[data-caso-interno-form]");

      const lookupUrl = form.dataset.empleadoLookup || "";
      const addCentroUrl = form.dataset.empleadoCentroAdd || "";
      const deleteCentroUrl = form.dataset.empleadoCentroDelete || "";
      const principalInput =
        form.querySelector("[data-trabajador-lookup]") ||
        queryByNameSuffix(form, "trabajador_principal_nombre", "#id_trabajador_principal_nombre");
      const principalHidden =
        form.querySelector("[data-trabajador-id]") ||
        queryByNameSuffix(form, "trabajador_principal", "#id_trabajador_principal");
      const extraHidden =
        form.querySelector("[data-trabajadores-extra]") ||
        queryByNameSuffix(form, "trabajadores_adicionales", "#id_trabajadores_adicionales");
      const manualHidden =
        form.querySelector("[data-trabajadores-manuales]") ||
        queryByNameSuffix(form, "trabajadores_manuales", "#id_trabajadores_manuales");
      const centrosHidden =
        form.querySelector("[data-trabajadores-centros-input]") ||
        queryByNameSuffix(form, "trabajadores_centros", "#id_trabajadores_centros");
      const centrosAdicionalesHidden =
        form.querySelector("[data-centros-adicionales-input]") ||
        queryByNameSuffix(form, "centros_trabajo_adicionales", "#id_centros_trabajo_adicionales");
      const centrosContainer = form.querySelector("[data-trabajadores-centros]");
      const extraInput =
        form.querySelector("[data-trabajador-extra-lookup]") ||
        form.querySelector("#trabajador-adicional-input");
      const extraAddBtn = form.querySelector("[data-trabajador-extra-add]");
      const manualOpenBtn = form.querySelector("[data-trabajador-manual-open]");
      const extraRows = form.querySelector("[data-trabajadores-extra-rows]");
      const toggleBtn = form.querySelector("[data-trabajadores-toggle]");
      const body = form.querySelector("[data-trabajadores-body]");
      const clearBtn = form.querySelector("[data-trabajadores-clear]");
      const openCentroBtn = form.querySelector("[data-trabajador-centro-open]");
      const centroModal = document.getElementById("trabajador-centro-modal");
      const manualModal =
        form.querySelector("[data-trabajador-manual-modal]") ||
        form.closest(".module-shell")?.querySelector("[data-trabajador-manual-modal]") ||
        document.querySelector("[data-trabajador-manual-modal]");

      const canAddCentro = form.dataset.centroCanAdd === "true";
      const canDeleteCentro = form.dataset.centroCanDelete === "true";

      const cctInput = queryByNameSuffix(form, "cct_codigo", "#id_cct_codigo");
      const cctNombre = queryByNameSuffix(form, "cct_nombre", "#id_cct_nombre");
      const cctModalidad = queryByNameSuffix(form, "cct_modalidad", "#id_cct_modalidad");
      const cctSistema = queryByNameSuffix(form, "cct_sistema", "#id_cct_sistema");
      const cctAsesor = queryByNameSuffix(form, "asesor_cct", "#id_asesor_cct");

      if (!principalHidden || !extraHidden || !centrosHidden) {
        return;
      }

    const parseJson = (value, fallback) => {
      if (!value) return fallback;
      try {
        const parsed = JSON.parse(value);
        return parsed ?? fallback;
      } catch (_err) {
        return fallback;
      }
    };

    const toId = (value) => String(value || "").trim();
    const isManualWorkerId = (value) => toId(value).startsWith("manual:");
    const makeManualWorkerId = () =>
      `manual:${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

    let principalId = principalHidden.value ? toId(principalHidden.value) : "";
    let centrosMap = parseJson(centrosHidden.value, {});
    if (!centrosMap || typeof centrosMap !== "object") {
      centrosMap = {};
    }

    const getCentrosAdicionalesSet = () => {
      const raw = centrosAdicionalesHidden ? centrosAdicionalesHidden.value : "";
      const list = parseJson(raw, []);
      const set = new Set();
      if (Array.isArray(list)) {
        list.forEach((item) => {
          const cct = typeof item === "string" ? item : item?.cct;
          if (cct) {
            set.add(String(cct).trim().toUpperCase());
          }
        });
      }
      return set;
    };

    const workers = new Map();

    const emitWorkerCatalogAdd = (worker) => {
      if (!worker || worker.manual || !worker.id || !worker.nombre) {
        return;
      }
      document.dispatchEvent(
        new CustomEvent("trabajador:catalogo-add", {
          detail: {
            id: worker.id,
            nombre: worker.nombre || "",
            rfc: worker.rfc || "",
            curp: worker.curp || "",
          },
        }),
      );
    };

    const addWorkerData = (data) => {
      if (!data || !data.id) {
        return;
      }
      const id = toId(data.id);
      const existing = workers.get(id) || {};
      const merged = {
        ...existing,
        ...data,
        id,
        nombre: data.nombre || existing.nombre || "",
        rfc: data.rfc || existing.rfc || "",
        curp: data.curp || existing.curp || "",
        manual: Boolean(data.manual || existing.manual || isManualWorkerId(id)),
      };
      workers.set(id, merged);
      emitWorkerCatalogAdd(merged);
      if (Array.isArray(merged.centros)) {
        const selected = centrosMap[id];
        const exists = selected
          ? merged.centros.some((centro) => toId(centro.cct) === selected)
          : true;
        if (selected && !exists) {
          delete centrosMap[id];
        }
      }
    };

    const buildWorkerLabel = (worker) => {
      if (!worker) {
        return "";
      }
      return [worker.nombre, worker.rfc, worker.curp]
        .map((value) => String(value || "").trim())
        .filter(Boolean)
        .join(" · ");
    };

    const replaceWorkerId = (fromId, toIdValue) => {
      const oldId = toId(fromId);
      const newId = toId(toIdValue);
      if (!oldId || !newId || oldId === newId || !workers.has(oldId)) {
        return;
      }
      workers.delete(oldId);
      if (centrosMap[oldId] && !centrosMap[newId]) {
        centrosMap[newId] = centrosMap[oldId];
      }
      delete centrosMap[oldId];
      if (principalId === oldId) {
        principalId = newId;
        if (principalHidden) {
          principalHidden.value = newId;
        }
      }
    };

    const promotePrincipal = (worker) => {
      const workerId = toId(worker?.id);
      if (!workerId) {
        return;
      }
      principalId = workerId;
      if (principalHidden) {
        principalHidden.value = workerId;
      }
      if (principalInput) {
        principalInput.value = buildWorkerLabel(worker) || worker.nombre || "";
      }
    };

    const fetchWorker = async (id) => {
      const workerId = toId(id);
      if (!workerId || isManualWorkerId(workerId) || !lookupUrl) return;
      try {
        const response = await fetch(`${lookupUrl}?id=${encodeURIComponent(workerId)}`);
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`);
        }
        const data = await response.json();
        addWorkerData(data);
        renderAll();
        if (principalId === workerId && data.centros && data.centros.length === 1) {
          if (!centrosMap[workerId]) {
            applyCentroToCct(workerId, data.centros[0]);
          }
        }
      } catch (error) {
        console.error("Error consultando trabajador:", error);
      }
    };

    const getOrderedWorkers = () => {
      const ordered = [];
      if (principalId && workers.has(principalId)) {
        ordered.push(workers.get(principalId));
      }
      Array.from(workers.values())
        .filter((worker) => worker.id !== principalId)
        .sort((a, b) => (a.nombre || "").localeCompare(b.nombre || ""))
        .forEach((worker) => ordered.push(worker));
      return ordered;
    };

    const syncExtraHidden = () => {
      if (!extraHidden) return;
      const extras = Array.from(workers.values()).filter(
        (worker) => worker.id !== principalId && !worker.manual,
      );
      const payload = extras.map((worker) => ({
        id: worker.id,
        nombre: worker.nombre || "",
        rfc: worker.rfc || "",
        curp: worker.curp || "",
      }));
      extraHidden.value = JSON.stringify(payload);
    };

    const syncManualHidden = () => {
      if (!manualHidden) return;
      const payload = Array.from(workers.values())
        .filter((worker) => worker.manual)
        .map((worker) => ({
          id: worker.id,
          nombre: worker.nombre || "",
          rfc: worker.rfc || "",
          curp: worker.curp || "",
          manual: true,
        }));
      manualHidden.value = JSON.stringify(payload);
    };

    const syncCentrosHidden = () => {
      if (!centrosHidden) return;
      centrosHidden.value = JSON.stringify(centrosMap);
    };

    const renderExtras = () => {
      if (!extraRows) return;
      const extras = Array.from(workers.values()).filter(
        (worker) => worker.id !== principalId,
      );
      if (!extras.length) {
        extraRows.innerHTML =
          '<tr class="table__empty-row"><td colspan="4" class="table__empty">No hay trabajadores adicionales.</td></tr>';
        return;
      }
      extraRows.innerHTML = extras
        .map(
          (worker) => `
          <tr>
            <td data-label="Nombre">
              ${worker.nombre || "-"}
              ${worker.manual ? '<span class="chip" style="margin-left:0.35rem;">Manual</span>' : ""}
            </td>
            <td data-label="RFC">${worker.rfc || "-"}</td>
            <td data-label="CURP">${worker.curp || "-"}</td>
            <td data-label="Acciones">
              ${worker.manual ? `<button type="button" class="table-actions__link" data-trabajador-manual-edit data-trabajador-id="${worker.id}">
                Editar
              </button>` : ""}
              <button type="button" class="table-actions__link table-actions__link--danger" data-trabajador-extra-remove data-trabajador-id="${worker.id}">
                Quitar
              </button>
            </td>
          </tr>
        `,
        )
        .join("");
    };

    const renderCentros = () => {
      if (!centrosContainer) return;
      const ordered = getOrderedWorkers();
      const adicionalesSet = getCentrosAdicionalesSet();
      const principalCct = (cctInput?.value || "").trim().toUpperCase();
      if (!ordered.length) {
        centrosContainer.innerHTML =
          '<p class="help-text">Selecciona un trabajador para ver sus centros de trabajo recientes.</p>';
        return;
      }
      centrosContainer.innerHTML = ordered
        .map((worker) => {
          const centrosRaw = Array.isArray(worker.centros) && worker.centros.length ? worker.centros : [];
          const centros =
            centrosRaw.length
              ? centrosRaw
              : Array.isArray(worker.registros)
                ? Array.from(
                    worker.registros.reduce((acc, registro) => {
                      const cct = String(registro.cct || "").trim();
                      if (!cct || acc.has(cct)) return acc;
                      acc.set(cct, {
                        cct,
                        nombre: registro.nombre || "",
                        asesor: "",
                        sistema: "",
                        modalidad: "",
                      });
                      return acc;
                    }, new Map())
                  ).map(([, value]) => value)
                : [];
          const ciclo = worker.ultimo_ciclo || "";
          const anio = worker.ultimo_anio || "";
          const preferido = centrosMap[worker.id] || "";
          const centroRows = centros.length
            ? centros
                .map(
                  (centro) => `
                  <div class="trabajador-centro-row">
                    <div>
                      <strong>${centro.cct || "-"}</strong><br>
                      <small>${centro.modalidad || ""}</small>
                    </div>
	                    <div>${centro.nombre || "-"}</div>
	                    <div>${centro.asesor || "-"}</div>
	                    <div class="table-actions">
	                      <button type="button" class="btn btn--ghost btn--sm" data-trabajador-center-use data-trabajador-id="${worker.id}" data-centro-cct="${centro.cct || ""}" data-centro-nombre="${centro.nombre || ""}" data-centro-sistema="${centro.sistema || ""}" data-centro-modalidad="${centro.modalidad || ""}" data-centro-asesor="${centro.asesor || ""}">
	                        ${preferido === centro.cct ? "Seleccionado" : isCaseForm ? "Usar en CCT" : "Usar"}
	                      </button>
	                      ${isCaseForm ? (
	                        centro.cct && centro.cct.toUpperCase() === principalCct
	                          ? `<button type="button" class="btn btn--ghost btn--sm" disabled>Es CCT principal</button>`
	                          : adicionalesSet.has((centro.cct || "").toUpperCase())
	                            ? `<button type="button" class="btn btn--ghost btn--sm" data-centro-caso-remove data-centro-cct="${centro.cct || ""}">Quitar del caso</button>`
	                            : `<button type="button" class="btn btn--secondary btn--sm" data-centro-caso-add data-centro-cct="${centro.cct || ""}" data-centro-nombre="${centro.nombre || ""}" data-centro-sistema="${centro.sistema || ""}" data-centro-modalidad="${centro.modalidad || ""}" data-centro-asesor="${centro.asesor || ""}">Agregar al caso</button>`
	                      ) : ""}
	                      ${canDeleteCentro ? `<button type="button" class="btn btn--danger btn--sm" data-trabajador-center-remove data-trabajador-id="${worker.id}" data-centro-cct="${centro.cct || ""}">Quitar</button>` : ""}
	                    </div>
	                  </div>
                `,
                )
                .join("")
            : '<div class="text-muted">Sin centros registrados para el último ciclo.</div>';
          return `
            <div class="trabajador-card" data-trabajador-id="${worker.id}">
              <div class="trabajador-card__header">
                <div>
                  <strong>${worker.nombre || "-"}</strong>
                  <div class="trabajador-card__meta">RFC: ${worker.rfc || "-"} · CURP: ${worker.curp || "-"}</div>
                </div>
                <div class="trabajador-card__meta">
                  ${worker.id === principalId ? '<span class="chip chip--strong">Principal</span>' : ""}
                  ${ciclo ? `<span class="chip">Ciclo: ${ciclo}</span>` : ""}
                  ${anio ? `<span class="chip">Año: ${anio}</span>` : ""}
                </div>
              </div>
	              <div class="trabajador-centros-list">
	                ${centroRows}
	              </div>
	              <p class="help-text">${isCaseForm ? "Agregar o quitar centros afecta solo este caso, no la plantilla." : "Seleccionar el centro preferido afecta solo este caso, no la plantilla."}</p>
	            </div>
	          `;
	        })
	        .join("");
	    };

	    const renderAll = () => {
      renderExtras();
      renderCentros();
      syncExtraHidden();
      syncManualHidden();
      syncCentrosHidden();
      syncWorkerSelectors(form, getOrderedWorkers());
    };

    const openManualModal = (worker = null) => {
      if (!manualModal) return;
      const modalForm = manualModal.querySelector("[data-trabajador-manual-form]");
      const idInput = manualModal.querySelector("[data-trabajador-manual-id]");
      const nameInput = modalForm?.querySelector('input[name="nombre"]');
      const rfcInput = modalForm?.querySelector('input[name="rfc"]');
      const curpInput = modalForm?.querySelector('input[name="curp"]');
      const title = manualModal.querySelector("[data-trabajador-manual-title]");
      const message = manualModal.querySelector("[data-trabajador-manual-message]");
      if (!modalForm || !idInput || !nameInput || !rfcInput || !curpInput) return;
      if (title) {
        title.textContent = worker ? "Editar trabajador nuevo" : "Agregar trabajador nuevo";
      }
      if (message) {
        message.textContent = "";
        message.className = "modal-message";
        message.style.display = "none";
      }
      idInput.value = worker?.id || "";
      nameInput.value = worker?.nombre || "";
      rfcInput.value = worker?.rfc || "";
      curpInput.value = worker?.curp || "";
      manualModal.hidden = false;
      nameInput.focus();
    };

    const closeManualModal = () => {
      if (!manualModal) return;
      const modalForm = manualModal.querySelector("[data-trabajador-manual-form]");
      const message = manualModal.querySelector("[data-trabajador-manual-message]");
      if (modalForm) {
        modalForm.reset();
      }
      if (message) {
        message.textContent = "";
        message.className = "modal-message";
        message.style.display = "none";
      }
      manualModal.hidden = true;
    };

	    const applyCentroToCct = (workerId, centro) => {
	      if (!centro || !centro.cct) {
	        return;
	      }
	      if (workerId) {
	        centrosMap[workerId] = centro.cct;
	        syncCentrosHidden();
	        renderCentros();
	      }
	      if (!cctInput) {
	        return;
	      }
	      cctInput.value = centro.cct;
	      cctInput.dispatchEvent(new Event("change"));
	      if (cctNombre && centro.nombre) {
	        cctNombre.value = centro.nombre;
	      }
	      if (cctModalidad && centro.modalidad) {
	        cctModalidad.value = centro.modalidad;
	      }
	      if (cctSistema && centro.sistema) {
	        cctSistema.value = centro.sistema;
	      }
	      if (cctAsesor && centro.asesor) {
	        cctAsesor.value = centro.asesor;
	        cctAsesor.dispatchEvent(new Event("change"));
	      }
	    };

    const updateToggleLabel = () => {
      if (!body || !toggleBtn) return;
      toggleBtn.textContent = body.hidden ? "Mostrar" : "Ocultar";
    };

    const loadInitial = () => {
      const manuales = parseJson(manualHidden?.value || "", []);
      if (Array.isArray(manuales)) {
        manuales.forEach((item) => {
          if (!item || typeof item !== "object") return;
          const id = toId(item.id) || makeManualWorkerId();
          addWorkerData({
            id,
            nombre: item.nombre || "",
            rfc: item.rfc || "",
            curp: item.curp || "",
            manual: true,
          });
        });
      }
      const extras = parseJson(extraHidden.value, []);
      if (Array.isArray(extras)) {
        extras.forEach((item) => {
          const id = toId(item?.id || item?.pk || item);
          if (!id) return;
          addWorkerData(item);
          fetchWorker(id);
        });
      }
      if (principalId) {
        addWorkerData({ id: principalId, nombre: principalInput?.value || "" });
        fetchWorker(principalId);
      }
      renderAll();
      updateToggleLabel();
    };

    document.addEventListener("trabajador:detalle", (event) => {
      const data = event.detail;
      if (!data || !data.id) return;
      const id = toId(data.id);
      if (principalHidden.value && toId(principalHidden.value) === id) {
        principalId = id;
      }
      addWorkerData(data);
      renderAll();
      if (body) {
        body.hidden = false;
      }
      updateToggleLabel();
    });

    document.addEventListener("trabajador:seleccion", (event) => {
      const selectedId = toId(event.detail?.id);
      if (!selectedId) return;
      principalId = selectedId;
      renderAll();
      if (body) {
        body.hidden = false;
      }
      updateToggleLabel();
    });

    if (principalInput) {
      principalInput.addEventListener("input", () => {
        if (principalInput.value.trim()) {
          return;
        }
        const previous = principalId;
        principalId = "";
        if (previous) {
          workers.delete(previous);
          delete centrosMap[previous];
        }
        if (principalHidden) {
          principalHidden.value = "";
        }
        renderAll();
        updateToggleLabel();
      });
    }

    if (extraRows) {
      extraRows.addEventListener("click", (event) => {
        const editManual = event.target.closest("[data-trabajador-manual-edit]");
        if (editManual) {
          const id = toId(editManual.dataset.trabajadorId);
          const worker = workers.get(id);
          if (worker && worker.manual) {
            openManualModal(worker);
          }
          return;
        }
        const target = event.target.closest("[data-trabajador-extra-remove]");
        if (!target) return;
        const id = toId(target.dataset.trabajadorId);
        if (!id) return;
        workers.delete(id);
        delete centrosMap[id];
        renderAll();
      });
    }

    let extraMap = new Map();
    let extraTimeout = null;
    if (extraInput && lookupUrl) {
      const datalistId = extraInput.getAttribute("list");
      const datalist = datalistId ? document.getElementById(datalistId) : null;
      const renderOptions = (results) => {
        if (!datalist) return;
        datalist.innerHTML = "";
        extraMap = new Map();
        results.forEach((item) => {
          const labelParts = [item.nombre, item.rfc, item.curp].filter(Boolean);
          const label = labelParts.join(" · ");
          extraMap.set(label, String(item.id));
          const option = document.createElement("option");
          option.value = label;
          datalist.appendChild(option);
        });
      };
      const fetchSuggestions = () => {
        const query = extraInput.value.trim();
        if (query.length < 2) {
          renderOptions([]);
          return;
        }
        fetch(`${lookupUrl}?q=${encodeURIComponent(query)}`)
          .then((response) => response.json())
          .then((data) => {
            renderOptions(data.results || []);
          })
          .catch((error) => console.error("Error buscando trabajadores:", error));
      };
      const scheduleFetch = () => {
        if (extraTimeout) {
          clearTimeout(extraTimeout);
        }
        extraTimeout = setTimeout(fetchSuggestions, 300);
      };
      extraInput.addEventListener("input", scheduleFetch);
      extraInput.addEventListener("search", scheduleFetch);
      extraInput.addEventListener("change", scheduleFetch);
    }

    if (extraAddBtn && extraInput) {
      extraAddBtn.addEventListener("click", () => {
        const label = extraInput.value.trim();
        const id = extraMap.get(label);
        if (!id) {
          window.alert("Selecciona un trabajador válido del catálogo.");
          return;
        }
        if (id === principalId) {
          window.alert("Ese trabajador ya está asignado como principal.");
          return;
        }
        if (workers.has(id)) {
          window.alert("Ese trabajador ya fue agregado.");
          return;
        }
        addWorkerData({ id });
        fetchWorker(id);
        extraInput.value = "";
      });
    }

    if (manualOpenBtn && manualModal) {
      manualOpenBtn.addEventListener("click", () => openManualModal());
    }

	    if (manualModal) {
	      const manualForm = manualModal.querySelector("[data-trabajador-manual-form]");
	      const closeManualBtns = manualModal.querySelectorAll("[data-trabajador-manual-close]");
      closeManualBtns.forEach((btn) => {
        btn.addEventListener("click", closeManualModal);
      });
      const overlay = manualModal.querySelector(".modal-overlay");
      if (overlay) {
        overlay.addEventListener("click", closeManualModal);
      }
	      if (manualForm) {
	        manualForm.addEventListener("submit", async (event) => {
	          event.preventDefault();
	          const idInput = manualForm.querySelector("[data-trabajador-manual-id]");
	          const nameInput = manualForm.querySelector('input[name="nombre"]');
	          const rfcInput = manualForm.querySelector('input[name="rfc"]');
	          const curpInput = manualForm.querySelector('input[name="curp"]');
          const message = manualModal.querySelector("[data-trabajador-manual-message]");
          const nombre = (nameInput?.value || "").trim();
	          if (!nombre) {
	            if (message) {
	              message.textContent = "El nombre del trabajador es obligatorio.";
	              message.className = "modal-message error";
	              message.style.display = "block";
            }
            nameInput?.focus();
            return;
          }
	          const rawId = toId(idInput?.value || "");
	          const rfc = (rfcInput?.value || "").trim().toUpperCase();
	          const curp = (curpInput?.value || "").trim().toUpperCase();

	          try {
	            if (lookupUrl) {
	              const body = new FormData();
	              body.append("nombre", nombre);
	              body.append("rfc", rfc);
	              body.append("curp", curp);
	              if (rawId && !rawId.startsWith("manual:")) {
	                body.append("id", rawId);
	              }
	              const response = await fetch(lookupUrl, {
	                method: "POST",
	                headers: {
	                  "X-Requested-With": "XMLHttpRequest",
	                  "X-CSRFToken": getCsrfToken(),
	                },
	                body,
	              });
	              let payload = {};
	              try {
	                payload = await response.json();
	              } catch (_err) {
	                payload = {};
	              }
		              if (!response.ok || !payload.id) {
	                const errorText =
	                  payload.error ||
	                  payload.detail ||
	                  "No se pudo guardar el trabajador en la base de datos.";
	                if (message) {
	                  message.textContent = errorText;
	                  message.className = "modal-message error";
	                  message.style.display = "block";
	                }
		                return;
		              }
		              const savedId = String(payload.id);
		              const shouldPromote = !principalId || (rawId && principalId === rawId);
		              replaceWorkerId(rawId, savedId);
		              const savedWorker = {
		                id: savedId,
		                nombre: payload.nombre || nombre,
		                rfc: payload.rfc || rfc,
		                curp: payload.curp || curp,
		                manual: false,
		              };
		              addWorkerData(savedWorker);
		              if (shouldPromote) {
		                promotePrincipal(savedWorker);
		              }
		            } else {
		              const manualId = rawId && workers.has(rawId) ? rawId : makeManualWorkerId();
		              const savedWorker = {
		                id: manualId,
		                nombre,
		                rfc,
		                curp,
		                manual: true,
		              };
		              addWorkerData(savedWorker);
		              if (!principalId) {
		                promotePrincipal(savedWorker);
		              }
		            }
	            renderAll();
	            closeManualModal();
	          } catch (_error) {
	            if (message) {
	              message.textContent = "No se pudo guardar el trabajador en la base de datos.";
	              message.className = "modal-message error";
	              message.style.display = "block";
	            }
	          }
	        });
	      }
	    }

    if (centrosContainer) {
      centrosContainer.addEventListener("click", (event) => {
        const useBtn = event.target.closest("[data-trabajador-center-use]");
        if (useBtn) {
          const workerId = toId(useBtn.dataset.trabajadorId);
          const centro = {
            cct: useBtn.dataset.centroCct || "",
            nombre: useBtn.dataset.centroNombre || "",
            sistema: useBtn.dataset.centroSistema || "",
            modalidad: useBtn.dataset.centroModalidad || "",
            asesor: useBtn.dataset.centroAsesor || "",
          };
          applyCentroToCct(workerId, centro);
          return;
        }
        const removeBtn = event.target.closest("[data-trabajador-center-remove]");
        if (removeBtn && deleteCentroUrl) {
          const workerId = toId(removeBtn.dataset.trabajadorId);
          const cct = removeBtn.dataset.centroCct || "";
          const worker = workers.get(workerId) || {};
          const formData = new FormData();
          formData.append("empleado_id", workerId);
          formData.append("cct", cct);
          if (worker.ultimo_ciclo) formData.append("ciclo", worker.ultimo_ciclo);
          if (worker.ultimo_anio) formData.append("anio", worker.ultimo_anio);
          fetch(deleteCentroUrl, {
            method: "POST",
            headers: { "X-Requested-With": "XMLHttpRequest", "X-CSRFToken": getCsrfToken() },
            body: formData,
          })
            .then((response) => {
              if (!response.ok) throw new Error(`HTTP ${response.status}`);
              return response.json();
            })
            .then((data) => {
              addWorkerData({ id: workerId, ...data });
              renderAll();
            })
            .catch((error) => console.error("Error eliminando centro:", error));
        }
        const addCasoBtn = event.target.closest("[data-centro-caso-add]");
        const removeCasoBtn = event.target.closest("[data-centro-caso-remove]");
        if (removeCasoBtn) {
          const detail = {
            cct: removeCasoBtn.dataset.centroCct || "",
          };
          form.dispatchEvent(new CustomEvent("centro:adicional:remove", { detail }));
          return;
        }
        if (addCasoBtn) {
          const detail = {
            cct: addCasoBtn.dataset.centroCct || "",
            nombre: addCasoBtn.dataset.centroNombre || "",
            sistema: addCasoBtn.dataset.centroSistema || "",
            modalidad: addCasoBtn.dataset.centroModalidad || "",
            asesor: addCasoBtn.dataset.centroAsesor || "",
          };
          form.dispatchEvent(new CustomEvent("centro:adicional:add", { detail }));
        }
      });
    }

    form.addEventListener("centro:adicional:changed", () => {
      renderCentros();
    });

    if (toggleBtn && body) {
      toggleBtn.addEventListener("click", () => {
        body.hidden = !body.hidden;
        updateToggleLabel();
      });
    }

    if (clearBtn) {
      clearBtn.addEventListener("click", () => {
        if (principalInput) principalInput.value = "";
        principalHidden.value = "";
        principalId = "";
        workers.clear();
        centrosMap = {};
        extraHidden.value = "";
        centrosHidden.value = "";
        renderAll();
        updateToggleLabel();
      });
    }

    if (openCentroBtn && centroModal && canAddCentro) {
      const modalForm = centroModal.querySelector("#trabajador-centro-form");
      const modalSelect = centroModal.querySelector("#trabajador-centro-empleado");
      const modalCct = centroModal.querySelector("#trabajador-centro-cct");
      const modalCiclo = centroModal.querySelector("#trabajador-centro-ciclo");
      const modalAnio = centroModal.querySelector("#trabajador-centro-anio");
      const modalMessage = centroModal.querySelector("[data-modal-message]");
      const closeBtns = centroModal.querySelectorAll("[data-modal-close]");

      const openModal = () => {
        if (!modalSelect) return;
        modalSelect.innerHTML = "";
        const ordered = getOrderedWorkers().filter((worker) => !worker.manual);
        if (!ordered.length) {
          window.alert("No hay trabajadores de plantilla para asociar centros de trabajo.");
          return;
        }
        ordered.forEach((worker) => {
          const option = document.createElement("option");
          option.value = worker.id;
          option.textContent = worker.nombre || `Trabajador ${worker.id}`;
          modalSelect.appendChild(option);
        });
        if (principalId) {
          modalSelect.value = principalId;
        }
        const worker = workers.get(modalSelect.value) || {};
        modalCiclo.value = worker.ultimo_ciclo || "";
        modalAnio.value = worker.ultimo_anio || "";
        if (modalMessage) {
          modalMessage.textContent = "";
          modalMessage.className = "modal-message";
          modalMessage.style.display = "none";
        }
        centroModal.hidden = false;
      };

      const closeModal = () => {
        centroModal.hidden = true;
        if (modalForm) modalForm.reset();
        if (modalMessage) {
          modalMessage.textContent = "";
          modalMessage.className = "modal-message";
          modalMessage.style.display = "none";
        }
      };

      openCentroBtn.addEventListener("click", openModal);
      closeBtns.forEach((btn) => btn.addEventListener("click", closeModal));

      if (modalSelect) {
        modalSelect.addEventListener("change", () => {
          const worker = workers.get(modalSelect.value) || {};
          modalCiclo.value = worker.ultimo_ciclo || "";
          modalAnio.value = worker.ultimo_anio || "";
        });
      }

      if (modalForm && addCentroUrl) {
        modalForm.addEventListener("submit", (event) => {
          event.preventDefault();
          const formData = new FormData(modalForm);
          fetch(addCentroUrl, {
            method: "POST",
            headers: { "X-Requested-With": "XMLHttpRequest", "X-CSRFToken": getCsrfToken() },
            body: formData,
          })
            .then((response) => {
              if (!response.ok) throw new Error(`HTTP ${response.status}`);
              return response.json();
            })
            .then((data) => {
              const workerId = toId(formData.get("empleado_id"));
              addWorkerData({ id: workerId, ...data });
              renderAll();
              closeModal();
            })
            .catch((error) => {
              if (modalMessage) {
                modalMessage.textContent = "No se pudo guardar el centro.";
                modalMessage.className = "modal-message error";
                modalMessage.style.display = "block";
              }
              console.error("Error agregando centro:", error);
            });
        });
      }
    }

      loadInitial();
    });
  }

  function initCentrosAdicionalesCaso() {
    const form = document.querySelector("[data-caso-interno-form]");
    if (!form) {
      return;
    }
    const hidden = form.querySelector("[data-centros-adicionales-input]");
    const input = form.querySelector("[data-centros-adicionales-search]");
    const addBtn = form.querySelector("[data-centros-adicionales-add]");
    const rows = form.querySelector("[data-centros-adicionales-rows]");
    const mainCctInput = form.querySelector("#id_cct_codigo");
    if (!hidden || !input || !addBtn || !rows) {
      return;
    }

    const parseJson = (value, fallback) => {
      if (!value) return fallback;
      try {
        const parsed = JSON.parse(value);
        return parsed ?? fallback;
      } catch (_err) {
        return fallback;
      }
    };

    const normalizeItem = (item) => {
      if (!item) return null;
      if (typeof item === "string") {
        return { cct: item.trim().toUpperCase(), nombre: "", asesor: "", modalidad: "", sistema: "" };
      }
      if (typeof item === "object") {
        const cct = String(item.cct || item.codigo || "").trim().toUpperCase();
        if (!cct) return null;
        return {
          cct,
          nombre: item.nombre || "",
          asesor: item.asesor || "",
          modalidad: item.modalidad || "",
          sistema: item.sistema || item.sostenimiento || "",
        };
      }
      return null;
    };

    const findOption = (cct) => {
      const options = Array.from(document.querySelectorAll("#cct-options option"));
      return options.find((opt) => (opt.value || "").toUpperCase() === cct);
    };

    const buildFromOption = (cct) => {
      const option = findOption(cct);
      if (!option) {
        return { cct, nombre: "", asesor: "", modalidad: "", sistema: "" };
      }
      return {
        cct,
        nombre: option.dataset.nombre || "",
        asesor: option.dataset.asesor || "",
        modalidad: option.dataset.servicio || "",
        sistema: option.dataset.sostenimiento || "",
      };
    };

    let items = [];
    const initial = parseJson(hidden.value, []);
    if (Array.isArray(initial)) {
      initial.forEach((item) => {
        const normalized = normalizeItem(item);
        if (normalized) {
          const enriched = buildFromOption(normalized.cct);
          items.push({ ...normalized, ...enriched });
        }
      });
    }

    const syncHidden = () => {
      hidden.value = JSON.stringify(
        items.map((item) => ({
          cct: item.cct,
          nombre: item.nombre || "",
          asesor: item.asesor || "",
          modalidad: item.modalidad || "",
          sistema: item.sistema || "",
        })),
      );
    };

    const render = () => {
      if (!items.length) {
        rows.innerHTML =
          '<tr class="table__empty-row"><td colspan="4" class="table__empty">No hay centros adicionales.</td></tr>';
        return;
      }
      rows.innerHTML = items
        .map(
          (item) => `
          <tr>
            <td data-label="CCT">${item.cct}</td>
            <td data-label="Nombre">${item.nombre || "-"}</td>
            <td data-label="Asesor">${item.asesor || "-"}</td>
            <td data-label="Acciones">
              <button type="button" class="table-actions__link table-actions__link--danger" data-centro-adicional-remove data-centro-cct="${item.cct}">
                Quitar
              </button>
            </td>
          </tr>
        `,
        )
        .join("");
    };

    const removeIfPrincipal = () => {
      const principal = (mainCctInput?.value || "").trim().toUpperCase();
      if (!principal) return;
      const before = items.length;
      items = items.filter((item) => item.cct !== principal);
      if (items.length !== before) {
        syncHidden();
        render();
      }
    };

    const addCentro = () => {
      const raw = input.value.trim();
      if (!raw) {
        window.alert("Selecciona un CCT válido del catálogo.");
        return;
      }
      const cct = raw.toUpperCase();
      const principal = (mainCctInput?.value || "").trim().toUpperCase();
      if (principal && principal === cct) {
        window.alert("Ese CCT ya está asignado como principal.");
        return;
      }
      if (items.some((item) => item.cct === cct)) {
        window.alert("Ese CCT ya fue agregado.");
        return;
      }
      const option = findOption(cct);
      if (!option) {
        window.alert("Selecciona un CCT válido del catálogo.");
        return;
      }
      items.push(buildFromOption(cct));
      syncHidden();
      render();
      form.dispatchEvent(new CustomEvent("centro:adicional:changed"));
      input.value = "";
    };

    const addCentroData = (data) => {
      if (!data) return;
      const cct = String(data.cct || "").trim().toUpperCase();
      if (!cct) return;
      const principal = (mainCctInput?.value || "").trim().toUpperCase();
      if (principal && principal === cct) {
        return;
      }
      if (items.some((item) => item.cct === cct)) {
        return;
      }
      const base = {
        cct,
        nombre: data.nombre || "",
        asesor: data.asesor || "",
        modalidad: data.modalidad || "",
        sistema: data.sistema || "",
      };
      const enriched = buildFromOption(cct);
      items.push({ ...enriched, ...base });
      syncHidden();
      render();
      form.dispatchEvent(new CustomEvent("centro:adicional:changed"));
    };

    addBtn.addEventListener("click", addCentro);
    input.addEventListener("keydown", (event) => {
      if (event.key === "Enter") {
        event.preventDefault();
        addCentro();
      }
    });
    rows.addEventListener("click", (event) => {
      const btn = event.target.closest("[data-centro-adicional-remove]");
      if (!btn) return;
      const cct = (btn.dataset.centroCct || "").toUpperCase();
      items = items.filter((item) => item.cct !== cct);
      syncHidden();
      render();
      form.dispatchEvent(new CustomEvent("centro:adicional:changed"));
    });
    if (mainCctInput) {
      mainCctInput.addEventListener("change", removeIfPrincipal);
    }

    syncHidden();
    render();

    form.addEventListener("centro:adicional:add", (event) => {
      addCentroData(event.detail);
    });

    form.addEventListener("centro:adicional:remove", (event) => {
      const cct = String(event.detail?.cct || "").trim().toUpperCase();
      if (!cct) return;
      items = items.filter((item) => item.cct !== cct);
      syncHidden();
      render();
      form.dispatchEvent(new CustomEvent("centro:adicional:changed"));
    });
  }

  const updateWorkerSelectOptions = (select, workers, currentValue = "") => {
    if (!select) return;
    const placeholder =
      select.dataset.placeholder || "Selecciona un trabajador";
    const desired = (currentValue || "").trim();
    select.innerHTML = "";
    const placeholderOption = document.createElement("option");
    placeholderOption.value = "";
    placeholderOption.textContent = placeholder;
    select.appendChild(placeholderOption);
    workers.forEach((worker) => {
      if (!worker?.nombre) return;
      const option = document.createElement("option");
      option.value = worker.nombre;
      option.textContent = worker.nombre;
      option.dataset.initials = worker.initials || buildInitials(worker.nombre);
      select.appendChild(option);
    });
    if (desired) {
      select.value = desired;
    }
  };

  const syncWorkerSelectors = (form, workers) => {
    if (!form) return;
    const list = (workers || [])
      .map((worker) => ({
        ...worker,
        nombre: (worker?.nombre || "").trim(),
        initials: buildInitials(worker?.nombre || ""),
      }))
      .filter((worker) => worker.nombre);

    const participantSelects = form.querySelectorAll("[data-trabajador-select]");
    participantSelects.forEach((select) => {
      const role = select.dataset.trabajadorRole || "";
      const nameInput = role
        ? form.querySelector(`[name$='${role}_nombre']`)
        : null;
      const current = (select.value || nameInput?.value || "").trim();
      updateWorkerSelectOptions(select, list, current);
      select.disabled = list.length === 0;
    });

    const incidenciaSelects = form.querySelectorAll(
      "[data-incidencia-worker-select]",
    );
    incidenciaSelects.forEach((select) => {
      const section = select.closest("[data-incidencias]") || form;
      const input = section?.querySelector(
        'input[name$="incidencia_nombre_docente"]',
      );
      const current = (select.value || input?.value || "").trim();
      updateWorkerSelectOptions(select, list, current);
      const wrapper = select.closest("[data-incidencia-worker-field]");
      if (wrapper) {
        wrapper.hidden = list.length === 0;
      }
      select.disabled = list.length === 0;
      if (list.length === 1 && input && !input.value.trim()) {
        setInputValue(input, list[0].nombre);
        select.value = list[0].nombre;
      } else if (!list.length && input) {
        setInputValue(input, "");
      }
      select.dispatchEvent(new Event("change", { bubbles: true }));
    });

    const rangoWorkerSelects = form.querySelectorAll(
      "[data-rango-fechas-worker-select]",
    );
    rangoWorkerSelects.forEach((select) => {
      const current = (select.value || "").trim();
      updateWorkerSelectOptions(select, list, current);
      select.disabled = list.length === 0;
    });
  };

  function initTrabajadorSelectors() {
    const participantSelects = document.querySelectorAll(
      "[data-trabajador-select]",
    );
    const incidenciaSelects = document.querySelectorAll(
      "[data-incidencia-worker-select]",
    );
    if (!participantSelects.length && !incidenciaSelects.length) {
      return;
    }

    participantSelects.forEach((select) => {
      const form = select.closest("form") || document;
      const role = select.dataset.trabajadorRole || "";
      if (!role) return;
      const nameInput = form.querySelector(`[name$='${role}_nombre']`);
      if (nameInput && nameInput.value && !select.value) {
        select.value = nameInput.value;
      }
      const optionCount = Math.max(select.options.length - 1, 0);
      if (optionCount === 0) {
        select.disabled = true;
      }
      const initialsInput = form.querySelector(`[name$='${role}_iniciales']`);
      if (select.value && initialsInput && !initialsInput.value.trim()) {
        setInputValue(initialsInput, buildInitials(select.value));
      }
      select.addEventListener("change", () => {
        const name = (select.value || "").trim();
        if (!name) return;
        const initials =
          select.selectedOptions?.[0]?.dataset?.initials ||
          buildInitials(name);
        setInputValue(nameInput, name);
        if (initialsInput) {
          setInputValue(initialsInput, initials);
        }
      });
    });

    incidenciaSelects.forEach((select) => {
      const section = select.closest("[data-incidencias]") || select.closest("form");
      const input = section?.querySelector(
        'input[name$="incidencia_nombre_docente"]',
      );
      if (input && input.value && !select.value) {
        select.value = input.value;
      }
      const optionCount = Math.max(select.options.length - 1, 0);
      const wrapper = select.closest("[data-incidencia-worker-field]");
      if (wrapper) {
        wrapper.hidden = optionCount === 0;
      }
      select.disabled = optionCount === 0;
      if (optionCount === 1 && input && !input.value.trim()) {
        const onlyOption = select.options[1];
        if (onlyOption) {
          select.value = onlyOption.value;
          setInputValue(input, onlyOption.value);
        }
      }
      select.addEventListener("change", () => {
        const name = (select.value || "").trim();
        if (!input) return;
        setInputValue(input, name);
      });
    });

    const rangoWorkerSelects = document.querySelectorAll(
      "[data-rango-fechas-worker-select]",
    );
    rangoWorkerSelects.forEach((select) => {
      const optionCount = Math.max(select.options.length - 1, 0);
      select.disabled = optionCount === 0;
    });
  }

  function initTrabajadorQuickFill() {
    const resolveTargetForm = (button) => {
      const summary = button.closest("[data-trabajador-summary]");
      const target = summary ? summary.dataset.targetForm : "";
      const selector =
        target === "caso" ? "[data-caso-interno-form]" : "[data-tramite-caso-form]";
      const forms = Array.from(document.querySelectorAll(selector));
      if (!forms.length) {
        return null;
      }
      return (
        forms.find((form) => form.offsetParent !== null) ||
        forms.find((form) => !form.hasAttribute("hidden")) ||
        forms[0]
      );
    };

    document.addEventListener("click", (event) => {
      const button = event.target.closest("[data-trabajador-use]");
      if (!button) {
        return;
      }
      const nombre = button.dataset.trabajadorNombre || "";
      if (!nombre) {
        return;
      }
      const role = button.dataset.trabajadorUse;
      if (!role) {
        return;
      }
      const form = resolveTargetForm(button);
      if (!form) {
        return;
      }
      const input = form.querySelector(`[name$='${role}_nombre']`);
      const initialsInput = form.querySelector(`[name$='${role}_iniciales']`);
      const select = form.querySelector(
        `[data-trabajador-select][data-trabajador-role='${role}']`,
      );
      if (select) {
        select.value = nombre;
      }
      setInputValue(input, nombre);
      if (initialsInput) {
        setInputValue(initialsInput, buildInitials(nombre));
      }
    });
  }

  function initFilterToggle() {
    const toggleBtn = document.querySelector("[data-filters-toggle]");
    const panel = document.querySelector("[data-filters-panel]");
    if (!toggleBtn || !panel) {
      return;
    }
    const hiddenClass = "is-hidden";
    const applyState = (hide) => {
      panel.classList.toggle(hiddenClass, hide);
      panel.hidden = hide;
      toggleBtn.textContent = hide ? "Mostrar filtros" : "Ocultar filtros";
    };
    // Oculto por defecto al cargar
    applyState(true);
    toggleBtn.addEventListener("click", () => {
      const hide = !panel.hidden;
      applyState(hide);
    });
  }

  const normaliseSistema = (value) => {
    const trimmed = (value || "").trim();
    return trimmed.toUpperCase() === "FEDERAL TRANSFERIDO" ? "FEDERAL" : trimmed;
  };

  function initSortableTables() {
    const tables = document.querySelectorAll('[data-table-sortable="true"]');
    if (!tables.length) return;

    const getCellValue = (row, index) => {
      const cell = row.children[index];
      if (!cell) return "";
      const raw = cell.dataset.sortValue || cell.textContent || "";
      const value = raw.toString().trim();
      const num = Number(value);
      if (!Number.isNaN(num) && value !== "") {
        return num;
      }
      return value.toLowerCase();
    };

    const sortTable = (table, columnIndex, direction) => {
      const tbody = table.querySelector("tbody");
      if (!tbody) return;
      const rows = Array.from(tbody.querySelectorAll("tr"));
      const dataRows = rows.filter((row) => !row.classList.contains("table__empty"));
      const emptyRows = rows.filter((row) => row.classList.contains("table__empty"));

      dataRows.sort((a, b) => {
        const aVal = getCellValue(a, columnIndex);
        const bVal = getCellValue(b, columnIndex);
        if (aVal < bVal) return direction === "asc" ? -1 : 1;
        if (aVal > bVal) return direction === "asc" ? 1 : -1;
        return 0;
      });

      [...dataRows, ...emptyRows].forEach((row) => tbody.appendChild(row));
    };

    tables.forEach((table) => {
      const headers = table.querySelectorAll("th[data-sort-key]");
      headers.forEach((th, index) => {
        th.tabIndex = 0;
        th.classList.add("table__sortable");
        th.setAttribute("role", "button");
        th.setAttribute("aria-sort", "none");

        const toggleSort = () => {
          const current = th.getAttribute("data-sort-direction") || "none";
          const next = current === "asc" ? "desc" : "asc";
          headers.forEach((h) => {
            h.setAttribute("aria-sort", "none");
            h.removeAttribute("data-sort-direction");
          });
          th.setAttribute("data-sort-direction", next);
          th.setAttribute("aria-sort", next === "asc" ? "ascending" : "descending");
          sortTable(table, index, next);
        };

        th.addEventListener("click", toggleSort);
        th.addEventListener("keydown", (event) => {
          if (event.key === "Enter" || event.key === " ") {
            event.preventDefault();
            toggleSort();
          }
        });
      });
    });
  }

  function initBulkCasoActions() {
    const bulkForm = document.querySelector("#bulk-form");
    if (!bulkForm) return;
    const actionSelect = bulkForm.querySelector("#bulk-action");
    const tramiteFields = bulkForm.querySelector("[data-bulk-tramite]");
    const convertFields = bulkForm.querySelector("[data-bulk-convert]");
    const estatusFields = bulkForm.querySelector("[data-bulk-estatus]");
    const modal = document.querySelector("#bulk-tramite-modal");
    const convertModal = document.querySelector("#bulk-convert-modal");
    const openModalBtn = bulkForm.querySelector("[data-bulk-tramite-open]");
    const openConvertBtn = bulkForm.querySelector("[data-bulk-convert-open]");
    const closeModalBtns = modal ? modal.querySelectorAll("[data-modal-close]") : [];
    const closeConvertBtns = convertModal ? convertModal.querySelectorAll("[data-modal-close]") : [];
    const selectAll = document.querySelector("#select-all-casos");
    const caseChecks = Array.from(document.querySelectorAll(".select-caso"));
    const counter = bulkForm.querySelector("[data-bulk-count]");
    const submitBtn = bulkForm.querySelector("[data-bulk-submit]");

    const toggleFields = () => {
      const value = actionSelect?.value || "";
      if (tramiteFields) {
        tramiteFields.style.display = value === "agregar_tramite" ? "grid" : "none";
      }
      if (convertFields) {
        convertFields.style.display = value === "convertir_anexo" ? "grid" : "none";
      }
      if (estatusFields) {
        estatusFields.style.display = value === "agregar_estatus" ? "grid" : "none";
      }
      const toggleInputs = (container, enable) => {
        if (!container) return;
        const controls = container.querySelectorAll("input, select, textarea");
        controls.forEach((control) => {
          if (!control.dataset.requiredStored) {
            control.dataset.requiredStored = control.required ? "1" : "0";
          }
          control.disabled = !enable;
          if (enable) {
            control.required = control.dataset.requiredStored === "1";
          } else {
            control.required = false;
          }
        });
      };
      toggleInputs(tramiteFields, value === "agregar_tramite");
      toggleInputs(modal, value === "agregar_tramite");
      toggleInputs(convertFields, value === "convertir_anexo");
      toggleInputs(convertModal, value === "convertir_anexo");
      toggleInputs(estatusFields, value === "agregar_estatus");
    };

    actionSelect?.addEventListener("change", toggleFields);
    toggleFields();

    if (selectAll) {
      selectAll.addEventListener("change", () => {
        caseChecks.forEach((check) => {
          check.checked = selectAll.checked;
        });
        updateCounter();
      });
    }

    if (modal) {
      const modalInputs = modal.querySelectorAll("input, select, textarea, button");
      modalInputs.forEach((input) => {
        if (input.form) return;
        input.setAttribute("form", "bulk-form");
      });
    }
    if (convertModal) {
      const modalInputs = convertModal.querySelectorAll("input, select, textarea, button");
      modalInputs.forEach((input) => {
        if (input.form) return;
        input.setAttribute("form", "bulk-form");
      });
    }

    if (openModalBtn && modal) {
      openModalBtn.addEventListener("click", () => {
        if (actionSelect) {
          actionSelect.value = "agregar_tramite";
          toggleFields();
        }
        modal.hidden = false;
        if (modal.dataset.inited === "true") {
          return;
        }
        const prefijoSelect = modal.querySelector("[data-prefijo-oficio-select]");
        if (prefijoSelect) {
          initPrefijoOficioMulti();
        }
        initReceptoresAdicionales();
        initGeneradoresAdicionales();
        initIncidenciasSections();
        modal.dataset.inited = "true";
      });
      closeModalBtns.forEach((btn) => {
        btn.addEventListener("click", () => {
          modal.hidden = true;
        });
      });
    }
    if (openConvertBtn && convertModal) {
      openConvertBtn.addEventListener("click", () => {
        if (actionSelect) {
          actionSelect.value = "convertir_anexo";
          toggleFields();
        }
        convertModal.hidden = false;
      });
      closeConvertBtns.forEach((btn) => {
        btn.addEventListener("click", () => {
          convertModal.hidden = true;
        });
      });
    }

    const modalSubmitBtn = modal ? modal.querySelector("[data-bulk-tramite-submit]") : null;
    if (modalSubmitBtn && bulkForm) {
      modalSubmitBtn.addEventListener("click", (event) => {
        event.preventDefault();
        if (actionSelect) {
          actionSelect.value = "agregar_tramite";
          toggleFields();
        }
        bulkForm.requestSubmit();
      });
    }
    const convertSubmitBtn = convertModal ? convertModal.querySelector("[data-bulk-convert-submit]") : null;
    if (convertSubmitBtn && bulkForm) {
      convertSubmitBtn.addEventListener("click", (event) => {
        event.preventDefault();
        if (actionSelect) {
          actionSelect.value = "convertir_anexo";
          toggleFields();
        }
        bulkForm.requestSubmit();
      });
    }

    if (bulkForm) {
      bulkForm.addEventListener("submit", (event) => {
        const value = actionSelect?.value || "";
        if (value !== "convertir_anexo") return;
        const eliminar = bulkForm.querySelector('input[name="eliminar_caso_origen"]');
        const confirmar = bulkForm.querySelector('input[name="confirmar_eliminacion"]');
        const confirmText = bulkForm.querySelector('input[name="confirmacion_textual"]');
        if (eliminar && eliminar.checked) {
          const textValue = (confirmText?.value || "").trim().toUpperCase();
          if (!confirmar?.checked || textValue !== "ELIMINAR") {
            event.preventDefault();
            if (convertModal) {
              convertModal.hidden = false;
              const focusTarget = !confirmar?.checked ? confirmar : confirmText;
              focusTarget?.focus();
            }
          }
        }
      });
    }

    const updateCounter = () => {
      const selected = caseChecks.filter((check) => check.checked).length;
      if (counter) {
        counter.textContent = `${selected} seleccionados`;
      }
      if (submitBtn) {
        submitBtn.disabled = selected === 0;
      }
    };

    caseChecks.forEach((check) => {
      check.addEventListener("change", updateCounter);
    });
    updateCounter();
  }

  function initInboxEnhancements() {
    const searchInput = document.querySelector(".inbox-filters__search input[type='search']");
    const query = searchInput ? (searchInput.value || "").trim() : "";
    if (query) {
      const terms = query
        .split(/\s+/)
        .filter(Boolean)
        .map((term) => term.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"));
      if (terms.length) {
        const regex = new RegExp(`(${terms.join("|")})`, "gi");
        document.querySelectorAll("[data-inbox-text]").forEach((node) => {
          node.innerHTML = node.innerHTML.replace(regex, '<mark class=\"inbox-highlight\">$1</mark>');
        });
      }
    }

    document.querySelectorAll("[data-mark-read-form]").forEach((form) => {
      form.addEventListener("submit", async (event) => {
        event.preventDefault();
        const card = form.closest("[data-inbox-item]");
        if (!card) return;
        const data = new FormData(form);
        try {
          const response = await fetch(form.action, {
            method: "POST",
            body: data,
            headers: { "X-Requested-With": "XMLHttpRequest" },
          });
          if (!response.ok) {
            form.submit();
            return;
          }
          card.classList.remove("inbox-item--unread");
          card.classList.add("inbox-item--read");
          const badge = card.querySelector(".inbox-item__new");
          if (badge) badge.remove();
          const status = card.querySelector(".inbox-item__status .status-chip");
          if (status) {
            status.textContent = "Leído";
            status.classList.remove("status-chip--pendiente-por-informacion");
            status.classList.add("status-chip--concluido");
          }
          form.remove();
          const navBadge = document.querySelector("[data-inbox-count]");
          if (navBadge) {
            const current = Number(navBadge.textContent.trim()) || 0;
            const next = Math.max(current - 1, 0);
            if (next === 0) {
              navBadge.remove();
            } else {
              navBadge.textContent = String(next);
              navBadge.setAttribute("aria-label", `${next} no leídas`);
            }
          }
        } catch (error) {
          form.submit();
        }
      });
    });

    const markAllForm = document.querySelector("[data-mark-all-form]");
    if (markAllForm) {
      markAllForm.addEventListener("submit", async (event) => {
        event.preventDefault();
        const data = new FormData(markAllForm);
        try {
          const response = await fetch(markAllForm.action, {
            method: "POST",
            body: data,
            headers: { "X-Requested-With": "XMLHttpRequest" },
          });
          if (!response.ok) {
            markAllForm.submit();
            return;
          }
          document.querySelectorAll("[data-inbox-item]").forEach((card) => {
            card.classList.remove("inbox-item--unread");
            card.classList.add("inbox-item--read");
            const badge = card.querySelector(".inbox-item__new");
            if (badge) badge.remove();
            const status = card.querySelector(".inbox-item__status .status-chip");
            if (status) {
              status.textContent = "Leído";
              status.classList.remove("status-chip--pendiente-por-informacion");
              status.classList.add("status-chip--concluido");
            }
            const form = card.querySelector("[data-mark-read-form]");
            if (form) form.remove();
          });
          const navBadge = document.querySelector("[data-inbox-count]");
          if (navBadge) {
            navBadge.remove();
          }
        } catch (error) {
          markAllForm.submit();
        }
      });
    }
  }

  function setupCCTForm(options) {
    const {
      form,
      lookupUrl = "",
      apiBase = "",
      cctInput,
      hiddenCctInput,
      nombreInput,
      servicioInput,
      sistemaInput,
      asesorInput,
      datalist,
      suggestionsContainer,
      modalId = "cct-modal",
      canCreate = false,
      canEdit = false,
      canDelete = false,
    } = options;
    if (!form || !cctInput || !hiddenCctInput || !nombreInput || !servicioInput || !datalist) {
      return;
    }

    const normalize = (value) => (value || "").trim().toUpperCase();
    const SUGGESTION_MIN_LENGTH = 3;
    const LOOKUP_MIN_LENGTH = 10;
    const SUGGESTION_DEBOUNCE = 200;
    let suggestionTimer = null;
    let suggestionAbortController = null;

    const upsertOption = (item) => {
      if (!item || !item.cct) {
        return;
      }
      const code = normalize(item.cct);
      const sistemaNormalizado = normaliseSistema(item.sostenimiento);
      item.sostenimiento = sistemaNormalizado;
      const existing = Array.from(datalist.options).find(
        (opt) => normalize(opt.value || opt.text) === code,
      );
      const label = `${code} · ${item.nombre || ""}`.trim();
      if (existing) {
        existing.value = code;
        existing.textContent = label;
        existing.dataset.nombre = item.nombre || "";
        existing.dataset.servicio = item.servicio || "";
        existing.dataset.asesor = item.asesor || "";
        existing.dataset.sostenimiento = sistemaNormalizado;
        existing.setAttribute("data-nombre", item.nombre || "");
        existing.setAttribute("data-servicio", item.servicio || "");
        existing.setAttribute("data-asesor", item.asesor || "");
        existing.setAttribute("data-sostenimiento", sistemaNormalizado);
      } else {
        const option = document.createElement("option");
        option.value = code;
        option.textContent = label;
        option.dataset.nombre = item.nombre || "";
        option.dataset.servicio = item.servicio || "";
        option.dataset.asesor = item.asesor || "";
        option.dataset.sostenimiento = sistemaNormalizado;
        option.setAttribute("data-nombre", item.nombre || "");
        option.setAttribute("data-servicio", item.servicio || "");
        option.setAttribute("data-asesor", item.asesor || "");
        option.setAttribute("data-sostenimiento", sistemaNormalizado);
        datalist.appendChild(option);
      }
    };

    const updateFromOption = (codigo) => {
      const option = Array.from(datalist.options).find(
        (opt) => normalize(opt.value || opt.text) === codigo,
      );
      if (!option) {
        return false;
      }
      nombreInput.value =
        option.dataset?.nombre || option.getAttribute("data-nombre") || "";
      servicioInput.value =
        option.dataset?.servicio || option.getAttribute("data-servicio") || "";
      const sistemaDato =
        option.dataset?.sostenimiento ||
        option.getAttribute("data-sostenimiento") ||
        "";
      if (sistemaInput) {
        sistemaInput.value = normaliseSistema(sistemaDato);
      }
      if (asesorInput) {
        asesorInput.value =
          option.dataset?.asesor || option.getAttribute("data-asesor") || "";
        asesorInput.dispatchEvent(new Event("change"));
      }
      hiddenCctInput.value = codigo;
      return true;
    };

    const fetchAndUpdate = async (codigo) => {
      if (!lookupUrl) {
        return null;
      }
      try {
        const response = await fetch(`${lookupUrl}?cct=${encodeURIComponent(codigo)}`, {
          headers: { "X-Requested-With": "XMLHttpRequest" },
        });
        if (!response.ok) {
          if (response.status === 404) {
            return null;
          }
          throw new Error("No fue posible consultar la información del CCT.");
        }
        const data = await response.json();
        if (!data.found) {
          return null;
        }
        const item = {
          cct: data.cct || codigo,
          nombre: data.c_nombre || "",
          sostenimiento: normaliseSistema(data.sostenimiento_c_subcontrol),
          servicio: data.tiponivelsub_c_servicion3 || "",
          asesor: data.asesor || "",
        };
        nombreInput.value = item.nombre;
        if (sistemaInput) {
          sistemaInput.value = item.sostenimiento;
        }
        servicioInput.value = item.servicio;
      if (asesorInput) {
        asesorInput.value = item.asesor;
        asesorInput.dispatchEvent(new Event("change"));
      }
        hiddenCctInput.value = item.cct;
        return item;
      } catch (error) {
        console.warn(error);
        return null;
      }
    };

    const hideSuggestions = () => {
      if (!suggestionsContainer) {
        return;
      }
      suggestionsContainer.innerHTML = "";
      suggestionsContainer.hidden = true;
    };

    const renderSuggestions = (items) => {
      if (!suggestionsContainer) {
        return;
      }
      suggestionsContainer.innerHTML = "";
      if (!items.length) {
        suggestionsContainer.hidden = true;
        return;
      }
      const list = document.createElement("ul");
      list.className = "cct-suggestion-list";
      items.forEach((item) => {
        const entry = document.createElement("li");
        entry.className = "cct-suggestion-item";
        const button = document.createElement("button");
        button.type = "button";
        button.className = "btn btn--ghost btn--sm";
        button.textContent = `${item.cct} · ${item.nombre || ""}`.trim();
        button.addEventListener("mousedown", (event) => {
          event.preventDefault();
          applySuggestion(item);
        });
        entry.appendChild(button);
        list.appendChild(entry);
      });
      suggestionsContainer.appendChild(list);
      suggestionsContainer.hidden = false;
    };

    const applySuggestion = (item) => {
      if (!item) {
        return;
      }
      const code = normalize(item.cct);
      cctInput.value = code;
      hiddenCctInput.value = code;
      nombreInput.value = item.nombre || "";
      if (sistemaInput) {
        sistemaInput.value = item.sostenimiento || "";
      }
      servicioInput.value = item.servicio || "";
      if (asesorInput) {
        asesorInput.value = item.asesor || "";
        asesorInput.dispatchEvent(new Event("change"));
      }
      upsertOption(item);
      hideSuggestions();
      void fetchAndUpdate(code);
    };

    const fetchSuggestions = async (term) => {
      if (!suggestionsContainer || !apiBase) {
        return;
      }
      if (suggestionAbortController) {
        suggestionAbortController.abort();
      }
      suggestionAbortController = new AbortController();
      try {
        const url = new URL(apiBase, window.location.origin);
        url.searchParams.set("search", term);
        url.searchParams.set("ordering", "cct");
        url.searchParams.set("page_size", "7");
        const response = await fetch(url, {
          headers: { Accept: "application/json" },
          signal: suggestionAbortController.signal,
        });
        if (!response.ok) {
          throw new Error("No fue posible obtener sugerencias.");
        }
        const data = await response.json();
        const items = Array.isArray(data?.results)
          ? data.results
          : Array.isArray(data)
            ? data
            : [];
        items.forEach((entry) => {
          entry.sostenimiento = normaliseSistema(entry.sostenimiento);
        });
        renderSuggestions(items);
      } catch (error) {
        if (error.name !== "AbortError") {
          console.warn(error);
        }
        hideSuggestions();
      } finally {
        suggestionAbortController = null;
      }
    };

    const scheduleSuggestions = (term) => {
      if (!suggestionsContainer) {
        return;
      }
      if (suggestionTimer) {
        window.clearTimeout(suggestionTimer);
      }
      suggestionTimer = window.setTimeout(() => {
        fetchSuggestions(term);
      }, SUGGESTION_DEBOUNCE);
    };

    const handleChange = async () => {
      hideSuggestions();
      const codigo = normalize(cctInput.value);
      if (!codigo) {
        hiddenCctInput.value = "";
        nombreInput.value = "";
        servicioInput.value = "";
        if (sistemaInput) {
          sistemaInput.value = "";
        }
        if (asesorInput) {
          asesorInput.value = "";
        }
        return;
      }
      if (updateFromOption(codigo)) {
        hiddenCctInput.value = codigo;
        if (lookupUrl) {
          void fetchAndUpdate(codigo);
        }
        return;
      }
      const fetched = await fetchAndUpdate(codigo);
      if (fetched) {
        upsertOption(fetched);
        hiddenCctInput.value = normalize(fetched.cct);
      } else {
        hiddenCctInput.value = "";
      }
    };

    cctInput.addEventListener("change", handleChange);
    cctInput.addEventListener("blur", () => window.setTimeout(() => hideSuggestions(), 150));
    cctInput.addEventListener("input", (event) => {
      const value = normalize(event.target.value);
      if (!value) {
        hiddenCctInput.value = "";
        nombreInput.value = "";
        servicioInput.value = "";
        if (sistemaInput) {
          sistemaInput.value = "";
        }
        if (asesorInput) {
          asesorInput.value = "";
        }
        hideSuggestions();
        return;
      }
      if (value.length >= SUGGESTION_MIN_LENGTH) {
        scheduleSuggestions(value);
      } else {
        hideSuggestions();
      }
    });
    cctInput.addEventListener("focus", () => {
      const value = normalize(cctInput.value);
      if (value && value.length >= SUGGESTION_MIN_LENGTH) {
        scheduleSuggestions(value);
      }
    });

    if (normalize(cctInput.value)) {
      void handleChange();
    }
    initCCTCrud({
      form,
      modalId,
      apiBase,
      datalist,
      cctInput,
      hiddenCctInput,
      nombreInput,
      servicioInput,
      asesorInput,
      normalize,
      updateFromOption,
      fetchAndUpdate,
      upsertOption,
      canCreate,
      canEdit,
      canDelete,
      lookupMinLength: LOOKUP_MIN_LENGTH,
    });
  }

  function initCasoInternoForm() {
    const form = document.querySelector("[data-caso-interno-form]");
    if (!form) {
      return;
    }
    setupCCTForm({
      form,
      lookupUrl: form.dataset.lookupUrl || "",
      apiBase: form.dataset.cctApi || "",
      cctInput: form.querySelector("#id_cct_codigo"),
      hiddenCctInput: form.querySelector("#id_cct"),
      nombreInput: form.querySelector("#id_cct_nombre"),
      servicioInput: form.querySelector("#id_cct_modalidad"),
      sistemaInput: form.querySelector("#id_cct_sistema"),
      asesorInput: form.querySelector("#id_asesor_cct"),
      datalist: document.getElementById("cct-options"),
      suggestionsContainer: form.querySelector("[data-cct-suggestions]"),
      modalId: "cct-modal",
      canCreate: form.dataset.cctCanCreate === "true",
      canEdit: form.dataset.cctCanEdit === "true",
      canDelete: form.dataset.cctCanDelete === "true",
    });
    initCentrosAdicionalesCaso();

    const asesorInput = form.querySelector("#id_asesor_cct");
    const usuariosCheckboxes = Array.from(
      form.querySelectorAll('input[name="usuarios_involucrados"][data-username]'),
    );
    if (asesorInput && usuariosCheckboxes.length) {
      const ASESOR_USUARIO = {
        ANGEL: "angel.canche",
        ALICIA: "alicia.alcerreca",
        CARLOS: "carlos.vales",
        CINDY: "cindy.baeza",
        SANDY: "sandy.garcia",
      };

      const normalize = (value) => (value || "").trim().toUpperCase();
      const resolveAsesorUsername = (raw) => {
        const key = normalize(raw);
        if (ASESOR_USUARIO[key]) {
          return ASESOR_USUARIO[key];
        }
        const match = Object.keys(ASESOR_USUARIO).find((name) => key.includes(name));
        return match ? ASESOR_USUARIO[match] : "";
      };

      const marcarUsuario = (username) => {
        if (!username) return;
        const target = usuariosCheckboxes.find(
          (input) => (input.dataset.username || "").toLowerCase() === username.toLowerCase(),
        );
        if (target) {
          target.checked = true;
        }
      };

      let lastAsesorUsername = "";

      const desmarcarUsuario = (username) => {
        if (!username) return;
        const target = usuariosCheckboxes.find(
          (input) => (input.dataset.username || "").toLowerCase() === username.toLowerCase(),
        );
        if (target) {
          target.checked = false;
        }
      };

      const aplicarAsesor = () => {
        const username = resolveAsesorUsername(asesorInput.value);
        if (lastAsesorUsername && lastAsesorUsername !== username) {
          desmarcarUsuario(lastAsesorUsername);
        }
        if (username) {
          marcarUsuario(username);
        }
        lastAsesorUsername = username;
      };

      asesorInput.addEventListener("change", aplicarAsesor);
      asesorInput.addEventListener("input", aplicarAsesor);
      const cctInput = form.querySelector("#id_cct_codigo");
      if (cctInput) {
        cctInput.addEventListener("change", () => {
          window.setTimeout(aplicarAsesor, 150);
        });
      }
      aplicarAsesor();
    }

    // Inicializar CRUD de tipos de proceso
    initTipoProcesoCrud();

    // Inicializar CRUD de prefijos de oficio y enlace con el campo
    initPrefijoOficioCrud();

    // Inicializar CRUD de tipos de violencia
    initTipoViolenciaCrud();
    initViolenciasAdicionales();

    // Inicializar CRUD de solicitante y destinatario
    initSolicitanteCrud();
    initDestinatarioCrud();

    // Inicializar gestor de receptores adicionales
    initReceptoresAdicionales();
    initGeneradoresAdicionales();

  }

  function initEstatusCrudUnified() {
    const configs = [
      {
        catalogType: "estatus-caso",
        selectSelector: "#id_estatus",
        modalId: "estatus-caso-modal",
        apiEndpoint: "/api/estatus-caso/",
        fieldConfig: { label: "estatus de caso" },
      },
      {
        catalogType: "estatus-caso",
        selectSelector: "#id_estatus_nuevo",
        modalId: "estatus-caso-modal",
        apiEndpoint: "/api/estatus-caso/",
        fieldConfig: { label: "estatus de caso" },
      },
      {
        catalogType: "estatus-tramite",
        selectSelector: "#id_estatus_nuevo",
        modalId: "estatus-tramite-modal",
        apiEndpoint: "/api/estatus-tramite/",
        fieldConfig: { label: "estatus de trámite" },
      },
      {
        catalogType: "estatus-tramite",
        selectSelector: "#id_estatus",
        modalId: "estatus-tramite-modal",
        apiEndpoint: "/api/estatus-tramite/",
        fieldConfig: { label: "estatus de trámite" },
      },
      {
        catalogType: "estatus-tramite",
        selectSelector: "#id_tramite_caso-estatus",
        modalId: "estatus-tramite-modal",
        apiEndpoint: "/api/estatus-tramite/",
        fieldConfig: { label: "estatus de trámite" },
      },
      {
        catalogType: "estatus-tramite",
        selectSelector: "#id_bulk_tramite-estatus",
        modalId: "estatus-tramite-modal",
        apiEndpoint: "/api/estatus-tramite/",
        fieldConfig: { label: "estatus de trámite" },
      },
    ];
    configs.forEach((cfg) => initGenericCrud(cfg));
  }

  function initTramiteCasoPrefijos() {
    const select = document.querySelector("[data-prefijo-oficio-modal-select]");
    const numeroInput = document.querySelector("#id_numero_oficio");
    if (!select || !numeroInput) {
      return;
    }
    select.addEventListener("change", () => {
      if (select.value) {
        numeroInput.value = select.value;
        numeroInput.focus();
      }
    });
  }

  function initCCTCrud(config) {
    const {
      form,
      modalId,
      apiBase,
      datalist,
      cctInput,
      hiddenCctInput,
      nombreInput,
      servicioInput,
      asesorInput,
      normalize,
      updateFromOption,
      fetchAndUpdate,
      upsertOption,
      canCreate = false,
      canEdit = false,
      canDelete = false,
      lookupMinLength = 10,
    } = config;
    if (!form || !modalId || !apiBase) {
      return;
    }
    const modal = document.getElementById(modalId);
    if (!modal) {
      return;
    }
    const actionButtons = form.querySelectorAll("[data-cct-action]");
    const cctForm = modal.querySelector("#cct-form");
    const messageBox = modal.querySelector("[data-modal-message]");
    const modalTitle = modal.querySelector("[data-modal-title]");
    const feedback = form.querySelector("[data-cct-feedback]");
    const overlay = modal.querySelector(".modal-overlay");
    const closeTriggers = modal.querySelectorAll("[data-modal-close]");
    const saveButton = cctForm?.querySelector("[data-cct-save]");
    const codigoInput = cctForm?.querySelector('input[name="cct"]');
    const nombreField = cctForm?.querySelector('input[name="nombre"]');
    const servicioField = cctForm?.querySelector('input[name="servicio"]');
    const sostenimientoField = cctForm?.querySelector('input[name="sostenimiento"]');
    const asesorField = cctForm?.querySelector('input[name="asesor"]');
    const municipioField = cctForm?.querySelector('input[name="municipio"]');
    const turnoField = cctForm?.querySelector('input[name="turno"]');
    const resultsContainer = modal.querySelector("[data-cct-results]");
    const searchInput = modal.querySelector("[data-cct-search]");
    const hint = modal.querySelector("[data-cct-hint]");

    if (
      !cctForm ||
      !messageBox ||
      !modalTitle ||
      !codigoInput ||
      !nombreField ||
      !servicioField ||
      !sostenimientoField ||
      !asesorField ||
      !resultsContainer ||
      !searchInput
    ) {
      return;
    }

    const HINT_DEFAULT = "Escribe al menos un carácter para ver resultados del catálogo.";
    const HINT_RESULTS =
      "Selecciona un CCT del listado o continúa refinando la búsqueda.";
    const HINT_EMPTY = "Sin coincidencias para tu búsqueda.";

    const setHint = (message) => {
      if (hint) {
        hint.textContent = message;
      }
    };

    const hideResults = () => {
      resultsContainer.innerHTML = "";
      resultsContainer.hidden = true;
    };

    const renderResultsPlaceholder = (message, { hintMessage } = {}) => {
      resultsContainer.innerHTML = "";
      if (!message) {
        resultsContainer.hidden = true;
      } else {
        const empty = document.createElement("p");
        empty.className = "modal-empty";
        empty.textContent = message;
        resultsContainer.appendChild(empty);
        resultsContainer.hidden = false;
      }
      if (hintMessage) {
        setHint(hintMessage);
      }
    };

    hideResults();
    setHint(HINT_DEFAULT);

    let mode = "create";
    let debounceTimer = null;

    const openModal = (nextMode) => {
      mode = nextMode;
      let title = "Buscar CCT";
      if (mode === "create") {
        title = "Registrar CCT";
      } else if (mode === "edit") {
        title = "Editar CCT";
      }
      modalTitle.textContent = title;
      messageBox.textContent = "";
      modal.classList.add("is-open");
      modal.hidden = false;
      hideResults();
      setHint(HINT_DEFAULT);
      const showForm = mode !== "search";
      cctForm.hidden = !showForm;
      if (saveButton) {
        saveButton.disabled = !showForm;
        saveButton.style.display = showForm ? "" : "none";
      }
      if (mode === "create") {
        cctForm.reset();
      }
      codigoInput.readOnly = mode === "edit";
      const focusTarget = showForm ? codigoInput : searchInput;
      window.setTimeout(() => focusTarget.focus(), 40);
    };

    const closeModal = () => {
      modal.classList.remove("is-open");
      modal.hidden = true;
      cctForm.reset();
      cctForm.hidden = false;
      codigoInput.readOnly = false;
      if (saveButton) {
        saveButton.disabled = false;
        saveButton.style.display = "";
      }
      messageBox.textContent = "";
      mode = "create";
      hideResults();
      setHint(HINT_DEFAULT);
    };

    const displayMessage = (text, isError = false) => {
      messageBox.textContent = text;
      messageBox.style.color = isError ? "#dc2626" : "#0f4c81";
    };

    const setFeedback = (text, isError = false) => {
      if (!feedback) {
        return;
      }
      feedback.textContent = text;
      feedback.classList.toggle("is-error", isError);
    };

    const upsertOptionFn =
      typeof upsertOption === "function"
        ? upsertOption
        : (item) => {
          if (!datalist) {
            return;
          }
          const code = item.cct;
          if (!code) {
            return;
          }
          const existing = Array.from(datalist.options).find(
            (opt) => normalize(opt.value) === normalize(code),
          );
          const label = `${code} · ${item.nombre || ""}`.trim();
          if (existing) {
            existing.value = code;
            existing.textContent = label;
            existing.dataset.nombre = item.nombre || "";
            existing.dataset.servicio = item.servicio || "";
            existing.dataset.asesor = item.asesor || "";
            existing.dataset.sostenimiento = item.sostenimiento || "";
            existing.setAttribute("data-nombre", item.nombre || "");
            existing.setAttribute("data-servicio", item.servicio || "");
            existing.setAttribute("data-asesor", item.asesor || "");
            existing.setAttribute("data-sostenimiento", item.sostenimiento || "");
          } else {
            const option = document.createElement("option");
            option.value = code;
            option.textContent = label;
            option.dataset.nombre = item.nombre || "";
            option.dataset.servicio = item.servicio || "";
            option.dataset.asesor = item.asesor || "";
            option.dataset.sostenimiento = item.sostenimiento || "";
            option.setAttribute("data-nombre", item.nombre || "");
            option.setAttribute("data-servicio", item.servicio || "");
            option.setAttribute("data-asesor", item.asesor || "");
            option.setAttribute("data-sostenimiento", item.sostenimiento || "");
            datalist.appendChild(option);
          }
        };

    const removeOption = (code) => {
      if (!datalist) {
        return;
      }
      const option = Array.from(datalist.options).find(
        (opt) => normalize(opt.value) === normalize(code),
      );
      option?.remove();
    };

    const fillMainForm = (item) => {
      if (!item) {
        return;
      }
      const code = item.cct;
      const sistema = normaliseSistema(item.sostenimiento);
      cctInput.value = code;
      hiddenCctInput.value = code;
      nombreInput.value = item.nombre || "";
      if (sostenimientoInput) {
        sostenimientoInput.value = sistema;
      }
      servicioInput.value = item.servicio || "";
      if (asesorInput) {
        asesorInput.value = item.asesor || "";
      }
    };

    const renderResults = (items) => {
      items.forEach((entry) => {
        entry.sostenimiento = normaliseSistema(entry.sostenimiento);
      });
      resultsContainer.innerHTML = "";
      if (!items.length) {
        renderResultsPlaceholder("Sin resultados.", { hintMessage: HINT_EMPTY });
        return;
      }
      const list = document.createElement("ul");
      list.className = "modal-result-list";
      items.forEach((item) => {
        const li = document.createElement("li");
        li.className = "modal-result-item";
        const info = document.createElement("div");
        info.className = "modal-result-info";
        info.innerHTML = `<strong>${item.cct}</strong> · ${item.nombre || ""}`;
        const actions = document.createElement("div");
        actions.className = "modal-result-actions";

        const selectBtn = document.createElement("button");
        selectBtn.type = "button";
        selectBtn.className = "btn btn--secondary btn--sm";
        selectBtn.textContent = "Seleccionar";
        selectBtn.addEventListener("click", () => {
          fillMainForm(item);
          upsertOptionFn(item);
          closeModal();
        });
        actions.append(selectBtn);

        if (canEdit) {
          const editBtn = document.createElement("button");
          editBtn.type = "button";
          editBtn.className = "btn btn--ghost btn--sm";
          editBtn.textContent = "Editar";
          editBtn.addEventListener("click", async () => {
            await loadForEdit(item.cct);
          });
          actions.append(editBtn);
        }

        if (canDelete) {
          const deleteBtn = document.createElement("button");
          deleteBtn.type = "button";
          deleteBtn.className = "btn btn--danger btn--sm";
          deleteBtn.textContent = "Eliminar";
          deleteBtn.addEventListener("click", () => {
            deleteCCT(item.cct);
          });
          actions.append(deleteBtn);
        }

        li.append(info, actions);
        list.appendChild(li);
      });
      resultsContainer.appendChild(list);
      resultsContainer.hidden = false;
      setHint(HINT_RESULTS);
    };

    const loadForEdit = async (code) => {
      if (!code || code.length < lookupMinLength) {
        window.alert("Proporciona un CCT completo para editar.");
        return;
      }
      if (!canEdit) {
        window.alert("No tienes permisos para editar CCT.");
        return;
      }
      try {
        const detail = await fetchCCTDetail(code);
        if (!detail) {
          displayMessage("No se encontró el CCT solicitado.", true);
          return;
        }
        cctForm.reset();
        codigoInput.value = detail.cct || "";
        nombreField.value = detail.nombre || "";
        servicioField.value = detail.servicio || "";
        sostenimientoField.value = normaliseSistema(detail.sostenimiento);
        asesorField.value = detail.asesor || "";
        if (municipioField) {
          municipioField.value = detail.municipio || "";
        }
        if (turnoField) {
          turnoField.value = detail.turno || "";
        }
        openModal("edit");
      } catch (error) {
        displayMessage(error.message, true);
      }
    };

    const fetchCCTDetail = async (code) => {
      if (!code || code.length < lookupMinLength) {
        return null;
      }
      const target = buildDetailUrl(apiBase, encodeURIComponent(code));
      const response = await fetch(target, {
        headers: { Accept: "application/json" },
      });
      if (!response.ok) {
        if (response.status === 404) {
          return null;
        }
        throw new Error("No fue posible obtener la información del CCT.");
      }
      const detail = await response.json();
      detail.sostenimiento = normaliseSistema(detail.sostenimiento);
      return detail;
    };

    const performSearch = async (term) => {
      const query = term.trim();
      if (!query) {
        hideResults();
        setHint(HINT_DEFAULT);
        displayMessage("");
        return;
      }
      renderResultsPlaceholder("Buscando resultados...", { hintMessage: HINT_RESULTS });
      const url = new URL(apiBase, window.location.origin);
      url.searchParams.set("search", query);
      url.searchParams.set("page_size", "10");
      const response = await fetch(url, {
        headers: { Accept: "application/json" },
      });
      if (!response.ok) {
        displayMessage("Ocurrió un problema al buscar CCT.", true);
        renderResultsPlaceholder("No fue posible completar la búsqueda.", {
          hintMessage: HINT_DEFAULT,
        });
        return;
      }
      const data = await response.json();
      const results = Array.isArray(data.results) ? data.results : [];
      renderResults(results);
    };

    const deleteCCT = async (code) => {
      if (!code || code.length < lookupMinLength) {
        window.alert("Proporciona un CCT completo para eliminar.");
        return;
      }
      if (!canDelete) {
        window.alert("No tienes permisos para eliminar CCT.");
        return;
      }
      if (!window.confirm(`¿Eliminar el CCT ${code}? Esta acción es irreversible.`)) {
        return;
      }
      const target = buildDetailUrl(apiBase, encodeURIComponent(code));
      const response = await fetch(target, {
        method: "DELETE",
        headers: defaultHeaders(),
      });
      if (!response.ok) {
        displayMessage("No fue posible eliminar el CCT.", true);
        setFeedback("No fue posible eliminar el CCT.", true);
        return;
      }
      removeOption(code);
      if (normalize(hiddenCctInput.value) === normalize(code)) {
        hiddenCctInput.value = "";
        cctInput.value = "";
        nombreInput.value = "";
        servicioInput.value = "";
        if (asesorInput) {
          asesorInput.value = "";
        }
      }
      await performSearch(searchInput.value.trim());
      displayMessage("CCT eliminado correctamente.");
      setFeedback("CCT eliminado correctamente.");
    };

    actionButtons.forEach((button) => {
      const action = button.dataset.cctAction;
      if (action === "create") {
        button.addEventListener("click", () => {
          if (!canCreate) {
            window.alert("No tienes permisos para crear CCT.");
            return;
          }
          cctForm.reset();
          openModal("create");
          searchInput.value = "";
          hideResults();
          setHint(HINT_DEFAULT);
          displayMessage("");
        });
      } else if (action === "edit") {
        button.addEventListener("click", async () => {
          if (!canEdit) {
            window.alert("No tienes permisos para editar CCT.");
            return;
          }
          const selectedCode = normalize(hiddenCctInput.value || cctInput.value);
          if (!selectedCode) {
            window.alert("Selecciona un CCT para editar.");
            return;
          }
          await loadForEdit(selectedCode);
        });
      } else if (action === "delete") {
        button.addEventListener("click", () => {
          if (!canDelete) {
            window.alert("No tienes permisos para eliminar CCT.");
            return;
          }
          const selectedCode = normalize(hiddenCctInput.value || cctInput.value);
          if (!selectedCode) {
            window.alert("Selecciona un CCT para eliminar.");
            return;
          }
          deleteCCT(selectedCode);
        });
      } else if (action === "search") {
        button.addEventListener("click", () => {
          openModal("search");
          searchInput.value = "";
          hideResults();
          setHint(HINT_DEFAULT);
          displayMessage("");
        });
      }
    });

    closeTriggers.forEach((trigger) => trigger.addEventListener("click", closeModal));
    overlay?.addEventListener("click", closeModal);
    modal.addEventListener("keydown", (event) => {
      if (event.key === "Escape") {
        event.preventDefault();
        closeModal();
      }
    });

    searchInput.addEventListener("input", (event) => {
      const term = event.target.value.trim();
      if (debounceTimer) {
        window.clearTimeout(debounceTimer);
      }
      if (!term) {
        hideResults();
        setHint(HINT_DEFAULT);
        displayMessage("");
        return;
      }
      debounceTimer = window.setTimeout(() => {
        performSearch(term);
      }, 250);
    });

    cctForm.addEventListener("submit", async (event) => {
      event.preventDefault();
      displayMessage("");
      if (mode === "create" && !canCreate) {
        displayMessage("No tienes permisos para crear CCT.", true);
        return;
      }
      if (mode === "edit" && !canEdit) {
        displayMessage("No tienes permisos para editar CCT.", true);
        return;
      }
      const sistemaValue = normaliseSistema(sostenimientoField.value.trim());
      sostenimientoField.value = sistemaValue;
      const payload = {
        cct: codigoInput.value.trim().toUpperCase(),
        nombre: nombreField.value.trim(),
        sostenimiento: sistemaValue,
        servicio: servicioField.value.trim(),
        asesor: asesorField?.value.trim() || "",
        municipio: municipioField?.value.trim() || "",
        turno: turnoField?.value.trim() || "",
      };
      if (!payload.cct) {
        displayMessage("La clave CCT es obligatoria.", true);
        codigoInput.focus();
        return;
      }
      if (!payload.nombre) {
        displayMessage("El nombre es obligatorio.", true);
        nombreField.focus();
        return;
      }
      try {
        let result;
        if (mode === "create") {
          const response = await fetch(apiBase, {
            method: "POST",
            headers: defaultHeaders(),
            body: JSON.stringify(payload),
          });
          if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            const msg = extractErrorMessage(errorData) || "No fue posible crear el CCT.";
            throw new Error(msg);
          }
          result = await response.json();
        } else {
          const target = buildDetailUrl(apiBase, encodeURIComponent(payload.cct));
          const response = await fetch(target, {
            method: "PUT",
            headers: defaultHeaders(),
            body: JSON.stringify(payload),
          });
          if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            const msg = extractErrorMessage(errorData) || "No fue posible actualizar el CCT.";
            throw new Error(msg);
          }
          result = await response.json();
        }
        upsertOptionFn(result);
        fillMainForm(result);
        const successText = mode === "create"
          ? "CCT guardado correctamente."
          : "CCT actualizado correctamente.";
        displayMessage(successText, false);
        setFeedback(successText, false);
        window.setTimeout(() => closeModal(), 800);
      } catch (error) {
        displayMessage(error.message, true);
        setFeedback(error.message, true);
      }
    });
  }

  function extractErrorMessage(data) {
    if (!data) {
      return "";
    }
    if (typeof data === "string") {
      return data;
    }
    if (Array.isArray(data)) {
      return data.join(" ");
    }
    if (typeof data === "object") {
      if (data.detail) {
        if (Array.isArray(data.detail)) {
          return data.detail.join(" ");
        }
        if (typeof data.detail === "string") {
          return data.detail;
        }
      }
      const messages = [];
      Object.values(data).forEach((value) => {
        if (!value) {
          return;
        }
        if (Array.isArray(value)) {
          messages.push(value.join(" "));
        } else if (typeof value === "string") {
          messages.push(value);
        } else if (typeof value === "object") {
          const nested = extractErrorMessage(value);
          if (nested) {
            messages.push(nested);
          }
        }
      });
      return messages.join(" ");
    }
    return "";
  }

  function defaultHeaders() {
    return {
      "Content-Type": "application/json",
      Accept: "application/json",
      "X-CSRFToken": getCsrfToken(),
    };
  }

  function buildDetailUrl(baseUrl, id) {
    const separator = baseUrl.endsWith("/") ? "" : "/";
    return `${baseUrl}${separator}${id}/`;
  }

  // Función genérica para inicializar CRUD de catálogos
  function initGenericCrud(config) {
    const {
      catalogType = "", // tipo-proceso, tipo-violencia, solicitante, destinatario, estatus-tramite
      selectSelector = "", // ID del select (#id_tipo_inicial)
      modalId = "generic-modal", // ID del modal a usar
      apiEndpoint = "/api/default/", // endpoint del API
      fieldConfig = {}, // config de campos { nombre: {...}, orden: {...}, etc }
    } = config;

    if (!catalogType || !selectSelector) {
      return;
    }

    const selectElement = document.querySelector(selectSelector);
    const modal = document.getElementById(modalId);
    const form = modal ? modal.querySelector("form") : null;

    if (!selectElement || !modal || !form) {
      return;
    }
    form.setAttribute("novalidate", "novalidate");

    // Buscar los botones CRUD que apunten a este catálogo
    const openBtn = document.querySelector(`[data-crud-open="${catalogType}"][data-crud-target="${selectSelector.substring(1)}"]`);
    const editBtn = document.querySelector(`[data-crud-edit="${catalogType}"][data-crud-target="${selectSelector.substring(1)}"]`);
    const deleteBtn = document.querySelector(`[data-crud-delete="${catalogType}"][data-crud-target="${selectSelector.substring(1)}"]`);
    if (!openBtn && !editBtn && !deleteBtn) {
      return;
    }
    const initKey = `${catalogType}|${selectSelector}|${modalId}|${form.id || "form"}`;
    if (initializedGenericCrudKeys.has(initKey)) {
      return;
    }
    initializedGenericCrudKeys.add(initKey);
    const closeBtns = modal.querySelectorAll("[data-modal-close]");
    const saveBtn = form.querySelector("button[type='submit']");
    const modalTitle = modal.querySelector("[data-modal-title]");
    const modalMessage = modal.querySelector("[data-modal-message]");
    const fieldset = form.querySelector("fieldset:first-of-type");

    let currentMode = "create";
    let selectedId = null;
    let isSubmitting = false;

    const showMessage = (message, isError = false) => {
      if (modalMessage) {
        modalMessage.textContent = message;
        modalMessage.className = isError ? "modal-message error" : "modal-message success";
        modalMessage.style.display = isError || message ? "block" : "none";
      }
    };

    const closeModal = () => {
      modal.hidden = true;
      form.reset();
      isSubmitting = false;
      if (saveBtn) {
        saveBtn.disabled = false;
      }
      if (modalMessage) {
        modalMessage.style.display = "none";
        modalMessage.className = "modal-message";
      }
    };

    const openModalForCreate = () => {
      currentMode = "create";
      if (modalTitle) {
        modalTitle.textContent = `Agregar ${fieldConfig.label || catalogType}`;
      }
      if (fieldset) {
        fieldset.style.display = "block";
      }
      // Habilitar validación requerida
      form.querySelectorAll("input[type='text']").forEach((input) => {
        input.required = true;
      });
      if (saveBtn) {
        saveBtn.textContent = "Guardar";
        saveBtn.classList.remove("btn--danger");
        saveBtn.classList.add("btn--primary");
      }
      form.reset();
      const firstInput = form.querySelector("input[type='text']");
      firstInput?.focus();
      if (modalMessage) {
        modalMessage.style.display = "none";
      }
      modal.hidden = false;
    };

    const openModalForEdit = () => {
      selectedId = parseInt(selectElement.value, 10);
      if (!selectedId) {
        showMessage(`Por favor selecciona un ${fieldConfig.label || catalogType} primero.`, true);
        return;
      }

      currentMode = "edit";
      if (modalTitle) {
        modalTitle.textContent = `Editar ${fieldConfig.label || catalogType}`;
      }
      if (fieldset) {
        fieldset.style.display = "block";
      }
      form.querySelectorAll("input[type='text']").forEach((input) => {
        input.required = true;
      });
      if (saveBtn) {
        saveBtn.textContent = "Guardar";
        saveBtn.classList.remove("btn--danger");
        saveBtn.classList.add("btn--primary");
      }

      fetch(`${apiEndpoint}${selectedId}/`, {
        headers: { "X-Requested-With": "XMLHttpRequest" },
      })
        .then((response) => {
          if (!response.ok) throw new Error(`No se pudo cargar ${fieldConfig.label || catalogType}`);
          return response.json();
        })
        .then((data) => {
          // Poblar campos del formulario
          form.querySelectorAll("input[type='text'], input[type='number'], textarea").forEach((input) => {
            if (data[input.name]) {
              input.value = data[input.name] || "";
            }
          });
          if (modalMessage) {
            modalMessage.style.display = "none";
          }
          modal.hidden = false;
        })
        .catch((error) => {
          showMessage(`Error: ${error.message}`, true);
        });
    };

    const openModalForDelete = () => {
      selectedId = parseInt(selectElement.value, 10);
      if (!selectedId) {
        showMessage(`Por favor selecciona un ${fieldConfig.label || catalogType} primero.`, true);
        return;
      }

      currentMode = "delete";
      if (modalTitle) {
        modalTitle.textContent = `Eliminar ${fieldConfig.label || catalogType}`;
      }
      if (fieldset) {
        fieldset.style.display = "none";
      }
      form.querySelectorAll("input[type='text']").forEach((input) => {
        input.required = false;
      });
      if (saveBtn) {
        saveBtn.textContent = "Eliminar";
        saveBtn.classList.remove("btn--primary");
        saveBtn.classList.add("btn--danger");
      }
      if (modalMessage) {
        modalMessage.textContent = `¿Estás seguro de que deseas eliminar este ${fieldConfig.label || catalogType}? Esta acción no se puede deshacer.`;
        modalMessage.className = "modal-message";
        modalMessage.style.display = "block";
      }
      modal.hidden = false;
    };

    const submitForm = async (event) => {
      event.preventDefault();
      if (isSubmitting) {
        return;
      }
      isSubmitting = true;
      if (saveBtn) {
        saveBtn.disabled = true;
      }

      try {
        if (currentMode === "delete") {
          await deleteItem(selectedId);
        } else {
          const formData = new FormData(form);
          const data = Object.fromEntries(formData);

          if (currentMode === "create") {
            await createItem(data);
          } else if (currentMode === "edit") {
            await updateItem(selectedId, data);
          }
        }
      } finally {
        isSubmitting = false;
        if (saveBtn) {
          saveBtn.disabled = false;
        }
      }
    };

    const createItem = async (data) => {
      try {
        const response = await fetch(apiEndpoint, {
          method: "POST",
          headers: defaultHeaders(),
          body: JSON.stringify(data),
        });

        if (!response.ok) {
          const contentType = response.headers.get("Content-Type") || "";
          let errorData = {};
          if (contentType.includes("application/json")) {
            errorData = await response.json();
          } else {
            errorData = { detail: await response.text() };
          }
          let errorMessage = `Error al crear ${fieldConfig.label || catalogType}.`;

          if (typeof errorData === "object") {
            const firstError = Object.values(errorData).flat()[0];
            if (firstError) {
              errorMessage = String(firstError);
            }
          } else if (typeof errorData === "string" && errorData.trim()) {
            errorMessage = errorData.trim();
          }

          showMessage(errorMessage, true);
          return;
        }

        const newItem = await response.json();
        addOption(selectElement, newItem);
        showMessage(`${fieldConfig.label || catalogType} creado exitosamente.`);
        setTimeout(closeModal, 1000);
      } catch (error) {
        showMessage(`Error: ${error.message}`, true);
      }
    };

    const updateItem = async (id, data) => {
      try {
        const response = await fetch(`${apiEndpoint}${id}/`, {
          method: "PATCH",
          headers: defaultHeaders(),
          body: JSON.stringify(data),
        });

        if (!response.ok) {
          const contentType = response.headers.get("Content-Type") || "";
          let errorData = {};
          if (contentType.includes("application/json")) {
            errorData = await response.json();
          } else {
            errorData = { detail: await response.text() };
          }
          let errorMessage = `Error al actualizar ${fieldConfig.label || catalogType}.`;

          if (typeof errorData === "object") {
            const firstError = Object.values(errorData).flat()[0];
            if (firstError) {
              errorMessage = String(firstError);
            }
          } else if (typeof errorData === "string" && errorData.trim()) {
            errorMessage = errorData.trim();
          }

          showMessage(errorMessage, true);
          return;
        }

        const updated = await response.json();
        updateOption(selectElement, updated);
        showMessage(`${fieldConfig.label || catalogType} actualizado exitosamente.`);
        setTimeout(closeModal, 1000);
      } catch (error) {
        showMessage(`Error: ${error.message}`, true);
      }
    };

    const deleteItem = async (id) => {
      try {
        const response = await fetch(`${apiEndpoint}${id}/`, {
          method: "DELETE",
          headers: defaultHeaders(),
        });

        if (!response.ok) {
          const contentType = response.headers.get("Content-Type") || "";
          let errorData = {};
          if (contentType.includes("application/json")) {
            errorData = await response.json();
          } else {
            errorData = { detail: await response.text() };
          }
          let errorMessage = `Error al eliminar ${fieldConfig.label || catalogType}.`;

          if (typeof errorData === "object") {
            const firstError = Object.values(errorData).flat()[0];
            if (firstError) {
              errorMessage = String(firstError);
            }
          } else if (typeof errorData === "string" && errorData.trim()) {
            errorMessage = errorData.trim();
          }

          showMessage(errorMessage, true);
          return;
        }

        removeOption(selectElement, id);
        showMessage(`${fieldConfig.label || catalogType} eliminado exitosamente.`);
        setTimeout(closeModal, 1000);
      } catch (error) {
        showMessage(`Error: ${error.message}`, true);
      }
    };

    const formatOptionText = (data) => {
      if (!data) return "";
      const nombre = data.nombre || "";
      const funcion = data.descripcion || "";
      return funcion ? `${nombre} · ${funcion}` : nombre;
    };

    const dispatchChange = (select) => {
      const evt = new Event("change", { bubbles: true });
      select.dispatchEvent(evt);
    };

    const addOption = (select, data) => {
      const option = document.createElement("option");
      option.value = data.id;
      option.textContent = formatOptionText(data);
      select.appendChild(option);
      select.value = data.id;
      dispatchChange(select);
    };

    const updateOption = (select, data) => {
      const option = select.querySelector(`option[value="${data.id}"]`);
      if (option) {
        option.textContent = formatOptionText(data);
        if (select.value === String(data.id)) {
          dispatchChange(select);
        }
      }
    };

    const removeOption = (select, id) => {
      const idStr = String(id);
      const option = select.querySelector(`option[value="${idStr}"]`);
      if (option) {
        option.remove();
      }
      if (select.value === idStr) {
        select.value = "";
        dispatchChange(select);
      }
    };

    // Event listeners
    if (openBtn) {
      openBtn.addEventListener("click", openModalForCreate);
    }
    if (editBtn) {
      editBtn.addEventListener("click", openModalForEdit);
    }
    if (deleteBtn) {
      deleteBtn.addEventListener("click", openModalForDelete);
    }

    closeBtns.forEach((btn) => {
      btn.addEventListener("click", closeModal);
    });

    if (form) {
      form.addEventListener("submit", submitForm);
    }

    const overlay = modal.querySelector(".modal-overlay");
    if (overlay) {
      overlay.addEventListener("click", closeModal);
    }
  }

  function getCsrfToken() {
    const input = document.querySelector('input[name="csrfmiddlewaretoken"]');
    return input ? input.value : "";
  }

  function initTipoProcesoCrud() {
    const selectElement = document.querySelector("#id_tipo_inicial");
    const modal = document.getElementById("tipo-proceso-modal");
    const form = document.getElementById("tipo-proceso-form");
    const fieldset = form ? form.querySelector("#tipo-proceso-fields") : null;
    const openBtn = document.querySelector("[data-tipo-proceso-modal-open]");
    const editBtn = document.querySelector("[data-tipo-proceso-modal-edit]");
    const deleteBtn = document.querySelector("[data-tipo-proceso-modal-delete]");
    const closeBtns = modal ? modal.querySelectorAll("[data-modal-close]") : [];
    const saveBtn = form ? form.querySelector("[data-tipo-proceso-save]") : null;
    const modalTitle = modal ? modal.querySelector("[data-modal-title]") : null;
    const modalMessage = modal ? modal.querySelector("[data-modal-message]") : null;

    if (!selectElement || !modal || !form) {
      return;
    }

    const apiBase = "/api/tipos-proceso/";
    let currentMode = "create"; // "create", "edit", or "delete"
    let selectedId = null;

    const showMessage = (message, isError = false) => {
      if (modalMessage) {
        modalMessage.textContent = message;
        modalMessage.className = isError ? "modal-message error" : "modal-message success";
        modalMessage.style.display = isError || message ? "block" : "none";
      }
    };

    const closeModal = () => {
      modal.hidden = true;
      form.reset();
      if (modalMessage) {
        modalMessage.style.display = "none";
        modalMessage.className = "modal-message";
      }
    };

    const openModalForCreate = () => {
      currentMode = "create";
      if (modalTitle) {
        modalTitle.textContent = "Agregar tipo de trámite";
      }
      if (fieldset) {
        fieldset.style.display = "block";
      }
      // Re-habilitar validación requerida
      const nombreInput = form.querySelector("#tipo-proceso-nombre");
      if (nombreInput) {
        nombreInput.required = true;
      }
      if (saveBtn) {
        saveBtn.textContent = "Guardar";
        saveBtn.classList.remove("btn--danger");
        saveBtn.classList.add("btn--primary");
      }
      form.reset();
      nombreInput.focus();
      if (modalMessage) {
        modalMessage.style.display = "none";
      }
      modal.hidden = false;
    };

    const openModalForEdit = () => {
      selectedId = parseInt(selectElement.value, 10);
      if (!selectedId) {
        showMessage("Por favor selecciona un tipo de trámite primero.", true);
        return;
      }

      currentMode = "edit";
      if (modalTitle) {
        modalTitle.textContent = "Editar tipo de trámite";
      }
      if (fieldset) {
        fieldset.style.display = "block";
      }
      // Re-habilitar validación requerida
      const nombreInput = form.querySelector("#tipo-proceso-nombre");
      if (nombreInput) {
        nombreInput.required = true;
      }
      if (saveBtn) {
        saveBtn.textContent = "Guardar";
        saveBtn.classList.remove("btn--danger");
        saveBtn.classList.add("btn--primary");
      }

      // Cargar datos del tipo seleccionado
      fetch(`${apiBase}${selectedId}/`, {
        headers: { "X-Requested-With": "XMLHttpRequest" },
      })
        .then((response) => {
          if (!response.ok) throw new Error("No se pudo cargar el tipo");
          return response.json();
        })
        .then((data) => {
          form.querySelector("#tipo-proceso-nombre").value = data.nombre || "";
          form.querySelector("#tipo-proceso-descripcion").value = data.descripcion || "";
          form.querySelector("#tipo-proceso-es-documento").checked = data.es_documento || false;
          if (modalMessage) {
            modalMessage.style.display = "none";
          }
          modal.hidden = false;
        })
        .catch((error) => {
          showMessage(`Error: ${error.message}`, true);
        });
    };

    const openModalForDelete = () => {
      selectedId = parseInt(selectElement.value, 10);
      if (!selectedId) {
        showMessage("Por favor selecciona un tipo de trámite primero.", true);
        return;
      }

      currentMode = "delete";
      if (modalTitle) {
        modalTitle.textContent = "Eliminar tipo de trámite";
      }
      if (fieldset) {
        fieldset.style.display = "none";
      }
      // Desactivar validación requerida cuando el fieldset está oculto
      const nombreInput = form.querySelector("#tipo-proceso-nombre");
      if (nombreInput) {
        nombreInput.required = false;
      }
      if (saveBtn) {
        saveBtn.textContent = "Eliminar";
        saveBtn.classList.remove("btn--primary");
        saveBtn.classList.add("btn--danger");
      }
      if (modalMessage) {
        modalMessage.textContent = "¿Estás seguro de que deseas eliminar este tipo de trámite? Esta acción no se puede deshacer.";
        modalMessage.className = "modal-message";
        modalMessage.style.display = "block";
      }
      modal.hidden = false;
    };

    const submitForm = async (event) => {
      event.preventDefault();

      if (currentMode === "delete") {
        await deleteType(selectedId);
      } else {
        // Validación de cliente antes de enviar
        const nombreInput = form.querySelector("#tipo-proceso-nombre");
        if (!nombreInput.value.trim()) {
          showMessage("El nombre del tipo es obligatorio.", true);
          nombreInput.focus();
          return;
        }

        const data = {
          nombre: nombreInput.value.trim(),
          descripcion: form.querySelector("#tipo-proceso-descripcion").value.trim(),
          es_documento: form.querySelector("#tipo-proceso-es-documento").checked,
        };

        if (currentMode === "create") {
          await createType(data);
        } else if (currentMode === "edit") {
          await updateType(selectedId, data);
        }
      }
    };

    const createType = async (data) => {
      try {
        const response = await fetch(apiBase, {
          method: "POST",
          headers: defaultHeaders(),
          body: JSON.stringify(data),
        });

        if (!response.ok) {
          const errorData = await response.json();
          let errorMessage = "Error al crear el tipo de trámite.";

          // Procesar errores del servidor
          if (errorData.nombre) {
            errorMessage = Array.isArray(errorData.nombre) ? errorData.nombre[0] : errorData.nombre;
          } else if (errorData.detail) {
            errorMessage = errorData.detail;
          } else if (typeof errorData === 'object') {
            const firstError = Object.values(errorData).flat()[0];
            if (firstError) {
              errorMessage = String(firstError);
            }
          }

          showMessage(errorMessage, true);
          return;
        }

        const newType = await response.json();
        addOption(selectElement, newType);
        showMessage("Tipo de trámite creado exitosamente.");
        setTimeout(closeModal, 1000);
      } catch (error) {
        showMessage(`Error: ${error.message}`, true);
      }
    };

    const updateType = async (id, data) => {
      try {
        const response = await fetch(`${apiBase}${id}/`, {
          method: "PATCH",
          headers: defaultHeaders(),
          body: JSON.stringify(data),
        });

        if (!response.ok) {
          const errorData = await response.json();
          let errorMessage = "Error al actualizar el tipo de trámite.";

          // Procesar errores del servidor
          if (errorData.nombre) {
            errorMessage = Array.isArray(errorData.nombre) ? errorData.nombre[0] : errorData.nombre;
          } else if (errorData.detail) {
            errorMessage = errorData.detail;
          } else if (typeof errorData === 'object') {
            const firstError = Object.values(errorData).flat()[0];
            if (firstError) {
              errorMessage = String(firstError);
            }
          }

          showMessage(errorMessage, true);
          return;
        }

        const updated = await response.json();
        updateOption(selectElement, updated);
        showMessage("Tipo de trámite actualizado exitosamente.");
        setTimeout(closeModal, 1000);
      } catch (error) {
        showMessage(`Error: ${error.message}`, true);
      }
    };

    const deleteType = async (id) => {
      try {
        const response = await fetch(`${apiBase}${id}/`, {
          method: "DELETE",
          headers: defaultHeaders(),
        });

        if (!response.ok) {
          const errorData = await response.json();
          let errorMessage = "Error al eliminar el tipo de trámite.";

          if (errorData.detail) {
            errorMessage = errorData.detail;
          } else if (typeof errorData === 'object') {
            const firstError = Object.values(errorData).flat()[0];
            if (firstError) {
              errorMessage = String(firstError);
            }
          }

          showMessage(errorMessage, true);
          return;
        }

        removeOption(selectElement, id);
        showMessage("Tipo de trámite eliminado exitosamente.");
        setTimeout(closeModal, 1000);
      } catch (error) {
        showMessage(`Error: ${error.message}`, true);
      }
    };

    const addOption = (select, data) => {
      const option = document.createElement("option");
      option.value = data.id;
      option.textContent = data.nombre;
      select.appendChild(option);
      select.value = data.id;
    };

    const updateOption = (select, data) => {
      const option = select.querySelector(`option[value="${data.id}"]`);
      if (option) {
        option.textContent = data.nombre;
      }
    };

    const removeOption = (select, id) => {
      const idStr = String(id);
      const option = select.querySelector(`option[value="${idStr}"]`);
      if (option) {
        option.remove();
      }
      if (select.value === idStr) {
        select.value = "";
      }
    };

    // Event listeners
    if (openBtn) {
      openBtn.addEventListener("click", openModalForCreate);
    }
    if (editBtn) {
      editBtn.addEventListener("click", openModalForEdit);
    }
    if (deleteBtn) {
      deleteBtn.addEventListener("click", openModalForDelete);
    }

    // Agregar event listeners a todos los botones de cerrar
    closeBtns.forEach((btn) => {
      btn.addEventListener("click", closeModal);
    });

    if (form) {
      form.addEventListener("submit", submitForm);
    }

    // Cerrar modal al hacer click en el overlay
    const overlay = modal ? modal.querySelector(".modal-overlay") : null;
    if (overlay) {
      overlay.addEventListener("click", closeModal);
    }
  }

  function initEstatusCasoCrud() {
    const selectElement =
      document.querySelector("[data-estatus-caso-select]") || document.querySelector("#id_estatus");
    const modal = document.getElementById("estatus-caso-modal");
    const form = document.getElementById("estatus-caso-form");
    const fieldset = form ? form.querySelector("#estatus-caso-fields") : null;
    const openBtn = document.querySelector("[data-estatus-caso-modal-open]");
    const editBtn = document.querySelector("[data-estatus-caso-modal-edit]");
    const deleteBtn = document.querySelector("[data-estatus-caso-modal-delete]");
    const closeBtns = modal ? modal.querySelectorAll("[data-modal-close]") : [];
    const saveBtn = form ? form.querySelector("[data-estatus-caso-save]") : null;
    const modalTitle = modal ? modal.querySelector("[data-modal-title]") : null;
    const modalMessage = modal ? modal.querySelector("[data-modal-message]") : null;

    if (!selectElement || !modal || !form) {
      return;
    }

    const apiBase = selectElement.dataset.estatusApi || "/api/estatus-caso/";
    const labelTarget = selectElement.dataset.estatusLabel || "estatus";
    let currentMode = "create";
    let selectedId = null;

    const showMessage = (message, isError = false) => {
      if (modalMessage) {
        modalMessage.textContent = message;
        modalMessage.className = isError ? "modal-message error" : "modal-message success";
        modalMessage.style.display = isError || message ? "block" : "none";
      }
    };

    const closeModal = () => {
      modal.hidden = true;
      form.reset();
      if (modalMessage) {
        modalMessage.style.display = "none";
        modalMessage.className = "modal-message";
      }
    };

    const openModalForCreate = () => {
      currentMode = "create";
      if (modalTitle) {
        modalTitle.textContent = `Agregar ${labelTarget}`;
      }
      if (fieldset) {
        fieldset.style.display = "block";
      }
      const nombreInput = form.querySelector("#estatus-caso-nombre");
      if (nombreInput) {
        nombreInput.required = true;
      }
      if (saveBtn) {
        saveBtn.textContent = "Guardar";
        saveBtn.classList.remove("btn--danger");
        saveBtn.classList.add("btn--primary");
      }
      form.reset();
      nombreInput.focus();
      if (modalMessage) {
        modalMessage.style.display = "none";
      }
      modal.hidden = false;
    };

    const openModalForEdit = () => {
      selectedId = parseInt(selectElement.value, 10);
      if (!selectedId) {
        showMessage("Por favor selecciona un estatus primero.", true);
        return;
      }

      currentMode = "edit";
      if (modalTitle) {
        modalTitle.textContent = `Editar ${labelTarget}`;
      }
      if (fieldset) {
        fieldset.style.display = "block";
      }
      const nombreInput = form.querySelector("#estatus-caso-nombre");
      if (nombreInput) {
        nombreInput.required = true;
      }
      if (saveBtn) {
        saveBtn.textContent = "Guardar";
        saveBtn.classList.remove("btn--danger");
        saveBtn.classList.add("btn--primary");
      }

      fetch(`${apiBase}${selectedId}/`, {
        headers: { "X-Requested-With": "XMLHttpRequest" },
      })
        .then((response) => {
          if (!response.ok) throw new Error("No se pudo cargar el estatus");
          return response.json();
        })
        .then((data) => {
          form.querySelector("#estatus-caso-nombre").value = data.nombre || "";
          form.querySelector("#estatus-caso-orden").value = data.orden || 1;
          if (modalMessage) {
            modalMessage.style.display = "none";
          }
          modal.hidden = false;
        })
        .catch((error) => {
          showMessage(`Error: ${error.message}`, true);
        });
    };

    const openModalForDelete = () => {
      selectedId = parseInt(selectElement.value, 10);
      if (!selectedId) {
        showMessage("Por favor selecciona un estatus primero.", true);
        return;
      }

      currentMode = "delete";
      if (modalTitle) {
        modalTitle.textContent = `Eliminar ${labelTarget}`;
      }
      if (fieldset) {
        fieldset.style.display = "none";
      }
      const nombreInput = form.querySelector("#estatus-caso-nombre");
      if (nombreInput) {
        nombreInput.required = false;
      }
      if (saveBtn) {
        saveBtn.textContent = "Eliminar";
        saveBtn.classList.remove("btn--primary");
        saveBtn.classList.add("btn--danger");
      }
      if (modalMessage) {
        modalMessage.textContent = "¿Estás seguro de que deseas eliminar este estatus? Esta acción no se puede deshacer.";
        modalMessage.className = "modal-message";
        modalMessage.style.display = "block";
      }
      modal.hidden = false;
    };

    const submitForm = async (event) => {
      event.preventDefault();

      if (currentMode === "delete") {
        await deleteStatus(selectedId);
      } else {
        const nombreInput = form.querySelector("#estatus-caso-nombre");
        if (!nombreInput.value.trim()) {
          showMessage("El nombre del estatus es obligatorio.", true);
          nombreInput.focus();
          return;
        }

        const data = {
          nombre: nombreInput.value.trim(),
          orden: parseInt(form.querySelector("#estatus-caso-orden").value, 10) || 1,
        };

        if (currentMode === "create") {
          await createStatus(data);
        } else if (currentMode === "edit") {
          await updateStatus(selectedId, data);
        }
      }
    };

    const createStatus = async (data) => {
      try {
        const response = await fetch(apiBase, {
          method: "POST",
          headers: defaultHeaders(),
          body: JSON.stringify(data),
        });

        if (!response.ok) {
          const errorData = await response.json();
          let errorMessage = "Error al crear el estatus.";

          if (errorData.nombre) {
            errorMessage = Array.isArray(errorData.nombre) ? errorData.nombre[0] : errorData.nombre;
          } else if (errorData.detail) {
            errorMessage = errorData.detail;
          } else if (typeof errorData === 'object') {
            const firstError = Object.values(errorData).flat()[0];
            if (firstError) {
              errorMessage = String(firstError);
            }
          }

          showMessage(errorMessage, true);
          return;
        }

        const newStatus = await response.json();
        addOption(selectElement, newStatus);
        showMessage("Estatus de caso creado exitosamente.");
        setTimeout(closeModal, 1000);
      } catch (error) {
        showMessage(`Error: ${error.message}`, true);
      }
    };

    const updateStatus = async (id, data) => {
      try {
        const response = await fetch(`${apiBase}${id}/`, {
          method: "PATCH",
          headers: defaultHeaders(),
          body: JSON.stringify(data),
        });

        if (!response.ok) {
          const errorData = await response.json();
          let errorMessage = "Error al actualizar el estatus.";

          if (errorData.nombre) {
            errorMessage = Array.isArray(errorData.nombre) ? errorData.nombre[0] : errorData.nombre;
          } else if (errorData.detail) {
            errorMessage = errorData.detail;
          } else if (typeof errorData === 'object') {
            const firstError = Object.values(errorData).flat()[0];
            if (firstError) {
              errorMessage = String(firstError);
            }
          }

          showMessage(errorMessage, true);
          return;
        }

        const updated = await response.json();
        updateOption(selectElement, updated);
        showMessage("Estatus de caso actualizado exitosamente.");
        setTimeout(closeModal, 1000);
      } catch (error) {
        showMessage(`Error: ${error.message}`, true);
      }
    };

    const deleteStatus = async (id) => {
      try {
        const response = await fetch(`${apiBase}${id}/`, {
          method: "DELETE",
          headers: defaultHeaders(),
        });

        if (!response.ok) {
          const errorData = await response.json();
          let errorMessage = "Error al eliminar el estatus.";

          if (errorData.detail) {
            errorMessage = errorData.detail;
          } else if (typeof errorData === 'object') {
            const firstError = Object.values(errorData).flat()[0];
            if (firstError) {
              errorMessage = String(firstError);
            }
          }

          showMessage(errorMessage, true);
          return;
        }

        removeOption(selectElement, id);
        showMessage("Estatus de caso eliminado exitosamente.");
        setTimeout(closeModal, 1000);
      } catch (error) {
        showMessage(`Error: ${error.message}`, true);
      }
    };

    const addOption = (select, data) => {
      const option = document.createElement("option");
      option.value = data.id;
      option.textContent = data.nombre;
      select.appendChild(option);
      select.value = data.id;
    };

    const updateOption = (select, data) => {
      const option = select.querySelector(`option[value="${data.id}"]`);
      if (option) {
        option.textContent = data.nombre;
      }
    };

    const removeOption = (select, id) => {
      const idStr = String(id);
      const option = select.querySelector(`option[value="${idStr}"]`);
      if (option) {
        option.remove();
      }
      if (select.value === idStr) {
        select.value = "";
      }
    };

    // Event listeners
    if (openBtn) {
      openBtn.addEventListener("click", openModalForCreate);
    }
    if (editBtn) {
      editBtn.addEventListener("click", openModalForEdit);
    }
    if (deleteBtn) {
      deleteBtn.addEventListener("click", openModalForDelete);
    }

    closeBtns.forEach((btn) => {
      btn.addEventListener("click", closeModal);
    });

    if (form) {
      form.addEventListener("submit", submitForm);
    }

    const overlay = modal ? modal.querySelector(".modal-overlay") : null;
    if (overlay) {
      overlay.addEventListener("click", closeModal);
    }
  }

  function initTipoViolenciaCrud() {
    const selectElement = document.querySelector("#id_tipo_violencia");
    const modal = document.getElementById("tipo-violencia-modal");
    const form = document.getElementById("tipo-violencia-form");
    const fieldset = form ? form.querySelector("#tipo-violencia-fields") : null;
    const openBtn = document.querySelector("[data-tipo-violencia-modal-open]");
    const editBtn = document.querySelector("[data-tipo-violencia-modal-edit]");
    const deleteBtn = document.querySelector("[data-tipo-violencia-modal-delete]");
    const closeBtns = modal ? modal.querySelectorAll("[data-modal-close]") : [];
    const saveBtn = form ? form.querySelector("[data-tipo-violencia-save]") : null;
    const modalTitle = modal ? modal.querySelector("[data-modal-title]") : null;
    const modalMessage = modal ? modal.querySelector("[data-modal-message]") : null;

    if (!selectElement || !modal || !form) {
      return;
    }

    const apiBase = "/api/tipos-violencia/";
    let currentMode = "create";
    let selectedId = null;

    const showMessage = (message, isError = false) => {
      if (modalMessage) {
        modalMessage.textContent = message;
        modalMessage.className = isError ? "modal-message error" : "modal-message success";
        modalMessage.style.display = isError || message ? "block" : "none";
      }
    };

    const closeModal = () => {
      modal.hidden = true;
      form.reset();
      if (modalMessage) {
        modalMessage.style.display = "none";
        modalMessage.className = "modal-message";
      }
    };

    const openModalForCreate = () => {
      currentMode = "create";
      if (modalTitle) {
        modalTitle.textContent = "Agregar tipo de violencia";
      }
      if (fieldset) {
        fieldset.style.display = "block";
      }
      const nombreInput = form.querySelector("#tipo-violencia-nombre");
      if (nombreInput) {
        nombreInput.required = true;
      }
      if (saveBtn) {
        saveBtn.textContent = "Guardar";
        saveBtn.classList.remove("btn--danger");
        saveBtn.classList.add("btn--primary");
      }
      form.reset();
      nombreInput.focus();
      if (modalMessage) {
        modalMessage.style.display = "none";
      }
      modal.hidden = false;
    };

    const openModalForEdit = () => {
      selectedId = parseInt(selectElement.value, 10);
      if (!selectedId) {
        showMessage("Selecciona un tipo de violencia primero.", true);
        return;
      }

      currentMode = "edit";
      if (modalTitle) {
        modalTitle.textContent = "Editar tipo de violencia";
      }
      if (fieldset) {
        fieldset.style.display = "block";
      }
      const nombreInput = form.querySelector("#tipo-violencia-nombre");
      if (nombreInput) {
        nombreInput.required = true;
      }
      if (saveBtn) {
        saveBtn.textContent = "Guardar";
        saveBtn.classList.remove("btn--danger");
        saveBtn.classList.add("btn--primary");
      }

      fetch(`${apiBase}${selectedId}/`, {
        headers: { "X-Requested-With": "XMLHttpRequest" },
      })
        .then((response) => {
          if (!response.ok) throw new Error("No se pudo cargar el tipo de violencia");
          return response.json();
        })
        .then((data) => {
          form.querySelector("#tipo-violencia-nombre").value = data.nombre || "";
          form.querySelector("#tipo-violencia-descripcion").value = data.descripcion || "";
          if (modalMessage) {
            modalMessage.style.display = "none";
          }
          modal.hidden = false;
        })
        .catch((error) => {
          showMessage(`Error: ${error.message}`, true);
        });
    };

    const openModalForDelete = () => {
      selectedId = parseInt(selectElement.value, 10);
      if (!selectedId) {
        showMessage("Selecciona un tipo de violencia primero.", true);
        return;
      }

      currentMode = "delete";
      if (modalTitle) {
        modalTitle.textContent = "Eliminar tipo de violencia";
      }
      if (fieldset) {
        fieldset.style.display = "none";
      }
      const nombreInput = form.querySelector("#tipo-violencia-nombre");
      if (nombreInput) {
        nombreInput.required = false;
      }
      if (saveBtn) {
        saveBtn.textContent = "Eliminar";
        saveBtn.classList.remove("btn--primary");
        saveBtn.classList.add("btn--danger");
      }
      if (modalMessage) {
        modalMessage.textContent = "¿Estás seguro de eliminar este tipo de violencia? Esta acción no se puede deshacer.";
        modalMessage.className = "modal-message warning";
        modalMessage.style.display = "block";
      }
      modal.hidden = false;
    };

    const submitForm = async (event) => {
      event.preventDefault();

      if (currentMode === "delete") {
        await deleteType(selectedId);
      } else {
        const nombreInput = form.querySelector("#tipo-violencia-nombre");
        if (!nombreInput.value.trim()) {
          showMessage("El nombre es obligatorio.", true);
          nombreInput.focus();
          return;
        }

        const data = {
          nombre: nombreInput.value.trim(),
          descripcion: form.querySelector("#tipo-violencia-descripcion").value.trim(),
        };

        if (currentMode === "create") {
          await createType(data);
        } else if (currentMode === "edit") {
          await updateType(selectedId, data);
        }
      }
    };

    const createType = async (data) => {
      try {
        const response = await fetch(apiBase, {
          method: "POST",
          headers: defaultHeaders(),
          body: JSON.stringify(data),
        });

        if (!response.ok) {
          const errorData = await response.json();
          const errorMessage = extractErrorMessage(errorData) || "Error al crear el tipo de violencia.";
          showMessage(errorMessage, true);
          return;
        }

        const created = await response.json();
        addOption(selectElement, created);
        selectElement.value = created.id;
        showMessage("Tipo de violencia creado.", false);
        setTimeout(closeModal, 800);
      } catch (error) {
        showMessage(`Error: ${error.message}`, true);
      }
    };

    const updateType = async (id, data) => {
      try {
        const response = await fetch(`${apiBase}${id}/`, {
          method: "PATCH",
          headers: defaultHeaders(),
          body: JSON.stringify(data),
        });

        if (!response.ok) {
          const errorData = await response.json();
          const errorMessage = extractErrorMessage(errorData) || "Error al actualizar el tipo de violencia.";
          showMessage(errorMessage, true);
          return;
        }

        const updated = await response.json();
        updateOption(selectElement, updated);
        showMessage("Tipo de violencia actualizado.", false);
        setTimeout(closeModal, 800);
      } catch (error) {
        showMessage(`Error: ${error.message}`, true);
      }
    };

    const deleteType = async (id) => {
      try {
        const response = await fetch(`${apiBase}${id}/`, {
          method: "DELETE",
          headers: defaultHeaders(),
        });

        if (!response.ok) {
          const errorData = await response.json();
          const errorMessage = extractErrorMessage(errorData) || "Error al eliminar el tipo de violencia.";
          showMessage(errorMessage, true);
          return;
        }

        removeOption(selectElement, id);
        showMessage("Tipo de violencia eliminado.", false);
        setTimeout(closeModal, 800);
      } catch (error) {
        showMessage(`Error: ${error.message}`, true);
      }
    };

    const addOption = (select, data) => {
      const option = document.createElement("option");
      option.value = data.id;
      option.textContent = data.nombre;
      select.appendChild(option);
    };

    const updateOption = (select, data) => {
      const option = select.querySelector(`option[value="${data.id}"]`);
      if (option) {
        option.textContent = data.nombre;
      }
    };

    const removeOption = (select, id) => {
      const idStr = String(id);
      const option = select.querySelector(`option[value="${idStr}"]`);
      if (option) {
        option.remove();
      }
      if (select.value === idStr) {
        select.value = "";
      }
    };

    if (openBtn) openBtn.addEventListener("click", openModalForCreate);
    if (editBtn) editBtn.addEventListener("click", openModalForEdit);
    if (deleteBtn) deleteBtn.addEventListener("click", openModalForDelete);
    if (saveBtn) form.addEventListener("submit", submitForm);
    closeBtns.forEach((btn) => btn.addEventListener("click", closeModal));
  }

  function initSolicitanteCrud() {
    createSimpleCrud({
      selectSelector: "#id_solicitante",
      modalId: "solicitante-modal",
      formId: "solicitante-form",
      fieldsetId: "solicitante-fields",
      openBtnSelector: "[data-solicitante-modal-open]",
      editBtnSelector: "[data-solicitante-modal-edit]",
      deleteBtnSelector: "[data-solicitante-modal-delete]",
      saveBtnSelector: "[data-solicitante-save]",
      modalTitleText: {
        create: "Agregar solicitante",
        edit: "Editar solicitante",
        delete: "Eliminar solicitante",
      },
      apiBase: "/api/solicitantes/",
      nameInputSelector: "#solicitante-nombre",
      descriptionSelector: "#solicitante-descripcion",
      deleteWarning:
        "¿Estás seguro de que deseas eliminar este solicitante? Esta acción no se puede deshacer.",
    });
  }

  function initDestinatarioCrud() {
    createSimpleCrud({
      selectSelector: "#id_dirigido_a",
      modalId: "destinatario-modal",
      formId: "destinatario-form",
      fieldsetId: "destinatario-fields",
      openBtnSelector: "[data-destinatario-modal-open]",
      editBtnSelector: "[data-destinatario-modal-edit]",
      deleteBtnSelector: "[data-destinatario-modal-delete]",
      saveBtnSelector: "[data-destinatario-save]",
      modalTitleText: {
        create: "Agregar destinatario",
        edit: "Editar destinatario",
        delete: "Eliminar destinatario",
      },
      apiBase: "/api/destinatarios/",
      nameInputSelector: "#destinatario-nombre",
      descriptionSelector: "#destinatario-descripcion",
      deleteWarning:
        "¿Estás seguro de que deseas eliminar este destinatario? Esta acción no se puede deshacer.",
    });
  }

  function initEstatusTramiteCrud() {
    createSimpleCrud({
      selectSelector: "#id_estatus",
      modalId: "estatus-caso-modal",
      formId: "estatus-caso-form",
      fieldsetId: "estatus-caso-fields",
      openBtnSelector: "[data-estatus-caso-modal-open]",
      editBtnSelector: "[data-estatus-caso-modal-edit]",
      deleteBtnSelector: "[data-estatus-caso-modal-delete]",
      saveBtnSelector: "[data-estatus-caso-save]",
      modalTitleText: {
        create: "Agregar estatus de trámite",
        edit: "Editar estatus de trámite",
        delete: "Eliminar estatus de trámite",
      },
      apiBase: "/api/estatus-tramite/",
      nameInputSelector: "#estatus-caso-nombre",
      descriptionSelector: "#estatus-caso-orden",
      deleteWarning:
        "¿Estás seguro de que deseas eliminar este estatus? Esta acción no se puede deshacer.",
      customDataBuilder: (form) => ({
        nombre: form.querySelector("#estatus-caso-nombre").value.trim(),
        orden: parseInt(form.querySelector("#estatus-caso-orden").value, 10) || 1,
      }),
      populateForm: (form, data) => {
        form.querySelector("#estatus-caso-nombre").value = data.nombre || "";
        form.querySelector("#estatus-caso-orden").value = data.orden || 1;
      },
    });
  }

  function createSimpleCrud(config) {
    const {
      selectSelector,
      modalId,
      formId,
      fieldsetId,
      openBtnSelector,
      editBtnSelector,
      deleteBtnSelector,
      saveBtnSelector,
      modalTitleText,
      apiBase,
      nameInputSelector,
      descriptionSelector,
      deleteWarning,
      customDataBuilder,
      populateForm,
    } = config;

    const selectElement = document.querySelector(selectSelector);
    const modal = document.getElementById(modalId);
    const form = document.getElementById(formId);
    const fieldset = form ? form.querySelector(`#${fieldsetId}`) : null;
    const openBtn = document.querySelector(openBtnSelector);
    const editBtn = document.querySelector(editBtnSelector);
    const deleteBtn = document.querySelector(deleteBtnSelector);
    const closeBtns = modal ? modal.querySelectorAll("[data-modal-close]") : [];
    const saveBtn = form ? form.querySelector(saveBtnSelector) : null;
    const modalTitle = modal ? modal.querySelector("[data-modal-title]") : null;
    const modalMessage = modal ? modal.querySelector("[data-modal-message]") : null;

    if (!selectElement || !modal || !form) {
      return;
    }
    form.setAttribute("novalidate", "novalidate");

    let currentMode = "create";
    let selectedId = null;

    const showMessage = (message, isError = false) => {
      if (modalMessage) {
        modalMessage.textContent = message;
        modalMessage.className = isError ? "modal-message error" : "modal-message success";
        modalMessage.style.display = isError || message ? "block" : "none";
      }
    };

    const closeModal = () => {
      modal.hidden = true;
      form.reset();
      if (modalMessage) {
        modalMessage.style.display = "none";
        modalMessage.className = "modal-message";
      }
    };

    const openModalForCreate = () => {
      currentMode = "create";
      if (modalTitle) {
        modalTitle.textContent = modalTitleText.create;
      }
      if (fieldset) {
        fieldset.style.display = "block";
      }
      const nombreInput = form.querySelector(nameInputSelector);
      if (nombreInput) {
        nombreInput.required = true;
      }
      if (saveBtn) {
        saveBtn.textContent = "Guardar";
        saveBtn.classList.remove("btn--danger");
        saveBtn.classList.add("btn--primary");
      }
      form.reset();
      nombreInput?.focus();
      if (modalMessage) {
        modalMessage.style.display = "none";
      }
      modal.hidden = false;
    };

    const openModalForEdit = () => {
      selectedId = parseInt(selectElement.value, 10);
      if (!selectedId) {
        showMessage("Selecciona un registro primero.", true);
        return;
      }

      currentMode = "edit";
      if (modalTitle) {
        modalTitle.textContent = modalTitleText.edit;
      }
      if (fieldset) {
        fieldset.style.display = "block";
      }
      const nombreInput = form.querySelector(nameInputSelector);
      if (nombreInput) {
        nombreInput.required = true;
      }
      if (saveBtn) {
        saveBtn.textContent = "Guardar";
        saveBtn.classList.remove("btn--danger");
        saveBtn.classList.add("btn--primary");
      }

      fetch(`${apiBase}${selectedId}/`, {
        headers: { "X-Requested-With": "XMLHttpRequest" },
      })
        .then((response) => {
          if (!response.ok) throw new Error("No se pudo cargar la información");
          return response.json();
        })
        .then((data) => {
          if (typeof populateForm === "function") {
            populateForm(form, data);
          } else {
            form.querySelector(nameInputSelector).value = data.nombre || "";
            form.querySelector(descriptionSelector).value = data.descripcion || "";
          }
          if (modalMessage) {
            modalMessage.style.display = "none";
          }
          modal.hidden = false;
        })
        .catch((error) => {
          showMessage(`Error: ${error.message}`, true);
        });
    };

    const openModalForDelete = () => {
      selectedId = parseInt(selectElement.value, 10);
      if (!selectedId) {
        showMessage("Selecciona un registro primero.", true);
        return;
      }

      currentMode = "delete";
      if (modalTitle) {
        modalTitle.textContent = modalTitleText.delete;
      }
      if (fieldset) {
        fieldset.style.display = "none";
      }
      const nombreInput = form.querySelector(nameInputSelector);
      if (nombreInput) {
        nombreInput.required = false;
      }
      if (saveBtn) {
        saveBtn.textContent = "Eliminar";
        saveBtn.classList.remove("btn--primary");
        saveBtn.classList.add("btn--danger");
      }
      if (modalMessage) {
        modalMessage.textContent = deleteWarning;
        modalMessage.className = "modal-message warning";
        modalMessage.style.display = "block";
      }
      modal.hidden = false;
    };

    const submitForm = async (event) => {
      event.preventDefault();

      if (currentMode === "delete") {
        await deleteRecord(selectedId);
      } else {
        const nombreInput = form.querySelector(nameInputSelector);
        if (!nombreInput.value.trim()) {
          showMessage("El nombre es obligatorio.", true);
          nombreInput.focus();
          return;
        }

        const data =
          typeof customDataBuilder === "function"
            ? customDataBuilder(form)
            : {
              nombre: nombreInput.value.trim(),
              descripcion: form.querySelector(descriptionSelector).value.trim(),
            };

        if (currentMode === "create") {
          await createRecord(data);
        } else if (currentMode === "edit") {
          await updateRecord(selectedId, data);
        }
      }
    };

    const createRecord = async (data) => {
      try {
        const response = await fetch(apiBase, {
          method: "POST",
          headers: defaultHeaders(),
          body: JSON.stringify(data),
        });

        if (!response.ok) {
          const errorData = await response.json();
          const errorMessage = extractErrorMessage(errorData) || "Error al crear el registro.";
          showMessage(errorMessage, true);
          return;
        }

        const created = await response.json();
        addOption(selectElement, created);
        selectElement.value = created.id;
        showMessage("Registro creado correctamente.");
        setTimeout(closeModal, 800);
      } catch (error) {
        showMessage(`Error: ${error.message}`, true);
      }
    };

    const updateRecord = async (id, data) => {
      try {
        const response = await fetch(`${apiBase}${id}/`, {
          method: "PATCH",
          headers: defaultHeaders(),
          body: JSON.stringify(data),
        });

        if (!response.ok) {
          const errorData = await response.json();
          const errorMessage = extractErrorMessage(errorData) || "Error al actualizar el registro.";
          showMessage(errorMessage, true);
          return;
        }

        const updated = await response.json();
        updateOption(selectElement, updated);
        showMessage("Registro actualizado correctamente.");
        setTimeout(closeModal, 800);
      } catch (error) {
        showMessage(`Error: ${error.message}`, true);
      }
    };

    const deleteRecord = async (id) => {
      try {
        const response = await fetch(`${apiBase}${id}/`, {
          method: "DELETE",
          headers: defaultHeaders(),
        });

        if (!response.ok) {
          const errorData = await response.json();
          const errorMessage = extractErrorMessage(errorData) || "Error al eliminar el registro.";
          showMessage(errorMessage, true);
          return;
        }

        removeOption(selectElement, id);
        showMessage("Registro eliminado.");
        setTimeout(closeModal, 800);
      } catch (error) {
        showMessage(`Error: ${error.message}`, true);
      }
    };

    const addOption = (select, data) => {
      const option = document.createElement("option");
      option.value = data.id;
      option.textContent = data.nombre;
      select.appendChild(option);
    };

    const updateOption = (select, data) => {
      const option = select.querySelector(`option[value="${data.id}"]`);
      if (option) {
        option.textContent = data.nombre;
      }
    };

    const removeOption = (select, id) => {
      const idStr = String(id);
      const option = select.querySelector(`option[value="${idStr}"]`);
      if (option) {
        option.remove();
      }
      if (select.value === idStr) {
        select.value = "";
      }
    };

    if (openBtn) openBtn.addEventListener("click", openModalForCreate);
    if (editBtn) editBtn.addEventListener("click", openModalForEdit);
    if (deleteBtn) deleteBtn.addEventListener("click", openModalForDelete);
    if (saveBtn) form.addEventListener("submit", submitForm);
    closeBtns.forEach((btn) => btn.addEventListener("click", closeModal));
  }

  function initReceptoresAdicionales(config = {}) {
    const {
      tableSelector = "[data-receptores-rows]",
      hiddenSelector = "#id_receptores_adicionales",
      addBtnSelector = "[data-receptor-adicional-add]",
      modalId = "receptor-adicional-modal",
      formId = "receptor-adicional-form",
      nameSelector = "#receptor-adicional-nombre",
      initialsSelector = "#receptor-adicional-iniciales",
      sexoSelector = "#receptor-adicional-sexo",
      saveBtnSelector = "[data-receptor-adicional-save]",
    } = config;
    const tableBody = document.querySelector(tableSelector);
    const hiddenInput = document.querySelector(hiddenSelector);
    const addBtn = document.querySelector(addBtnSelector);
    const modal = document.getElementById(modalId);
    const form = document.getElementById(formId);
    const modalMessage = modal ? modal.querySelector("[data-modal-message]") : null;
    const saveBtn = form ? form.querySelector(saveBtnSelector) : null;
    const closeBtns = modal ? modal.querySelectorAll("[data-modal-close]") : [];

    if (!tableBody || !hiddenInput || !modal || !form) {
      return null;
    }

    let currentIndex = null;

    const loadData = () => {
      try {
        const data = JSON.parse(hiddenInput.value || "[]");
        return Array.isArray(data) ? data : [];
      } catch (_err) {
        return [];
      }
    };

    const saveData = (data) => {
      hiddenInput.value = JSON.stringify(data);
      renderTable(data);
    };

    const renderTable = (data) => {
      tableBody.innerHTML = "";
      if (!data.length) {
        const row = document.createElement("tr");
        row.className = "table__empty-row";
        const cell = document.createElement("td");
        cell.colSpan = 4;
        cell.className = "table__empty";
        cell.textContent = "No hay receptores adicionales.";
        row.appendChild(cell);
        tableBody.appendChild(row);
        return;
      }
      data.forEach((item, index) => {
        const row = document.createElement("tr");
        row.innerHTML = `
          <td>${item.nombre || "-"}</td>
          <td>${item.iniciales || "-"}</td>
          <td>${item.sexo === "M" ? "Mujer" : item.sexo === "H" ? "Hombre" : "-"}</td>
          <td class="table-actions">
            <button type="button" class="table-actions__link" data-action="edit" data-index="${index}">Editar</button>
            <button type="button" class="table-actions__link table-actions__link--danger" data-action="delete" data-index="${index}">Eliminar</button>
          </td>
        `;
        tableBody.appendChild(row);
      });
    };

    const openModal = (index = null) => {
      currentIndex = index;
      const data = loadData();
      if (index != null && data[index]) {
        form.querySelector(nameSelector).value = data[index].nombre || "";
        form.querySelector(initialsSelector).value = data[index].iniciales || "";
        form.querySelector(sexoSelector).value = data[index].sexo || "";
      } else {
        form.reset();
      }
      if (modalMessage) {
        modalMessage.style.display = "none";
        modalMessage.className = "modal-message";
        modalMessage.textContent = "";
      }
      modal.hidden = false;
    };

    const closeModal = () => {
      modal.hidden = true;
      form.reset();
      if (modalMessage) {
        modalMessage.style.display = "none";
        modalMessage.className = "modal-message";
        modalMessage.textContent = "";
      }
    };

    const handleSubmit = (event) => {
      event.preventDefault();
      const nombre = form.querySelector(nameSelector).value.trim();
      const iniciales = form.querySelector(initialsSelector).value.trim();
      const sexo = form.querySelector(sexoSelector).value;
      if (!nombre && !iniciales && !sexo) {
        if (modalMessage) {
          modalMessage.textContent = "Captura al menos un dato (nombre, iniciales o sexo).";
          modalMessage.className = "modal-message error";
          modalMessage.style.display = "block";
        }
        return;
      }
      const data = loadData();
      const record = { nombre, iniciales, sexo };
      if (currentIndex != null && data[currentIndex]) {
        data[currentIndex] = record;
      } else {
        data.push(record);
      }
      saveData(data);
      closeModal();
    };

    const handleTableClick = (event) => {
      const target = event.target;
      if (!(target instanceof HTMLElement)) return;
      const action = target.dataset.action;
      const index = target.dataset.index ? parseInt(target.dataset.index, 10) : null;
      if (action === "edit" && index != null) {
        openModal(index);
      } else if (action === "delete" && index != null) {
        const data = loadData();
        data.splice(index, 1);
        saveData(data);
      }
    };

    addBtn?.addEventListener("click", () => openModal(null));
    form.addEventListener("submit", handleSubmit);
    tableBody.addEventListener("click", handleTableClick);
    closeBtns.forEach((btn) => btn.addEventListener("click", closeModal));

    renderTable(loadData());

    return {
      reset() {
        saveData([]);
      },
    };
  }

  function initGeneradoresAdicionales(config = {}) {
    return initReceptoresAdicionales({
      tableSelector: "[data-generadores-rows]",
      hiddenSelector: "#id_generadores_adicionales",
      addBtnSelector: "[data-generador-adicional-add]",
      modalId: "generador-adicional-modal",
      formId: "generador-adicional-form",
      nameSelector: "#generador-adicional-nombre",
      initialsSelector: "#generador-adicional-iniciales",
      sexoSelector: "#generador-adicional-sexo",
      saveBtnSelector: "[data-generador-adicional-save]",
      ...config,
    });
  }

  function initViolenciasAdicionales(config = {}) {
    const {
      tableSelector = "[data-violencias-rows]",
      hiddenSelector = "#id_tipos_violencia_adicionales",
      addBtnSelector = "[data-violencia-adicional-add]",
      selectSelector = "#id_tipo_violencia",
    } = config;
    const tableBody = document.querySelector(tableSelector);
    const hiddenInput = document.querySelector(hiddenSelector);
    const addBtn = document.querySelector(addBtnSelector);
    const select = document.querySelector(selectSelector);

    if (!tableBody || !hiddenInput || !addBtn || !select) {
      return null;
    }

    const loadData = () => {
      try {
        const value = hiddenInput.value || "[]";
        const data = JSON.parse(value);
        return Array.isArray(data) ? data : [];
      } catch (_err) {
        return [];
      }
    };

    const saveData = (data) => {
      hiddenInput.value = JSON.stringify(data);
      renderTable(data);
    };

    const renderTable = (data) => {
      tableBody.innerHTML = "";
      if (!data.length) {
        const row = document.createElement("tr");
        row.className = "table__empty-row";
        row.innerHTML = '<td colspan="2" class="table__empty">No hay tipos adicionales.</td>';
        tableBody.appendChild(row);
        return;
      }
      data.forEach((item, index) => {
        const row = document.createElement("tr");
        row.innerHTML = `
          <td>${item.nombre || "-"}</td>
          <td class="table-actions">
            <button type="button" class="table-actions__link table-actions__link--danger" data-action="delete" data-index="${index}">Eliminar</button>
          </td>
        `;
        tableBody.appendChild(row);
      });
    };

    addBtn.addEventListener("click", () => {
      const value = select.value;
      const nombre = select.options[select.selectedIndex]?.textContent?.trim() || "";
      if (!value || !nombre) {
        window.alert("Selecciona un tipo de violencia antes de agregarlo.");
        return;
      }
      const data = loadData();
      if (data.some((item) => String(item.id) === String(value))) {
        window.alert("Ese tipo de violencia ya fue agregado.");
        return;
      }
      data.push({ id: value, nombre });
      saveData(data);
    });

    tableBody.addEventListener("click", (event) => {
      const target = event.target;
      if (!(target instanceof HTMLElement)) return;
      if (target.dataset.action !== "delete") return;
      const index = parseInt(target.dataset.index || "-1", 10);
      if (index < 0) return;
      const data = loadData();
      data.splice(index, 1);
      saveData(data);
    });

    renderTable(loadData());
    return {
      reset() {
        saveData([]);
      },
    };
  }

  function initSelectTypeahead() {
    const boundForms = new WeakSet();

    document.querySelectorAll("[data-select-typeahead]").forEach((input) => {
      const targetSelector = input.getAttribute("data-typeahead-target");
      const resultsSelector = input.getAttribute("data-typeahead-results");
      const limitAttr = input.getAttribute("data-typeahead-limit");
      const parsedLimit =
        limitAttr === null ? Number.POSITIVE_INFINITY : parseInt(limitAttr, 10);
      const resultsLimit =
        Number.isFinite(parsedLimit) && parsedLimit > 0
          ? parsedLimit
          : Number.POSITIVE_INFINITY;
      if (!targetSelector || !resultsSelector) return;
      const select = document.querySelector(targetSelector);
      const results = document.querySelector(resultsSelector);
      if (!select || !results) return;

      const normalize = (value) => {
        const text = String(value || "").trim().toLowerCase();
        try {
          return text.normalize("NFD").replace(/[\u0300-\u036f]/g, "");
        } catch (_err) {
          return text;
        }
      };

      const renderResults = (query) => {
        const needle = normalize(query);
        results.innerHTML = "";
        let options = Array.from(select.options)
          .filter((option) => option.value)
          .filter((option) => !needle || normalize(option.textContent).includes(needle));
        if (Number.isFinite(resultsLimit)) {
          options = options.slice(0, resultsLimit);
        }
        const matches = options;
        if (!matches.length) {
          results.hidden = true;
          return;
        }
        const list = document.createElement("ul");
        list.className = "cct-suggestion-list";
        matches.forEach((option) => {
          const entry = document.createElement("li");
          entry.className = "cct-suggestion-item";
          const btn = document.createElement("button");
          btn.type = "button";
          btn.className = "btn btn--ghost btn--sm";
          btn.textContent = option.textContent;
          btn.addEventListener("click", () => {
            select.value = option.value;
            select.dispatchEvent(new Event("change", { bubbles: true }));
            input.value = option.textContent;
            results.hidden = true;
          });
          entry.appendChild(btn);
          list.appendChild(entry);
        });
        results.appendChild(list);
        results.hidden = false;
      };

      const clearSelection = () => {
        if (!select.value) return;
        select.value = "";
        select.dispatchEvent(new Event("change", { bubbles: true }));
      };

      input.addEventListener("input", () => {
        renderResults(input.value);
        if (!String(input.value || "").trim()) {
          clearSelection();
        }
      });
      select.addEventListener("change", () => {
        const selected = select.selectedOptions && select.selectedOptions[0];
        if (selected && selected.value) {
          input.value = selected.textContent || "";
        }
      });
      const selectExactMatch = () => {
        const value = normalize(input.value);
        if (!value) {
          clearSelection();
          results.hidden = true;
          return;
        }
        const options = Array.from(select.options).filter((option) => option.value);
        const match = options.find((option) => normalize(option.textContent) === value);
        if (match) {
          select.value = match.value;
          select.dispatchEvent(new Event("change", { bubbles: true }));
          results.hidden = true;
        }
      };
      const initialSelected = select.selectedOptions && select.selectedOptions[0];
      if (initialSelected && initialSelected.value) {
        input.value = initialSelected.textContent || "";
      }
      input.addEventListener("focus", () => renderResults(input.value));
      input.addEventListener("blur", selectExactMatch);
      input.addEventListener("keydown", (event) => {
        if (event.key === "Enter") {
          selectExactMatch();
        }
      });
      document.addEventListener("click", (event) => {
        if (!(event.target instanceof Node)) return;
        if (!results.contains(event.target) && event.target !== input) {
          results.hidden = true;
        }
      });

      const form = input.closest("form");
      if (form && !boundForms.has(form)) {
        boundForms.add(form);
        form.addEventListener("submit", (event) => {
          let hasErrors = false;
          form.querySelectorAll("[data-select-typeahead]").forEach((typeahead) => {
            const target = typeahead.getAttribute("data-typeahead-target");
            if (!target) return;
            const linkedSelect = document.querySelector(target);
            if (!linkedSelect || !linkedSelect.required) return;
            const value = linkedSelect.value;
            const errorId = `${linkedSelect.id}-error`;
            let error = form.querySelector(`#${errorId}`);
            if (!value) {
              hasErrors = true;
              if (!error) {
                error = document.createElement("span");
                error.className = "error-text";
                error.id = errorId;
                typeahead.insertAdjacentElement("afterend", error);
              }
              error.textContent = "Selecciona una opción de la lista.";
              typeahead.setAttribute("aria-invalid", "true");
            } else if (error) {
              error.remove();
              typeahead.removeAttribute("aria-invalid");
            }
          });
          if (hasErrors) {
            event.preventDefault();
          }
        });
      }
    });
  }

  function initTramiteCasoDetail() {
    const modal = document.getElementById("tramite-caso-modal");
    const openBtn = document.querySelector("[data-tramite-caso-modal-open]");
    const closeBtns = modal ? modal.querySelectorAll("[data-modal-close]") : [];
    const form = modal ? modal.querySelector("form") : null;
    const standaloneForm = document.querySelector("[data-tramite-caso-form]");
    if (!modal || !openBtn || !form) {
      if (standaloneForm) {
        const standaloneCctInput = queryByNameSuffix(
          standaloneForm,
          "cct_codigo",
          "#id_cct_codigo",
        );
        const standaloneHiddenCctInput = queryByNameSuffix(
          standaloneForm,
          "cct",
          "#id_cct",
        );
        const standaloneNombreInput = queryByNameSuffix(
          standaloneForm,
          "cct_nombre",
          "#id_cct_nombre",
        );
        const standaloneModalidadInput = queryByNameSuffix(
          standaloneForm,
          "cct_modalidad",
          "#id_cct_modalidad",
        );
        const standaloneSistemaInput = queryByNameSuffix(
          standaloneForm,
          "cct_sistema",
          "#id_cct_sistema",
        );
        const standaloneAsesorInput = queryByNameSuffix(
          standaloneForm,
          "asesor_cct",
          "#id_asesor_cct",
        );
        const standaloneDatalist = document.getElementById("cct-options");

        setupCCTForm({
          form: standaloneForm,
          lookupUrl: standaloneForm.dataset.lookupUrl || "",
          apiBase: standaloneForm.dataset.cctApi || "",
          cctInput: standaloneCctInput,
          hiddenCctInput: standaloneHiddenCctInput,
          nombreInput: standaloneNombreInput,
          servicioInput: standaloneModalidadInput,
          sistemaInput: standaloneSistemaInput,
          asesorInput: standaloneAsesorInput,
          datalist: standaloneDatalist,
          suggestionsContainer: standaloneForm.querySelector("[data-cct-suggestions]"),
          modalId: "cct-modal",
          canCreate: standaloneForm.dataset.cctCanCreate === "true",
          canEdit: standaloneForm.dataset.cctCanEdit === "true",
          canDelete: standaloneForm.dataset.cctCanDelete === "true",
        });

        const hiddenInput = standaloneForm.querySelector("[name$='receptores_adicionales']");
        initReceptoresAdicionales({
          tableSelector: "[data-receptores-rows]",
          hiddenSelector: hiddenInput ? `#${hiddenInput.id}` : "#id_receptores_adicionales",
          addBtnSelector: "[data-receptor-adicional-add]",
          modalId: "receptor-adicional-modal",
          formId: "receptor-adicional-form",
          nameSelector: "#receptor-adicional-nombre",
          initialsSelector: "#receptor-adicional-iniciales",
          sexoSelector: "#receptor-adicional-sexo",
        });
        const hiddenGeneradores = standaloneForm.querySelector("[name$='generadores_adicionales']");
        initGeneradoresAdicionales({
          tableSelector: "[data-generadores-rows]",
          hiddenSelector: hiddenGeneradores ? `#${hiddenGeneradores.id}` : "#id_generadores_adicionales",
          addBtnSelector: "[data-generador-adicional-add]",
          modalId: "generador-adicional-modal",
          formId: "generador-adicional-form",
          nameSelector: "#generador-adicional-nombre",
          initialsSelector: "#generador-adicional-iniciales",
          sexoSelector: "#generador-adicional-sexo",
          saveBtnSelector: "[data-generador-adicional-save]",
        });
        const hiddenViolencias = standaloneForm.querySelector("[name$='tipos_violencia_adicionales']");
        initViolenciasAdicionales({
          tableSelector: "[data-violencias-rows]",
          hiddenSelector: hiddenViolencias ? `#${hiddenViolencias.id}` : "#id_tipos_violencia_adicionales",
          addBtnSelector: "[data-violencia-adicional-add]",
          selectSelector: standaloneForm.querySelector("#id_tipo_violencia")
            ? "#id_tipo_violencia"
            : "#id_tramite_caso-tipo_violencia",
        });
        initPrefijoOficioCrud();
      }
      return;
    }

    if (openBtn && !openBtn.dataset.modalFallbackBound) {
      openBtn.dataset.modalFallbackBound = "true";
      openBtn.addEventListener("click", (event) => {
        event.preventDefault();
        modal.hidden = false;
        const firstInput = modal.querySelector("input, select, textarea");
        firstInput?.focus();
      });
    }
    closeBtns.forEach((btn) => {
      if (btn.dataset.modalFallbackBound) {
        return;
      }
      btn.dataset.modalFallbackBound = "true";
      btn.addEventListener("click", () => {
        modal.hidden = true;
      });
    });

    const modalCctInput = queryByNameSuffix(form, "cct_codigo");
    const modalHiddenCctInput = queryByNameSuffix(form, "cct");
    const modalNombreInput = queryByNameSuffix(form, "cct_nombre");
    const modalModalidadInput = queryByNameSuffix(form, "cct_modalidad");
    const modalSistemaInput = queryByNameSuffix(form, "cct_sistema");
    const modalAsesorInput = queryByNameSuffix(form, "asesor_cct");
    const modalDatalist = document.getElementById("cct-options-modal");
    if (modalCctInput && modalDatalist) {
      modalCctInput.setAttribute("list", modalDatalist.id);
    }

    setupCCTForm({
      form,
      lookupUrl: form.dataset.lookupUrl || "",
      apiBase: form.dataset.cctApi || "",
      cctInput: modalCctInput,
      hiddenCctInput: modalHiddenCctInput,
      nombreInput: modalNombreInput,
      servicioInput: modalModalidadInput,
      sistemaInput: modalSistemaInput,
      asesorInput: modalAsesorInput,
      datalist: modalDatalist,
      suggestionsContainer: form.querySelector("[data-cct-suggestions]"),
      modalId: "cct-modal",
      canCreate: form.dataset.cctCanCreate === "true",
      canEdit: form.dataset.cctCanEdit === "true",
      canDelete: form.dataset.cctCanDelete === "true",
    });

    const hiddenReceptores = form.querySelector("[name$='receptores_adicionales']");
    const hiddenGeneradores = form.querySelector("[name$='generadores_adicionales']");
    const hiddenViolencias = form.querySelector("[name$='tipos_violencia_adicionales']");

    const receptorsManager = initReceptoresAdicionales({
      tableSelector: "[data-receptores-rows-modal]",
      hiddenSelector: hiddenReceptores ? `#${hiddenReceptores.id}` : "#id_tramite_caso-receptores_adicionales",
      addBtnSelector: "[data-receptor-adicional-modal-add]",
      modalId: "receptor-adicional-modal-tramite",
      formId: "receptor-adicional-form-tramite",
      nameSelector: "#receptor-adicional-nombre-tramite",
      initialsSelector: "#receptor-adicional-iniciales-tramite",
      sexoSelector: "#receptor-adicional-sexo-tramite",
    });
    const generatorsManager = initGeneradoresAdicionales({
      tableSelector: "[data-generadores-rows-modal]",
      hiddenSelector: hiddenGeneradores ? `#${hiddenGeneradores.id}` : "#id_tramite_caso-generadores_adicionales",
      addBtnSelector: "[data-generador-adicional-modal-add]",
      modalId: "generador-adicional-modal-tramite",
      formId: "generador-adicional-form-tramite",
      nameSelector: "#generador-adicional-nombre-tramite",
      initialsSelector: "#generador-adicional-iniciales-tramite",
      sexoSelector: "#generador-adicional-sexo-tramite",
      saveBtnSelector: "[data-generador-adicional-save]",
    });
    const violenceManager = initViolenciasAdicionales({
      tableSelector: "[data-violencias-rows-modal]",
      hiddenSelector: hiddenViolencias ? `#${hiddenViolencias.id}` : "#id_tramite_caso-tipos_violencia_adicionales",
      addBtnSelector: "[data-violencia-adicional-modal-add]",
      selectSelector: "#id_tramite_caso-tipo_violencia",
    });

    const resetForm = () => {
      const folioIds = Array.from(form.querySelectorAll("[name='folio_generado_id'], [name$='-folio_generado_id']"))
        .map((input) => (input.value || "").trim())
        .filter(Boolean);
      if (folioIds.length) {
        document.dispatchEvent(
          new CustomEvent("folio:cancel-preview", {
            detail: { folioIds },
          }),
        );
      }
      form.reset();
      if (receptorsManager) {
        receptorsManager.reset();
      }
      if (generatorsManager) {
        generatorsManager.reset();
      }
      if (violenceManager) {
        violenceManager.reset();
      }
      modal.querySelectorAll("[data-select-typeahead]").forEach((input) => {
        input.value = "";
        input.dispatchEvent(new Event("input", { bubbles: true }));
      });
      form.querySelectorAll("[data-folio-preview-hint]").forEach((hint) => {
        hint.classList.remove("is-pending");
        hint.textContent =
          "El folio generado se confirma al guardar el registro. Si sales sin guardar, se cancelará automáticamente.";
      });
    };

    const initCatalogCruds = () => {
      // Inicializar CRUD para Tipo de Proceso
      initGenericCrud({
        catalogType: "tipo-proceso",
        selectSelector: "#id_tramite_caso-tipo",
        modalId: "tipo-proceso-modal",
        apiEndpoint: "/api/tipos-proceso/",
        fieldConfig: { label: "tipo de trámite" },
      });

      // Inicializar CRUD para Tipo de Violencia
      initGenericCrud({
        catalogType: "tipo-violencia",
        selectSelector: "#id_tramite_caso-tipo_violencia",
        modalId: "tipo-violencia-modal",
        apiEndpoint: "/api/tipos-violencia/",
        fieldConfig: { label: "tipo de violencia" },
      });

      // Inicializar CRUD para Solicitante
      initGenericCrud({
        catalogType: "solicitante",
        selectSelector: "#id_tramite_caso-solicitante",
        modalId: "solicitante-modal",
        apiEndpoint: "/api/solicitantes/",
        fieldConfig: { label: "solicitante" },
      });

      // Inicializar CRUD para Destinatario
      initGenericCrud({
        catalogType: "destinatario",
        selectSelector: "#id_tramite_caso-dirigido_a",
        modalId: "destinatario-modal",
        apiEndpoint: "/api/destinatarios/",
        fieldConfig: { label: "destinatario" },
      });

      // Inicializar CRUD para Estatus de Trámite
      initGenericCrud({
        catalogType: "estatus-tramite",
        selectSelector: "#id_tramite_caso-estatus",
        modalId: "estatus-tramite-modal",
        apiEndpoint: "/api/estatus-tramite/",
        fieldConfig: { label: "estatus de trámite" },
      });
    };

    // Inicializar CRUD de Prefijos una sola vez
    initPrefijoOficioCrud();

    openBtn.addEventListener("click", (event) => {
      event.preventDefault();
      resetForm();
      modal.hidden = false;
      initTramiteCasoPrefijos();
      initCatalogCruds();
      const firstInput = modal.querySelector("input, select, textarea");
      firstInput?.focus();
    });
    closeBtns.forEach((btn) =>
      btn.addEventListener("click", () => {
        resetForm();
        modal.hidden = true;
      })
    );
  }

  function initSimpleModals() {
    const configs = [
      { openSelector: "[data-convertir-caso-modal-open]", modalId: "convertir-caso-modal" },
      { openSelector: "[data-promover-tramite-modal-open]", modalId: "promover-tramite-modal" },
    ];
    configs.forEach(({ openSelector, modalId }) => {
      const openBtn = document.querySelector(openSelector);
      const modal = document.getElementById(modalId);
      if (!openBtn || !modal) return;
      const closeBtns = modal.querySelectorAll("[data-modal-close]");
      openBtn.addEventListener("click", () => {
        modal.hidden = false;
        modal.classList.add("is-open");
        const firstInput = modal.querySelector("input, select, textarea");
        firstInput?.focus();
      });
      closeBtns.forEach((btn) =>
        btn.addEventListener("click", () => {
          modal.hidden = true;
          modal.classList.remove("is-open");
        })
      );
    });
  }

  function initFolioGenerador() {
    const modal = document.getElementById("folio-generar-modal");
    if (!modal) return;
    const openButtons = document.querySelectorAll("[data-folio-open]");
    const openPreviewButtons = document.querySelectorAll("[data-folio-modal-open]");
    const closeBtns = modal.querySelectorAll("[data-modal-close]");
    const tipoInput = modal.querySelector("#folio-tipo");
    const casoInput = modal.querySelector("#folio-caso-id");
    const tramiteInput = modal.querySelector("#folio-tramite-id");
    const nextInput = modal.querySelector("#folio-next");
    const form = modal.querySelector("#folio-generar-form");
    const previewUrl = form?.dataset.folioPreviewUrl || "/folios/generar/preview/";
    const cancelUrl = form?.dataset.folioCancelUrl || "/folios/generar/cancelar/";
    const folioHiddenSelector = "input[name='folio_generado_id'], input[name$='-folio_generado_id']";
    const pendingFolios = new Set();
    const boundForms = new WeakSet();
    const baseHintText =
      "El folio generado se confirma al guardar el registro. Si sales sin guardar, se cancelará automáticamente.";

    const updateFolioHint = (idInput, folioValue, pending) => {
      const block = idInput?.closest(".expediente-block");
      const hint = block?.querySelector("[data-folio-preview-hint]");
      if (!hint) return;
      if (pending && folioValue) {
        hint.textContent = `Folio provisional: ${folioValue}. Se confirmará cuando guardes el registro.`;
        hint.classList.add("is-pending");
        return;
      }
      hint.textContent = baseHintText;
      hint.classList.remove("is-pending");
    };

    const bindOwnerForm = (ownerForm) => {
      if (!ownerForm || boundForms.has(ownerForm)) return;
      boundForms.add(ownerForm);
      ownerForm.addEventListener("submit", () => {
        ownerForm.querySelectorAll(folioHiddenSelector).forEach((hidden) => {
          const value = (hidden.value || "").trim();
          if (value) {
            pendingFolios.delete(value);
          }
          updateFolioHint(hidden, "", false);
        });
      });
    };

    const cancelFolios = (folioIds, useBeacon = false) => {
      const ids = Array.from(
        new Set(
          (folioIds || [])
            .map((value) => String(value || "").trim())
            .filter(Boolean),
        ),
      );
      if (!ids.length) return;

      ids.forEach((id) => pendingFolios.delete(id));

      if (useBeacon && navigator.sendBeacon) {
        const payload = new FormData();
        payload.append("csrfmiddlewaretoken", getCsrfToken());
        ids.forEach((id) => payload.append("folio_ids", id));
        navigator.sendBeacon(cancelUrl, payload);
        return;
      }

      const body = new URLSearchParams();
      body.set("csrfmiddlewaretoken", getCsrfToken());
      ids.forEach((id) => body.append("folio_ids", id));
      fetch(cancelUrl, {
        method: "POST",
        headers: {
          "X-Requested-With": "XMLHttpRequest",
          "X-CSRFToken": getCsrfToken(),
        },
        body,
        keepalive: true,
      }).catch((error) => {
        console.error("No se pudieron cancelar folios provisionales", error);
      });
    };

    const flushPendingFolios = (useBeacon = false) => {
      if (!pendingFolios.size) return;
      cancelFolios(Array.from(pendingFolios), useBeacon);
    };

    document.addEventListener("folio:cancel-preview", (event) => {
      const ids = event?.detail?.folioIds || [];
      cancelFolios(ids, false);
    });

    window.addEventListener("pagehide", () => {
      flushPendingFolios(true);
    });
    document.addEventListener("visibilitychange", () => {
      if (document.visibilityState === "hidden") {
        flushPendingFolios(true);
      }
    });

    const openModal = (btn) => {
      const tipo = btn.dataset.tipo || "";
      const id = btn.dataset.id || "";
      const next = btn.dataset.next || "";
      if (tipoInput) tipoInput.value = tipo;
      if (casoInput) casoInput.value = tipo === "caso" ? id : "";
      if (tramiteInput) tramiteInput.value = tipo === "tramite" ? id : "";
      if (nextInput) nextInput.value = next;
      delete modal.dataset.folioTargetInput;
      delete modal.dataset.folioTargetId;
      delete modal.dataset.folioPreview;
      modal.hidden = false;
    };

    openButtons.forEach((btn) => {
      btn.addEventListener("click", () => openModal(btn));
    });
    openPreviewButtons.forEach((btn) => {
      btn.addEventListener("click", () => {
        if (tipoInput) tipoInput.value = btn.dataset.folioTipo || "";
        if (casoInput) casoInput.value = "";
        if (tramiteInput) tramiteInput.value = "";
        if (nextInput) nextInput.value = "";
        if (btn.dataset.folioInput) modal.dataset.folioTargetInput = btn.dataset.folioInput;
        if (btn.dataset.folioIdInput) modal.dataset.folioTargetId = btn.dataset.folioIdInput;
        modal.dataset.folioPreview = "true";
        modal.hidden = false;
      });
    });
    closeBtns.forEach((btn) => {
      btn.addEventListener("click", () => {
        modal.hidden = true;
      });
    });

    if (form) {
      form.addEventListener("submit", async (event) => {
        if (modal.dataset.folioPreview !== "true") return;
        event.preventDefault();
        const prefijoSelect = form.querySelector("#folio-prefijo");
        if (!prefijoSelect || !prefijoSelect.value) {
          window.alert("Selecciona un prefijo para generar el folio.");
          return;
        }
        const tipo = tipoInput?.value || "";
        if (!tipo) {
          window.alert("No se pudo determinar el tipo de folio.");
          return;
        }
        const formData = new FormData();
        formData.append("prefijo_id", prefijoSelect.value);
        formData.append("tipo", tipo);
        try {
          const res = await fetch(previewUrl, {
            method: "POST",
            headers: { "X-Requested-With": "XMLHttpRequest", "X-CSRFToken": getCsrfToken() },
            body: formData,
          });
          if (!res.ok) throw new Error(`HTTP ${res.status}`);
          const data = await res.json();
          const input = modal.dataset.folioTargetInput
            ? document.querySelector(modal.dataset.folioTargetInput)
            : null;
          const idInput = modal.dataset.folioTargetId
            ? document.querySelector(modal.dataset.folioTargetId)
            : null;
          const previousId = (idInput?.value || "").trim();
          if (input && data.folio) {
            input.value = data.folio;
            input.dispatchEvent(new Event("input", { bubbles: true }));
            input.dispatchEvent(new Event("change", { bubbles: true }));
          }
          if (idInput && data.folio_id) {
            const nextId = String(data.folio_id).trim();
            if (previousId && previousId !== nextId) {
              pendingFolios.add(previousId);
            }
            idInput.value = nextId;
            pendingFolios.add(nextId);
            bindOwnerForm(idInput.closest("form"));
            updateFolioHint(idInput, data.folio || "", true);
          }
          modal.hidden = true;
        } catch (error) {
          console.error("Error generando folio", error);
          window.alert("No se pudo generar el folio. Intenta de nuevo.");
        }
      });
    }

    initGenericCrud({
      catalogType: "prefijo-folio",
      selectSelector: "#folio-prefijo",
      modalId: "prefijo-folio-modal",
      apiEndpoint: "/api/prefijos-folio/",
      fieldConfig: { label: "prefijo de folio" },
    });
  }

  function initFolioGeneradorCampos() {
    const buttons = document.querySelectorAll("[data-folio-generate]");
    if (!buttons.length) return;
    buttons.forEach((btn) => {
      btn.addEventListener("click", async () => {
        const modal = document.getElementById("folio-generar-modal");
        if (!modal) return;
        modal.dataset.folioTargetInput = btn.dataset.folioInput || "";
        modal.dataset.folioTargetId = btn.dataset.folioIdInput || "";
        modal.dataset.folioPreview = "true";
        const tipoInput = modal.querySelector("#folio-tipo");
        const casoInput = modal.querySelector("#folio-caso-id");
        const tramiteInput = modal.querySelector("#folio-tramite-id");
        const nextInput = modal.querySelector("#folio-next");
        if (tipoInput) tipoInput.value = btn.dataset.folioTipo || "";
        if (casoInput) casoInput.value = "";
        if (tramiteInput) tramiteInput.value = "";
        if (nextInput) nextInput.value = "";
        modal.hidden = false;
      });
    });
  }

  function initPrefijoFolioCrud() {
    initGenericCrud({
      catalogType: "prefijo-folio",
      selectSelector: "#id_prefijo",
      modalId: "prefijo-folio-modal",
      apiEndpoint: "/api/prefijos-folio/",
      fieldConfig: { label: "prefijo de folio" },
    });
  }

  function initFolioBuscar() {
    const input = document.querySelector("[data-folio-buscar]");
    const table = document.querySelector("#folio-buscar-resultados tbody");
    const selectCasos = document.querySelector("#id_casos");
    const selectTramite = document.querySelector("#id_tramite");
    const selectTipo = document.querySelector("#id_tipo");
    const filters = document.querySelectorAll("[data-folio-filter]");
    const idHint = document.querySelector("#folio-buscar-id-hint");
    let currentFilter = "all";
    const info = document.querySelector("#folio-buscar-seleccion");
    const casosContainer = document.querySelector("#folio-casos-seleccionados");
    const tramiteInfo = document.querySelector("#folio-tramite-seleccion");
    if (!input || !table) return;

    const selectedCasos = new Map();
    let selectedTramite = null;
    const escapeHtml = (value) =>
      String(value || "")
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/\"/g, "&quot;")
        .replace(/'/g, "&#39;");

    const renderEmpty = (text) => {
      table.innerHTML = `<tr><td colspan="4" class="table__empty">${text}</td></tr>`;
    };

    const ensureSelectOption = (select, value, label, selected = true) => {
      if (!select) return;
      if (select.tagName !== "SELECT") {
        select.value = value;
        return;
      }
      const strValue = String(value || "");
      if (!strValue) return;
      let option = Array.from(select.options).find((opt) => opt.value === strValue);
      if (!option) {
        option = document.createElement("option");
        option.value = strValue;
        option.textContent = label || strValue;
        select.appendChild(option);
      }
      if (selected) option.selected = true;
      if (!select.multiple) select.value = strValue;
    };

    const renderSelectedCasos = () => {
      if (!casosContainer) return;
      if (!selectedCasos.size) {
        casosContainer.innerHTML = "";
        return;
      }
      casosContainer.innerHTML = Array.from(selectedCasos.entries())
        .map(([id, label]) => {
          const safeLabel = escapeHtml(label);
          return `<span class="chip chip--strong" data-caso-chip="${id}">${safeLabel}<button type="button" class="chip__remove" data-remove-caso="${id}" aria-label="Quitar caso">&times;</button></span>`;
        })
        .join("");
    };

    const updateInfo = () => {
      if (info) {
        if (selectedCasos.size) {
          info.textContent = `Casos seleccionados: ${selectedCasos.size}`;
        } else if (selectedTramite) {
          info.textContent = `Trámite seleccionado: ${selectedTramite.label}`;
        } else {
          info.textContent = "";
        }
      }
      if (tramiteInfo) {
        tramiteInfo.textContent = selectedTramite ? selectedTramite.label : "";
      }
    };

    const clearCasos = () => {
      selectedCasos.clear();
      if (selectCasos && selectCasos.tagName === "SELECT") {
        Array.from(selectCasos.options).forEach((option) => {
          option.selected = false;
        });
      }
      renderSelectedCasos();
    };

    const setCaso = (id, label) => {
      const strId = String(id || "");
      if (!strId) return;
      selectedCasos.set(strId, label || strId);
      ensureSelectOption(selectCasos, strId, label, true);
      selectedTramite = null;
      if (selectTramite) selectTramite.value = "";
      if (selectTipo) selectTipo.value = "caso";
      renderSelectedCasos();
      updateInfo();
    };

    const setTramite = (id, label) => {
      const strId = String(id || "");
      if (!strId) return;
      selectedTramite = { id: strId, label: label || strId };
      ensureSelectOption(selectTramite, strId, label, true);
      clearCasos();
      if (selectTipo) selectTipo.value = "tramite";
      updateInfo();
    };

    const syncInitialSelection = () => {
      if (selectCasos && selectCasos.tagName === "SELECT") {
        Array.from(selectCasos.options).forEach((option) => {
          if (option.selected) {
            selectedCasos.set(option.value, option.textContent || option.value);
          }
        });
        renderSelectedCasos();
      }
      if (selectTramite && selectTramite.value) {
        const option = selectTramite.tagName === "SELECT"
          ? selectTramite.options[selectTramite.selectedIndex]
          : null;
        selectedTramite = {
          id: selectTramite.value,
          label: option?.textContent || selectTramite.value,
        };
      }
      if (selectTipo) {
        if (selectedCasos.size) {
          selectTipo.value = "caso";
        } else if (selectedTramite) {
          selectTipo.value = "tramite";
        } else {
          selectTipo.value = "";
        }
      }
      updateInfo();
    };

    const debounce = (fn, wait = 350) => {
      let t;
      return (...args) => {
        clearTimeout(t);
        t = setTimeout(() => fn(...args), wait);
      };
    };

    const search = debounce(async () => {
      const q = input.value.trim();
      const isNumeric = /^\d+$/.test(q);
      if (idHint) {
        idHint.hidden = !isNumeric;
      }
      if (!q) {
        renderEmpty("Busca para mostrar resultados.");
        return;
      }
      try {
        const url = input.dataset.folioBuscarUrl || "/folios/buscar/";
        const res = await fetch(`${url}?q=${encodeURIComponent(q)}`, {
          headers: { "X-Requested-With": "XMLHttpRequest" },
        });
        if (!res.ok) {
          renderEmpty("No se pudo cargar la búsqueda. Intenta de nuevo.");
          return;
        }
        const data = await res.json();
        const rows = [];
        const escapeRegExp = (value) => String(value || "").replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
        const highlightWithClass = (value, term, className) => {
          const safe = escapeHtml(value);
          if (!term) return safe;
          const re = new RegExp(`(${escapeRegExp(term)})`, "ig");
          return safe.replace(re, `<mark class="${className}">$1</mark>`);
        };
        const highlight = (value, term) => highlightWithClass(value, term, "inbox-highlight");
        const highlightSubtle = (value, term) => highlightWithClass(value, term, "inbox-highlight--subtle");

        const buildMeta = (item, term) => {
          const parts = [];
          if (item.cct) parts.push(`CCT: ${highlightSubtle(item.cct, term)}`);
          if (item.fecha) parts.push(`Fecha: ${item.fecha}`);
          if (item.estatus) parts.push(`Estatus: ${item.estatus}`);
          if (item.docente) parts.push(`Docente: ${highlightSubtle(item.docente, term)}`);
          if (item.tipo_tramite) parts.push(`Tipo: ${item.tipo_tramite}`);
          if (item.jerarquia) parts.push(item.jerarquia);
          return highlight(parts.join(" · "), term);
        };

        const casos = data.casos || [];
        const tramites = data.tramites || [];

        filters.forEach((btn) => {
          const label = btn.dataset.filterLabel || btn.textContent.trim();
          let countText = "";
          if (btn.dataset.folioFilter === "casos") countText = ` (${casos.length})`;
          if (btn.dataset.folioFilter === "tramites") countText = ` (${tramites.length})`;
          if (btn.dataset.folioFilter === "all") countText = ` (${casos.length + tramites.length})`;
          btn.textContent = `${label}${countText}`;
        });

        if (currentFilter !== "tramites") {
          casos.forEach((caso) => {
          const label = highlight(caso.label, q);
          const asunto = highlight(caso.asunto, q);
          rows.push(`
            <tr>
              <td data-label="Tipo">Caso</td>
              <td data-label="Referencia">
                <div class="search-result">
                  <div class="search-result__title">${label}</div>
                  <div class="search-result__meta">${buildMeta(caso, q)}</div>
                  ${caso.asunto ? `<div class="search-result__hint">${asunto}</div>` : ""}
                </div>
              </td>
              <td data-label="Expediente">${highlight(caso.expediente || "-", q)}</td>
              <td data-label="Asignar"><button type="button" class="btn btn--secondary btn--sm" data-folio-select data-tipo="caso" data-id="${caso.id}" data-label="${caso.label}">Asignar</button></td>
            </tr>
          `);
          });
        }
        if (currentFilter !== "casos") {
          tramites.forEach((tramite) => {
          const label = highlight(tramite.label, q);
          const asunto = highlight(tramite.asunto, q);
          rows.push(`
            <tr>
              <td data-label="Tipo">Trámite</td>
              <td data-label="Referencia">
                <div class="search-result">
                  <div class="search-result__title">${label}</div>
                  <div class="search-result__meta">${buildMeta(tramite, q)}</div>
                  ${tramite.asunto ? `<div class="search-result__hint">${asunto}</div>` : ""}
                </div>
              </td>
              <td data-label="Expediente">${highlight(tramite.expediente || "-", q)}</td>
              <td data-label="Asignar"><button type="button" class="btn btn--secondary btn--sm" data-folio-select data-tipo="tramite" data-id="${tramite.id}" data-label="${tramite.label}">Asignar</button></td>
            </tr>
          `);
          });
        }
        table.innerHTML = rows.length ? rows.join("") : `<tr><td colspan="4" class="table__empty">Sin resultados.</td></tr>`;
      } catch (err) {
        console.error("Folio search error", err);
        renderEmpty("Error de conexión al buscar.");
      }
    }, 350);

    const setFilter = (value) => {
      currentFilter = value;
      filters.forEach((btn) => {
        btn.classList.toggle("pill--active", btn.dataset.folioFilter === value);
      });
      search();
    };

    filters.forEach((btn) => {
      btn.addEventListener("click", () => setFilter(btn.dataset.folioFilter || "all"));
    });

    input.addEventListener("input", search);
    input.addEventListener("change", search);
    table.addEventListener("click", (event) => {
      const btn = event.target.closest("[data-folio-select]");
      if (!btn) return;
      if (btn.dataset.tipo === "caso") {
        setCaso(btn.dataset.id, btn.dataset.label || "");
      } else if (btn.dataset.tipo === "tramite") {
        setTramite(btn.dataset.id, btn.dataset.label || "");
      }
    });

    if (casosContainer) {
      casosContainer.addEventListener("click", (event) => {
        const btn = event.target.closest("[data-remove-caso]");
        if (!btn) return;
        const id = btn.dataset.removeCaso;
        selectedCasos.delete(id);
        if (selectCasos && selectCasos.tagName === "SELECT") {
          const option = Array.from(selectCasos.options).find((opt) => opt.value === id);
          if (option) option.selected = false;
        }
        renderSelectedCasos();
        updateInfo();
        if (selectTipo && !selectedCasos.size) {
          selectTipo.value = selectedTramite ? "tramite" : "";
        }
      });
    }

    syncInitialSelection();
  }

  function initFolioCopy() {
    const buttons = document.querySelectorAll("[data-copy-folio]");
    if (!buttons.length) return;

    const copyText = async (value) => {
      if (!value) return false;
      if (navigator.clipboard?.writeText) {
        try {
          await navigator.clipboard.writeText(value);
          return true;
        } catch (err) {
          console.warn("Clipboard API failed, falling back.", err);
        }
      }
      const textarea = document.createElement("textarea");
      textarea.value = value;
      textarea.setAttribute("readonly", "");
      textarea.style.position = "fixed";
      textarea.style.top = "-9999px";
      document.body.appendChild(textarea);
      textarea.select();
      let success = false;
      try {
        success = document.execCommand("copy");
      } catch (err) {
        success = false;
      }
      document.body.removeChild(textarea);
      return success;
    };

    buttons.forEach((btn) => {
      btn.addEventListener("click", async () => {
        const value = btn.dataset.copyFolio || "";
        const original = btn.textContent;
        const ok = await copyText(value);
        btn.textContent = ok ? "Copiado" : "No se pudo copiar";
        btn.classList.toggle("is-success", ok);
        btn.classList.toggle("is-error", !ok);
        setTimeout(() => {
          btn.textContent = original;
          btn.classList.remove("is-success", "is-error");
        }, 1400);
      });
    });
  }

  function initPdfFileValidation() {
    const inputs = document.querySelectorAll('input[type="file"][accept*="pdf"]');
    if (!inputs.length) return;
    inputs.forEach((input) => {
      input.addEventListener("change", () => {
        const files = Array.from(input.files || []);
        const invalid = files.find((file) => {
          const type = (file.type || "").toLowerCase();
          const name = (file.name || "").toLowerCase();
          return type !== "application/pdf" && type !== "application/x-pdf" && !name.endsWith(".pdf");
        });
        if (invalid) {
          input.setCustomValidity("Solo se permiten archivos PDF.");
          input.reportValidity();
          input.value = "";
        } else {
          input.setCustomValidity("");
        }
      });
    });
  }

  function initConvertirCasoConfirmations() {
    const wrappers = document.querySelectorAll("[data-confirm-wrapper]");
    const textWrappers = document.querySelectorAll("[data-confirm-text-wrapper]");
    if (!wrappers.length && !textWrappers.length) return;
    wrappers.forEach((wrapper) => {
      const scope = wrapper.closest(".modal") || wrapper.closest("form") || document;
      const eliminarCheckbox = scope.querySelector('input[name$="eliminar_caso_origen"]');
      const confirmarCheckbox = wrapper.querySelector('input[type="checkbox"]');
      const textWrapper = scope.querySelector("[data-confirm-text-wrapper]");
      const textInput = textWrapper ? textWrapper.querySelector("input, textarea") : null;
      if (!eliminarCheckbox || !confirmarCheckbox) return;
      const toggle = () => {
        const shouldConfirm = eliminarCheckbox.checked;
        wrapper.hidden = !shouldConfirm;
        confirmarCheckbox.required = shouldConfirm;
        if (!shouldConfirm) {
          confirmarCheckbox.checked = false;
        }
        if (textWrapper && textInput) {
          textWrapper.hidden = !shouldConfirm;
          textInput.required = shouldConfirm;
          if (!shouldConfirm) {
            textInput.value = "";
          }
        }
      };
      eliminarCheckbox.addEventListener("change", toggle);
      toggle();
    });
  }

  function initCasoDestinoSearch() {
    const containers = document.querySelectorAll("[data-caso-destino-search]");
    if (!containers.length) return;

    const debounce = (fn, wait = 350) => {
      let t;
      return (...args) => {
        clearTimeout(t);
        t = setTimeout(() => fn(...args), wait);
      };
    };

    containers.forEach((container) => {
      const input = container.querySelector("[data-caso-destino-input]");
      const idInput = container.querySelector("[data-caso-destino-id]");
      const goButton = container.querySelector("[data-caso-destino-go]");
      const tableBody = container.querySelector("[data-caso-destino-resultados] tbody");
      const select = container.querySelector('select[name$="caso_destino"]');
      const idHint = container.querySelector("[data-caso-destino-id-hint]");
      const info = container.querySelector("[data-caso-destino-seleccion]");
      if (!input || !tableBody || !select) return;

      const renderEmpty = (text) => {
        tableBody.innerHTML = `<tr><td colspan="7" class="table__empty">${text}</td></tr>`;
      };

      const setSelection = (tipo, id, label) => {
        if (tipo !== "caso") {
          return;
        }
        select.value = id;
        select.dispatchEvent(new Event("change", { bubbles: true }));
        if (info) {
          info.textContent = `Seleccionado: ${label}`;
        }
      };

      const escapeHtml = (value) =>
        String(value || "")
          .replace(/&/g, "&amp;")
          .replace(/</g, "&lt;")
          .replace(/>/g, "&gt;")
          .replace(/\"/g, "&quot;")
          .replace(/'/g, "&#39;");

      const escapeRegExp = (value) => String(value || "").replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
      const highlight = (value, term) => {
        const safe = escapeHtml(value);
        if (!term) return safe;
        const re = new RegExp(`(${escapeRegExp(term)})`, "ig");
        return safe.replace(re, '<mark class="inbox-highlight">$1</mark>');
      };

      const search = debounce(async () => {
        const q = input.value.trim();
        const isNumeric = /^\d+$/.test(q);
        if (idHint) idHint.hidden = !isNumeric;
        if (!q) {
          renderEmpty("Busca para mostrar resultados.");
          return;
        }
        try {
          const url = input.dataset.buscarUrl || "/folios/buscar/";
          const res = await fetch(`${url}?q=${encodeURIComponent(q)}`, {
            headers: { "X-Requested-With": "XMLHttpRequest" },
          });
          if (!res.ok) {
            renderEmpty("No se pudo cargar la búsqueda. Intenta de nuevo.");
            return;
          }
          const data = await res.json();
          const casos = data.casos || [];

          const rows = [];
          casos.forEach((caso) => {
            const label = highlight(caso.label, q);
            const asunto = highlight(caso.asunto, q);
            const cct = `${escapeHtml(caso.cct || "")}${caso.cct_nombre ? ` · ${escapeHtml(caso.cct_nombre)}` : ""}`;
            rows.push(`
              <tr>
                <td data-label="Tipo">Caso</td>
                <td data-label="Referencia">${label}${caso.asunto ? `<div class="table__hint">${asunto}</div>` : ""}</td>
                <td data-label="Expediente">${highlight(caso.expediente || "-", q)}</td>
                <td data-label="Estatus">${escapeHtml(caso.estatus || "Sin estatus")}</td>
                <td data-label="Asesor">${escapeHtml(caso.asesor || "-")}</td>
                <td data-label="CCT">${cct || "-"}</td>
                <td data-label="Seleccionar"><button type="button" class="btn btn--secondary btn--sm" data-caso-select data-tipo="caso" data-id="${caso.id}" data-label="${escapeHtml(caso.label)}">Seleccionar</button></td>
              </tr>
            `);
          });

          tableBody.innerHTML = rows.length
            ? rows.join("")
            : `<tr><td colspan="7" class="table__empty">Sin resultados.</td></tr>`;
        } catch (err) {
          console.error("Caso destino search error", err);
          renderEmpty("Error de conexión al buscar.");
        }
      }, 350);

      input.addEventListener("input", search);
      input.addEventListener("change", search);
      tableBody.addEventListener("click", (event) => {
        const btn = event.target.closest("[data-caso-select]");
        if (!btn || btn.disabled) return;
        setSelection(btn.dataset.tipo, btn.dataset.id, btn.dataset.label || "");
      });

      if (goButton && idInput) {
        goButton.addEventListener("click", () => {
          const value = idInput.value.trim();
          if (!value) return;
          input.value = value;
          input.dispatchEvent(new Event("input", { bubbles: true }));
        });
      }

      if (select.value && info) {
        const option = select.querySelector(`option[value="${select.value}"]`);
        if (option) {
          info.textContent = `Seleccionado: ${option.textContent}`;
        }
      }
    });
  }

  function initToggleSections() {
    const toggles = document.querySelectorAll("[data-toggle-section]");
    if (!toggles.length) return;
    toggles.forEach((btn) => {
      const targetSelector = btn.dataset.toggleSection;
      if (!targetSelector) return;
      const target = document.querySelector(targetSelector);
      if (!target) return;
      if (target.id) {
        btn.setAttribute("aria-controls", target.id);
      }
      const storageKey = `toggle:${targetSelector}`;
      const saved = window.localStorage.getItem(storageKey);
      const defaultMode = target.dataset.toggleDefault || "show";
      const count = Number(target.dataset.toggleCount || "0");
      const showLabel = btn.dataset.toggleShowLabel || "Mostrar";
      const hideLabel = btn.dataset.toggleHideLabel || "Ocultar";
      if (saved === "hidden") {
        target.hidden = true;
      } else if (saved === "visible") {
        target.hidden = false;
      } else if (defaultMode === "hidden") {
        target.hidden = true;
      } else if (defaultMode === "auto" && count >= 10) {
        target.hidden = true;
      }
      const updateLabel = () => {
        btn.textContent = target.hidden ? showLabel : hideLabel;
        btn.setAttribute("aria-expanded", String(!target.hidden));
      };
      btn.addEventListener("click", () => {
        target.hidden = !target.hidden;
        window.localStorage.setItem(storageKey, target.hidden ? "hidden" : "visible");
        updateLabel();
      });
      updateLabel();
    });
  }

  function initDuplicadosPreview() {
    const forms = document.querySelectorAll("[data-duplicados-form]");
    if (!forms.length) return;
    const endpoint = "/tramites/duplicados/preview/";
    const debounce = (fn, wait = 400) => {
      let t;
      return (...args) => {
        clearTimeout(t);
        t = setTimeout(() => fn(...args), wait);
      };
    };

    forms.forEach((form) => {
      const outputExp = form.querySelector("[data-duplicados-output-expediente]");
      const outputPart = form.querySelector("[data-duplicados-output-participantes]");
      if (!outputExp && !outputPart) return;
      const getVal = (base) => {
        const direct = form.querySelector(`[name="${base}"]`);
        if (direct) return direct.value.trim();
        const prefixed = form.querySelector(`[name$="-${base}"]`);
        return prefixed ? prefixed.value.trim() : "";
      };
      const normalizeExpediente = (value) => {
        if (!value) return "";
        const compact = value.toUpperCase().replace(/[.\-\s]/g, "");
        if (compact === "SN") return "";
        return value;
      };
      const excludeType = form.dataset.duplicadosType || "";
      const excludeId = form.dataset.duplicadosId || "";
      const buildList = (items) =>
        items
          .map((item) => {
            const label =
              item.type === "caso"
                ? `Caso #${item.id} · ${item.cct || ""} · ${item.numero_oficio || "sin expediente"}`
                : `Trámite #${item.id} · Caso ${item.caso_id} · ${item.numero_oficio || "sin expediente"}`;
            return `<li><a href="${item.url}">${label}</a></li>`;
          })
          .join("");

      const render = (data, hasExpedienteQuery, hasParticipantesQuery) => {
        const expItems = [...(data.expediente?.casos || []), ...(data.expediente?.tramites || [])];
        const partItems = [...(data.participantes?.casos || []), ...(data.participantes?.tramites || [])];

        if (outputExp) {
          if (!hasExpedienteQuery) {
            outputExp.hidden = true;
            outputExp.innerHTML = "";
          } else if (!expItems.length) {
            outputExp.hidden = false;
            outputExp.innerHTML = `<div class="duplicate-alert__title">Posibles duplicados encontrados</div><div class="help-text">Esta advertencia no bloquea el guardado.</div><div class="duplicate-alert__group"><div class="duplicate-alert__group-title">Coincidencias por número de expediente</div><div class="help-text">Sin coincidencias.</div></div>`;
          } else {
            outputExp.hidden = false;
            outputExp.innerHTML = `<div class="duplicate-alert__title">Posibles duplicados encontrados</div><div class="help-text">Esta advertencia no bloquea el guardado.</div><div class="duplicate-alert__group"><div class="duplicate-alert__group-title">Coincidencias por número de expediente</div><ul class="duplicate-alert__list">${buildList(expItems)}</ul></div>`;
          }
        }

        if (outputPart) {
          if (!hasParticipantesQuery) {
            outputPart.hidden = true;
            outputPart.innerHTML = "";
          } else if (!partItems.length) {
            outputPart.hidden = false;
            outputPart.innerHTML = `<div class="duplicate-alert__title">Posibles duplicados encontrados</div><div class="help-text">Esta advertencia no bloquea el guardado.</div><div class="duplicate-alert__group"><div class="duplicate-alert__group-title">Coincidencias por participantes</div><div class="help-text">Sin coincidencias.</div></div>`;
          } else {
            outputPart.hidden = false;
            outputPart.innerHTML = `<div class="duplicate-alert__title">Posibles duplicados encontrados</div><div class="help-text">Esta advertencia no bloquea el guardado.</div><div class="duplicate-alert__group"><div class="duplicate-alert__group-title">Coincidencias por participantes</div><ul class="duplicate-alert__list">${buildList(partItems)}</ul></div>`;
          }
        }
      };

      const requestPreview = debounce(async () => {
        const numeroOficioRaw = getVal("numero_oficio");
        const numeroOficio = normalizeExpediente(numeroOficioRaw);
        const payload = new URLSearchParams({
          numero_oficio: numeroOficio,
          generador_nombre: getVal("generador_nombre"),
          generador_iniciales: getVal("generador_iniciales"),
          receptor_nombre: getVal("receptor_nombre"),
          receptor_iniciales: getVal("receptor_iniciales"),
          exclude_type: excludeType,
          exclude_id: excludeId,
        });
        const hasExpedienteQuery = Boolean(numeroOficio);
        const hasParticipantesQuery = Boolean(
          payload.get("generador_nombre") ||
            payload.get("generador_iniciales") ||
            payload.get("receptor_nombre") ||
            payload.get("receptor_iniciales")
        );
        if (
          !hasExpedienteQuery &&
          !hasParticipantesQuery
        ) {
          if (outputExp) {
            outputExp.hidden = true;
            outputExp.innerHTML = "";
          }
          if (outputPart) {
            outputPart.hidden = true;
            outputPart.innerHTML = "";
          }
          return;
        }
        try {
          const response = await fetch(`${endpoint}?${payload.toString()}`, {
            headers: { "X-Requested-With": "XMLHttpRequest" },
          });
          if (!response.ok) return;
          const data = await response.json();
          render(data, hasExpedienteQuery, hasParticipantesQuery);
        } catch (err) {
          console.error("Duplicados preview error", err);
        }
      }, 450);

      const watched = [
        "numero_oficio",
        "generador_nombre",
        "generador_iniciales",
        "receptor_nombre",
        "receptor_iniciales",
      ];
      watched.forEach((base) => {
        const inputs = form.querySelectorAll(`[name="${base}"], [name$="-${base}"]`);
        inputs.forEach((input) => {
          input.addEventListener("input", requestPreview);
          input.addEventListener("change", requestPreview);
        });
      });
    });
  }

  function initFuncionDisplays() {
    const containers = document.querySelectorAll("[data-funcion-display]");
    containers.forEach((container) => {
      const targetId = container.dataset.target;
      const select = document.getElementById(targetId);
      if (!select) return;
      const primary = container.querySelector("[data-funcion-nombre]");
      const secondary = container.querySelector("[data-funcion-detalle]");

      const update = () => {
        const option = select.options[select.selectedIndex];
        if (!option || !primary || !secondary) return;
        const text = option.textContent || "";
        const [nombre, detalle] = text.split("·").map((t) => t.trim());
        primary.textContent = nombre || "-";
        secondary.textContent = detalle || "";
        secondary.style.display = detalle ? "block" : "none";
      };

      select.addEventListener("change", update);
      update();
    });
  }
  function initPrefijoOficioCrud() {
    // Inicializar objeto de debugging
    window.prefijoCrudDebug = window.prefijoCrudDebug || {
      logs: [],
      errors: [],
      calls: 0,
    };
    window.prefijoCrudDebug.calls++;

    const debugLog = (msg, data) => {
      console.log(msg, data);
      window.prefijoCrudDebug.logs.push({ timestamp: new Date().toISOString(), msg, data });
    };

    const debugError = (msg, data) => {
      console.error(msg, data);
      window.prefijoCrudDebug.errors.push({ timestamp: new Date().toISOString(), msg, data });
    };

    debugLog("[initPrefijoOficioCrud] Iniciando... (llamada #" + window.prefijoCrudDebug.calls + ")", new Date().toISOString());

    // Determinar si estamos en tramites_form o tramites_detail
    let numeroInput = document.querySelector("#id_numero_oficio");
    const isDetailView = !numeroInput;
    if (!numeroInput) {
      numeroInput = document.querySelector("#id_tramite_caso-numero_oficio");
    }
    if (!numeroInput) {
      numeroInput = document.querySelector("#id_bulk_tramite-numero_oficio");
    }

    debugLog("[initPrefijoOficioCrud] Contexto detectado:", {
      isDetailView,
      numeroInput: !!numeroInput,
      numeroInputId: numeroInput?.id,
    });

    // Buscar el select de prefijos de forma robusta para ambos contextos.
    let selectElement = null;
    if (isDetailView) {
      selectElement = document.querySelector("#prefijo-oficio-select-modal");
    }
    if (!selectElement) {
      selectElement = document.querySelector("#prefijo-oficio-select");
    }
    if (!selectElement && numeroInput) {
      const ownerForm = numeroInput.closest("form");
      if (ownerForm) {
        selectElement = ownerForm.querySelector("[data-prefijo-oficio-select]");
      }
    }
    if (!selectElement) {
      const allSelects = document.querySelectorAll("[data-prefijo-oficio-select]");
      if (allSelects.length) {
        selectElement = isDetailView ? allSelects[allSelects.length - 1] : allSelects[0];
      }
    }

    debugLog("[initPrefijoOficioCrud] Select encontrado:", {
      selectElement: !!selectElement,
      selectId: selectElement?.id,
    });

    const modal = document.getElementById("prefijo-oficio-modal");
    const form = document.getElementById("prefijo-oficio-form");
    const fieldset = form ? form.querySelector("#prefijo-oficio-fields") : null;

    debugLog("[initPrefijoOficioCrud] Modal y form encontrados:", {
      modal: !!modal,
      form: !!form,
      fieldset: !!fieldset,
    });

    // Buscar los botones con múltiples estrategias
    let openBtn = null, editBtn = null, deleteBtn = null;

    // Estrategia 1: Buscar en el contenedor padre directo
    if (selectElement) {
      const fieldContainer = selectElement.closest(".form-field");
      const actionsContainer = fieldContainer?.querySelector(".field-actions");

      debugLog("[initPrefijoOficioCrud] Búsqueda estrategia 1 (contenedor padre):", {
        fieldContainer: !!fieldContainer,
        actionsContainer: !!actionsContainer,
      });

      if (actionsContainer) {
        openBtn = actionsContainer.querySelector("[data-prefijo-oficio-modal-open]");
        editBtn = actionsContainer.querySelector("[data-prefijo-oficio-modal-edit]");
        deleteBtn = actionsContainer.querySelector("[data-prefijo-oficio-modal-delete]");

        debugLog("[initPrefijoOficioCrud] Botones encontrados en contenedor:", {
          openBtn: !!openBtn,
          editBtn: !!editBtn,
          deleteBtn: !!deleteBtn,
        });
      }
    }

    // Estrategia 2: Buscar todos los botones y seleccionar el correcto
    if (!openBtn || !editBtn || !deleteBtn) {
      const allOpenBtns = document.querySelectorAll("[data-prefijo-oficio-modal-open]");
      const allEditBtns = document.querySelectorAll("[data-prefijo-oficio-modal-edit]");
      const allDeleteBtns = document.querySelectorAll("[data-prefijo-oficio-modal-delete]");

      debugLog("[initPrefijoOficioCrud] Búsqueda estrategia 2 (todos los botones):", {
        allOpenBtns: allOpenBtns.length,
        allEditBtns: allEditBtns.length,
        allDeleteBtns: allDeleteBtns.length,
      });

      if (!openBtn && allOpenBtns.length > 0) {
        openBtn = isDetailView ? allOpenBtns[allOpenBtns.length - 1] : allOpenBtns[0];
      }
      if (!editBtn && allEditBtns.length > 0) {
        editBtn = isDetailView ? allEditBtns[allEditBtns.length - 1] : allEditBtns[0];
      }
      if (!deleteBtn && allDeleteBtns.length > 0) {
        deleteBtn = isDetailView ? allDeleteBtns[allDeleteBtns.length - 1] : allDeleteBtns[0];
      }

      debugLog("[initPrefijoOficioCrud] Botones seleccionados (estrategia 2):", {
        openBtn: !!openBtn,
        editBtn: !!editBtn,
        deleteBtn: !!deleteBtn,
      });
    }

    const closeBtns = modal ? modal.querySelectorAll("[data-modal-close]") : [];
    const saveBtn = form ? form.querySelector("[data-prefijo-oficio-save]") : null;
    const modalTitle = modal ? modal.querySelector("[data-modal-title]") : null;
    const modalMessage = modal ? modal.querySelector("[data-modal-message]") : null;
    const datalist = document.getElementById("prefijo-oficio-options");

    debugLog("[initPrefijoOficioCrud] Elementos adicionales encontrados:", {
      closeBtns: closeBtns.length,
      saveBtn: !!saveBtn,
      modalTitle: !!modalTitle,
      modalMessage: !!modalMessage,
      datalist: !!datalist,
    });

    if (!selectElement || !modal || !form || !numeroInput || !openBtn) {
      debugError("[initPrefijoOficioCrud] ❌ ELEMENTOS FALTANTES - Inicialización cancelada:", {
        selectElement: !!selectElement,
        selectElementId: selectElement?.id,
        modal: !!modal,
        form: !!form,
        numeroInput: !!numeroInput,
        numeroInputId: numeroInput?.id,
        isDetailView,
        openBtn: !!openBtn,
        editBtn: !!editBtn,
        deleteBtn: !!deleteBtn,
        timestamp: new Date().toISOString(),
      });
      return;
    }

    debugLog("[initPrefijoOficioCrud] ✅ Inicializado correctamente", {
      isDetailView,
      numeroInputId: numeroInput?.id,
      selectElementId: selectElement?.id,
      openBtn: !!openBtn,
      editBtn: !!editBtn,
      deleteBtn: !!deleteBtn,
      timestamp: new Date().toISOString(),
    });

    const apiBase = "/api/prefijos-oficio/";
    let currentMode = "create";
    let selectedId = null;

    const showMessage = (message, isError = false) => {
      if (modalMessage) {
        modalMessage.textContent = message;
        modalMessage.className = isError ? "modal-message error" : "modal-message success";
        modalMessage.style.display = isError || message ? "block" : "none";
      }
    };

    const closeModal = () => {
      modal.hidden = true;
      form.reset();
      if (modalMessage) {
        modalMessage.style.display = "none";
        modalMessage.className = "modal-message";
      }
    };

    const openModalForCreate = () => {
      console.log("[openModalForCreate] Click detectado en botón", new Date().toISOString());
      currentMode = "create";
      if (modalTitle) {
        modalTitle.textContent = "Agregar prefijo de oficio";
      }
      if (fieldset) {
        fieldset.style.display = "block";
      }
      const nombreInput = form.querySelector("#prefijo-oficio-nombre");
      if (nombreInput) {
        nombreInput.required = true;
      }
      if (saveBtn) {
        saveBtn.textContent = "Guardar";
        saveBtn.classList.remove("btn--danger");
        saveBtn.classList.add("btn--primary");
      }
      form.reset();
      nombreInput.focus();
      if (modalMessage) {
        modalMessage.style.display = "none";
      }
      modal.hidden = false;
      console.log("[openModalForCreate] Modal abierta correctamente");
    };

    const openModalForEdit = () => {
      console.log("[openModalForEdit] Click detectado en botón", new Date().toISOString());
      selectedId = parseInt(selectElement.value, 10);
      if (!selectedId) {
        showMessage("Selecciona un prefijo primero.", true);
        return;
      }

      currentMode = "edit";
      console.log("[openModalForEdit] Iniciando carga de prefijo ID:", selectedId);
      if (modalTitle) {
        modalTitle.textContent = "Editar prefijo de oficio";
      }
      if (fieldset) {
        fieldset.style.display = "block";
      }
      const nombreInput = form.querySelector("#prefijo-oficio-nombre");
      if (nombreInput) {
        nombreInput.required = true;
      }
      if (saveBtn) {
        saveBtn.textContent = "Guardar";
        saveBtn.classList.remove("btn--danger");
        saveBtn.classList.add("btn--primary");
      }

      fetch(`${apiBase}${selectedId}/`, {
        headers: { "X-Requested-With": "XMLHttpRequest" },
      })
        .then((response) => {
          if (!response.ok) throw new Error("No se pudo cargar el prefijo");
          return response.json();
        })
        .then((data) => {
          form.querySelector("#prefijo-oficio-nombre").value = data.nombre || "";
          form.querySelector("#prefijo-oficio-descripcion").value = data.descripcion || "";
          if (modalMessage) {
            modalMessage.style.display = "none";
          }
          modal.hidden = false;
        })
        .catch((error) => {
          showMessage(`Error: ${error.message}`, true);
        });
    };

    const openModalForDelete = () => {
      console.log("[openModalForDelete] Click detectado en botón", new Date().toISOString());
      selectedId = parseInt(selectElement.value, 10);
      if (!selectedId) {
        showMessage("Selecciona un prefijo primero.", true);
        return;
      }

      currentMode = "delete";
      console.log("[openModalForDelete] Preparando eliminación de ID:", selectedId);
      if (modalTitle) {
        modalTitle.textContent = "Eliminar prefijo de oficio";
      }
      if (fieldset) {
        fieldset.style.display = "none";
      }
      const nombreInput = form.querySelector("#prefijo-oficio-nombre");
      if (nombreInput) {
        nombreInput.required = false;
      }
      if (saveBtn) {
        saveBtn.textContent = "Eliminar";
        saveBtn.classList.remove("btn--primary");
        saveBtn.classList.add("btn--danger");
      }
      if (modalMessage) {
        modalMessage.textContent = "¿Estás seguro de que deseas eliminar este prefijo? Esta acción no se puede deshacer.";
        modalMessage.className = "modal-message";
        modalMessage.style.display = "block";
      }
      modal.hidden = false;
    };

    const submitForm = async (event) => {
      event.preventDefault();

      if (currentMode === "delete") {
        await deletePrefix(selectedId);
      } else {
        const nombreInput = form.querySelector("#prefijo-oficio-nombre");
        if (!nombreInput.value.trim()) {
          showMessage("El prefijo es obligatorio.", true);
          nombreInput.focus();
          return;
        }

        const data = {
          nombre: nombreInput.value.trim(),
          descripcion: form.querySelector("#prefijo-oficio-descripcion").value.trim(),
        };

        if (currentMode === "create") {
          await createPrefix(data);
        } else if (currentMode === "edit") {
          await updatePrefix(selectedId, data);
        }
      }
    };

    const createPrefix = async (data) => {
      try {
        const response = await fetch(apiBase, {
          method: "POST",
          headers: defaultHeaders(),
          body: JSON.stringify(data),
        });

        if (!response.ok) {
          const errorData = await response.json();
          const errorMessage = extractErrorMessage(errorData) || "Error al crear el prefijo.";
          showMessage(errorMessage, true);
          return;
        }

        const created = await response.json();
        addOption(selectElement, created);
        upsertDatalistOption(created.nombre);
        numeroInput.value = created.nombre;
        showMessage("Prefijo creado exitosamente.");
        setTimeout(closeModal, 800);
      } catch (error) {
        showMessage(`Error: ${error.message}`, true);
      }
    };

    const updatePrefix = async (id, data) => {
      try {
        const response = await fetch(`${apiBase}${id}/`, {
          method: "PATCH",
          headers: defaultHeaders(),
          body: JSON.stringify(data),
        });

        if (!response.ok) {
          const errorData = await response.json();
          const errorMessage = extractErrorMessage(errorData) || "Error al actualizar el prefijo.";
          showMessage(errorMessage, true);
          return;
        }

        const updated = await response.json();
        updateOption(selectElement, updated);
        upsertDatalistOption(updated.nombre);
        if (selectElement.value === String(updated.id)) {
          numeroInput.value = updated.nombre;
        }
        showMessage("Prefijo actualizado exitosamente.");
        setTimeout(closeModal, 800);
      } catch (error) {
        showMessage(`Error: ${error.message}`, true);
      }
    };

    const deletePrefix = async (id) => {
      try {
        const response = await fetch(`${apiBase}${id}/`, {
          method: "DELETE",
          headers: defaultHeaders(),
        });

        if (!response.ok) {
          const errorData = await response.json();
          const errorMessage = extractErrorMessage(errorData) || "Error al eliminar el prefijo.";
          showMessage(errorMessage, true);
          return;
        }

        const option = selectElement.querySelector(`option[value="${id}"]`);
        const optionLabel = option ? option.textContent : "";
        removeOption(selectElement, id);
        if (optionLabel) {
          removeDatalistOption(optionLabel);
          if (numeroInput.value === optionLabel) {
            numeroInput.value = "";
          }
        }
        showMessage("Prefijo eliminado.");
        setTimeout(closeModal, 800);
      } catch (error) {
        showMessage(`Error: ${error.message}`, true);
      }
    };

    const addOption = (select, data) => {
      const option = document.createElement("option");
      option.value = data.id;
      option.textContent = data.nombre;
      select.appendChild(option);
      select.value = data.id;
    };

    const updateOption = (select, data) => {
      const option = select.querySelector(`option[value="${data.id}"]`);
      if (option) {
        option.textContent = data.nombre;
      }
    };

    const removeOption = (select, id) => {
      const idStr = String(id);
      const option = select.querySelector(`option[value="${idStr}"]`);
      if (option) {
        option.remove();
      }
      if (select.value === idStr) {
        select.value = "";
      }
    };

    const upsertDatalistOption = (value) => {
      if (!datalist) {
        return;
      }
      const existing = Array.from(datalist.children).find((opt) => opt.value === value);
      if (existing) {
        return;
      }
      const option = document.createElement("option");
      option.value = value;
      datalist.appendChild(option);
    };

    const removeDatalistOption = (value) => {
      if (!datalist) {
        return;
      }
      const option = Array.from(datalist.children).find((opt) => opt.value === value);
      if (option) {
        option.remove();
      }
    };

    const applySelectedPrefix = () => {
      const selected = selectElement.selectedOptions[0];
      if (selected && selected.textContent) {
        numeroInput.value = selected.textContent;
        numeroInput.focus();
      }
    };

    if (openBtn) {
      openBtn.addEventListener("click", openModalForCreate);
      debugLog("[initPrefijoOficioCrud] Event listener registrado para openBtn");
    }
    if (editBtn) {
      editBtn.addEventListener("click", openModalForEdit);
      debugLog("[initPrefijoOficioCrud] Event listener registrado para editBtn");
    }
    if (deleteBtn) {
      deleteBtn.addEventListener("click", openModalForDelete);
      debugLog("[initPrefijoOficioCrud] Event listener registrado para deleteBtn");
    }
    if (saveBtn) {
      form.addEventListener("submit", submitForm);
      debugLog("[initPrefijoOficioCrud] Event listener registrado para form submit");
    }
    closeBtns.forEach((btn) => btn.addEventListener("click", closeModal));
    selectElement.addEventListener("change", applySelectedPrefix);
    debugLog("[initPrefijoOficioCrud] ✅ TODOS LOS EVENT LISTENERS REGISTRADOS");
  }
})();
