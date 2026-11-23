"""Versi tervektorisasi (numpy) dari quiz.src.scoring, khusus untuk simulasi massal.

Bukan sumber kebenaran: hasilnya diuji identik dengan implementasi referensi di
quiz/tests/test_simulation_engine.py. Mendukung soal single, multi, dan major (opsional),
tie-break field_order / strong_count / answer_rotation / random, serta aturan klaster.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

import numpy as np

from ..src.config import field_keys
from ..src.scoring import match_major, max_points


@dataclass
class Answers:
    singles: dict[str, np.ndarray]  # qid -> (N,) indeks opsi
    multi: dict[str, np.ndarray]  # qid -> (N, n_opsi) bool, termasuk opsi eksklusif
    major_entry: np.ndarray | None = None  # (N,) indeks entri major_mapping, -1 = kosong

    @property
    def n(self) -> int:
        any_single = next(iter(self.singles.values()))
        return len(any_single)


class Engine:
    def __init__(self, config: dict[str, Any]):
        self.config = config
        self.keys = field_keys(config)
        self.F = len(self.keys)
        idx = {k: i for i, k in enumerate(self.keys)}
        self.questions = []
        for position, q in enumerate(config["questions"], start=1):
            if q["type"] not in ("single", "multi"):
                continue
            W = np.zeros((len(q["options"]), self.F), dtype=np.int64)
            for o_i, opt in enumerate(q["options"]):
                for key, pts in opt["points"].items():
                    W[o_i, idx[key]] = pts
            exclusive = np.array([o["id"] in set(q.get("exclusive_option_ids", [])) for o in q["options"]])
            self.questions.append(
                {"id": q["id"], "type": q["type"], "position": position, "W": W,
                 "exclusive": exclusive, "cap": q.get("per_field_cap")}
            )
        major_q = next((q for q in config["questions"] if q["type"] == "major"), None)
        self.major_cap = major_q.get("per_field_cap") if major_q else None
        # Baris e = poin bila jurusan peserta adalah kata kunci pertama entri e. Teks itu bisa cocok
        # dengan lebih dari satu entri (misalnya "manajemen informatika"), jadi pakai match_major.
        self.major_W = np.zeros((len(config.get("major_mapping", [])), self.F), dtype=np.int64)
        for e_i, entry in enumerate(config.get("major_mapping", [])):
            for matched in match_major(config, entry["keywords"][0]):
                for key, pts in matched["points"].items():
                    self.major_W[e_i, idx[key]] = max(self.major_W[e_i, idx[key]], pts)
        if self.major_cap is not None:
            self.major_W = np.minimum(self.major_W, self.major_cap)
        self.M = np.array([max_points(config, False)[k] for k in self.keys], dtype=np.int64)
        self.M_major = np.array([max_points(config, True)[k] for k in self.keys], dtype=np.int64)
        cluster_of = {f: i + 1 for i, c in enumerate(config.get("clusters", [])) for f in c["fields"]}
        self.cluster_ids = np.array([cluster_of.get(k, 0) for k in self.keys])

    # ------------------------------------------------------------------ poin
    def points(self, ans: Answers) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        N = ans.n
        pts = np.zeros((N, self.F), dtype=np.int64)
        strong = np.zeros((N, self.F), dtype=np.int64)
        offset = np.zeros(N, dtype=np.int64)
        for q in self.questions:
            W = q["W"]
            if q["type"] == "single":
                a = ans.singles[q["id"]]
                contrib = W[a]
                pts += contrib
                strong += contrib >= 2
                offset += q["position"] * (a + 1)
            else:
                sel = ans.multi[q["id"]]
                raw = sel.astype(np.int64) @ W
                pts += raw if q["cap"] is None else np.minimum(raw, q["cap"])
                offset += q["position"] * (sel.astype(np.int64) @ (np.arange(W.shape[0]) + 1))
        has_major = np.zeros(N, dtype=bool)
        if ans.major_entry is not None:
            has_major = ans.major_entry >= 0
            pts[has_major] += self.major_W[ans.major_entry[has_major]]
        return pts, strong, (offset % self.F), has_major

    # --------------------------------------------------------------- ranking
    def rank(self, ans: Answers, tie_break: list[str] | None = None, rng: np.random.Generator | None = None,
             diversity: dict[str, Any] | None = None) -> dict[str, np.ndarray]:
        cfg_scoring = self.config["scoring"]
        tie_break = tie_break if tie_break is not None else cfg_scoring["tie_break"]
        diversity = diversity if diversity is not None else cfg_scoring["diversity"]
        pts, strong, offset, has_major = self.points(ans)
        N = pts.shape[0]
        if cfg_scoring["normalization"] == "max_achievable":
            M = np.where(has_major[:, None], self.M_major[None, :], self.M[None, :])
            L = math.lcm(*[int(x) for x in np.unique(np.concatenate([self.M, self.M_major])) if x > 0])
            scaled = pts * (L // np.maximum(M, 1))  # proporsional terhadap pts / M, eksak
            ref = M.max(axis=1)
            unit = L // ref  # nilai 'scaled' untuk 1 poin pada bidang dengan M = ref
        else:  # user_max: urutan sama dengan poin mentah
            scaled = pts.copy()
            unit = np.ones(N, dtype=np.int64)
        idx = np.arange(self.F)
        # Kunci gabungan: makin besar makin baik. Komponen disusun berjenjang agar setara tuple.
        comp = scaled.astype(np.int64)
        for rule in list(tie_break) + ["field_order"]:
            if rule == "strong_count":
                comp = comp * 16 + strong
            elif rule == "answer_rotation":
                comp = comp * self.F + (self.F - 1 - ((idx[None, :] - offset[:, None]) % self.F))
            elif rule == "random":
                rand_off = rng.integers(0, self.F, size=N)
                comp = comp * self.F + (self.F - 1 - ((idx[None, :] - rand_off[:, None]) % self.F))
            elif rule == "field_order":
                comp = comp * self.F + (self.F - 1 - idx[None, :])
        comp = np.where(pts > 0, comp, -1)
        order = np.argsort(-comp, axis=1, kind="stable")
        top_n = cfg_scoring["top_n"]
        if diversity["type"] == "none":
            top = order[:, :top_n].copy()
        else:
            top = self._diverse(order, scaled, unit, pts, diversity, top_n)
        top_valid = np.take_along_axis(pts, np.where(top >= 0, top, 0), axis=1) > 0
        top = np.where((top >= 0) & top_valid, top, -1)
        first = np.where(top[:, 0] >= 0, top[:, 0], 0)
        second = np.where(top[:, 1] >= 0, top[:, 1], 0)
        s1 = np.take_along_axis(scaled, first[:, None], axis=1)[:, 0]
        s2 = np.take_along_axis(scaled, second[:, None], axis=1)[:, 0]
        gap_points = np.where(top[:, 1] >= 0, (s1 - s2) / unit, np.inf)
        return {"top": top, "gap_points": gap_points, "scaled": scaled, "pts": pts}

    def _diverse(self, order, scaled, unit, pts, rule, top_n):
        limit, gap = rule["max"], rule["override_gap_points"]
        N = order.shape[0]
        out = -np.ones((N, top_n), dtype=np.int64)
        for r in range(N):
            remaining = [int(f) for f in order[r] if pts[r, f] > 0]
            selected: list[int] = []
            while remaining and len(selected) < top_n:
                cand = remaining.pop(0)
                cl = self.cluster_ids[cand]
                if cl != 0 and sum(self.cluster_ids[s] == cl for s in selected) >= limit:
                    alt = next((x for x in remaining
                                if self.cluster_ids[x] == 0
                                or sum(self.cluster_ids[s] == self.cluster_ids[x] for s in selected) < limit), None)
                    if alt is not None and (scaled[r, cand] - scaled[r, alt]) < gap * unit[r]:
                        continue
                selected.append(cand)
            out[r, : len(selected)] = selected
        return out


# ---------------------------------------------------------------------------
# Pembangkit jawaban sintetis
# ---------------------------------------------------------------------------


def uniform_answers(engine: Engine, n: int, rng: np.random.Generator, p_tool: float = 0.5) -> Answers:
    singles, multi = {}, {}
    for q in engine.questions:
        n_opt = q["W"].shape[0]
        if q["type"] == "single":
            singles[q["id"]] = rng.integers(0, n_opt, size=n)
        else:
            sel = (rng.random((n, n_opt)) < p_tool) & ~q["exclusive"][None, :]
            none = ~sel.any(axis=1)
            sel[:, q["exclusive"]] = none[:, None]
            multi[q["id"]] = sel
    return Answers(singles, multi)


def persona_answers(engine: Engine, target: int, n: int, rng: np.random.Generator, eps: float = 0.2,
                    tool_noise: float = 0.15, major_entry: int | None = None) -> Answers:
    """Persona sintetis: dengan peluang 1-eps memilih opsi berbobot tertinggi untuk bidang target
    (bila tidak ada opsi untuk target di soal itu, memilih acak), selain itu acak seragam.
    Q4: opsi yang memberi poin ke target dicentang dengan peluang 1-eps, opsi lain dengan peluang
    tool_noise."""
    singles, multi = {}, {}
    for q in engine.questions:
        W = q["W"]
        n_opt = W.shape[0]
        if q["type"] == "single":
            col = W[:, target]
            best = np.flatnonzero(col == col.max()) if col.max() > 0 else np.arange(n_opt)
            pick_best = best[rng.integers(0, len(best), size=n)]
            pick_rand = rng.integers(0, n_opt, size=n)
            singles[q["id"]] = np.where(rng.random(n) < 1 - eps, pick_best, pick_rand)
        else:
            relevant = (W[:, target] > 0) & ~q["exclusive"]
            p = np.where(relevant, 1 - eps, tool_noise)
            sel = (rng.random((n, n_opt)) < p[None, :]) & ~q["exclusive"][None, :]
            none = ~sel.any(axis=1)
            sel[:, q["exclusive"]] = none[:, None]
            multi[q["id"]] = sel
    major = None if major_entry is None else np.full(n, major_entry, dtype=np.int64)
    return Answers(singles, multi, major)


def answers_to_dicts(engine: Engine, ans: Answers, confidence: int = 3) -> list[dict[str, Any]]:
    """Ubah Answers menjadi daftar dict jawaban untuk implementasi referensi."""
    out = []
    for r in range(ans.n):
        row: dict[str, Any] = {}
        for q in engine.config["questions"]:
            qid = q["id"]
            if q["type"] == "single":
                row[qid] = q["options"][int(ans.singles[qid][r])]["id"]
            elif q["type"] == "multi":
                row[qid] = [o["id"] for o, s in zip(q["options"], ans.multi[qid][r]) if s]
            elif q["type"] == "scale":
                row[qid] = confidence
            elif q["type"] == "major":
                entry = None if ans.major_entry is None else int(ans.major_entry[r])
                row[qid] = None if entry is None or entry < 0 else engine.config["major_mapping"][entry]["keywords"][0]
        out.append(row)
    return out
