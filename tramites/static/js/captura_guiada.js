(function () {
  "use strict";

  const normalizeText = (value) => {
    return String(value || "")
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .toLowerCase()
      .trim();
  };

  const parseJSON = (rawValue, fallback) => {
    if (rawValue === undefined || rawValue === null || rawValue === "") {
      return fallback;
    }
    if (typeof rawValue === "object") {
      return rawValue;
    }
    try {
      const parsed = JSON.parse(rawValue);
      return parsed && typeof parsed === "object" ? parsed : fallback;
    } catch (error) {
      return fallback;
    }
  };

  const uniq = (items) => {
    const seen = new Set();
    return items.filter((item) => {
      if (!item || seen.has(item)) {
        return false;
      }
      seen.add(item);
      return true;
    });
  };

  const findFieldInputs = (form, fieldName) => {
    if (!fieldName) {
      return [];
    }
    return Array.from(
      form.querySelectorAll(
        `[name="${fieldName}"], [name$="-${fieldName}"]`
      )
    );
  };

  const findFieldContainer = (fieldInput) => {
    if (!fieldInput) {
      return null;
    }
    return (
      fieldInput.closest(".form-field") ||
      fieldInput.parentElement
    );
  };

  const getSelectedOptionText = (select) => {
    if (!select) {
      return "";
    }
    const option = select.options[select.selectedIndex];
    return option ? option.textContent || "" : "";
  };

  const findStatusRule = (template, statusId, statusName) => {
    const rules = Array.isArray(template?.status_rules) ? template.status_rules : [];
    const normalizedStatus = normalizeText(statusName);
    const rawStatusId = String(statusId || "").trim();
    for (const rule of rules) {
      if (!rule || typeof rule !== "object") {
        continue;
      }
      const ids = Array.isArray(rule.match_estatus_ids)
        ? rule.match_estatus_ids.map((item) => String(item || "").trim()).filter(Boolean)
        : [];
      if (rawStatusId && ids.includes(rawStatusId)) {
        return rule;
      }
      const matchAny = Array.isArray(rule.match_any)
        ? rule.match_any.map((item) => normalizeText(item)).filter(Boolean)
        : [];
      if (normalizedStatus && matchAny.some((token) => normalizedStatus.includes(token))) {
        return rule;
      }
    }
    return null;
  };

  const buildEffectiveRule = (template, statusRule) => {
    const managedFields = Array.isArray(template?.managed_fields)
      ? template.managed_fields
      : [];
    const defaultVisible = Array.isArray(template?.default_visible_fields)
      ? template.default_visible_fields
      : managedFields;
    const defaultRequired = Array.isArray(template?.default_required_fields)
      ? template.default_required_fields
      : [];
    const visibleFields = statusRule && Array.isArray(statusRule.visible_fields) && statusRule.visible_fields.length
      ? statusRule.visible_fields
      : defaultVisible;
    const requiredFields = uniq(
      defaultRequired.concat(
        statusRule && Array.isArray(statusRule.required_fields)
          ? statusRule.required_fields
          : []
      )
    );
    return {
      managedFields: uniq(managedFields),
      visibleFields: uniq(visibleFields),
      requiredFields,
    };
  };

  const renderSummary = (summaryEl, templateName, statusName, rule) => {
    if (!summaryEl) {
      return;
    }
    const status = statusName || "Sin estatus";
    const templateLabel = templateName || "Plantilla estándar";
    const ruleLabel = rule?.id ? `Regla aplicada: ${rule.id}` : "Regla aplicada: estándar";
    summaryEl.innerHTML = `
      <strong>Plantilla activa:</strong> ${templateLabel}<br>
      <strong>Estatus:</strong> ${status}<br>
      <span class="captura-guiada__ok">${ruleLabel}</span>
    `;
  };

  const updateFieldVisibility = (form, effectiveRule) => {
    const managed = new Set(effectiveRule.managedFields);
    const visible = new Set(effectiveRule.visibleFields);
    const required = new Set(effectiveRule.requiredFields);

    managed.forEach((fieldName) => {
      const inputs = findFieldInputs(form, fieldName);
      inputs.forEach((input) => {
        if ((input.type || "").toLowerCase() === "hidden") {
          return;
        }
        const container = findFieldContainer(input);
        const keepVisible =
          String(input?.dataset?.capturaKeepVisible || "").trim().toLowerCase() === "true";
        if (container) {
          container.hidden = keepVisible ? false : !visible.has(fieldName);
        }
        if ("required" in input) {
          input.required = required.has(fieldName);
        }
      });
    });
  };

  const emptyChecklistTable = (rowsEl) => {
    if (!rowsEl) {
      return;
    }
    rowsEl.innerHTML = `
      <tr class="table__empty-row">
        <td colspan="4" class="table__empty">No hay documentos para esta etapa.</td>
      </tr>
    `;
  };

  const buildStageMap = (template) => {
    const stages = Array.isArray(template?.checklist_etapas) ? template.checklist_etapas : [];
    const stageMap = new Map();
    stages.forEach((stage) => {
      if (stage && typeof stage === "object" && stage.id) {
        stageMap.set(String(stage.id), stage);
      }
    });
    return stageMap;
  };

  const buildItemsMap = (state) => {
    const map = new Map();
    const items = Array.isArray(state?.items) ? state.items : [];
    items.forEach((item) => {
      if (!item || typeof item !== "object") {
        return;
      }
      const key = String(item.key || "").trim();
      if (!key) {
        return;
      }
      map.set(key, item);
    });
    return map;
  };

  const updateChecklistAlert = (alertEl, message) => {
    if (!alertEl) {
      return;
    }
    if (!message) {
      alertEl.hidden = true;
      alertEl.textContent = "";
      return;
    }
    alertEl.hidden = false;
    alertEl.innerHTML = `<p><strong>Validación documental:</strong> ${message}</p>`;
  };

  const serializeChecklistState = (checklistInput, modelInput, state) => {
    const serialized = JSON.stringify(state || {});
    if (checklistInput) {
      checklistInput.value = serialized;
    }
    if (modelInput) {
      modelInput.value = serialized;
    }
  };

  const initGuidedForm = (form) => {
    const configScriptId = form.dataset.capturaConfigScript;
    const configScript = configScriptId ? document.getElementById(configScriptId) : null;
    if (!configScript) {
      return;
    }
    const config = parseJSON(configScript.textContent, {});
    const tipoFieldId = form.dataset.capturaTipoField;
    const estatusFieldId = form.dataset.capturaEstatusField;
    const tipoSelect = tipoFieldId ? document.getElementById(tipoFieldId) : null;
    const estatusSelect = estatusFieldId ? document.getElementById(estatusFieldId) : null;
    if (!tipoSelect || !estatusSelect) {
      return;
    }
    const enforceChecklistCritical = String(
      form.dataset.capturaEnforceCritical || "true"
    ).toLowerCase() === "true";

    const checklistInput = document.getElementById(form.dataset.capturaChecklistInput || "");
    const modelInput = document.getElementById(form.dataset.capturaModelInput || "");
    const summaryEl = form.querySelector("[data-captura-summary]");
    const stageSelect = form.querySelector("[data-captura-stage]");
    const docsRows = form.querySelector("[data-captura-docs-rows]");
    const helpEl = form.querySelector("[data-captura-checklist-help]");
    const alertEl = form.querySelector("[data-captura-alert]");

    let checklistState = parseJSON(
      checklistInput?.value || modelInput?.value || "",
      parseJSON(config.checklist_documental, {})
    );
    if (!checklistState || typeof checklistState !== "object" || Array.isArray(checklistState)) {
      checklistState = {};
    }

    let currentTemplate = {};
    let currentStage = null;
    let missingCritical = [];

    const getTemplate = () => {
      const key = String(tipoSelect.value || "").trim();
      const byTipo = config.templates_by_tipo || {};
      return byTipo[key] || config.default_template || {};
    };

    const renderChecklist = (statusRule) => {
      const stageMap = buildStageMap(currentTemplate);
      const stages = Array.from(stageMap.values());
      if (!stageSelect || !docsRows) {
        serializeChecklistState(checklistInput, modelInput, checklistState);
        return;
      }
      if (!stages.length) {
        stageSelect.innerHTML = `<option value="">Sin etapa</option>`;
        stageSelect.disabled = true;
        emptyChecklistTable(docsRows);
        checklistState = {};
        missingCritical = [];
        if (helpEl) {
          helpEl.textContent = "Sin checklist configurado para este tipo.";
        }
        updateChecklistAlert(alertEl, "");
        serializeChecklistState(checklistInput, modelInput, checklistState);
        return;
      }
      stageSelect.disabled = false;
      stageSelect.innerHTML = stages
        .map(
          (stage) =>
            `<option value="${String(stage.id)}">${String(stage.nombre || stage.id)}</option>`
        )
        .join("");
      let stageId = String(checklistState.stage || "").trim();
      if (!stageId && statusRule && statusRule.checklist_stage) {
        stageId = String(statusRule.checklist_stage).trim();
      }
      if (!stageMap.has(stageId)) {
        stageId = String(stages[0].id);
      }
      stageSelect.value = stageId;
      checklistState.stage = stageId;
      currentStage = stageMap.get(stageId) || null;
      const docs = Array.isArray(currentStage?.documentos) ? currentStage.documentos : [];
      const itemMap = buildItemsMap(checklistState);
      if (!docs.length) {
        emptyChecklistTable(docsRows);
        checklistState.items = [];
        missingCritical = [];
        if (helpEl) {
          helpEl.textContent = currentStage?.descripcion || "No hay documentos para esta etapa.";
        }
        updateChecklistAlert(alertEl, "");
        serializeChecklistState(checklistInput, modelInput, checklistState);
        return;
      }
      const rows = [];
      const normalizedItems = [];
      missingCritical = [];
      docs.forEach((doc) => {
        const key = String(doc.key || "").trim();
        if (!key) {
          return;
        }
        const source = itemMap.get(key) || {};
        const checked = Boolean(source.checked);
        const note = String(source.note || "");
        const critical = Boolean(doc.critico);
        if (critical && !checked) {
          missingCritical.push(String(doc.nombre || key));
        }
        normalizedItems.push({
          key,
          nombre: String(doc.nombre || key),
          critico: critical,
          checked,
          note,
        });
        rows.push(`
          <tr>
            <td>
              <strong>${String(doc.nombre || key)}</strong>
              ${doc.descripcion ? `<div class="help-text">${String(doc.descripcion)}</div>` : ""}
            </td>
            <td>${critical ? `<span class="captura-guiada__critical">Crítico</span>` : "-"}</td>
            <td>
              <input type="checkbox" data-captura-doc-check data-doc-key="${key}" ${checked ? "checked" : ""}>
            </td>
            <td>
              <input type="text" class="form-input" data-captura-doc-note data-doc-key="${key}" value="${note.replace(/"/g, "&quot;")}" placeholder="Observación opcional">
            </td>
          </tr>
        `);
      });
      docsRows.innerHTML = rows.join("");
      checklistState.items = normalizedItems;
      const shouldBlock = currentStage?.bloquear_si_falta_critico !== false;
      if (helpEl) {
        helpEl.textContent = currentStage?.descripcion || "";
        if (missingCritical.length && shouldBlock) {
          helpEl.innerHTML += ` <span class="captura-guiada__warn">Faltan críticos: ${missingCritical.join(", ")}.</span>`;
        }
      }
      updateChecklistAlert(
        alertEl,
        missingCritical.length && shouldBlock
          ? `Faltan documentos críticos: ${missingCritical.join(", ")}.`
          : ""
      );
      serializeChecklistState(checklistInput, modelInput, checklistState);
    };

    const syncFromRows = () => {
      if (!docsRows) {
        return;
      }
      const checks = Array.from(docsRows.querySelectorAll("[data-captura-doc-check]"));
      const notes = Array.from(docsRows.querySelectorAll("[data-captura-doc-note]"));
      const notesMap = new Map();
      notes.forEach((noteInput) => {
        notesMap.set(noteInput.getAttribute("data-doc-key"), noteInput.value || "");
      });
      const currentDocs = Array.isArray(currentStage?.documentos) ? currentStage.documentos : [];
      const docMap = new Map(
        currentDocs.map((doc) => [String(doc.key || ""), doc])
      );
      const nextItems = [];
      missingCritical = [];
      checks.forEach((checkInput) => {
        const key = String(checkInput.getAttribute("data-doc-key") || "").trim();
        if (!key) {
          return;
        }
        const def = docMap.get(key) || {};
        const critical = Boolean(def.critico);
        const checked = Boolean(checkInput.checked);
        if (critical && !checked) {
          missingCritical.push(String(def.nombre || key));
        }
        nextItems.push({
          key,
          nombre: String(def.nombre || key),
          critico: critical,
          checked,
          note: String(notesMap.get(key) || "").trim(),
        });
      });
      checklistState.items = nextItems;
      const shouldBlock = currentStage?.bloquear_si_falta_critico !== false;
      updateChecklistAlert(
        alertEl,
        missingCritical.length && shouldBlock
          ? `Faltan documentos críticos: ${missingCritical.join(", ")}.`
          : ""
      );
      serializeChecklistState(checklistInput, modelInput, checklistState);
    };

    const updateFormBySelection = () => {
      currentTemplate = getTemplate();
      const statusName = getSelectedOptionText(estatusSelect);
      const statusRule = findStatusRule(currentTemplate, estatusSelect.value, statusName);
      const effectiveRule = buildEffectiveRule(currentTemplate, statusRule);
      updateFieldVisibility(form, effectiveRule);
      renderSummary(summaryEl, currentTemplate.template_name, statusName, statusRule);
      renderChecklist(statusRule);
      if (docsRows) {
        docsRows
          .querySelectorAll("[data-captura-doc-check], [data-captura-doc-note]")
          .forEach((input) => {
            input.addEventListener("change", syncFromRows);
            input.addEventListener("input", syncFromRows);
          });
      }
    };

    if (stageSelect) {
      stageSelect.addEventListener("change", () => {
        checklistState.stage = stageSelect.value || "";
        const statusName = getSelectedOptionText(estatusSelect);
        const statusRule = findStatusRule(currentTemplate, estatusSelect.value, statusName);
        renderChecklist(statusRule);
        if (docsRows) {
          docsRows
            .querySelectorAll("[data-captura-doc-check], [data-captura-doc-note]")
            .forEach((input) => {
              input.addEventListener("change", syncFromRows);
              input.addEventListener("input", syncFromRows);
            });
        }
      });
    }

    tipoSelect.addEventListener("change", updateFormBySelection);
    estatusSelect.addEventListener("change", updateFormBySelection);

    form.addEventListener("submit", (event) => {
      syncFromRows();
      const shouldBlock = currentStage?.bloquear_si_falta_critico !== false;
      if (enforceChecklistCritical && shouldBlock && missingCritical.length) {
        event.preventDefault();
        updateChecklistAlert(
          alertEl,
          `Faltan documentos críticos: ${missingCritical.join(", ")}.`
        );
        const firstMissing = docsRows?.querySelector("[data-captura-doc-check]:not(:checked)");
        if (firstMissing) {
          firstMissing.focus();
        }
      }
    });

    updateFormBySelection();
  };

  const init = () => {
    const forms = document.querySelectorAll("[data-captura-guiada-form]");
    if (!forms.length) {
      return;
    }
    forms.forEach((form) => {
      try {
        initGuidedForm(form);
      } catch (error) {
        // Mantiene el flujo principal del formulario incluso si falla la guía.
        console.error("captura_guiada init error", error);
      }
    });
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
