"""Score + foley + mix for the Rakesh Steels Dhanteras/Diwali film → out/mix.wav (48 kHz stereo).
Reads events.json (exported from the page) so every sound lands on its frame. Grid: 96 bpm from IGN = 8.5 s."""
import json, os, sys
import numpy as np, soundfile as sf
HERE = os.path.dirname(os.path.abspath(__file__))
LIB = os.environ.get('LIB') or os.path.expanduser('~/lemo-opuscar')
sys.path.insert(0, LIB)
from core.audio import sampler as S, pluck as P
from core.audio.sfx import SR, add, limit, lp, hp, bp, noise, brown, norm, t_, env_exp, thump, whoosh, click, ignite as sfx_ignite

S.seed(11)
EV = json.load(open(os.path.join(HERE, 'events.json')))
DUR_ALL = EV['dur']; EVA = EV['ev']
OPEN = next(e['len'] for e in EVA if e['type'] == 'open')     # the opening brand card comes before the main film
EV = [dict(e, t=e['t'] - OPEN) for e in EVA if e['t'] >= OPEN - 1e-6]
DUR = DUR_ALL - OPEN
N = int(DUR * SR) + SR
IGN, Bt = 8.5, 60 / 96
beat = lambda n: IGN + n * Bt
rng = np.random.default_rng(5)
def buf(): return np.zeros((N, 2), np.float32)
def m2(x): return x.astype(np.float32)

music, fol, amb = buf(), buf(), buf()

# ------------------------------------------------------------------ synthesised instruments
def tanpura(f0, d, v=1.0):
    """drone pluck with a buzzing bridge: harmonics that bloom upward over time (jawari)"""
    tt = t_(d); y = np.zeros_like(tt)
    for n in range(1, 24):
        bloom = np.exp(-((tt - .25 * n ** .7) ** 2) / (2 * (.5 + .05 * n) ** 2)) * .8 + .2
        y += np.sin(2 * np.pi * f0 * n * (1 + .0007 * n) * tt + n) * bloom / n ** .9
    return m2(norm(lp(y * env_exp(d, 2.6) * np.minimum(1, tt / .01), 5000)) * v)

def tabla(bol, v=1.0):
    d = .6; tt = t_(d)
    def dayan(f, tau):
        y = sum(a * np.sin(2 * np.pi * f * k * tt) * np.exp(-tt / (tau / k ** .5)) for k, a in [(1, 1), (2, .5), (3, .35), (4.1, .2)])
        return y + hp(noise(d), 3000) * np.exp(-tt / .006) * .6
    def bayan(tau=.35):
        f = 72 + 30 * (1 - np.exp(-tt / .12))          # the heel pushes the pitch up (ghe)
        return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt / tau) * 1.3
    na, tin = dayan(294, .22), dayan(294, .07)
    ka = lp(noise(d), 900) * np.exp(-tt / .025) * 1.2
    y = {'dha': na + bayan(), 'ge': bayan(), 'na': na, 'ti': tin, 'ka': ka, 'dhi': tin + bayan(), 'tin': tin, 'te': tin * .8}[bol]
    return m2(norm(y) * v)

def metal(freqs, d, taus, v=1.0, click_=.3):
    tt = t_(d); y = sum(np.sin(2 * np.pi * f * tt + i) * np.exp(-tt / tau) for i, (f, tau) in enumerate(zip(freqs, taus)))
    y = y + hp(noise(d), 4000) * np.exp(-tt / .004) * click_ * len(freqs)
    return m2(norm(y) * v)

def clink(seed, v=.6):
    r = np.random.default_rng(seed); base = 1400 + r.random() * 1400
    return metal([base, base * 2.76, base * 5.4, base * 8.9], .7, [.25, .12, .06, .03], v)

def whistle(d=.6, v=.5):
    tt = t_(d); f = 1100 + 1400 * tt / d
    y = np.sin(2 * np.pi * np.cumsum(f) / SR) * .6 + bp(noise(d), 2000, 5000) * .5
    return m2(norm(y) * np.minimum(1, tt / .05) * (1 - tt / d) * v)

def boom(v=1.0):
    d = 2.2; tt = t_(d)
    body = np.sin(2 * np.pi * 52 * tt * (1 - .2 * tt)) * np.exp(-tt / .35)
    blast = lp(noise(d), 1800) * np.exp(-tt / .18)
    cr = hp(noise(d), 2500) * (rng.random(len(tt)) > .985) * 4 * np.exp(-np.maximum(tt - .15, 0) / .6) * (tt > .15)
    return m2(norm(body + blast * .8 + lp(cr, 9000) * .5) * v)

def crackle(d, density=.997, v=.3, lo=2000):
    tt = t_(d); c = hp(noise(d), lo) * (rng.random(len(tt)) > density) * 6
    return m2(lp(c, 9000) * v)

def shimmer(d=1.2, v=.3):
    tt = t_(d); y = sum(np.sin(2 * np.pi * f * tt + f) * np.exp(-tt / (.3 + .4 * rng.random())) for f in rng.uniform(3000, 9000, 18))
    return m2(norm(y) * np.minimum(1, tt / .15) * v)

# ------------------------------------------------------------------ SCORE
ev = []   # (t, inst, pitch, dur, vel, pan[, gain])
# tanpura: Pa Sa Sa Sa (A2 D3 D3 D2) from 1.5 s, with rests in the two silences
for k in range(40):
    t0 = 1.5 + k * 1.25
    if t0 > DUR - .5: break
    if 8.0 <= t0 < 8.5 or 25.0 <= t0 < 25.6: continue
    f = [110.0, 146.83, 146.83, 73.42][k % 4]
    add(music, tanpura(f, 4.5, .16 if t0 < IGN else .2), t0, 1, [-.3, .3, .1, -.1][k % 4])

# harp glissando following the falling spark (D pentatonic, high → low, then a turn up to the wick)
PENT = [74, 76, 78, 81, 83, 86, 88, 90]               # D5 E5 F#5 A5 B5 D6 E6 F#6
gl = [90, 88, 86, 83, 81, 78, 76, 74, 71, 69, 66, 64, 62, 64, 66, 69, 71, 74, 76, 78]
for i, m in enumerate(gl): ev.append((4.6 + i * (3.3 / len(gl)), 'harp', m, 1.5, .45 + .2 * (i / len(gl)), -.4 + .8 * (i % 5) / 4))
# ignition: bell + chimes + string swell
ev += [(IGN, 'tubular_bells', 'D5', 4, .8, 0), (IGN, 'hand_chimes', 'D6', 3, .5, -.3), (IGN + .04, 'hand_chimes', 'F#6', 3, .45, .3), (IGN + .08, 'hand_chimes', 'A6', 3, .4, 0)]
for p, pan in [('D4', -.3), ('F#4', .2), ('A4', .4), ('D5', -.1)]: ev.append(dict(t=IGN, inst='violins', pitch=p, dur=6.6, vel=.42, pan=pan, attack=.9))
for p in ['D3', 'A3']: ev.append(dict(t=IGN, inst='cellos', pitch=p, dur=6.6, vel=.45, pan=0, attack=.9))
# counted light: one chime per pair of diyas, climbing
for k in range(8):
    tt = beat(3 + k); ev.append((tt, 'hand_chimes', PENT[k], 1.6, .62, -.25 + .07 * k)); ev.append((tt, 'glockenspiel', PENT[k] + 12, 1.0, .35, .25 - .07 * k))
# pizzicato bass walk under the counting
for k in range(12): ev.append((beat(2 + k * .5), 'cellos_pizz', ['D3', 'A2', 'D3', 'F#3', 'A3', 'F#3'][k % 6], .4, .5, 0))
# door: timpani hit, then a harp sweep up as it opens
ev.append((beat(11), 'timpani', 'D3', 1.5, .8, 0))
for i, m in enumerate([62, 64, 66, 69, 71, 74, 76, 78, 81, 83, 86]): ev.append((beat(11) + .05 + i * .025, 'harp', m, 1.2, .5, -.3 + .06 * i))
# rangoli theme: shamisen-with-buzz as a sitar voice (meend slides), flute answers, violins pizzicato
theme = [(12, 'A4', 1, None), (13, 'B4', .5, None), (13.5, 'A4', .5, None), (14, 'F#4', 1, [(.0, -2), (.18, 0)]), (15, 'E4', .5, None), (15.5, 'F#4', .5, None),
         (16, 'A4', 1.5, [(.0, -3), (.25, 0)]), (17.5, 'D5', .5, None), (18, 'B4', .5, None), (18.5, 'A4', .5, [(.1, 0), (.3, 2)])]
for b, p, d, bend in theme:
    kw = dict(bend=bend) if bend else {}
    add(music, m2(P.pluck('shamisen', p, d * Bt + .6, .7, buzz=.6, **kw)), beat(b), .55, -.15)
    add(music, m2(P.pluck('shamisen', p, d * Bt + .6, .35, buzz=.6, **kw)), beat(b) + .012, .25, .3)   # a sympathetic double
for b, p, d in [(16, 'D5', 1.5), (17.5, 'E5', 1), (18.5, 'F#5', 1.2)]: ev.append(dict(t=beat(b), inst='flute', pitch=p, dur=d * Bt, vel=.45, pan=.25, attack=.08))
for k in range(16): ev.append((beat(11.5 + k * .5), 'violins_pizz', ['D4', 'A4', 'F#4', 'A4'][k % 4], .3, .4, .35 if k % 2 else -.35))
# the lock
ev += [(beat(19), 'crash', None, None, .55, 0), (beat(19), 'timpani', 'D3', 2, .9, 0), (beat(19), 'tubular_bells', 'D5', 3, .7, 0), (beat(19), 'nepal_bells', None, None, .5, .3)]
for p in ['D4', 'F#4', 'A4', 'D5']: ev.append(dict(t=beat(19), inst='violins', pitch=p, dur=1.4, vel=.5, pan=0, attack=.02))
# fireworks: brass fanfare figures on the bursts, horns sustain
fan = [(20, 'D5', .33), (20.33, 'A4', .33), (20.67, 'D5', .33), (21, 'F#5', 1), (22, 'A5', .5), (22.5, 'F#5', .5), (23.5, 'D5', .33), (23.83, 'E5', .33), (24.17, 'F#5', .33),
       (24.5, 'A5', .5), (25, 'B5', .5), (25.5, 'A5', .5), (25.75, 'D6', .4)]
for b, p, d in fan: ev.append((beat(b), 'trumpet_stac', p, d * Bt, .6, .15))
for p in ['D3', 'A3']: ev.append(dict(t=beat(20), inst='horn', pitch=p, dur=beat(26.6) - beat(20), vel=.5, pan=-.2, attack=.2))
ev.append(dict(t=beat(20), inst='violins_trem', pitch='A4', dur=beat(26.6) - beat(20), vel=.35, pan=.3, attack=.3))
# final cadence
CARD = 25.6
for i, m in enumerate([62, 66, 69, 74, 78, 81, 86]): ev.append((CARD + i * .07, 'harp', m, 2.5, .55, -.4 + .13 * i))
for p, pan in [('D5', -.2), ('F#5', .2), ('A5', 0)]: ev.append(dict(t=CARD, inst='violins', pitch=p, dur=DUR - CARD, vel=.4, pan=pan, attack=1.0))
for p in ['D3', 'A3']: ev.append(dict(t=CARD, inst='cellos', pitch=p, dur=DUR - CARD, vel=.42, pan=0, attack=1.0))
for t0, p, d in [(26.1, 'A5', .9), (27.0, 'B5', .45), (27.45, 'A5', .45), (27.9, 'F#5', .9), (28.8, 'E5', .6), (29.4, 'D5', 1.6)]: ev.append(dict(t=t0, inst='flute', pitch=p, dur=d, vel=.45, pan=.15, attack=.06))
ev += [(27.6, 'tubular_bells', 'D5', 3.4, .65, 0), (27.6, 'nepal_bells', None, None, .45, -.3)]
for i, m in enumerate(PENT + [93, 95, 98]): ev.append((27.6 + i * .045, 'hand_chimes', m, 1.5, .4, -.5 + i * .09))

music += S.render(ev, dur=N / SR, master=False)[:N]
# tabla: keherwa (one cycle per bar), from the diyas to the silence; 16ths from beat 24 (acceleration)
KEH = ['dha', 'ge', 'na', 'ti', 'na', 'ka', 'dhi', 'na']
tb = buf()
for k in range(int((beat(27) - 10.0) / (Bt / 2))):
    t0 = 10.0 + k * Bt / 2
    if beat(11) - .3 < t0 < beat(11) + .3: continue
    if t0 >= 25.15: break
    bol = KEH[k % 8]; acc = 1.0 if k % 8 == 0 else .7
    add(tb, tabla(bol, acc), t0, .5, .1 if bol in ('na', 'ti', 'tin') else -.1)
    if t0 >= beat(24): add(tb, tabla('te', .5), t0 + Bt / 4, .35, .15)
music += tb
music = S.room(music, size=.5, mix=.2)

# duck the music for the two silences
g = np.ones(N, np.float32); tt = np.arange(N) / SR
for a, b, lvl in [(8.0, 8.5, .08), (25.2, 25.6, .0)]:
    g = np.minimum(g, np.interp(tt, [a - .25, a, b - .02, b], [1, lvl, lvl, 1]))
music *= g[:, None]

# ------------------------------------------------------------------ FOLEY
evs = lambda typ: [e for e in EV if e['type'] == typ]
# saw spin-up whine 0 → bite
d = .55; tq = t_(d); f = 300 + 650 * (tq / d) ** .6
add(fol, m2(norm(sum(np.sin(2 * np.pi * np.cumsum(f * k) / SR) / k for k in (1, 2, 3, 5))) * np.minimum(1, tq / .1) * .5), 0, .3)
# grind: the cut
e = evs('grind')[0]; d = e['dur'] + .15; tq = t_(d)
wh = sum(np.sin(2 * np.pi * np.cumsum(np.full(len(tq), 950 * k) + 40 * np.sin(2 * np.pi * 7 * tq)) / SR) / k for k in (1, 2, 3, 4))
scr = bp(noise(d), 2200, 7000) * (1 + .5 * np.sin(2 * np.pi * 19 * tq))
ring = sum(np.sin(2 * np.pi * fr * tq) for fr in (1230, 2710, 4120)) * .3
gr = norm(wh * .4 + scr + ring + crackle(d, .993, 2.0)) * np.minimum(1, tq / .03) * np.minimum(1, (d - tq) / .1)
add(fol, m2(gr), e['t'], .95)
add(fol, m2(thump(1, 90)), evs('bite')[0]['t'], .6); add(fol, clink(3, 1), evs('bite')[0]['t'], .5)
# metal ring as the saw leaves (runs over the pull-back: L-cut)
add(fol, metal([620, 1712, 3350, 5520], 3.5, [1.4, .9, .5, .25], 1, .5), evs('through')[0]['t'], .45)
# workshop bed 0 → 8, receding
d = 8.6; tq = t_(d); bed = lp(brown(d), 260) + np.sin(2 * np.pi * 50 * tq) * .05 + np.sin(2 * np.pi * 100 * tq) * .03
add(amb, m2(norm(bed) * np.interp(tq, [0, .3, 3.5, 8, 8.6], [0, .5, .5, .05, 0])), 0, .45)
# the spark's sizzle, panned with it
e = evs('sizzle')[0]; d = e['dur']; tq = t_(d)
sz = hp(noise(d), 3500) * (.4 + .6 * (rng.random(len(tq)) > .97)) * (.6 + .4 * np.sin(2 * np.pi * 11 * tq))
pans = evs('sparkpan'); px = np.interp(tq + e['t'], [p['t'] for p in pans], [np.clip(p['pan'], -1, 1) for p in pans])
L, R = np.cos((px + 1) * np.pi / 4), np.sin((px + 1) * np.pi / 4)
s0 = int(e['t'] * SR); sz = norm(sz) * np.minimum(1, tq / .1) * .16
fol[s0:s0 + len(sz), 0] += sz * L * 1.4; fol[s0:s0 + len(sz), 1] += sz * R * 1.4
# match + ignition whoomph
add(fol, m2(lp(noise(.25), 3000) * np.exp(-t_(.25) / .06)), evs('match')[0]['t'], .3)
add(fol, m2(lp(sfx_ignite(1), 900)), evs('ignite')[0]['t'], .55)
# each lamp: a tiny tick + puff
for e in evs('diya'):
    add(fol, m2(click(1.6, .5)), e['t'], .25, e['pan'])
    add(fol, m2(lp(noise(.3), 1400) * np.exp(-t_(.3) / .07)), e['t'] + .01, .22, e['pan'])
for typ in ('archdraw', 'titleOn', 'shimmer'):
    for e in evs(typ): add(fol, shimmer(1.4, .4), e['t'], .25)
# doors
add(fol, m2(whoosh(.45, 1)), evs('doorSwing')[0]['t'], .35)
add(fol, m2(thump(1, 70)), evs('doorShut')[0]['t'], .55); add(fol, metal([310, 860, 1700], 1.2, [.5, .3, .15], 1, .2), evs('doorShut')[0]['t'], .35)
add(fol, m2(whoosh(.5, 1)), evs('doorOpen')[0]['t'], .3)
# rangoli pieces landing (steel clinks), powder, lock
for e in evs('clink'): add(fol, clink(int(e['i'] * 7 + sum(map(ord, e['k'])) % 97), .6), e['t'] + e['i'] * .012, .28, e['pan'])
add(fol, m2(lp(noise(.9), 2500) * np.sin(np.pi * t_(.9) / .9) ** 2), evs('powder')[0]['t'], .18)
e = evs('lock')[0]; add(fol, metal([880, 1320, 2210, 3530, 5180, 7040], 2.5, [1.2, 1, .8, .6, .4, .3], 1, .6), e['t'], .4); add(fol, shimmer(2, .6), e['t'], .3)
# fireworks: crackle bed from 19.6 (J-cut), rockets, bursts
d = 25.2 - 19.6; add(amb, crackle(d, .9985, .35, 1500) * np.minimum(1, t_(d) / 1.5), 19.6, .5)
d = DUR - 25.6; add(amb, crackle(d, .9994, .2, 1500), 25.6, .4)
for e in evs('rocket'): add(fol, whistle(.6, .5), e['t'], .35, e['pan'])
for e in evs('burst'): add(fol, boom(.6 + .4 * e['r'] / 430), e['t'], .5, e['pan'] * .8)
# night air bed 10 → end
d = DUR - 9.6; tq = t_(d); add(amb, m2(norm(lp(noise(d), 700) + lp(brown(d), 200)) * np.minimum(1, tq / 1.5) * .12), 9.6, 1)
# card: reveal whoosh, brand chime and the sheen shimmer
add(fol, m2(whoosh(.8, 1)), evs('reveal')[0]['t'], .25)
add(fol, m2(thump(.6, 80)), evs('brand')[0]['t'] + .3, .3)
add(fol, shimmer(1.6, .7), evs('sheen')[0]['t'], .35)

# silence 2: kill beds briefly too
for a, b in [(25.2, 25.6)]:
    gg = np.interp(tt, [a - .1, a, b, b + .2], [1, .1, .1, 1]); amb *= gg[:, None]

# Kuber ji appears: a conch (shankh) call with temple bells
def shankh(d=1.8, v=1.0):
    tq = t_(d); f = 293.66 * (1 + .012 * np.minimum(1, tq / .5)) * (1 + .004 * np.sin(2 * np.pi * 5.5 * tq))
    ph = 2 * np.pi * np.cumsum(f) / SR
    y = sum(np.sin(k * ph) * a for k, a in [(1, 1), (2, .7), (3, .5), (4, .25), (5, .18), (6, .1)])
    y = bp(y, 250, 3200) + bp(noise(d), 600, 2500) * .08
    return m2(norm(y) * np.minimum(1, tq / .3) * np.minimum(1, (d - tq) / .5) * v)
e = evs('kuber')[0]
add(fol, shankh(1.9, 1), e['t'], .32, 0)
music += S.render([(e['t'] + .9, 'nepal_bells', None, None, .5, -.3), (e['t'] + .9, 'tubular_bells', 'A4', 3, .45, .2)], dur=N / SR, master=False)[:N] * .9
add(fol, shimmer(1.6, .6), e['t'] + .2, .25)
for e in evs('coin'): add(fol, metal([3800 + 300 * (e['i'] % 4), 6100 + 200 * (e['i'] % 3), 8700], .35, [.12, .07, .04], .5, .2), e['t'], .16, e['pan'])

out = music * .9 + fol * 1.0 + amb * .8
end = int(DUR * SR); out = out[:end]
# ---- the opening brand card (0 → OPEN), then the main film after it
o0 = int(OPEN * SR); op = np.zeros((o0 + end, 2), np.float32); op[o0:] = out
ob = np.zeros((o0 + 2 * SR, 2), np.float32)
for k, f in enumerate([73.42, 146.83, 110.0, 146.83]): add(ob, tanpura(f, 4.0, .18), .15 + k * 1.25, 1, [-.2, .2, 0, .1][k])
oe = [(.1 + i * .06, 'harp', m, 2.0, .5, -.4 + .1 * i) for i, m in enumerate([62, 66, 69, 74, 78, 81, 86, 90])]
oe += [(.75, 'tubular_bells', 'D5', 3, .7, 0), (.75, 'timpani', 'D3', 2, .55, 0), (.75, 'nepal_bells', None, None, .35, .3)]
oe += [dict(t=.75, inst='violins', pitch=p, dur=4.3, vel=.38, pan=pn, attack=.6) for p, pn in [('D4', -.3), ('A4', .3), ('F#5', 0)]]
oe += [(1.25 + i * .05, 'hand_chimes', m, 1.4, .38, -.5 + i * .1) for i, m in enumerate([74, 76, 78, 81, 83, 86, 88, 90, 93, 95])]
oe += [(2.2 + i * .05, 'hand_chimes', m, 1.4, .3, .5 - i * .1) for i, m in enumerate([86, 88, 90, 93, 95, 98])]
ob += S.room(S.render(oe, dur=len(ob) / SR, master=False)[:len(ob)], size=.5, mix=.22)
add(ob, metal([520, 1460, 2890, 4610, 6900], 2.6, [1.3, .9, .6, .4, .25], 1, .5), .75, .28)      # the steel ring as the name opens
add(ob, shimmer(1.2, .5), .1, .22); add(ob, m2(whoosh(.5, 1)), OPEN - .5, .3)
fo = np.ones(len(ob)); fo[int((OPEN - .3) * SR):] = np.linspace(1, 0, len(ob) - int((OPEN - .3) * SR)) ** 2   # tails fade under the saw
op[:len(ob)] += ob * fo[:, None]
out = op
fade = int(1.2 * SR); out[-fade:] *= (np.linspace(1, 0, fade) ** 1.5)[:, None]
out = np.stack([limit(out[:, 0], .95), limit(out[:, 1], .95)], 1)
os.makedirs(os.path.join(HERE, 'out'), exist_ok=True)
sf.write(os.path.join(HERE, 'out', 'mix.wav'), out.astype(np.float32), SR)
print('mix', out.shape[0] / SR, 's  peak', np.abs(out).max())
