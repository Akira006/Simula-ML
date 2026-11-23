// Menjalankan client/src/lib/score.ts ASLI (bukan salinan) terhadap kasus dari Python.
// Node >= 23.6 bisa mengimpor .ts langsung (type stripping). Pemakaian:
//   node reviewer/tests/score_crosscheck.mjs <path ke client/src/lib/score.ts> <cases.json>
// Keluaran: JSON { points: [...], totals: [...] } ke stdout.
import { readFileSync } from 'node:fs';
import { pathToFileURL } from 'node:url';

const [scorePath, casesPath] = process.argv.slice(2);
const { getCriterionPoints, calculateTotalScore } = await import(pathToFileURL(scorePath).href);
const cases = JSON.parse(readFileSync(casesPath, 'utf8'));
const points = cases.points.map(({ level, weight }) => getCriterionPoints({ level, weight }));
const totals = cases.totals.map((criteria) => calculateTotalScore(criteria));
process.stdout.write(JSON.stringify({ node: process.version, points, totals }));
