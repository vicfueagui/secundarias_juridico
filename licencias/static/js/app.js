(() => {
  "use strict";

  document.addEventListener("DOMContentLoaded", () => {
    initTabs();
    initDiagnosticoCrud();
    initControlInternoForm();
  });

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

  function initDiagnosticoCrud() {
    const modal = document.getElementById("diagnostico-modal");
    const select = document.getElementById("id_diagnostico");
    if (!modal || !select) {
      return;
    }

    const apiListUrl = modal.dataset.apiList;
    const form = modal.querySelector("#diagnostico-form");
    const nombreInput = form?.querySelector('input[name="nombre"]');
    const descripcionInput = form?.querySelector('textarea[name="descripcion"]');
    const idInput = form?.querySelector('input[name="diagnosticoId"]');
    const messageBox = modal.querySelector("[data-modal-message]");
    const titleEl = modal.querySelector("[data-modal-title]");
    const overlay = modal.querySelector(".modal-overlay");
    const actionButtons = document.querySelectorAll("[data-diagnostico-action]");

    if (
      !apiListUrl ||
      !form ||
      !nombreInput ||
      !descripcionInput ||
      !idInput ||
      !messageBox ||
      !titleEl ||
      !actionButtons.length
    ) {
      return;
    }

    let mode = "create";

    const closeTriggers = modal.querySelectorAll("[data-modal-close]");
    closeTriggers.forEach((trigger) => {
      trigger.addEventListener("click", closeModal);
    });
    overlay?.addEventListener("click", closeModal);
    modal.addEventListener("keydown", (event) => {
      if (event.key === "Escape") {
        event.preventDefault();
        closeModal();
      }
    });

    actionButtons.forEach((button) => {
      const action = button.dataset.diagnosticoAction;
      if (action === "create") {
        button.addEventListener("click", () => {
          form.reset();
          idInput.value = "";
          openModal("create");
        });
      } else if (action === "edit") {
        button.addEventListener("click", async () => {
          const selectedId = select.value;
          if (!selectedId) {
            window.alert("Selecciona un diagnóstico para editar.");
            return;
          }
          try {
            const data = await fetchDiagnosticoDetail(apiListUrl, selectedId);
            form.reset();
            idInput.value = data.id;
            nombreInput.value = data.nombre || "";
            descripcionInput.value = data.descripcion || "";
            openModal("edit");
          } catch (error) {
            displayMessage(error.message, true);
          }
        });
      } else if (action === "delete") {
        button.addEventListener("click", async () => {
          const selectedId = select.value;
          const option = select.options[select.selectedIndex];
          if (!selectedId || !option) {
            window.alert("Selecciona un diagnóstico para eliminar.");
            return;
          }
          if (!window.confirm(`¿Eliminar el diagnóstico "${option.text}"?`)) {
            return;
          }
          try {
            await deleteDiagnostico(apiListUrl, selectedId);
            option.remove();
            select.value = "";
          } catch (error) {
            window.alert(error.message);
          }
        });
      }
    });

    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      displayMessage("", false);
      const payload = {
        nombre: nombreInput.value.trim(),
        descripcion: descripcionInput.value.trim(),
        esta_activo: true,
      };
      if (!payload.nombre) {
        displayMessage("El nombre es obligatorio.", true);
        nombreInput.focus();
        return;
      }
      try {
        if (mode === "create") {
          const created = await createDiagnostico(apiListUrl, payload);
          appendOption(created);
          select.value = String(created.id);
        } else {
          const updated = await updateDiagnostico(apiListUrl, idInput.value, payload);
          updateOption(updated);
          select.value = String(updated.id);
        }
        closeModal();
      } catch (error) {
        displayMessage(error.message, true);
      }
    });

    function openModal(nextMode) {
      mode = nextMode;
      titleEl.textContent = nextMode === "create" ? "Agregar diagnóstico" : "Editar diagnóstico";
      modal.classList.add("is-open");
      modal.hidden = false;
      displayMessage("", false);
      window.setTimeout(() => nombreInput.focus(), 30);
    }

    function closeModal() {
      modal.classList.remove("is-open");
      modal.hidden = true;
      form.reset();
      mode = "create";
      displayMessage("", false);
    }

    function displayMessage(text, isError) {
      messageBox.textContent = text;
      messageBox.style.color = isError ? "#dc2626" : "#0f4c81";
    }

  function appendOption(item) {
      const option = new Option(item.nombre, item.id, true, true);
      select.add(option);
    }

    function updateOption(item) {
      const option = Array.from(select.options).find((opt) => opt.value === String(item.id));
      if (option) {
        option.text = item.nombre;
      } else {
        appendOption(item);
      }
    }
  }

  async function fetchDiagnosticoDetail(baseUrl, id) {
    const response = await fetch(buildDetailUrl(baseUrl, id), {
      headers: {
        Accept: "application/json",
      },
      credentials: "same-origin",
    });
    return handleResponse(response);
  }

  async function createDiagnostico(baseUrl, payload) {
    const response = await fetch(baseUrl, {
      method: "POST",
      headers: defaultHeaders(),
      body: JSON.stringify(payload),
      credentials: "same-origin",
    });
    return handleResponse(response);
  }

  async function updateDiagnostico(baseUrl, id, payload) {
    const response = await fetch(buildDetailUrl(baseUrl, id), {
      method: "PATCH",
      headers: defaultHeaders(),
      body: JSON.stringify(payload),
      credentials: "same-origin",
    });
    return handleResponse(response);
  }

  async function deleteDiagnostico(baseUrl, id) {
    const response = await fetch(buildDetailUrl(baseUrl, id), {
      method: "DELETE",
      headers: {
        "X-CSRFToken": getCsrfToken(),
      },
      credentials: "same-origin",
    });
    if (!response.ok) {
      const message = await parseError(response);
      throw new Error(message);
    }
  }

  async function handleResponse(response) {
    if (!response.ok) {
      const message = await parseError(response);
      throw new Error(message);
    }
    if (response.status === 204) {
      return null;
    }
    return response.json();
  }

  async function parseError(response) {
    const fallback = "Ocurrió un error al procesar la solicitud.";
    try {
      const data = await response.json();
      const normalised = normaliseError(data);
      return normalised || fallback;
    } catch (error) {
      return fallback;
    }
  }

  function normaliseError(data) {
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
        return String(data.detail);
      }
      const messages = [];
      for (const value of Object.values(data)) {
        if (Array.isArray(value)) {
          messages.push(value.join(" "));
        } else if (typeof value === "string") {
          messages.push(value);
        }
      }
      return messages.join(" ");
    }
    return "";
  }

  const normaliseSistema = (value) => {
    const trimmed = (value || "").trim();
    return trimmed.toUpperCase() === "FEDERAL TRANSFERIDO" ? "FEDERAL" : trimmed;
  };

  function initControlInternoForm() {
    const form = document.querySelector("[data-control-interno-form]");
    if (!form) {
      return;
    }
    const lookupUrl = form.dataset.lookupUrl || "";
    const apiBase = form.dataset.cctApi || "";
    const cctInput = form.querySelector("#id_cct_codigo");
    const hiddenCctInput = form.querySelector("#id_cct");
    const nombreInput = form.querySelector("#id_cct_nombre");
    const sostenimientoInput = form.querySelector("#id_sostenimiento_c_subcontrol");
    const servicioInput = form.querySelector("#id_tiponivelsub_c_servicion3");
    const asesorInput = form.querySelector("#id_asesor");
    const anioInput = form.querySelector("#id_anio");
    const oficioInput = form.querySelector("#id_numero_oficio_contestacion");
    const oficioButtons = form.querySelectorAll("[data-oficio-template]");
    const estatusInput = form.querySelector("#id_estatus");
    const estatusButtons = form.querySelectorAll("[data-estatus-value]");
    const datalist = document.getElementById("cct-options");
    const suggestionsContainer = form.querySelector("[data-cct-suggestions]");

    if (!cctInput || !hiddenCctInput || !nombreInput || !servicioInput || !datalist) {
      return;
    }

    const SUGGESTION_MIN_LENGTH = 3;
    const LOOKUP_MIN_LENGTH = 10;
    const SUGGESTION_DEBOUNCE = 200;
    let suggestionTimer = null;
    let suggestionAbortController = null;

    const resolveCurrentYear = () => {
      const raw = anioInput?.value?.trim?.() || "";
      if (/^\d{4}$/.test(raw)) {
        return raw;
      }
      return String(new Date().getFullYear());
    };

    const updateOficioYear = () => {
      if (!oficioInput) {
        return;
      }
      const value = oficioInput.value.trim();
      if (!value.includes("/")) {
        return;
      }
      const parts = value.split("/").map((part) => part.trim());
      if (parts.length < 4) {
        return;
      }
      const year = resolveCurrentYear();
      parts[parts.length - 1] = year;
      oficioInput.value = parts.join("/");
    };

    if (anioInput && oficioInput) {
      anioInput.addEventListener("change", updateOficioYear);
      anioInput.addEventListener("blur", updateOficioYear);
      anioInput.addEventListener("input", () => {
        if (/^\d{4}$/.test(anioInput.value.trim())) {
          updateOficioYear();
        }
      });
    }

    if (oficioInput && oficioButtons.length) {
      oficioButtons.forEach((button) => {
        button.addEventListener("click", () => {
          const rawTemplate = button.dataset.oficioTemplate || "";
          const prefix = rawTemplate.replace(/\/+$/, "");
          if (!prefix) {
            return;
          }
          const existing = oficioInput.value.trim();
          let folio = "";
          if (existing.includes("/")) {
            const segments = existing.split("/").map((part) => part.trim());
            if (segments.length >= 4) {
              folio = segments[3];
            }
          }
          if (!folio) {
            folio = "000";
          }
          const year = resolveCurrentYear();
          const nextValue = `${prefix}/${folio}/${year}`;
          oficioInput.value = nextValue;
          oficioInput.dispatchEvent(new Event("input", { bubbles: true }));
          oficioInput.focus();
          if (typeof oficioInput.setSelectionRange === "function") {
            const start = `${prefix}/`.length;
            const end = start + folio.length;
            window.setTimeout(() => {
              try {
                oficioInput.setSelectionRange(start, end);
              } catch (error) {
                // ignore selection errors in unsupported browsers
              }
            }, 0);
          }
        });
      });
    }

    if (oficioInput && oficioInput.value) {
      updateOficioYear();
    }

    if (estatusInput && estatusButtons.length) {
      estatusButtons.forEach((button) => {
        button.addEventListener("click", () => {
          const value = button.dataset.estatusValue || "";
          estatusInput.value = value;
          estatusInput.focus();
          estatusInput.dispatchEvent(new Event("input", { bubbles: true }));
        });
      });
    }

    const normalize = (value) => (value || "").trim().toUpperCase();

    const upsertOption = (item) => {
      if (!item || !item.cct) {
        return;
      }
      const code = normalize(item.cct);
      const sistema = normaliseSistema(item.sostenimiento);
      item.sostenimiento = sistema;
      const existing = Array.from(datalist.options).find(
        (opt) => normalize(opt.value || opt.text) === code
      );
      const label = `${code} · ${item.nombre || ""}`.trim();
      if (existing) {
        existing.value = code;
        existing.textContent = label;
        existing.dataset.nombre = item.nombre || "";
        existing.dataset.servicio = item.servicio || "";
        existing.dataset.asesor = item.asesor || "";
        existing.dataset.sostenimiento = sistema;
        existing.setAttribute("data-nombre", item.nombre || "");
        existing.setAttribute("data-servicio", item.servicio || "");
        existing.setAttribute("data-asesor", item.asesor || "");
        existing.setAttribute("data-sostenimiento", sistema);
      } else {
        const option = document.createElement("option");
        option.value = code;
        option.textContent = label;
        option.dataset.nombre = item.nombre || "";
        option.dataset.servicio = item.servicio || "";
        option.dataset.asesor = item.asesor || "";
        option.dataset.sostenimiento = sistema;
        option.setAttribute("data-nombre", item.nombre || "");
        option.setAttribute("data-servicio", item.servicio || "");
        option.setAttribute("data-asesor", item.asesor || "");
        option.setAttribute("data-sostenimiento", sistema);
        datalist.appendChild(option);
      }
    };

    const updateFromOption = (codigo) => {
      const option = Array.from(datalist.options).find(
        (opt) => normalize(opt.value || opt.text) === codigo
      );
      if (!option) {
        return false;
      }
      nombreInput.value =
        option.dataset?.nombre || option.getAttribute("data-nombre") || "";
      servicioInput.value =
        option.dataset?.servicio || option.getAttribute("data-servicio") || "";
      const sistemaDato =
        option.dataset?.sostenimiento || option.getAttribute("data-sostenimiento") || "";
      if (sostenimientoInput) {
        sostenimientoInput.value = normaliseSistema(sistemaDato);
      }
      if (asesorInput) {
        asesorInput.value =
          option.dataset?.asesor || option.getAttribute("data-asesor") || "";
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
        if (sostenimientoInput) {
          sostenimientoInput.value = item.sostenimiento;
        }
        servicioInput.value = item.servicio;
        if (asesorInput) {
          asesorInput.value = item.asesor;
        }
        hiddenCctInput.value = item.cct;
        return item;
      } catch (error) {
        console.warn(error);
        return null;
      }
    };

    const clearCctFields = () => {
      hiddenCctInput.value = "";
      nombreInput.value = "";
      if (sostenimientoInput) {
        sostenimientoInput.value = "";
      }
      servicioInput.value = "";
      if (asesorInput) {
        asesorInput.value = "";
      }
    };

    const applySuggestion = (item) => {
      if (!item) {
        return;
      }
      const code = normalize(item.cct);
      cctInput.value = code;
      hiddenCctInput.value = code;
      nombreInput.value = item.nombre || "";
      if (sostenimientoInput) {
        sostenimientoInput.value = item.sostenimiento || "";
      }
      servicioInput.value = item.servicio || "";
      if (asesorInput) {
        asesorInput.value = item.asesor || "";
      }
      upsertOption(item);
      hideSuggestions();
      void fetchAndUpdate(code);
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
        void fetchSuggestions(term);
      }, SUGGESTION_DEBOUNCE);
    };

    const handleChange = () => {
      const codigo = normalize(cctInput.value);
      cctInput.value = codigo;
      if (!codigo) {
        hideSuggestions();
        clearCctFields();
        return;
      }

      if (codigo.length >= SUGGESTION_MIN_LENGTH) {
        scheduleSuggestions(codigo);
      } else {
        hideSuggestions();
      }

      if (codigo.length < LOOKUP_MIN_LENGTH) {
        clearCctFields();
        return;
      }

      if (updateFromOption(codigo)) {
        hideSuggestions();
        return;
      }
      clearCctFields();
      void fetchAndUpdate(codigo).then((data) => {
        if (data) {
          hideSuggestions();
          upsertOption(data);
        } else {
          clearCctFields();
        }
      });
    };

    cctInput.addEventListener("input", handleChange);
    cctInput.addEventListener("change", handleChange);
    cctInput.addEventListener("blur", () => {
      window.setTimeout(() => hideSuggestions(), 150);
    });
    cctInput.addEventListener("focus", () => {
      const value = normalize(cctInput.value);
      if (value && value.length >= SUGGESTION_MIN_LENGTH) {
        scheduleSuggestions(value);
      }
    });

    if (normalize(cctInput.value)) {
      handleChange();
    }
    initCCTCrud({
      form,
      modalId: "cct-modal",
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
      canCreate: form.dataset.cctCanCreate === "true",
      canEdit: form.dataset.cctCanEdit === "true",
      canDelete: form.dataset.cctCanDelete === "true",
      lookupMinLength: LOOKUP_MIN_LENGTH,
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
    const actionButtons = document.querySelectorAll("[data-cct-action]");
    const cctForm = modal.querySelector("#cct-form");
    const messageBox = modal.querySelector("[data-modal-message]");
    const modalTitle = modal.querySelector("[data-modal-title]");
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
        closeModal();
      } catch (error) {
        displayMessage(error.message, true);
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

  function getCsrfToken() {
    const input = document.querySelector('input[name="csrfmiddlewaretoken"]');
    return input ? input.value : "";
  }
})();
