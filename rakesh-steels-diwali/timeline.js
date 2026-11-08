// One timeline for picture, foley and score. Music grid: 96 bpm from IGN (beat n lands at IGN + n * B).
export const BPM = 96, B = 60 / BPM, IGN = 8.5;
export const beat = n => IGN + n * B;
export const DUR = 32.0;              // main film; the opening brand card adds OPEN seconds before it
export const OPEN = 5.5;

export const T = {
  bite: 0.5,          // saw touches the bar
  cutEnd: 3.4,        // saw through
  lift: 3.6,          // saw gone, one spark left
  sp0: 4.0, sp1: 8.0, // the spark's path
  ign: IGN,           // diya lights (after a near-silence 8.0 → 8.5)
  arch: 10.0,         // the arch draws on
  title: 10.4,        // शुभ दीपावली
  greet: 11.1,        // दीपावली की हार्दिक शुभकामनाएँ
  door: beat(11),     // 15.375: leaves meet on the seam
  open: beat(11) + .32,
  lock: beat(19),     // 20.375: the rangoli locks
  match: beat(20),    // 21.0: rangoli ring → first firework
  bless: 20.95,
  hush: 25.2,         // silence 2
  kuber: 11.6,        // Kuber ji appears in the arch
  card: 25.6,
  coins: 26.6,        // coins from Kuber ji's pot
  brand: 27.0,
  sheen: 27.6,
  contact: 27.9,
};
// 8 pairs of arch diyas, one pair per beat, from the crown outward
export const PAIRS = [3, 4, 5, 6, 7, 8, 9, 10].map(beat);
// rangoli pieces: group → landing beat
export const RANG = { spokes: beat(12), discs: beat(13), rings: beat(14), petals: beat(15), marigolds: beat(16), lotus: beat(17.5) };
// fireworks (sky coordinates; x, y, radius, launch→burst). The first one is the rangoli ring itself.
export const BURSTS = [
  { x: 540, y: 790, r: 430, t: beat(20), match: true, seed: 3, tone: 'gold' },
  { x: 270, y: 560, r: 250, t: beat(22), seed: 11, tone: 'saffron' },
  { x: 810, y: 560, r: 250, t: beat(22), seed: 12, tone: 'saffron' },
  { x: 390, y: 430, r: 210, t: beat(23.5), seed: 21, tone: 'ivory' },
  { x: 690, y: 430, r: 210, t: beat(23.5), seed: 22, tone: 'ivory' },
  { x: 540, y: 600, r: 320, t: beat(24), seed: 31, tone: 'gold' },
  { x: 230, y: 760, r: 170, t: beat(25), seed: 41, tone: 'emerald' },
  { x: 850, y: 760, r: 170, t: beat(25), seed: 42, tone: 'emerald' },
  { x: 540, y: 380, r: 200, t: beat(25.5), seed: 51, tone: 'saffron' },
  { x: 330, y: 330, r: 150, t: beat(25.75), seed: 61, tone: 'gold' },
  { x: 750, y: 330, r: 150, t: beat(25.75), seed: 62, tone: 'gold' },
];
