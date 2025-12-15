import test from "node:test";
import assert from "node:assert/strict";

import {
  parseISODate,
  calculateValidDays,
  evaluateLicensesRequirement,
  evaluateYearsRequirement,
} from "../../tramites/static/js/analizador_core.js";

test("evaluateYearsRequirement valida los 15 años de servicio y fechas inconsistentes", () => {
  const ingreso = parseISODate("2010-01-01");
  const analisisCumple = parseISODate("2025-01-02");
  const analisisInvalida = parseISODate("2009-12-31");

  const cumple = evaluateYearsRequirement(ingreso, analisisCumple, 15);
  assert.equal(cumple.valid, true);
  assert.equal(cumple.ready, true);
  assert.match(cumple.description, /Cumple/);

  const inconsistente = evaluateYearsRequirement(ingreso, analisisInvalida, 15);
  assert.equal(inconsistente.valid, false);
  assert.equal(inconsistente.badgeText, "Inconsistente");

  const faltante = evaluateYearsRequirement(ingreso, parseISODate("2024-12-31"), 15);
  assert.equal(faltante.valid, false);
  assert.match(faltante.description, /Faltan/);
});

test("calculateValidDays cuenta solo días posteriores a la fecha de ingreso", () => {
  const ingreso = parseISODate("2020-01-01");
  const start = parseISODate("2019-12-20");
  const end = parseISODate("2020-01-05");

  const result = calculateValidDays(start, end, ingreso);
  // Del 2 al 5 de enero son 4 días válidos (la fecha de ingreso no cuenta).
  assert.equal(result, 4);
});

test("evaluateLicensesRequirement suma días válidos y detecta faltantes", () => {
  const ingreso = parseISODate("2020-01-01");
  const licencias = [
    { start: "2020-01-10", end: "2020-01-15" }, // 6 días
    { start: "2019-12-28", end: "2020-01-03" }, // solo 2 días válidos (2 y 3 de enero; ingreso no cuenta)
  ];

  const requiredDays = 8;
  const result = evaluateLicensesRequirement(ingreso, licencias, requiredDays);

  assert.equal(result.validDays, 8);
  assert.equal(result.valid, true);
  assert.equal(result.badgeText, "Cumple");

  const faltante = evaluateLicensesRequirement(ingreso, licencias, 12);
  assert.equal(faltante.valid, false);
  assert.match(faltante.description, /Faltan/);
});
