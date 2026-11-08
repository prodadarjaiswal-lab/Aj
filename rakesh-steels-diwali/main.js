// Rakesh Steels · Dhanteras & Diwali — Art Deco, 1080×1350, deterministic in t.
import * as D from './engine/deco.js';
import * as TY from './engine/type.js';
import { T, PAIRS, RANG, BURSTS, DUR, B, beat, OPEN } from './timeline.js';
import { kuber } from './kuber.js';
const { C, TAU, clamp, lerp, seg, ss, eio, eo, ei, back, mix, rgba, gline, airbrush, glow, sparkle, sunburst, toPath, arcPts, goldGrad, hash, mulberry } = D;

const W = 1080, H = 1350;
const cv = document.getElementById('c'); cv.width = W; cv.height = H;
let g = cv.getContext('2d');

// ---------- palette additions ----------
const SAF = '#ff9a2e', SAF_L = '#ffd27a', SAF_D = '#c2530f';           // the one colour: fire
const STEEL = '#8e7658', STEEL_L = '#f0d3a2', STEEL_D = '#1f1710';
const CLAY = '#8a3a1c', MARI = '#d88a1e', MARI_L = '#f2b640', MARI_D = '#8a4a0c';

// ---------- small helpers ----------
const nz = x => { const i = Math.floor(x), f = x - i, u = f * f * (3 - 2 * f); return lerp(hash(i), hash(i + 1), u) * 2 - 1; };
const pulse = (t, t0, d = .18) => (t < t0 ? 0 : Math.exp(-(t - t0) / d));
const ignite = (t, t0) => { if (t < t0) return 0; const a = t - t0; return clamp(a / .06) * (1 + .6 * Math.exp(-a / .09) * Math.sin(Math.min(a / .18, 1) * Math.PI)); };
function ell(cx, cy, rx, ry, a0 = 0, a1 = TAU) { const p = new Path2D(); p.ellipse(cx, cy, Math.max(.1, rx), Math.max(.1, ry), 0, a0, a1); return p; }
function catmull(P, n = 18) {
  const o = [];
  for (let i = 0; i < P.length - 1; i++) {
    const p0 = P[Math.max(0, i - 1)], p1 = P[i], p2 = P[i + 1], p3 = P[Math.min(P.length - 1, i + 2)];
    for (let k = 0; k < n; k++) {
      const s = k / n, s2 = s * s, s3 = s2 * s;
      o.push([.5 * (2 * p1[0] + (-p0[0] + p2[0]) * s + (2 * p0[0] - 5 * p1[0] + 4 * p2[0] - p3[0]) * s2 + (-p0[0] + 3 * p1[0] - 3 * p2[0] + p3[0]) * s3),
              .5 * (2 * p1[1] + (-p0[1] + p2[1]) * s + (2 * p0[1] - 5 * p1[1] + 4 * p2[1] - p3[1]) * s2 + (-p0[1] + 3 * p1[1] - 3 * p2[1] + p3[1]) * s3)]);
    }
  }
  o.push(P[P.length - 1]); return o;
}
function at(pts, f) { // point + direction at fraction f of the polyline length
  const L = D.polyLen(pts); let d = clamp(f) * L;
  for (let i = 1; i < pts.length; i++) {
    const s = Math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]);
    if (d <= s || i === pts.length - 1) { const k = s ? d / s : 0; return [lerp(pts[i - 1][0], pts[i][0], k), lerp(pts[i - 1][1], pts[i][1], k), Math.atan2(pts[i][1] - pts[i - 1][1], pts[i][0] - pts[i - 1][0])]; }
    d -= s;
  }
}
function fitText(text, size, font, maxW) { g.save(); g.font = `${size}px ${font}`; const w = g.measureText(text).width; g.restore(); return w > maxW ? size * maxW / w : size; }

// ---------- world layout (the final card = world at zoom 1) ----------
const DIYA = [540, 752];                     // bowl rim centre
const BAR_R = 50, BASE = 1078;
const BARS = [];
[5, 4, 3].forEach((n, row) => { for (let i = 0; i < n; i++) BARS.push([540 + (i - (n - 1) / 2) * BAR_R * 2.04, BASE - BAR_R - row * BAR_R * 1.76]); });
const CUT_Y = -720;                           // the bar the saw cuts (above the card, out of the final frame)
const SPARK_PATH = catmull([[540, CUT_Y + 62], [770, -470], [300, -170], [790, 140], [330, 420], [600, 600], [540, 712]], 22);
const ARCH_OUT = D.stepArchPts(540, 1092, 1000, 700, { steps: 3, crown: 'round' });
const ARCH_DIYAS = (() => { // 16 lamps on the outer arch, in pairs from the crown outward
  const o = []; for (let k = 0; k < 8; k++) { const f = .045 + k * .062; o.push([at(ARCH_OUT, .5 - f), at(ARCH_OUT, .5 + f)]); } return o;
})();

// ---------- camera ----------
function camAt(t) {
  if (t < T.lift) return { x: 540, y: CUT_Y + 40, z: lerp(1.22, 1.42, ss(t / T.lift)) };
  if (t < T.ign) {
    const u = eio(seg(t, 3.8, 8.25));
    return { x: 540, y: lerp(CUT_Y + 40, 620, u), z: lerp(1.42, 1.22, ss(seg(t, 3.8, 8.3))) };
  }
  if (t < T.arch) return { x: 540, y: 620, z: lerp(1.22, 1.3, eo(seg(t, T.ign, T.arch))) };
  const u = eio(seg(t, T.arch, 12.8));
  return { x: 540, y: lerp(620, 675, u), z: lerp(1.3, 1, u) };
}
function applyCam(c, shake = 0, t = 0) {
  g.translate(W / 2 + shake * nz(t * 31), H / 2 + shake * nz(t * 29 + 7));
  g.scale(c.z, c.z); g.translate(-c.x, -c.y);
}

// ---------- props ----------
function steelLvl(t) { return t < T.ign ? lerp(.38, .55, ss(seg(t, 6.5, 8.4))) : lerp(.55, 1, ss(seg(t, T.ign, T.ign + .9))); }
function barFace(x, y, r, lvl, sh) {
  const base = mix(STEEL, '#000000', .6 * (1 - lvl)), L = mix(STEEL_L, '#000000', .55 * (1 - lvl));
  airbrush(g, ell(x, y, r, r), { base, light: L, dark: STEEL_D, radial: [x - r * .35, y - r * .4, r * 1.35], bbox: [x - r, y - r, x + r, y + r] });
  g.save(); g.globalAlpha = .22 + .15 * lvl; g.strokeStyle = mix(STEEL_D, '#000000', .2); g.lineWidth = 1;
  for (let k = 1; k <= 5; k++) { g.beginPath(); g.arc(x, y, r * k / 6.2, 0, TAU); g.stroke(); }
  g.restore();
  if (sh > -1) { // light sweep across the face
    g.save(); g.clip(ell(x, y, r, r)); const sx = lerp(x - r * 2, x + r * 2, sh);
    const gr = g.createLinearGradient(sx - r * .5, y - r, sx + r * .5, y + r); gr.addColorStop(0, 'rgba(255,240,200,0)'); gr.addColorStop(.5, 'rgba(255,240,200,.55)'); gr.addColorStop(1, 'rgba(255,240,200,0)');
    g.fillStyle = gr; g.fillRect(x - r, y - r, r * 2, r * 2); g.restore();
  }
  gline(g, ell(x, y, r, r), { w: 2.2, bb: [x - r, y - r, x + r, y + r], sheen: .25 + .1 * hash(x) });
  g.fillStyle = rgba(C.gold2, .5 * lvl); g.beginPath(); g.arc(x, y, 2.2, 0, TAU); g.fill();
}
function stack(x, yb, w, n, lvl, { hole = 0, h = 24, gap = 5, seed = 1 } = {}) {
  const ry = w * .2;
  for (let i = 0; i < n; i++) {
    const ww = w * (1 - .04 * hash(seed * 13 + i)), y = yb - i * (h + gap);
    const base = mix(STEEL, '#000000', .6 * (1 - lvl)), L = mix(STEEL_L, '#000000', .55 * (1 - lvl));
    const side = new Path2D(); side.moveTo(x - ww, y - h); side.lineTo(x - ww, y); side.ellipse(x, y, ww, ry, 0, Math.PI, 0, true); side.lineTo(x + ww, y - h); side.closePath();
    const gr = g.createLinearGradient(x - ww, 0, x + ww, 0); gr.addColorStop(0, STEEL_D); gr.addColorStop(.3, L); gr.addColorStop(.55, base); gr.addColorStop(1, STEEL_D);
    g.fillStyle = gr; g.fill(side);
    gline(g, arcPts(x, y, ww, 0, Math.PI, 30, ry), { w: 1.4, sheen: .3 });
    airbrush(g, ell(x, y - h, ww, ry), { base, light: L, dark: mix(base, '#000000', .5), radial: [x - ww * .3, y - h - ry * .4, ww * 1.2], bbox: [x - ww, y - h - ry, x + ww, y - h + ry] });
    if (hole) { airbrush(g, ell(x, y - h, ww * hole, ry * hole), { base: '#0b0806', light: '#2a2016', dark: '#000000', dir: 1.2 }); gline(g, ell(x, y - h, ww * hole, ry * hole), { w: 1.2 }); }
    gline(g, ell(x, y - h, ww, ry), { w: 1.8, bb: [x - ww, y - h - ry, x + ww, y - h + ry] });
  }
}
function marigold(x, y, r, lvl = 1, rot = 0) {
  const ring = (n, rr, pr, c1, c2, off) => {
    for (let i = 0; i < n; i++) { const a = rot + off + i * TAU / n, px = x + Math.cos(a) * rr, py = y + Math.sin(a) * rr;
      airbrush(g, ell(px, py, pr, pr), { base: mix(c1, '#000000', .55 * (1 - lvl)), light: c2, dark: MARI_D, radial: [px - pr * .3, py - pr * .3, pr * 1.3], bbox: [px - pr, py - pr, px + pr, py + pr] }); }
  };
  ring(14, r * .7, r * .32, MARI, MARI_L, 0);
  ring(10, r * .42, r * .3, mix(MARI, MARI_L, .4), '#ffd877', .3);
  airbrush(g, ell(x, y, r * .28, r * .28), { base: MARI_D, light: MARI, dark: '#4a2406', radial: [x, y, r * .3] });
  gline(g, ell(x, y, r * 1.0, r * 1.0), { w: 1, alpha: .55 * lvl });
}
function diyaBowl(x, y, s, lvl = 1) {
  const rx = 74 * s, ry = 15 * s, dh = 50 * s;
  const body = new Path2D(); body.moveTo(x - rx, y); body.bezierCurveTo(x - rx, y + dh * .9, x - rx * .4, y + dh, x, y + dh); body.bezierCurveTo(x + rx * .4, y + dh, x + rx, y + dh * .9, x + rx, y); body.closePath();
  // stepped foot
  const fw = rx * .42, fh = 9 * s; const foot = D.rectPts(x - fw, y + dh - 2 * s, fw * 2, fh); const foot2 = D.rectPts(x - fw * 1.3, y + dh + fh - 2 * s, fw * 2.6, fh * .8);
  for (const f of [foot2, foot]) { airbrush(g, f, { base: mix(CLAY, '#000000', .5 * (1 - lvl)), light: '#c4643a', dark: '#2a0e05', dir: -2.5 }); gline(g, f, { w: 1.2, closed: true }); }
  airbrush(g, body, { base: mix(CLAY, '#000000', .5 * (1 - lvl)), light: mix('#d27a48', '#000000', .4 * (1 - lvl)), dark: '#240b04', dir: -2.2, bbox: [x - rx, y - ry, x + rx, y + dh] });
  // engraved petals on the bowl
  g.save(); g.clip(body);
  for (let i = -2; i <= 2; i++) { const px = x + i * rx * .36, py = y + dh * .62; D.fan(g, px, py, 17 * s, { a0: Math.PI, a1: TAU, ribs: 4, fill: mix(C.gold1, '#000000', .5 * (1 - lvl)), ring: .3 }); }
  g.restore();
  gline(g, arcPts(x, y, rx, 0, Math.PI, 40, dh * 1.0), { w: 2.2 * s, sheen: .3 });
  airbrush(g, ell(x, y, rx, ry), { base: '#3a1f0c', light: '#7a4a1c', dark: '#120803', dir: 1.6 });     // oil
  gline(g, ell(x, y, rx, ry), { w: 2.4 * s, bb: [x - rx, y - ry, x + rx, y + ry] });
  // wick
  g.strokeStyle = '#2a1a0c'; g.lineWidth = 3 * s; g.beginPath(); g.moveTo(x, y + 2 * s); g.quadraticCurveTo(x + 2 * s, y - 6 * s, x, y - 11 * s); g.stroke();
}
function flame(x, y, s, t, k) { // k = ignition 0..1.6 (overshoot)
  if (k <= 0) return;
  const fl = 1 + .07 * nz(t * 9 + x * .01) + .04 * Math.sin(t * 23.7 + x), sway = 4 * s * nz(t * 3.1 + x * .03);
  const h = 82 * s * k * fl, w = 21 * s * Math.min(1.2, k);
  glow(g, x, y - h * .45, 260 * s * Math.min(1.3, k), '#ff9e3a', .38 * Math.min(1, k));
  glow(g, x, y - h * .4, 90 * s * Math.min(1.3, k), '#ffd27a', .55 * Math.min(1, k));
  const p = new Path2D(); p.moveTo(x, y); p.bezierCurveTo(x - w * 1.25, y - h * .25, x - w * .55, y - h * .7, x + sway, y - h);
  p.bezierCurveTo(x + w * .55, y - h * .7, x + w * 1.25, y - h * .25, x, y); p.closePath();
  const gr = g.createRadialGradient(x, y - h * .22, 0, x, y - h * .35, h * .8);
  gr.addColorStop(0, '#fffaf0'); gr.addColorStop(.25, '#ffe9a8'); gr.addColorStop(.55, SAF); gr.addColorStop(1, rgba(SAF_D, .2));
  g.fillStyle = gr; g.fill(p);
  g.fillStyle = 'rgba(60,90,200,.35)'; g.beginPath(); g.ellipse(x, y - h * .06, w * .35, h * .07, 0, 0, TAU); g.fill();
}
function smallDiya(x, y, s, t, tl) {
  diyaBowl(x, y, s, .85);
  const k = ignite(t, tl);
  if (k > 0) { flame(x, y - 10 * s, s * 1.15, t, k); if (t - tl < .5) sparkle(g, x, y - 60 * s, 34 * s * pulse(t, tl, .14) * 1.5, { color: '#fff1c4' }); }
}
function blade(x, y, R, rot, lvl) {
  const teeth = 48, p = new Path2D();
  for (let i = 0; i < teeth; i++) { const a = rot + i * TAU / teeth, b = a + TAU / teeth * .62, c2 = a + TAU / teeth;
    i ? p.lineTo(x + Math.cos(a) * R * .94, y + Math.sin(a) * R * .94) : p.moveTo(x + Math.cos(a) * R * .94, y + Math.sin(a) * R * .94);
    p.lineTo(x + Math.cos(b) * R, y + Math.sin(b) * R); p.lineTo(x + Math.cos(c2) * R * .94, y + Math.sin(c2) * R * .94); }
  p.closePath();
  airbrush(g, p, { base: '#6e6050', light: '#c9b48e', dark: '#120e0a', radial: [x - R * .3, y - R * .3, R * 1.3], bbox: [x - R, y - R, x + R, y + R] });
  gline(g, p, { w: 1.6, bb: [x - R, y - R, x + R, y + R] });
  sunburst(g, x, y, { rays: 24, r0: R * .2, r1: R * .78, rot, mode: 'lines', w: 2.4, alpha: .55 });  // deco spokes, spinning
  for (const rr of [.8, .22]) gline(g, ell(x, y, R * rr, R * rr), { w: 2, bb: [x - R, y - R, x + R, y + R] });
  airbrush(g, ell(x, y, R * .2, R * .2), { base: '#3a3128', light: '#bfae8c', dark: '#000000', radial: [x - 8, y - 8, R * .25] });
  D.fan(g, x, y, R * .16, { a0: 0, a1: TAU, ribs: 8, fill: C.gold1, rot: rot * .2 });
}
function sparkSpray(t, x, y, amt, seed = 7) { // symmetric fans of streaks below the cut
  if (amt <= 0) return;
  const R = mulberry(seed); g.save(); g.globalCompositeOperation = 'lighter';
  for (let i = 0; i < 280; i++) {
    const per = .35 + R() * .45, ph = R(), side = i % 2 ? 1 : -1, ang = lerp(.12, 1.05, R()), sp = lerp(650, 1350, R());
    const age = ((t + ph * per) % per), born = t - age; if (born < T.bite || born > T.cutEnd) continue;
    const vx = side * Math.cos(ang) * sp, vy = Math.sin(ang) * sp * .55 - 120;
    const px = x + vx * age, py = y + vy * age + 900 * age * age, L = .03 + .02 * R();
    const qx = px - vx * L, qy = py - (vy + 1800 * age) * L, a = (1 - age / per) * amt;
    const gr = g.createLinearGradient(px, py, qx, qy); gr.addColorStop(0, rgba('#fff4d0', a)); gr.addColorStop(.35, rgba(SAF_L, a * .9)); gr.addColorStop(1, rgba(SAF, 0));
    g.strokeStyle = gr; g.lineWidth = 3 + R() * 2.4; g.lineCap = 'round'; g.beginPath(); g.moveTo(px, py); g.lineTo(qx, qy); g.stroke();
  }
  g.restore();
}
function fizz(t, x, y, n, rad, seed, a = 1) {
  const R = mulberry(seed); g.save(); g.globalCompositeOperation = 'lighter';
  for (let i = 0; i < n; i++) { const per = .4 + R() * .5, ph = R(), ang = R() * TAU, age = ((t + ph * per) % per) / per, rr = rad * age * (.4 + R());
    const px = x + Math.cos(ang) * rr, py = y + Math.sin(ang) * rr + 40 * age * age;
    g.fillStyle = rgba(i % 3 ? SAF_L : '#fff4d0', (1 - age) * a); g.beginPath(); g.arc(px, py, 1.6 + 1.6 * (1 - age), 0, TAU); g.fill(); }
  g.restore();
}

// ---------- scene A: the steel world (shots 1–4, and the card) ----------
function background(t, warm) {
  D.ground(g, W, H, { top: '#120d08', bot: C.ink, vig: 0 });
  if (warm > 0) glow(g, W / 2, H * .56, H * .75, '#ff8a2a', .16 * warm);
}
function worldA(t, cam, opt = {}) {
  const lvl = steelLvl(t), lit = ss(seg(t, T.ign, T.ign + .8));
  // faint deco rays from the diya (the world's backdrop), grow after ignition
  sunburst(g, DIYA[0], DIYA[1] - 40, { rays: 64, r0: 120, r1: 1700, mode: 'both', w: 1.3, alpha: .14 + .3 * lit, colorA: rgba('#c9a24b', .05 + .05 * lit), sheen: .4 });
  // ---- the cutting station ----
  if (cam.y - H / 2 / cam.z < CUT_Y + 400) {
    const by = CUT_Y, br = 60;
    const cyl = D.rectPts(-200, by - br, 1480, br * 2);
    const gr = g.createLinearGradient(0, by - br, 0, by + br); gr.addColorStop(0, STEEL_D); gr.addColorStop(.28, STEEL_L); gr.addColorStop(.5, STEEL); gr.addColorStop(1, '#0d0a07');
    g.fillStyle = gr; g.fill(toPath(cyl, true));
    for (const yy of [by - br, by + br]) gline(g, [[-200, yy], [1280, yy]], { w: 2, sheen: .3 });
    // vise blocks (stepped)
    for (const sx of [-1, 1]) { const vx = 540 + sx * 330; const pts = D.stepArchPts(vx, by + br + 70, 120, 230, { steps: 2, crown: 'flat' });
      airbrush(g, pts, { base: '#3a3027', light: '#9b8a70', dark: '#0a0806', dir: -2.4, rim: 2 }); gline(g, pts, { w: 2, closed: true }); }
    // the cut
    const cutD = clamp(seg(t, T.bite, T.cutEnd)) * br * 2;
    if (t > T.bite) { g.fillStyle = '#050302'; g.fillRect(540 - 5, by - br, 10, cutD); glow(g, 540, by - br + cutD, 90, '#ffb04a', .7 * (t < T.cutEnd ? 1 : Math.exp(-(t - T.cutEnd) / .4))); }
    // blade: comes down, cuts, lifts
    const R = 290, yTouch = by - br - R + 4;
    let yb = t < T.bite ? lerp(yTouch - 420, yTouch, eo(seg(t, 0, T.bite))) : t < T.cutEnd ? yTouch + cutD : lerp(yTouch + br * 2, yTouch - 700, ei(seg(t, T.cutEnd, T.lift + .5)));
    if (yb > CUT_Y - 1200) { blade(540, yb, R, -t * 14, 1); if (t > T.bite - .05 && t < T.cutEnd + .1) speedLines(540, yb, t); }
    if (t > T.bite && t < T.cutEnd) { glow(g, 540, by - br + cutD, 260, SAF, .45); sunburst(g, 540, by - br + cutD, { rays: 40, r0: 30, r1: 520, a0: .1, a1: Math.PI - .1, mode: 'lines', w: 2.4, alpha: .35 + .2 * Math.sin(t * 37) }); }
    sparkSpray(t, 540, by - br + cutD, (t < T.cutEnd ? 1 : 0) * (.75 + .25 * Math.sin(t * 40)));
  }
  // ---- the spark's engraved path ----
  const sp = sparkAt(t);
  if (t > T.lift - .1) {
    const fade = 1 - ss(seg(t, 10.2, 11.2));
    if (fade > 0 && sp.f > 0) gline(g, SPARK_PATH, { w: 2.4, part: sp.f, glow: .7, alpha: fade, sheen: .5 });
  }
  // ---- props ----
  const RINGS_L = [[226, 1010], [854, 1010]], DISCS = [[150, 1066], [930, 1066]];
  for (const [x, y] of RINGS_L) stack(x, y, 44, 6, lvl, { hole: .55, seed: x });
  for (const [x, y] of DISCS) stack(x, y, 64, 5, lvl, { seed: x + 1, h: 28 });
  for (const [x, y] of BARS) barFace(x, y, BAR_R, lvl, t > T.ign ? lerp(-.2, 1.3, seg(t, T.ign + .15 + (x - 300) / 2400, T.ign + .95 + (x - 300) / 2400)) : -2);
  for (const [x, y, r] of [[250, 1092, 34], [330, 1100, 26], [750, 1100, 26], [830, 1092, 34], [96, 1104, 30], [984, 1104, 30]]) marigold(x, y, r, lvl, hash(x) * 3);
  // floor line
  gline(g, [[-300, 1112], [1380, 1112]], { w: 2, sheen: .4, alpha: .8 });
  D.rules(g, 120, 1124, 960, 1124, 2, 7, 1.1, { alpha: .6 });
  // ---- diya ----
  diyaBowl(DIYA[0], DIYA[1], 1, lerp(.7, 1, lit));
  const k = ignite(t, T.ign);
  flame(DIYA[0], DIYA[1] - 10, 1.18, t, k);
  if (k > 0 && t < T.ign + .6) { sparkle(g, DIYA[0], DIYA[1] - 70, 120 * pulse(t, T.ign, .16), { color: '#fff4d0' }); D.sunburst(g, DIYA[0], DIYA[1] - 60, { rays: 32, r0: 60, r1: 60 + 520 * eo(seg(t, T.ign, T.ign + .5)), mode: 'lines', w: 2, alpha: 1 - seg(t, T.ign + .2, T.ign + .6) }); }
  // ---- spark ----
  if (t > T.lift - .2 && t < T.ign + .05) {
    const hov = t < T.sp0 ? 1 - .3 * Math.sin(t * 30) : 1;
    glow(g, sp.x, sp.y, 120, SAF, .55);
    fizz(t, sp.x, sp.y, 18, 46, 5);
    if (t > T.sp0 && t < T.sp1) D.speedLines(g, sp.x, sp.y, sp.a + Math.PI, { n: 4, len: 140, spread: 24, w: 4, color: SAF_L, seed: 2 });
    D.drawShape(g, D.starPts(sp.x, sp.y, 26 * hov, .22, t * 3), { color: SAF, lw: 1.4 });
    sparkle(g, sp.x, sp.y, 30 * hov, { rot: t * 2, color: '#fff4d0' });
  }
  // ---- the arch and its lamps ----
  if (t > T.arch || opt.archFull) {
    const part = opt.archFull ? 1 : eio(seg(t, T.arch, T.arch + 1.1));
    D.archFrame(g, 540, 1092, 1000, 700, { rings: 2, gap: 16, steps: 3, part, burst: false, lw: 2.4, sheen: .45 });
    ARCH_DIYAS.forEach((pr, k2) => pr.forEach(([x, y]) => { if (part > .98 || opt.archFull) smallDiya(x, y - 6, .34, t, opt.archFull ? -10 : PAIRS[k2]); }));
  }
  const kp = opt.archFull ? 1 : seg(t, T.kuber, T.kuber + 1.6);
  if (kp > 0) {
    kuber(g, 540, 650, .82, kp, t);
    for (const sx of [-1, 1]) { const px = 540 + sx * 150, py = 676; gline(g, D.stepArchPts(px, py + 40, 64, 40, { steps: 2, crown: 'flat' }), { w: 1.6, alpha: ss(kp) }); smallDiya(px, py, .46, t, opt.archFull ? -10 : T.kuber + 1.4 + (sx > 0 ? .08 : 0)); }
  }
  if (opt.coins) coins(t);
}
function coins(t) { // a shower of gold coins from Kuber ji's pot onto the steel
  for (let i = 0; i < 12; i++) {
    const t0 = T.coins + i * .11, a = t - t0; if (a < 0) continue;
    const x0 = 540 + 66, y0 = 640 - 75, vx = (i % 2 ? 1 : -1) * (40 + 30 * hash(i)) + 30, land = 770 + 30 * hash(i + 9);
    let x = x0 + vx * Math.min(a, .7), y = y0 - 120 * a + 520 * a * a; if (y > land) y = land;
    const spin = Math.abs(Math.cos(a * 14 + i)), fade = 1 - ss(seg(a, 1.4, 2.4)); if (fade <= 0) continue;
    g.save(); g.globalAlpha = fade; g.fillStyle = goldGrad(g, x - 9, y - 9, x + 9, y + 9, { sheen: .6 }); g.beginPath(); g.ellipse(x, y, 9 * Math.max(.15, spin), 9, 0, 0, TAU); g.fill();
    g.strokeStyle = C.gold0; g.lineWidth = 1; g.stroke(); g.restore();
    if (y >= land && a < 1.6) sparkle(g, x, y - 6, 10 * pulse(a, (land - y0) / 400, .1), { glow: 0 });
  }
}
function speedLines(x, y, t) { // blur ring around the spinning blade
  g.save(); g.globalAlpha = .25; g.strokeStyle = C.gold2; g.lineWidth = 2;
  for (let i = 0; i < 6; i++) { const a = -t * 14 + i * TAU / 6; g.beginPath(); g.arc(x, y, 300, a, a + .5); g.stroke(); }
  g.restore();
}
function sparkAt(t) {
  if (t < T.sp0) return { x: SPARK_PATH[0][0], y: SPARK_PATH[0][1] - 6 * Math.sin(t * 6), a: Math.PI / 2, f: 0 };
  const f = eio(seg(t, T.sp0, T.sp1)), p = at(SPARK_PATH, f);
  if (t > T.sp1) { const h = seg(t, T.sp1, T.ign); return { x: 540, y: lerp(712, 735, ei(h)) - 6 * Math.sin(t * 20) * (1 - h), a: Math.PI / 2, f: 1 }; }
  return { x: p[0], y: p[1], a: p[2], f };
}

// ---------- the text band ----------
function devText(text, x, y, size, font, a = 1, sheen = .4) { if (a <= 0) return; TY.goldText(g, text, x, y, { size, font, track: 0, sheen, alpha: a }); }
function riseIn(t, t0, d = .7) { return ss(seg(t, t0, t0 + d)); }
const TXT = {
  title: 'शुभ दीपावली',
  greet: 'दीपावली की हार्दिक शुभकामनाएँ',
  sh1: 'शुभं करोति कल्याणम् आरोग्यं धनसम्पदा ।',
  sh2: 'दीपज्योतिर्नमोऽस्तुते ॥',
  b1: 'दीपों की रोशनी आपके जीवन में',
  b2: 'सुख, समृद्धि और नई उम्मीदों का उजाला भर दे ।',
  card: 'दीपावली की हार्दिक शुभकामनाएँ',
  en: 'HAPPY DIWALI',
  brand: 'RAKESH STEELS',
  contact: 'Howrah  •  8013626232',
};
function textBack(y0, y1, a) { // a soft lacquer band so text never sits on busy lines
  const gr = g.createLinearGradient(0, y0, 0, y1); gr.addColorStop(0, 'rgba(8,6,4,0)'); gr.addColorStop(.2, `rgba(8,6,4,${.78 * a})`); gr.addColorStop(.8, `rgba(8,6,4,${.78 * a})`); gr.addColorStop(1, 'rgba(8,6,4,0)');
  g.fillStyle = gr; g.fillRect(0, y0, W, y1 - y0);
}
function lotus(cx, cy, s, part, sheen = .4) { // deco lotus: three stacked fans + pointed petals, drawn on
  const pet = (a, L, w2) => { const ux = Math.cos(a), uy = Math.sin(a), nx = -uy, ny = ux; return [[cx, cy], [cx + ux * L * .5 + nx * w2, cy + uy * L * .5 + ny * w2], [cx + ux * L, cy + uy * L], [cx + ux * L * .5 - nx * w2, cy + uy * L * .5 - ny * w2], [cx, cy]]; };
  const P = [[-Math.PI / 2, 46, 14], [-Math.PI / 2 - .55, 40, 12], [-Math.PI / 2 + .55, 40, 12], [-Math.PI / 2 - 1.1, 32, 10], [-Math.PI / 2 + 1.1, 32, 10]];
  P.forEach(([a, L, w2], i) => { const q = seg(part, i * .08, .6 + i * .08); if (q > 0) gline(g, pet(a, L * s, w2 * s), { w: 2.2, part: q, glow: .4, sheen }); });
  if (part > .5) gline(g, [[cx - 40 * s, cy + 2], [cx + 40 * s, cy + 2]], { w: 2, part: seg(part, .5, 1) });
}
function topRules(y, part, half = 320, gap = 140) {
  if (part <= 0) return;
  for (const sgn of [-1, 1]) gline(g, [[540 + sgn * gap / 2, y], [540 + sgn * (gap / 2 + half * part), y]], { w: 1.8, sheen: .5 });
}
function diamond(x, y, s, a = 1) { sparkle(g, x, y, s, { alpha: a, glow: 0, color: C.gold2 }); }

// ---------- scene B: overhead rangoli ----------
const RC = [540, 800];
function rangoli(t) {
  D.ground(g, W, H, { top: '#0f0b07', bot: '#070504', vig: .5 });
  const lockK = pulse(t, T.lock, .22);
  const rot = lerp(.9, 0, eio(seg(t, T.open - .2, T.lock)));       // the pattern turns, and stops on the lock
  const z = lerp(.9, 1.0, ss(seg(t, T.open, T.lock))) * (1 + .025 * lockK);
  g.save(); g.translate(RC[0], RC[1]); g.scale(z, z);
  // floor medallion
  for (const r of [470, 452]) gline(g, ell(0, 0, r, r), { w: 1.4, alpha: .45 });
  sunburst(g, 0, 0, { rays: 96, r0: 470, r1: 900, mode: 'lines', w: 1.2, alpha: .22 });
  g.rotate(rot);
  const land = (t0, i, n, from = 900) => { const u = back(seg(t, t0 - .55 - i * .015, t0 + i * .0), 1.2); return { u, r: lerp(from, 0, u) }; };
  // coloured powder petals (jewel tones)
  const pp = ss(seg(t, RANG.petals - .6, RANG.petals));
  for (let i = 0; i < 8; i++) { const a = i * TAU / 8 + TAU / 16; g.save(); g.rotate(a);
    const L = 250 * pp, w2 = 46 * pp; const pts = [[95, 0], [95 + L * .5, w2], [95 + L, 0], [95 + L * .5, -w2], [95, 0]];
    if (pp > 0) { airbrush(g, pts, { base: i % 2 ? C.emerald : C.burg, light: i % 2 ? C.emeraldL : C.burgL, dark: i % 2 ? C.emeraldD : C.burgD, dir: Math.PI }); gline(g, pts, { w: 1.6, closed: true }); }
    g.restore(); }
  // steel bars as spokes (top view)
  for (let i = 0; i < 8; i++) { const { u, r } = land(RANG.spokes, i, 8); if (u <= 0) continue; const a = i * TAU / 8; g.save(); g.rotate(a); g.translate(r, 0);
    const pts = D.rectPts(120, -16, 190, 32); airbrush(g, pts, { base: STEEL, light: STEEL_L, dark: STEEL_D, dir: -Math.PI / 2 }); gline(g, pts, { w: 1.6, closed: true });
    barFace(310, 0, 16, 1, -2); g.restore(); }
  // bar cross-sections on the ring
  for (let i = 0; i < 8; i++) { const { u, r } = land(RANG.discs, i, 8); if (u <= 0) continue; const a = i * TAU / 8; const R0 = 350 + r; barFace(Math.cos(a) * R0, Math.sin(a) * R0, 44, 1, t > T.lock ? lerp(-.2, 1.3, seg(t, T.lock + i * .03, T.lock + .5 + i * .03)) : -2); }
  // steel rings between
  for (let i = 0; i < 8; i++) { const { u, r } = land(RANG.rings, i, 8); if (u <= 0) continue; const a = i * TAU / 8 + TAU / 16, R0 = 360 + r, x = Math.cos(a) * R0, y = Math.sin(a) * R0;
    airbrush(g, ell(x, y, 30, 30), { base: STEEL, light: STEEL_L, dark: STEEL_D, radial: [x - 8, y - 8, 36] }); g.fillStyle = '#0b0806'; g.beginPath(); g.arc(x, y, 14, 0, TAU); g.fill();
    gline(g, ell(x, y, 30, 30), { w: 1.8 }); gline(g, ell(x, y, 14, 14), { w: 1.2 }); }
  // marigolds on the outer ring
  for (let i = 0; i < 16; i++) { const { u, r } = land(RANG.marigolds, i % 8, 16); if (u <= 0) continue; const a = i * TAU / 16 + TAU / 32, R0 = 430 + r; marigold(Math.cos(a) * R0, Math.sin(a) * R0, 22, 1, i); }
  // lotus + diya at the centre
  const lp = seg(t, RANG.lotus - 1.2, RANG.lotus);
  for (let i = 0; i < 8; i++) { const q = seg(lp, i * .06, .55 + i * .06); if (q <= 0) continue; const a = i * TAU / 8; g.save(); g.rotate(a);
    gline(g, [[30, 0], [62, 18], [104, 0], [62, -18], [30, 0]], { w: 2.2, part: q, glow: .4 }); g.restore(); }
  g.restore();
  // centre diya (top view): bowl + flame glow (not rotated)
  const cx = RC[0], cy = RC[1];
  airbrush(g, ell(cx, cy, 34 * z, 34 * z), { base: CLAY, light: '#d27a48', dark: '#240b04', radial: [cx - 10, cy - 10, 40] }); gline(g, ell(cx, cy, 34 * z, 34 * z), { w: 2 });
  glow(g, cx, cy, 160, '#ff9e3a', .55); glow(g, cx, cy, 50, '#fff1c4', .9);
  sparkle(g, cx, cy, 30 + 8 * Math.sin(t * 7), { color: '#fff4d0' });
  for (let i = 0; i < 8; i++) { const a = i * TAU / 8 + TAU / 16, R0 = 505 * z, x = cx + Math.cos(a) * R0, y = cy + Math.sin(a) * R0; if (t < RANG.petals) continue;
    airbrush(g, ell(x, y, 22, 22), { base: CLAY, light: '#d27a48', dark: '#240b04', radial: [x - 6, y - 6, 26] }); gline(g, ell(x, y, 22, 22), { w: 1.6 });
    const k = ignite(t, T.lock + .06 * i); if (k > 0) { glow(g, x, y, 70 * k, '#ff9e3a', .5); glow(g, x, y, 22, '#fff1c4', .9 * Math.min(1, k)); sparkle(g, x, y, 14 * Math.min(1.4, k), { color: '#fff4d0', glow: 0 }); } }
  // the lock: ring of light runs round + glints
  if (t > T.lock) {
    const rp = eo(seg(t, T.lock, T.lock + .55));
    gline(g, arcPts(cx, cy, 470 * z, -Math.PI / 2, -Math.PI / 2 + TAU * rp, 120), { w: 3.2, glow: 1, sheen: .6 });
    for (let i = 0; i < 8; i++) { const a = i * TAU / 8, q = pulse(t, T.lock + .05 + i * .04, .2); sparkle(g, cx + Math.cos(a) * 350 * z, cy + Math.sin(a) * 350 * z, 46 * q, { rot: .3 }); }
    glow(g, cx, cy, 620, '#ffcf7a', .25 * lockK);
  }
}

// ---------- scene C: fireworks ----------
const TONES = { gold: [C.gold2, '#fff4d0'], saffron: [SAF, SAF_L], ivory: ['#f2e8d5', '#ffffff'], emerald: [C.emeraldL, '#bff0dc'] };
function burst(b, t, dy) {
  const a = t - b.t, cx = b.x, cy = b.y + dy * .55;
  const horizon = 1200 + dy;
  if (!b.match && a < 0 && a > -.6) { // rocket
    const u = eo((a + .6) / .6), y = lerp(horizon, cy, u);
    D.speedLines(g, cx, y, Math.PI / 2, { n: 3, len: 160, spread: 8, w: 3, color: SAF_L, seed: b.seed });
    sparkle(g, cx, y, 14, { color: '#fff4d0' }); return;
  }
  if (a < 0) return;
  const A = b.match ? a + .32 : a;              // the match-cut burst starts already open
  if (A > 2.3) return;
  const [c1, c2] = TONES[b.tone], R = b.r, n = 36, Rn = mulberry(b.seed);
  const open = eo(A / .55), fade = 1 - ss(seg(A, .7, 2.2)), drop = 120 * A * A;
  g.save(); g.globalCompositeOperation = 'lighter';
  if (A < .25) glow(g, cx, cy, R * .9, c1, .6 * (1 - A / .25));
  for (let i = 0; i < n; i++) {
    const ang = i * TAU / n + (b.seed % 3) * .05, rr = R * open * (.92 + .08 * Rn());
    const x1 = cx + Math.cos(ang) * rr, y1 = cy + Math.sin(ang) * rr + drop, x0 = cx + Math.cos(ang) * rr * lerp(.2, .72, seg(A, 0, .9)), y0 = cy + Math.sin(ang) * rr * lerp(.2, .72, seg(A, 0, .9)) + drop * .6;
    const gr = g.createLinearGradient(x0, y0, x1, y1); gr.addColorStop(0, rgba(c1, 0)); gr.addColorStop(1, rgba(c2, fade));
    g.strokeStyle = gr; g.lineWidth = i % 2 ? 3 : 4.6; g.lineCap = 'round'; g.beginPath(); g.moveTo(x0, y0); g.lineTo(x1, y1); g.stroke();
    if (A > .5) for (let k = 1; k <= 3; k++) { const ff = fade * (.5 + .5 * Math.sin(A * 25 + i * 3 + k)); g.fillStyle = rgba(c2, ff * .8); g.beginPath(); g.arc(lerp(x0, x1, k / 4), lerp(y0, y1, k / 4) + 30 * k * A, 2, 0, TAU); g.fill(); }
    if (i % 2 === 0) sparkle(g, x1, y1, (i % 4 ? 9 : 16) * fade * (A < .9 ? 1 : .5 + .5 * Math.sin(A * 30 + i)), { color: c2, glow: 0 });
  }
  // inner ring of dots (deco double ring)
  for (let i = 0; i < 16; i++) { const ang = i * TAU / 16 + .1, rr = R * .5 * open; g.fillStyle = rgba(c1, fade); g.beginPath(); g.arc(cx + Math.cos(ang) * rr, cy + Math.sin(ang) * rr + drop * .8, 3.2, 0, TAU); g.fill(); }
  g.restore();
}
function sky(t) {
  const dy = lerp(0, 150, eio(seg(t, T.match, T.hush)));        // the tilt up: the world sinks
  const gr = g.createLinearGradient(0, 0, 0, H); gr.addColorStop(0, '#05070c'); gr.addColorStop(.6, '#0d0a0e'); gr.addColorStop(1, '#1a0f07'); g.fillStyle = gr; g.fillRect(0, 0, W, H);
  // stars: tiny deco glints
  const R = mulberry(9); for (let i = 0; i < 60; i++) { const x = R() * W, y = R() * 900 + dy * .2, tw = .5 + .5 * Math.sin(t * (2 + R() * 3) + i); sparkle(g, x, y, 3 + 4 * R() * tw, { alpha: .6, glow: 0, color: C.gold2 }); }
  sunburst(g, 540, 1260 + dy, { rays: 40, r0: 200, r1: 1500, a0: Math.PI, a1: TAU, mode: 'lines', w: 1.2, alpha: .18 });
  for (const b of BURSTS) burst(b, t, dy);
  // parapet with a row of lamps
  const hy = 1200 + dy;
  const gp = g.createLinearGradient(0, hy, 0, H); gp.addColorStop(0, '#1c130b'); gp.addColorStop(1, '#070504'); g.fillStyle = gp; g.fillRect(0, hy, W, H - hy + 10);
  gline(g, [[0, hy], [W, hy]], { w: 2.4, sheen: .4 }); D.rules(g, 0, hy + 12, W, hy + 12, 2, 6, 1, { alpha: .6 });
  D.chevrons(g, 0, W, hy + 30, { n: 18, h: 16, rows: 2, gap: 10, w: 1.2 });
  for (let i = 0; i < 9; i++) smallDiya(60 + i * 120, hy - 4, .42, t, -10);
}

// ---------- doors (lattice leaves closing on the seam) ----------
function doors(t) {
  const c = eio(seg(t, T.door - .4, T.door)), o = eio(seg(t, T.door + .04, T.open));
  const k = t < T.door ? c : 1 - o; if (k <= 0) return;
  for (const s of [-1, 1]) {
    const w = W / 2 * k, x0 = s < 0 ? 0 : W - w;
    g.save(); g.beginPath(); g.rect(x0, 0, w, H); g.clip();
    const lx = s < 0 ? w - W / 2 : W / 2 + (W / 2 - w);   // leaf slides in from its edge
    g.translate(lx, 0);
    const gr = g.createLinearGradient(0, 0, W / 2, 0); gr.addColorStop(0, '#0e0a06'); gr.addColorStop(1, '#1c140b'); g.fillStyle = gr; g.fillRect(0, 0, W / 2, H);
    D.fishScale(g, 30, 60, W / 2 - 60, H - 120, 34, { stroke: 'rgba(201,162,75,.55)' });
    gline(g, D.rectPts(18, 40, W / 2 - 36, H - 80), { w: 2.4, closed: true }); gline(g, D.rectPts(30, 52, W / 2 - 60, H - 104), { w: 1.2, closed: true });
    D.fan(g, s < 0 ? W / 2 - 18 : 18, H / 2, 70, { a0: s < 0 ? Math.PI / 2 : -Math.PI / 2, a1: s < 0 ? Math.PI * 1.5 : Math.PI / 2, ribs: 7, fill: C.gold1 });
    g.restore();
  }
  if (Math.abs(t - T.door) < .2) { gline(g, [[W / 2, 0], [W / 2, H]], { w: 3, glow: 1 }); sparkle(g, W / 2, H / 2, 80 * pulse(t, T.door, .12)); }
}

// ---------- texts per shot (also reported to readcheck) ----------
const shown = [];
function say(id, text, x, y, size, font, a, sheen = .4) { devText(text, x, y, size, font, a, sheen); if (a > .98) { g.save(); g.font = `${size}px ${font}`; const w = g.measureText(text).width; g.restore(); shown.push({ id, text, x0: x - w / 2, y0: y - size, x1: x + w / 2, y1: y + size * .35 }); } }

function textsA(t) { // shots 4: title + greeting
  if (t < T.title || t > T.door) return;
  textBack(70, 360, ss(seg(t, T.title, T.title + .5)));
  const p = seg(t, T.title, T.title + 1.4);
  TY.titleBar(g, TXT.title, 540, 180, { p, size: 92, font: 'Rozha', track: 0, wings: true });
  if (p >= 1) shown.push({ id: 'title', text: TXT.title, x0: 300, y0: 120, x1: 780, y1: 240 });
  const a = riseIn(t, T.greet, .6);
  if (a > 0) { topRules(330, ss(seg(t, T.greet + .2, T.greet + 1))); say('greet', TXT.greet, 540, 300 + (1 - a) * 18, fitText(TXT.greet, 50, 'TiroH', 900), 'TiroH', a, lerp(-.2, 1.2, seg(t, T.greet, T.greet + 1.6))); }
}
function textsB(t) { // shloka over the rangoli
  const a1 = riseIn(t, 16.2, .7), a2 = riseIn(t, 16.75, .6), out = 1 - ss(seg(t, T.match - .3, T.match));
  if (a1 <= 0) return;
  textBack(60, 330, a1 * out);
  lotus(540, 102, .8, seg(t, 15.9, 16.9));
  const s1 = fitText(TXT.sh1, 50, 'TiroS', 960);
  say('sh1', TXT.sh1, 540, 200 + (1 - a1) * 16, s1, 'TiroS', a1 * out, lerp(-.2, 1.2, seg(t, 16.2, 18)));
  say('sh2', TXT.sh2, 540, 272 + (1 - a2) * 16, s1, 'TiroS', a2 * out, lerp(-.2, 1.2, seg(t, 17, 18.8)));
  diamond(540, 312, 10, a2 * out);
}
function textsC(t) { // blessing over the fireworks
  const a1 = riseIn(t, T.bless, .35), a2 = riseIn(t, T.bless + .02, .35), out = 1 - ss(seg(t, T.hush + .25, T.card));
  if (a1 <= 0 || out <= 0) return;
  textBack(80, 330, a1 * out);
  topRules(116, a1 * out, 220, 40); diamond(540, 116, 9, a1 * out);
  const s = fitText(TXT.b2, 46, 'TiroH', 940);
  say('b1', TXT.b1, 540, 196 + (1 - a1) * 16, s, 'TiroH', a1 * out);
  say('b2', TXT.b2, 540, 262 + (1 - a2) * 16, s, 'TiroH', a2 * out);
  topRules(300, a2 * out, 220, 40); diamond(540, 300, 9, a2 * out);
}
function card(t) { // shot 7: the poster
  const rev = eio(seg(t, T.card, T.card + .8));
  background(t, 1);
  g.save(); g.beginPath(); g.rect(W / 2 - W / 2 * rev, 0, W * rev, H); g.clip();
  worldA(t, { x: 540, y: 675, z: 1 }, { archFull: true, coins: true });
  g.restore();
  if (rev < 1) gline(g, [[W / 2 - W / 2 * rev, 0], [W / 2 - W / 2 * rev, H]], { w: 2, glow: 1, alpha: 1 - rev }), gline(g, [[W / 2 + W / 2 * rev, 0], [W / 2 + W / 2 * rev, H]], { w: 2, glow: 1, alpha: 1 - rev });
  // falling sparks from the last bursts become the rules
  fallSparks(t);
  // top band
  textBack(20, 380, rev);
  lotus(540, 70, .8, seg(t, T.card + .1, T.card + 1.1));
  topRules(64, eio(seg(t, T.card + .1, T.card + .9)), 230, 120);
  const p = seg(t, T.card + .2, T.card + 1.5);
  TY.titleBar(g, TXT.title, 540, 168, { p, size: 88, font: 'Rozha', track: 0, wings: true });
  if (p >= 1) shown.push({ id: 'title2', text: TXT.title, x0: 300, y0: 110, x1: 780, y1: 226 });
  const a = riseIn(t, T.card + .9), a2 = riseIn(t, T.card + 1.25);
  say('card', TXT.card, 540, 286 + (1 - a) * 16, fitText(TXT.card, 44, 'TiroH', 960), 'TiroH', a, lerp(-.2, 1.2, seg(t, T.card + 1, T.card + 2.4)));
  if (a2 > 0) { TY.goldText(g, TXT.en, 540, 334 + (1 - a2) * 10, { size: 26, font: 'Josefin', weight: 600, track: 7, alpha: a2, shadow: false });
    if (a2 > .98) shown.push({ id: 'en', text: TXT.en, x0: 430, y0: 314, x1: 650, y1: 340 }); }
  // brand
  textBack(1112, 1350, ss(seg(t, T.brand - .3, T.brand + .3)));
  const pb = seg(t, T.brand, T.brand + 1.2);
  const sh = t < T.sheen ? -.2 : lerp(-.2, 1.25, eio(seg(t, T.sheen, T.sheen + .8)));
  TY.titleBar(g, TXT.brand, 540, 1186, { p: pb, size: 70, font: 'Limelight', track: 6, wings: true, sheen: pb < 1 ? null : sh });
  if (pb >= 1) shown.push({ id: 'brand', text: TXT.brand, x0: 230, y0: 1140, x1: 850, y1: 1230 });
  if (t > T.sheen && t < T.sheen + 1) { const x = lerp(250, 830, eio(seg(t, T.sheen, T.sheen + .8))); glow(g, x, 1180, 120, SAF, .5); sparkle(g, x, 1176, 26, { color: '#fff4d0', rot: t * 4 }); }
  const ac = riseIn(t, T.contact);
  if (ac > 0) { TY.goldText(g, TXT.contact, 540, 1282 + (1 - ac) * 10, { size: 34, font: 'Josefin', weight: 600, track: 3, alpha: ac, shadow: false });
    if (ac > .98) shown.push({ id: 'contact', text: TXT.contact, x0: 360, y0: 1252, x1: 720, y1: 1290 }); }
  topRules(1318, eio(seg(t, T.contact + .2, T.contact + 1)), 260, 50); diamond(540, 1318, 10, ac);
  // gentle twinkles over the finished card
  if (t > T.contact + .8) { const R = mulberry(77); for (let i = 0; i < 6; i++) { const x = 120 + R() * 840, y = 420 + R() * 600, ph = R() * 3; const q = Math.max(0, Math.sin((t - T.contact) * 1.6 + ph * 2)); sparkle(g, x, y, 18 * q * q, { alpha: .8 }); } }
}
function fallSparks(t) {
  if (t < BURSTS[8].t || t > T.card + 1.2) return;
  const R = mulberry(4); g.save(); g.globalCompositeOperation = 'lighter';
  for (let i = 0; i < 70; i++) {
    const x = 120 + R() * 840, t0 = BURSTS[8].t + R() * .4, y0 = 260 + R() * 360, a = t - t0; if (a < 0) continue;
    const y = y0 + 60 * a + 160 * a * a; const al = (1 - ss(seg(t, T.card + .2, T.card + 1.2))) * (.6 + .4 * Math.sin(a * 20 + i));
    g.fillStyle = rgba(i % 3 ? C.gold2 : SAF_L, al); g.beginPath(); g.arc(x, y, 2.4, 0, TAU); g.fill();
  }
  g.restore();
}

// ---------- render ----------
window.DUR = DUR + OPEN;
const off = document.createElement('canvas'); off.width = W; off.height = H;
function brandCard(gg, t) { // the film opens on Rakesh Steels
  const keep = g; g = gg;
  g.setTransform(1, 0, 0, 1, 0, 0); g.globalAlpha = 1; g.globalCompositeOperation = 'source-over';
  D.ground(g, W, H, { top: '#140e08', bot: C.ink, vig: 0 });
  glow(g, W / 2, 640, 700, '#ff8a2a', .07 + .07 * ss(seg(t, .2, 1.2)));
  sunburst(g, 540, 640, { rays: 72, r0: 160, r1: 1300, mode: 'both', w: 1.3, alpha: .1 + .2 * ss(seg(t, .3, 1.4)), colorA: 'rgba(201,162,75,.06)' });
  lotus(540, 470, 1.1, seg(t, .9, 1.9));
  topRules(470, eio(seg(t, 1.0, 1.8)), 230, 150);
  const p = seg(t, .1, 1.3);
  TY.titleBar(g, TXT.brand, 540, 640, { p, size: 92, font: 'Limelight', track: 8, wings: true, sheen: p < 1 ? null : lerp(-.2, 1.2, eio(seg(t, 2.2, 3.4))) });
  if (p >= 1 && gg === cv.getContext('2d')) shown.push({ id: 'brand0', text: TXT.brand, x0: 160, y0: 580, x1: 920, y1: 700 });
  const a = riseIn(t, .95, .5);
  if (a > 0) { TY.goldText(g, 'HOWRAH', 540, 780 + (1 - a) * 10, { size: 32, font: 'Josefin', weight: 600, track: 14, alpha: a, shadow: false }); diamond(540, 818, 9, a); }
  const a2 = riseIn(t, 1.25, .5);
  say('pres', 'की ओर से दीपावली की शुभकामनाएँ', 540, 890 + (1 - a2) * 12, 44, 'TiroH', a2);
  topRules(930, eio(seg(t, 1.8, 2.6)), 260, 40);
  if (t > 2.2 && t < 3.5) { const x = lerp(170, 910, eio(seg(t, 2.2, 3.3))); glow(g, x, 636, 110, '#ff9a2e', .45); sparkle(g, x, 630, 24, { color: '#fff4d0', rot: t * 4 }); }
  D.vignette(g, W, H, .5);
  g = keep;
}
window.render = (T0) => {
  shown.length = 0;
  g.setTransform(1, 0, 0, 1, 0, 0); g.globalAlpha = 1; g.globalCompositeOperation = 'source-over';
  const SPLIT = OPEN - .45;
  if (T0 < SPLIT) { brandCard(g, T0); return; }
  renderMain(T0 - OPEN);
  if (T0 < OPEN) { // the card parts along its centre seam
    const k = eio(seg(T0, SPLIT, OPEN)); brandCard(off.getContext('2d'), SPLIT);
    g.setTransform(1, 0, 0, 1, 0, 0);
    g.drawImage(off, 0, 0, W / 2, H, -W / 2 * k, 0, W / 2, H); g.drawImage(off, W / 2, 0, W / 2, H, W / 2 + W / 2 * k, 0, W / 2, H);
    for (const x of [W / 2 - W / 2 * k, W / 2 + W / 2 * k]) gline(g, [[x, 0], [x, H]], { w: 2.4, glow: 1 });
  }
};
function renderMain(t) {
  if (t < T.door + .02) {
    const cam = camAt(t), warm = ss(seg(t, T.ign, T.ign + 1));
    background(t, warm);
    g.save(); applyCam(cam, t > T.bite && t < T.cutEnd ? 3 : t < T.bite + .25 && t > T.bite ? 6 : 0, t); worldA(t, cam); g.restore();
    textsA(t);
  } else if (t < T.match) {
    rangoli(t); textsB(t);
  } else if (t < T.card) {
    sky(t); textsC(t);
    if (t > T.hush) fallSparks(t);
  } else card(t);
  doors(t);
  // match-cut flash
  if (Math.abs(t - T.match) < .12) { g.fillStyle = `rgba(255,236,190,${.22 * (1 - Math.abs(t - T.match) / .12)})`; g.fillRect(0, 0, W, H); }
  D.vignette(g, W, H, .5);
}
window.TEXTS = (t) => { window.render(t); return shown.slice(); };

// ---------- sound events (for mix.py) ----------
const EV = [];
EV.push({ t: 0, type: 'whine' }, { t: T.bite, type: 'bite' }, { t: T.bite, type: 'grind', dur: T.cutEnd - T.bite }, { t: T.cutEnd, type: 'through' }, { t: T.lift, type: 'sizzle', dur: T.ign - T.lift });
for (let k = 0; k <= 40; k++) { const tt = T.sp0 + k * .1; const s = sparkAt(tt); EV.push({ t: tt, type: 'sparkpan', pan: (s.x - 540) / 400 }); }
EV.push({ t: T.ign - .12, type: 'match' }, { t: T.ign, type: 'ignite' });
PAIRS.forEach((tt, k) => { EV.push({ t: tt, type: 'diya', pan: -.3 - k * .08, k }, { t: tt, type: 'diya', pan: .3 + k * .08, k }); });
EV.push({ t: T.arch, type: 'archdraw' }, { t: T.title + .4, type: 'titleOn' }, { t: T.greet, type: 'shimmer' });
EV.push({ t: T.door - .4, type: 'doorSwing' }, { t: T.door, type: 'doorShut' }, { t: T.door + .05, type: 'doorOpen' });
for (const [k, tt] of Object.entries(RANG)) if (k !== 'petals' && k !== 'lotus') for (let i = 0; i < 8; i++) EV.push({ t: tt + i * 0, type: 'clink', pan: Math.cos(i * TAU / 8) * .7, i, k });
EV.push({ t: RANG.petals - .6, type: 'powder' }, { t: RANG.lotus - 1.2, type: 'shimmer' }, { t: T.lock, type: 'lock' });
for (const b of BURSTS) { if (!b.match) EV.push({ t: b.t - .6, type: 'rocket', pan: (b.x - 540) / 540 }); EV.push({ t: b.t, type: 'burst', pan: (b.x - 540) / 540, r: b.r }); }
EV.push({ t: 19.6, type: 'crackleBed' });
EV.push({ t: T.card, type: 'reveal' }, { t: T.brand, type: 'brand' }, { t: T.sheen, type: 'sheen' });
EV.push({ t: T.kuber, type: 'kuber' }, { t: T.kuber + 1.4, type: 'diya', pan: -.3, k: 9 }, { t: T.kuber + 1.48, type: 'diya', pan: .3, k: 9 });
for (let i = 0; i < 8; i++) EV.push({ t: T.lock + .06 * i, type: 'diya', pan: Math.cos(i * TAU / 8 + TAU / 16) * .6, k: 10 });
for (let i = 0; i < 12; i++) EV.push({ t: T.coins + i * .11 + .45, type: 'coin', pan: (i % 2 ? .3 : -.1), i });
for (const e of EV) e.t += OPEN;
EV.push({ t: 0, type: 'open', len: OPEN }, { t: .1, type: 'brandOpen' }, { t: .75, type: 'brandBar' }, { t: 2.2, type: 'sheen' }, { t: OPEN - .45, type: 'split' });
window.EV = EV.sort((a, b) => a.t - b.t);

const fams = ['92px Rozha', '50px TiroS', '50px TiroH', '70px Limelight', '600 30px Josefin', '30px Poiret'];
Promise.all(fams.map(f => document.fonts.load(f, f.includes('Rozha') || f.includes('Tiro') ? 'शुभ दीपावली' : 'RAKESH'))).then(() => document.fonts.ready).then(() => { window.render(0); window.READY = true; });
