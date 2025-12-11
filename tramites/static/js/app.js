(() => {
  "use strict";

  document.addEventListener("DOMContentLoaded", () => {
    initTabs();
    initCasoInternoForm();
    initFilterToggle();
    initTramiteCasoDetail();
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
    applyState(false);
    toggleBtn.addEventListener("click", () => {
      const hide = !panel.hidden;
      applyState(hide);
    });
  }

  const normaliseSistema = (value) => {
    const trimmed = (value || "").trim();
    return trimmed.toUpperCase() === "FEDERAL TRANSFERIDO" ? "FEDERAL" : trimmed;
  };

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

    // Inicializar CRUD de tipos de proceso
    initTipoProcesoCrud();
    
    // Inicializar CRUD de estatus de caso
    initEstatusCasoCrud();

    // Inicializar CRUD de prefijos de oficio y enlace con el campo
    initPrefijoOficioCrud();

    // Inicializar CRUD de tipos de violencia
    initTipoViolenciaCrud();

    // Inicializar CRUD de solicitante y destinatario
    initSolicitanteCrud();
    initDestinatarioCrud();

    // Inicializar gestor de receptores adicionales
    initReceptoresAdicionales();

    // Inicializar CRUD de estatus de trámite (para trámites del caso en detalle)
    initEstatusTramiteCrud();
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

    // Buscar los botones CRUD que apunten a este catálogo
    const openBtn = document.querySelector(`[data-crud-open="${catalogType}"][data-crud-target="${selectSelector.substring(1)}"]`);
    const editBtn = document.querySelector(`[data-crud-edit="${catalogType}"][data-crud-target="${selectSelector.substring(1)}"]`);
    const deleteBtn = document.querySelector(`[data-crud-delete="${catalogType}"][data-crud-target="${selectSelector.substring(1)}"]`);
    const closeBtns = modal.querySelectorAll("[data-modal-close]");
    const saveBtn = form.querySelector("button[type='submit']");
    const modalTitle = modal.querySelector("[data-modal-title]");
    const modalMessage = modal.querySelector("[data-modal-message]");
    const fieldset = form.querySelector("fieldset:first-of-type");

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
    };

    const createItem = async (data) => {
      try {
        const response = await fetch(apiEndpoint, {
          method: "POST",
          headers: defaultHeaders(),
          body: JSON.stringify(data),
        });

        if (!response.ok) {
          const errorData = await response.json();
          let errorMessage = `Error al crear ${fieldConfig.label || catalogType}.`;

          if (typeof errorData === "object") {
            const firstError = Object.values(errorData).flat()[0];
            if (firstError) {
              errorMessage = String(firstError);
            }
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
          const errorData = await response.json();
          let errorMessage = `Error al actualizar ${fieldConfig.label || catalogType}.`;

          if (typeof errorData === "object") {
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
          const errorData = await response.json();
          let errorMessage = `Error al eliminar ${fieldConfig.label || catalogType}.`;

          if (typeof errorData === "object") {
            const firstError = Object.values(errorData).flat()[0];
            if (firstError) {
              errorMessage = String(firstError);
            }
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
    const selectElement = document.querySelector("#id_estatus");
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
    } = config;
    const tableBody = document.querySelector(tableSelector);
    const hiddenInput = document.querySelector(hiddenSelector);
    const addBtn = document.querySelector(addBtnSelector);
    const modal = document.getElementById(modalId);
    const form = document.getElementById(formId);
    const modalMessage = modal ? modal.querySelector("[data-modal-message]") : null;
    const saveBtn = form ? form.querySelector("[data-receptor-adicional-save]") : null;
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

  function initTramiteCasoDetail() {
    const modal = document.getElementById("tramite-caso-modal");
    const openBtn = document.querySelector("[data-tramite-caso-modal-open]");
    const closeBtns = modal ? modal.querySelectorAll("[data-modal-close]") : [];
    const form = modal ? modal.querySelector("form") : null;
    const standaloneForm = document.querySelector("[data-tramite-caso-form]");
    if (!modal || !openBtn || !form) {
      if (standaloneForm) {
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
        initPrefijoOficioCrud();
      }
      return;
    }

    const receptorsManager = initReceptoresAdicionales({
      tableSelector: "[data-receptores-rows-modal]",
      hiddenSelector: "#id_receptores_adicionales_modal",
      addBtnSelector: "[data-receptor-adicional-modal-add]",
      modalId: "receptor-adicional-modal-tramite",
      formId: "receptor-adicional-form-tramite",
      nameSelector: "#receptor-adicional-nombre-tramite",
      initialsSelector: "#receptor-adicional-iniciales-tramite",
      sexoSelector: "#receptor-adicional-sexo-tramite",
    });

    const resetForm = () => {
      form.reset();
      if (receptorsManager) {
        receptorsManager.reset();
      }
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

    openBtn.addEventListener("click", () => {
      resetForm();
      modal.hidden = false;
      initTramiteCasoPrefijos();
      initCatalogCruds();
      const firstInput = modal.querySelector("input, select, textarea");
      firstInput?.focus();
    });
    closeBtns.forEach((btn) =>
      btn.addEventListener("click", () => {
        modal.hidden = true;
      })
    );
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

    debugLog("[initPrefijoOficioCrud] Contexto detectado:", {
      isDetailView,
      numeroInput: !!numeroInput,
      numeroInputId: numeroInput?.id,
    });

    // Buscar el select específicamente basado en el contexto
    let selectElement;
    if (isDetailView) {
      selectElement = document.querySelector("#prefijo-oficio-select-modal");
    } else {
      selectElement = document.querySelector("#prefijo-oficio-select");
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
