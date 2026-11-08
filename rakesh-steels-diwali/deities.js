// Shri Ganesha ji and Maa Lakshmi ji, drawn in the same Art Deco manner as Kuber ji (kuber.js):
// gold keylines, airbrushed fills, a halo of rays, seated on a lotus. Origin = centre of the seat base; ~300 units tall.
import * as D from './engine/deco.js';
const { C, TAU, lerp, seg, ss, eo, gline, airbrush, glow, sparkle, sunburst, mix, rgba } = D;
const ell = (cx, cy, rx, ry) => { const p = new Path2D(); p.ellipse(cx, cy, rx, ry, 0, 0, TAU); return p; };

function stages(p) { return { line: ss(seg(p, 0, .6)), fill: ss(seg(p, .35, .9)), halo: eo(seg(p, .5, 1)) }; }
function halo(g, cy, r, k, color = '#ffcf7a') {
  if (k <= 0) return;
  glow(g, 0, cy, r * 3.4, color, .35 * k);
  sunburst(g, 0, cy, { rays: 36, r0: r, r1: r + 110 * k, mode: 'lines', w: 2.2, alpha: .85 * k });
  gline(g, D.arcPts(0, cy, r, 0, TAU * k, 60), { w: 2.4, glow: .6 });
}
function lotusSeat(g, fill, kw, base, light, dark, n = 4, pw = 27) {
  const petal = (cx, h, w) => [[cx - w, 0], [cx - w * .55, -h * .7], [cx, -h], [cx + w * .55, -h * .7], [cx + w, 0]];
  for (let i = -n; i <= n; i++) { const pts = petal(i * pw, 34 - Math.abs(i) * 2, pw * .82);
    if (fill > 0) airbrush(g, pts, { base, light, dark, dir: -1.6, alpha: fill }); gline(g, pts, { ...kw, closed: false }); }
  gline(g, [[-(n + 1) * pw, 0], [(n + 1) * pw, 0]], { ...kw, w: 2.4 });
}
function seatedLegs(g, fill, kw, base, light, dark, w = 122) {
  const legs = new Path2D(); legs.moveTo(-w, -24); legs.bezierCurveTo(-w, -62, -w * .66, -78, -40, -74); legs.lineTo(40, -74); legs.bezierCurveTo(w * .66, -78, w, -62, w, -24); legs.closePath();
  if (fill > 0) airbrush(g, legs, { base, light, dark, dir: -2.2, alpha: fill });
  gline(g, legs, kw); gline(g, [[-w + 4, -30], [w - 4, -30]], { ...kw, w: 3 });
  gline(g, [[-w + 14, -36], [-20, -50], [60, -40], [w - 14, -34]], { ...kw, w: 1.4 });
}
function arm(g, pts, fill, kw, skin, skinL, w = 26) {
  if (fill > 0) { g.save(); g.globalAlpha *= fill; g.strokeStyle = skin; g.lineCap = 'round'; g.lineJoin = 'round'; g.lineWidth = w; g.beginPath(); pts.forEach((q, i) => i ? g.lineTo(q[0], q[1]) : g.moveTo(q[0], q[1])); g.stroke();
    g.strokeStyle = skinL; g.lineWidth = w * .25; g.globalAlpha *= .5; g.stroke(); g.restore(); }
  gline(g, pts, { ...kw, w: 1.2 });
  const [a, b] = [pts[pts.length - 2], pts[pts.length - 1]], L = Math.hypot(b[0] - a[0], b[1] - a[1]) || 1, nx = -(b[1] - a[1]) / L * w * .55, ny = (b[0] - a[0]) / L * w * .55;
  const x = lerp(a[0], b[0], .8), y = lerp(a[1], b[1], .8); gline(g, [[x - nx, y - ny], [x + nx, y + ny]], { ...kw, w: 3 });   // bangle
  const [c, d] = [pts[0], pts[1]], x2 = lerp(c[0], d[0], .45), y2 = lerp(c[1], d[1], .45), L2 = Math.hypot(d[0] - c[0], d[1] - c[1]) || 1, mx = -(d[1] - c[1]) / L2 * w * .55, my = (d[0] - c[0]) / L2 * w * .55;
}
function blessingHand(g, x, y, fill, kw, skin, skinL, skinD) { // palm facing out, fingers up; (x, y) = wrist
  const palm = new Path2D(); palm.moveTo(x - 12, y); palm.lineTo(x - 13, y - 24); palm.lineTo(x + 12, y - 24); palm.lineTo(x + 11, y); palm.quadraticCurveTo(x, y + 5, x - 12, y); palm.closePath();
  if (fill > 0) { airbrush(g, palm, { base: skin, light: skinL, dark: skinD, alpha: fill });
    g.save(); g.globalAlpha *= fill; g.strokeStyle = skin; g.lineCap = 'round'; g.lineWidth = 6;
    for (const [fx, fh] of [[-9.5, 13], [-3.2, 17], [3.2, 16], [9.5, 12]]) { g.beginPath(); g.moveTo(x + fx, y - 22); g.lineTo(x + fx, y - 22 - fh); g.stroke(); }
    g.beginPath(); g.moveTo(x + 12, y - 6); g.lineTo(x + 20, y - 16); g.stroke(); g.restore();
    g.fillStyle = rgba('#c2301e', fill); g.beginPath(); g.arc(x, y - 12, 2.8, 0, TAU); g.fill(); }
  gline(g, palm, { ...kw, w: 1.2 });
}
function crown(g, cy, w, h, fill, kw, t) { // stepped mukut sitting on the head at cy
  const s = w / 56, top = cy - h;
  const cr = [[-w / 2 - 3 * s, cy], [-w / 2, cy - h * .28], [-w * .36, cy - h * .28], [-w * .36, cy - h * .52], [-w * .18, cy - h * .52], [-w * .18, cy - h * .76], [0, top],
    [w * .18, cy - h * .76], [w * .18, cy - h * .52], [w * .36, cy - h * .52], [w * .36, cy - h * .28], [w / 2, cy - h * .28], [w / 2 + 3 * s, cy], [-w / 2 - 3 * s, cy]];
  if (fill > 0) { g.save(); g.globalAlpha *= fill; g.fillStyle = D.goldGrad(g, -w / 2, top, w / 2, cy, { sheen: .3 + .3 * Math.sin(t * .8) }); g.fill(D.toPath(cr, true)); g.restore(); }
  gline(g, cr, { ...kw, w: 2 });
  if (fill > .5) { airbrush(g, ell(0, cy - h * .34, 6 * s, 7 * s), { base: C.emerald, light: C.emeraldL, dark: C.emeraldD, alpha: fill }); airbrush(g, ell(0, cy - h * .64, 4 * s, 5 * s), { base: C.burg, light: C.burgL, dark: C.burgD, alpha: fill }); }
}
function lotusFlower(g, x, y, r, fill, kw) {
  for (const [a, L] of [[-Math.PI / 2, 1], [-Math.PI / 2 - .6, .85], [-Math.PI / 2 + .6, .85], [-Math.PI / 2 - 1.15, .65], [-Math.PI / 2 + 1.15, .65]]) {
    const ux = Math.cos(a), uy = Math.sin(a), nx = -uy, ny = ux, l = r * L, w = r * .32;
    const pts = [[x, y], [x + ux * l * .5 + nx * w, y + uy * l * .5 + ny * w], [x + ux * l, y + uy * l], [x + ux * l * .5 - nx * w, y + uy * l * .5 - ny * w], [x, y]];
    if (fill > 0) airbrush(g, pts, { base: '#e2788c', light: '#ffc2cc', dark: '#7a1e34', dir: -1.6, alpha: fill });
    gline(g, pts, { ...kw, w: 1.2, closed: true });
  }
}

// ---------------------------------------------------------------- Shri Ganesha ji
export function ganesha(g, x, y, s, p, t) {
  if (p <= 0) return;
  const { line, fill, halo: hk } = stages(p);
  const SK = '#e98f62', SKL = '#ffc49a', SKD = '#8a3c1a';
  g.save(); g.translate(x, y); g.scale(s, s);
  const kw = { w: 1.8, part: line, bb: [-160, -330, 160, 10] };
  halo(g, -200, 66, hk);
  lotusSeat(g, fill, kw, mix(C.burg, '#e37a8a', .25), '#f2a0a8', C.burgD);
  // mouse (mushak) by the seat
  if (fill > .2) { g.save(); g.globalAlpha *= fill; const mx = -112, my = -8;
    airbrush(g, ell(mx, my - 9, 15, 10), { base: '#8a7a6a', light: '#cdbfae', dark: '#3a3028', dir: -2 }); airbrush(g, ell(mx - 15, my - 13, 8, 7), { base: '#8a7a6a', light: '#cdbfae', dark: '#3a3028' });
    airbrush(g, ell(mx - 13, my - 21, 4, 5), { base: '#d89a9a', light: '#f2c0c0', dark: '#7a4a4a' }); g.fillStyle = '#120a06'; g.beginPath(); g.arc(mx - 18, my - 14, 1.6, 0, TAU); g.fill();
    g.strokeStyle = '#6a5a4a'; g.lineWidth = 2; g.beginPath(); g.moveTo(mx + 14, my - 6); g.quadraticCurveTo(mx + 28, my - 2, mx + 26, my - 16); g.stroke(); g.restore(); }
  seatedLegs(g, fill, kw, '#c42a2a', '#f2604a', '#5a0a0a');
  // torso with round belly
  const tor = new Path2D(); tor.moveTo(-54, -168); tor.bezierCurveTo(-58, -140, -74, -118, -72, -98); tor.bezierCurveTo(-70, -70, -36, -66, 0, -66);
  tor.bezierCurveTo(36, -66, 70, -70, 72, -98); tor.bezierCurveTo(74, -118, 58, -140, 54, -168); tor.bezierCurveTo(30, -176, -30, -176, -54, -168); tor.closePath();
  if (fill > 0) airbrush(g, tor, { base: SK, light: SKL, dark: SKD, radial: [-18, -118, 110], alpha: fill });
  gline(g, tor, kw); gline(g, D.arcPts(0, -96, 9, .2, Math.PI - .2, 12, 5), { ...kw, w: 1.2 });
  gline(g, [[-46, -166], [-10, -128], [30, -92], [56, -78]], { ...kw, w: 1.3 });       // sacred thread
  gline(g, D.arcPts(0, -168, 34, .25, Math.PI - .25, 24, 26), { ...kw, w: 2.4 });
  // four arms: axe and lotus raised, blessing, modak bowl
  arm(g, [[-50, -160], [-90, -150], [-102, -192]], fill, kw, SK, SKL);
  arm(g, [[50, -160], [90, -150], [102, -192]], fill, kw, SK, SKL);
  arm(g, [[-54, -150], [-82, -112], [-90, -138]], fill, kw, SK, SKL);
  arm(g, [[54, -150], [86, -108], [76, -86]], fill, kw, SK, SKL);
  // axe (parashu) in the upper right hand, lotus in the upper left
  gline(g, [[-102, -176], [-102, -246]], { ...kw, w: 3 });
  const axe = [[-102, -246], [-128, -254], [-134, -236], [-128, -218], [-102, -226]];
  if (fill > 0) { g.save(); g.globalAlpha *= fill; g.fillStyle = D.goldGrad(g, -134, -256, -100, -216, { sheen: .5 }); g.fill(D.toPath(axe, true)); g.restore(); }
  gline(g, axe, { ...kw, closed: true, w: 1.6 });
  lotusFlower(g, 104, -200, 26, fill, kw);
  blessingHand(g, -90, -136, fill, kw, SK, SKL, SKD);
  // bowl of modaks
  const bowl = new Path2D(); bowl.moveTo(56, -90); bowl.quadraticCurveTo(58, -64, 78, -62); bowl.quadraticCurveTo(98, -64, 100, -90); bowl.closePath();
  if (fill > 0) { g.save(); g.globalAlpha *= fill; g.fillStyle = D.goldGrad(g, 56, -92, 100, -60, { sheen: .5 }); g.fill(bowl); g.restore();
    for (const [mx, my] of [[68, -92], [78, -98], [88, -92]]) { const m = new Path2D(); m.moveTo(mx - 7, my + 2); m.quadraticCurveTo(mx - 6, my - 8, mx, my - 13); m.quadraticCurveTo(mx + 6, my - 8, mx + 7, my + 2); m.closePath();
      airbrush(g, m, { base: '#f0e2c0', light: '#fffaf0', dark: '#b8a070', alpha: fill }); } }
  gline(g, bowl, { ...kw, closed: true });
  // elephant head: ears as deco fans, dome, trunk curling to his left, one tusk broken
  for (const sx of [-1, 1]) {
    const ear = ell(sx * 50, -198, 27, 38);
    if (fill > 0) airbrush(g, ear, { base: SK, light: SKL, dark: SKD, radial: [sx * 40, -210, 50], alpha: fill });
    if (fill > 0) airbrush(g, ell(sx * 54, -196, 15, 26), { base: '#e39a8a', light: '#ffc8b8', dark: '#9a5050', alpha: fill * .8 });
    gline(g, ear, kw); for (let i = 0; i < 2; i++) gline(g, D.arcPts(sx * 50, -198, 21 - i * 7, sx > 0 ? -1.2 : Math.PI - 1.9, sx > 0 ? 1.9 : Math.PI + 1.2, 16, 31 - i * 9), { ...kw, w: 1 });
  }
  const head = ell(0, -206, 34, 36);
  if (fill > 0) airbrush(g, head, { base: SK, light: SKL, dark: SKD, radial: [-8, -216, 46], alpha: fill });
  gline(g, head, kw);
  // trunk
  const trunk = [[0, -200], [1, -182], [-3, -164], [-2, -146], [6, -128], [20, -120], [32, -126], [34, -140]];
  if (fill > 0) { g.save(); g.globalAlpha *= fill; g.strokeStyle = SK; g.lineCap = 'round'; g.lineJoin = 'round';
    for (let i = 1; i < trunk.length; i++) { g.lineWidth = lerp(24, 10, i / (trunk.length - 1)); g.beginPath(); g.moveTo(...trunk[i - 1]); g.lineTo(...trunk[i]); g.stroke(); } g.restore(); }
  { const L = trunk.map(([a, b], i) => [a - lerp(12, 5, i / (trunk.length - 1)), b]), Rr = trunk.map(([a, b], i) => [a + lerp(12, 5, i / (trunk.length - 1)), b]); gline(g, L, { ...kw, w: 1.4 }); gline(g, Rr, { ...kw, w: 1.4 }); }
  for (let i = 0; i < 5; i++) gline(g, [[-9, -184 + i * 9], [7, -184 + i * 9]], { ...kw, w: .8, alpha: .55, color: '#8a3c1a' });        // trunk folds
  const tusk = [[-15, -184], [-24, -168], [-19, -160]];
  if (fill > 0) { g.save(); g.globalAlpha *= fill; g.strokeStyle = '#fff4dc'; g.lineWidth = 6; g.lineCap = 'round'; g.beginPath(); g.moveTo(...tusk[0]); g.quadraticCurveTo(...tusk[1], ...tusk[2]); g.stroke();
    g.beginPath(); g.moveTo(15, -184); g.lineTo(19, -177); g.stroke(); g.restore(); }
  if (fill > .3) {
    const fk = { ...kw, w: 1.4, color: '#4a2210' };
    for (const sx of [-1, 1]) gline(g, D.arcPts(sx * 15, -210, 6, .15, Math.PI - .15, 10, 3), fk);
    g.fillStyle = rgba('#c2301e', fill); g.fillRect(-1.8, -232, 3.6, 12);                                        // tilak
    for (const yy of [-226, -221]) gline(g, [[-12, yy], [12, yy]], { ...kw, w: 1.2, color: '#fff4dc' });            // tripundra
  }
  crown(g, -232, 52, 64, fill, kw, t);
  g.restore();
  if (p > .95) sparkle(g, x, y - 300 * s, 22 * s * (.6 + .4 * Math.sin(t * 2.2 + 1)), { alpha: .9 });
}

// ---------------------------------------------------------------- Maa Lakshmi ji
export function lakshmi(g, x, y, s, p, t, coinsFrom = 0) {
  if (p <= 0) return;
  const { line, fill, halo: hk } = stages(p);
  const SK = '#f0b48a', SKL = '#ffdcbc', SKD = '#9a5a34';
  g.save(); g.translate(x, y); g.scale(s, s);
  const kw = { w: 1.8, part: line, bb: [-160, -330, 160, 10] };
  halo(g, -200, 62, hk, '#ffd59a');
  lotusSeat(g, fill, kw, '#e0708a', '#ffc2cc', '#7a1e34', 4, 28);
  // long hair behind
  const hair = new Path2D(); hair.moveTo(-26, -226); hair.bezierCurveTo(-44, -196, -46, -150, -52, -120); hair.lineTo(52, -120); hair.bezierCurveTo(46, -150, 44, -196, 26, -226); hair.closePath();
  if (fill > 0) airbrush(g, hair, { base: '#22140c', light: '#4a3020', dark: '#080402', dir: -2, alpha: fill });
  // red sari on the crossed legs, gold border
  seatedLegs(g, fill, kw, '#b3162e', '#e8485a', '#4a0410', 118);
  // torso: blouse and the sari's pallu across the chest
  const tor = new Path2D(); tor.moveTo(-42, -170); tor.bezierCurveTo(-46, -140, -40, -112, -46, -76); tor.lineTo(46, -76); tor.bezierCurveTo(40, -112, 46, -140, 42, -170); tor.bezierCurveTo(24, -178, -24, -178, -42, -170); tor.closePath();
  if (fill > 0) airbrush(g, tor, { base: SK, light: SKL, dark: SKD, radial: [-12, -140, 90], alpha: fill });
  const pallu = [[-42, -170], [-16, -174], [46, -96], [46, -76], [10, -76], [-44, -150]];
  if (fill > 0) airbrush(g, pallu, { base: '#b3162e', light: '#e8485a', dark: '#4a0410', dir: -2.2, alpha: fill });
  gline(g, tor, kw); gline(g, pallu, { ...kw, closed: true }); gline(g, [[-16, -174], [46, -96]], { ...kw, w: 3 });
  for (const yy of [-168, -160]) gline(g, D.arcPts(0, yy, 26, .3, Math.PI - .3, 20, 22), { ...kw, w: 2 });             // necklaces
  // four arms: two lotuses raised, blessing, coins pouring
  arm(g, [[-40, -162], [-74, -160], [-84, -196]], fill, kw, SK, SKL, 20);
  arm(g, [[40, -162], [74, -160], [84, -196]], fill, kw, SK, SKL, 20);
  arm(g, [[-42, -150], [-72, -112], [-80, -134]], fill, kw, SK, SKL, 20);
  arm(g, [[42, -150], [76, -116], [84, -96]], fill, kw, SK, SKL, 20);
  lotusFlower(g, -86, -204, 28, fill, kw); lotusFlower(g, 86, -204, 28, fill, kw);
  blessingHand(g, -80, -132, fill, kw, SK, SKL, SKD);
  // the giving hand, palm down
  const hand = ell(86, -90, 11, 8);
  if (fill > 0) airbrush(g, hand, { base: SK, light: SKL, dark: SKD, alpha: fill }); gline(g, hand, { ...kw, w: 1.2 });
  if (fill > .8) for (let i = 0; i < 9; i++) {   // a steady stream of gold coins
    const ph = ((t - coinsFrom) * 1.3 + i / 9) % 1; if (t < coinsFrom || ph < 0) continue;
    const cx = 88 + Math.sin(i * 2.1) * 4, cy = -82 + ph * 84, spin = Math.abs(Math.cos(t * 9 + i * 1.7));
    g.save(); g.globalAlpha *= fill * (1 - ss(seg(ph, .8, 1))); g.fillStyle = D.goldGrad(g, cx - 7, cy - 7, cx + 7, cy + 7, { sheen: .6 });
    g.beginPath(); g.ellipse(cx, cy, 7 * Math.max(.15, spin), 7, 0, 0, TAU); g.fill(); g.strokeStyle = C.gold0; g.lineWidth = 1; g.stroke(); g.restore();
  }
  // face
  const head = ell(0, -204, 23, 28);
  if (fill > 0) airbrush(g, head, { base: SK, light: SKL, dark: SKD, radial: [-6, -212, 34], alpha: fill });
  gline(g, head, kw);
  if (fill > .3) {
    const fk = { ...kw, w: 1.3, color: '#3a160a' };
    for (const sx of [-1, 1]) { gline(g, D.arcPts(sx * 9, -206, 6, .15, Math.PI - .15, 10, 2.6), fk); gline(g, D.arcPts(sx * 9, -212, 7, Math.PI + .35, TAU - .35, 10, 2.4), fk); }
    gline(g, [[0, -204], [-1.5, -195], [1.5, -194]], fk);
    gline(g, D.arcPts(0, -188, 6, .35, Math.PI - .35, 10, 3), { ...fk, color: '#9a1a2a', w: 1.8 });
    g.fillStyle = rgba('#c2301e', fill); g.beginPath(); g.arc(0, -219, 2.6, 0, TAU); g.fill();                       // bindi
    gline(g, D.arcPts(5, -193, 3, 0, TAU, 10), { ...kw, w: 1.2 });                                                   // nose ring
  }
  for (const sx of [-1, 1]) gline(g, [[sx * 23, -200], [sx * 24, -186]], { ...kw, w: 2.4 });                     // jhumka earrings
  crown(g, -226, 46, 70, fill, kw, t + 1);
  g.restore();
  if (p > .95) sparkle(g, x, y - 300 * s, 22 * s * (.6 + .4 * Math.sin(t * 2.2 + 2)), { alpha: .9 });
}
