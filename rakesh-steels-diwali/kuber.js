// Shri Kuber ji, drawn in the Art Deco manner: seated on a lotus, halo of rays, stepped crown,
// right hand raised in blessing, left hand holding the pot of wealth. Origin = centre of the seat base.
import * as D from './engine/deco.js';
const { C, TAU, clamp, lerp, seg, ss, eo, gline, airbrush, glow, sparkle, sunburst, mix } = D;
const SKIN = '#e2a464', SKIN_L = '#ffd7a0', SKIN_D = '#8a4f22';
const ell = (cx, cy, rx, ry) => { const p = new Path2D(); p.ellipse(cx, cy, rx, ry, 0, 0, TAU); return p; };

// p: 0→1 appearance (lines draw on, then fills come up), t: time (breathing glow)
export function kuber(g, x, y, s, p, t) {
  if (p <= 0) return;
  const line = ss(seg(p, 0, .6)), fill = ss(seg(p, .35, .9)), halo = eo(seg(p, .5, 1));
  g.save(); g.translate(x, y); g.scale(s, s);
  const kw = { w: 1.8, part: line, bb: [-160, -330, 160, 10] };
  // halo
  if (halo > 0) {
    glow(g, 0, -190, 210, '#ffcf7a', .35 * halo);
    sunburst(g, 0, -195, { rays: 36, r0: 62, r1: 62 + 110 * halo, mode: 'lines', w: 2.2, alpha: .85 * halo });
    gline(g, D.arcPts(0, -195, 60, 0, TAU * halo, 60), { w: 2.4, glow: .6 });
  }
  // lotus seat
  const petal = (cx, cy, w, h) => [[cx - w, cy], [cx - w * .55, cy - h * .7], [cx, cy - h], [cx + w * .55, cy - h * .7], [cx + w, cy]];
  for (let i = -4; i <= 4; i++) {
    const pts = petal(i * 27, 0, 22, 34 - Math.abs(i) * 2);
    if (fill > 0) airbrush(g, pts, { base: mix(C.burg, '#e37a8a', .25), light: '#f2a0a8', dark: C.burgD, dir: -1.6, alpha: fill });
    gline(g, pts, { ...kw, closed: false });
  }
  gline(g, [[-130, 0], [130, 0]], { ...kw, w: 2.4 });
  // crossed legs in a dhoti
  const legs = new Path2D(); legs.moveTo(-122, -24); legs.bezierCurveTo(-122, -62, -80, -78, -40, -74); legs.lineTo(40, -74); legs.bezierCurveTo(80, -78, 122, -62, 122, -24); legs.closePath();
  if (fill > 0) airbrush(g, legs, { base: '#c7731c', light: '#f3b54a', dark: '#5e2c06', dir: -2.2, alpha: fill });
  gline(g, [[-122, -24], [-122, -40], [-100, -66], [-40, -74], [40, -74], [100, -66], [122, -40], [122, -24], [-122, -24]], kw);
  gline(g, [[-108, -36], [-20, -50], [60, -40], [108, -34]], { ...kw, w: 1.4 });           // fold of the cloth
  gline(g, [[-118, -30], [118, -30]], { ...kw, w: 3 });                                    // gold hem
  for (const fx of [-34, 40]) { if (fill > 0) airbrush(g, ell(fx, -40, 15, 8), { base: SKIN, light: SKIN_L, dark: SKIN_D, alpha: fill }); }
  // long dark hair behind the head, falling to the shoulders
  const hair = new Path2D(); hair.moveTo(-30, -228); hair.bezierCurveTo(-44, -200, -46, -176, -60, -160); hair.lineTo(60, -160); hair.bezierCurveTo(46, -176, 44, -200, 30, -228); hair.closePath();
  if (fill > 0) airbrush(g, hair, { base: '#2a1a10', light: '#5a3a22', dark: '#0a0604', dir: -2, alpha: fill });
  // torso with the round belly
  const tor = new Path2D(); tor.moveTo(-54, -168); tor.bezierCurveTo(-58, -140, -72, -118, -70, -98); tor.bezierCurveTo(-68, -72, -36, -66, 0, -66);
  tor.bezierCurveTo(36, -66, 68, -72, 70, -98); tor.bezierCurveTo(72, -118, 58, -140, 54, -168); tor.bezierCurveTo(30, -176, -30, -176, -54, -168); tor.closePath();
  if (fill > 0) airbrush(g, tor, { base: SKIN, light: SKIN_L, dark: SKIN_D, radial: [-18, -118, 110], alpha: fill });
  gline(g, tor, kw);
  gline(g, D.arcPts(0, -96, 9, .2, Math.PI - .2, 12, 5), { ...kw, w: 1.2 });           // navel
  // sacred thread and necklaces
  gline(g, [[-46, -166], [-10, -128], [30, -92], [56, -78]], { ...kw, w: 1.3 });
  gline(g, D.arcPts(0, -170, 34, .25, Math.PI - .25, 24, 26), { ...kw, w: 2.4 });
  if (line > .7) { for (let i = 0; i <= 12; i++) { const a = lerp(.35, Math.PI - .35, i / 12); const px = Math.cos(a) * 46, py = -170 + Math.sin(a) * 58; airbrush(g, ell(px, py, 5.5, 5.5), { base: '#e8961e', light: '#ffd56a', dark: '#7a3d06', alpha: fill }); } }
  // arms
  const arm = (pts) => { if (fill > 0) { g.save(); g.globalAlpha *= fill; g.strokeStyle = SKIN; g.lineCap = 'round'; g.lineJoin = 'round'; g.lineWidth = 28; g.beginPath(); pts.forEach((q, i) => i ? g.lineTo(q[0], q[1]) : g.moveTo(q[0], q[1])); g.stroke(); g.strokeStyle = SKIN_L; g.lineWidth = 6; g.globalAlpha *= .5; g.stroke(); g.restore(); } gline(g, pts, { ...kw, w: 1.2 }); };
  arm([[-52, -158], [-84, -114], [-92, -146]]);                                        // right hand raised (viewer's left)
  arm([[54, -160], [86, -114], [74, -86]]);                                             // left hand to the pot
  const band = (ax, ay, bx, by, f) => { const x = lerp(ax, bx, f), y = lerp(ay, by, f), L = Math.hypot(bx - ax, by - ay), nx = -(by - ay) / L * 15, ny = (bx - ax) / L * 15; gline(g, [[x - nx, y - ny], [x + nx, y + ny]], { ...kw, w: 4 }); };
  band(-52, -158, -84, -114, .45); band(52, -158, 86, -114, .45); band(-84, -114, -92, -146, .8); band(86, -114, 74, -86, .75);   // armlets and bangles
  // blessing palm
  const palm = new Path2D(); palm.moveTo(-105, -146); palm.lineTo(-106, -172); palm.lineTo(-79, -172); palm.lineTo(-80, -146); palm.quadraticCurveTo(-92, -140, -105, -146); palm.closePath();
  if (fill > 0) { airbrush(g, palm, { base: SKIN, light: SKIN_L, dark: SKIN_D, alpha: fill });
    g.save(); g.globalAlpha *= fill; g.strokeStyle = SKIN; g.lineCap = 'round'; g.lineWidth = 6.5;
    for (const [fx, fh] of [[-102, 15], [-95.5, 19], [-89, 18], [-82.5, 14]]) { g.beginPath(); g.moveTo(fx, -170); g.lineTo(fx, -170 - fh); g.stroke(); }
    g.beginPath(); g.moveTo(-80, -152); g.lineTo(-72, -164); g.stroke(); g.restore(); }
  gline(g, palm, { ...kw, w: 1.2 }); if (fill > .5) { g.fillStyle = D.rgba('#c2301e', fill); g.beginPath(); g.arc(-92, -164, 3, 0, TAU); g.fill(); }
  // the pot of wealth
  const pot = new Path2D(); pot.moveTo(66, -96); pot.bezierCurveTo(46, -92, 44, -60, 60, -48); pot.lineTo(100, -48); pot.bezierCurveTo(116, -60, 114, -92, 94, -96); pot.closePath();
  if (fill > 0) { g.save(); g.globalAlpha *= fill; g.fillStyle = D.goldGrad(g, 44, -100, 116, -46, { sheen: .45 }); g.fill(pot); g.restore(); }
  gline(g, pot, kw); gline(g, [[64, -98], [96, -98]], { ...kw, w: 3 });
  if (fill > .5) for (let i = 0; i < 4; i++) { const cx = 70 + i * 7, cy = -102 - (i % 2) * 5; g.fillStyle = D.goldGrad(g, cx - 6, cy - 3, cx + 6, cy + 3, { sheen: .6 }); g.beginPath(); g.ellipse(cx, cy, 6, 3, 0, 0, TAU); g.fill(); }
  // neck and head
  if (fill > 0) airbrush(g, D.rectPts(-12, -186, 24, 20), { base: SKIN, light: SKIN_L, dark: SKIN_D, alpha: fill });
  const head = ell(0, -205, 28, 31);
  if (fill > 0) airbrush(g, head, { base: SKIN, light: SKIN_L, dark: SKIN_D, radial: [-8, -214, 40], alpha: fill });
  gline(g, head, kw);
  // serene face: lowered eyelids, brows, nose, gentle smile, tilak
  const fk = { ...kw, w: 1.4, color: '#4a2210' };
  if (fill > .3) {
    for (const sx of [-1, 1]) { gline(g, D.arcPts(sx * 11, -207, 7, .15, Math.PI - .15, 10, 3), fk); gline(g, D.arcPts(sx * 11, -214, 8, Math.PI + .3, TAU - .3, 10, 3), fk); }
    gline(g, [[0, -207], [-2, -196], [2, -195]], fk);
    gline(g, D.arcPts(0, -190, 8, .3, Math.PI - .3, 10, 4), fk);
    g.fillStyle = D.rgba('#c2301e', fill); g.fillRect(-1.6, -228, 3.2, 10);
  }
  for (const sx of [-1, 1]) { gline(g, D.arcPts(sx * 29, -196, 6, 0, TAU, 14), { ...kw, w: 2 }); }      // earrings
  // stepped crown (mukut)
  for (const sx of [-1, 1]) { const fl = [[sx * 30, -226], [sx * 40, -236], [sx * 38, -212], [sx * 30, -214]]; if (fill > 0) { g.save(); g.globalAlpha *= fill; g.fillStyle = D.goldGrad(g, -40, -240, 40, -210, { sheen: .5 }); g.fill(D.toPath(fl, true)); g.restore(); } gline(g, fl, { ...kw, closed: true, w: 1.4 }); }
  const cr = [[-31, -222], [-28, -244], [-20, -244], [-20, -262], [-10, -262], [-10, -280], [0, -300], [10, -280], [10, -262], [20, -262], [20, -244], [28, -244], [31, -222], [-31, -222]];
  if (fill > 0) { g.save(); g.globalAlpha *= fill; g.fillStyle = D.goldGrad(g, -30, -300, 30, -224, { sheen: .3 + .3 * Math.sin(t * .8) }); g.fill(D.toPath(cr, true)); g.restore(); }
  gline(g, cr, { ...kw, w: 2 });
  if (fill > .5) { airbrush(g, ell(0, -246, 6, 7), { base: C.emerald, light: C.emeraldL, dark: C.emeraldD, alpha: fill }); airbrush(g, ell(0, -272, 4, 5), { base: C.burg, light: C.burgL, dark: C.burgD, alpha: fill }); }
  g.restore();
  if (p > .95) sparkle(g, x, y - 300 * s, 22 * s * (.6 + .4 * Math.sin(t * 2.2)), { alpha: .9 });
}
