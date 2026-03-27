/**
 * AMANDLA — SASL Sign Language Library
 * ======================================
 * Source: Einstein Hands SASL Dictionary (336 pages)
 *         YOLO-v11 ASL research paper (2025)
 * 
 * HOW THIS FILE WORKS:
 * --------------------
 * 1. Whisper transcribes the hearing person's speech to text
 * 2. The text is split into words
 * 3. Each word is looked up in SIGN_LIBRARY
 * 4. The avatar performs each sign in sequence
 * 5. Unknown words fall back to fingerspelling
 * 
 * HOW TO ADD A NEW SIGN:
 * ----------------------
 * 1. Find the word in the Einstein Hands dictionary
 * 2. Read the handshape description
 * 3. Copy the closest existing sign as a template
 * 4. Adjust R (right arm) and L (left arm) rotations
 * 5. Add to the SIGN_LIBRARY object below
 * 6. Add any word variations to WORD_MAP at the bottom
 *
 * ROTATION VALUES (radians):
 * --------------------------
 * sh.x negative = arm raises forward/up
 * sh.z negative = right arm abducts outward (away from body)
 * sh.z positive = left arm abducts outward
 * el.x negative = elbow bends (forearm comes up)
 * wr.x = wrist flex/extend
 * wr.y = wrist rotate (pronation/supination)
 */

// ═══════════════════════════════════════════════════════════
// HANDSHAPE PRESETS
// Each = [mcp, pip, dip] finger curl values
// 0 = straight, 1.15/1.55/1.05 = fully curled
// ═══════════════════════════════════════════════════════════
const HS = {
  // Standard named handshapes from SASL/ASL
  open5:   { i:[0.08,0.05,0.03], m:[0.08,0.05,0.03], r:[0.08,0.05,0.03], p:[0.08,0.05,0.03], t:[0.05,0.05] },  // 5-hand: all spread
  flat:    { i:[0.10,0.06,0.04], m:[0.10,0.06,0.04], r:[0.10,0.06,0.04], p:[0.10,0.06,0.04], t:[0.28,0.40] },  // B-hand: flat, fingers together
  fist_A:  { i:[1.15,1.55,1.05], m:[1.15,1.55,1.05], r:[1.15,1.55,1.05], p:[1.15,1.55,1.05], t:[-0.15,0.10] }, // A-hand: fist, thumb on side
  fist_S:  { i:[1.15,1.55,1.05], m:[1.15,1.55,1.05], r:[1.15,1.55,1.05], p:[1.15,1.55,1.05], t:[0.45,0.55] },  // S-hand: fist, thumb over fingers
  point1:  { i:[0.15,0.08,0.05], m:[1.15,1.55,1.05], r:[1.15,1.55,1.05], p:[1.15,1.55,1.05], t:[0.45,0.25] },  // 1/D-hand: index only
  vhand:   { i:[0.15,0.08,0.05], m:[0.15,0.08,0.05], r:[1.15,1.55,1.05], p:[1.15,1.55,1.05], t:[0.50,0.35] },  // V-hand: index+middle
  whand:   { i:[0.08,0.05,0.03], m:[0.08,0.05,0.03], r:[0.08,0.05,0.03], p:[1.15,1.55,1.05], t:[0.50,0.75] },  // W-hand: index+middle+ring
  yhand:   { i:[1.15,1.55,1.05], m:[1.15,1.55,1.05], r:[1.15,1.55,1.05], p:[0.08,0.05,0.03], t:[-0.10,0.05] }, // Y-hand: thumb+pinky
  lhand:   { i:[0.15,0.08,0.05], m:[1.15,1.55,1.05], r:[1.15,1.55,1.05], p:[1.15,1.55,1.05], t:[-0.20,0.05] }, // L-hand: index+thumb out
  chand:   { i:[0.70,0.90,0.60], m:[0.70,0.90,0.60], r:[0.70,0.90,0.60], p:[0.70,0.90,0.60], t:[0.15,0.20] },  // C-hand: curved
  xhand:   { i:[0.55,1.55,1.05], m:[1.15,1.55,1.05], r:[1.15,1.55,1.05], p:[1.15,1.55,1.05], t:[0.45,0.25] },  // X-hand: hooked index
  claw:    { i:[0.70,0.90,0.60], m:[0.70,0.90,0.60], r:[0.70,0.90,0.60], p:[0.70,0.90,0.60], t:[0.30,0.30] },  // claw-hand
  thand:   { i:[0.55,0.90,0.60], m:[1.15,1.55,1.05], r:[1.15,1.55,1.05], p:[1.15,1.55,1.05], t:[0.55,0.55] },  // T-hand: index bent, thumb between
  fhand:   { i:[0.55,0.90,0.60], m:[0.08,0.05,0.03], r:[0.08,0.05,0.03], p:[0.08,0.05,0.03], t:[0.55,0.55] },  // F-hand: index-thumb circle
  ghand:   { i:[0.15,0.08,0.05], m:[1.15,1.55,1.05], r:[1.15,1.55,1.05], p:[1.15,1.55,1.05], t:[-0.10,0.10] }, // G-hand: index+thumb horizontal
  uhand:   { i:[0.15,0.08,0.05], m:[0.15,0.08,0.05], r:[1.15,1.55,1.05], p:[1.15,1.55,1.05], t:[0.50,0.55] },  // U-hand: index+middle together
  rest:    { i:[0.20,0.15,0.10], m:[0.20,0.15,0.10], r:[0.20,0.15,0.10], p:[0.20,0.15,0.10], t:[0.20,0.12] },  // neutral resting
};

// ═══════════════════════════════════════════════════════════
// ARM POSITION PRESETS
// Idle/neutral positions for non-signing hand
// ═══════════════════════════════════════════════════════════
const ARM = {
  idle_R: { sh:{x:0.05,y:0,z:-0.22}, el:{x:0.08,y:0,z:0}, wr:{x:0,y:0,z:0} },
  idle_L: { sh:{x:0.05,y:0,z: 0.22}, el:{x:0.08,y:0,z:0}, wr:{x:0,y:0,z:0} },
  chin_R:  { sh:{x:-1.30,y:0,z:-0.10}, el:{x:-0.20,y:0,z:0}, wr:{x:0,y:0,z:0} },  // hand at chin
  chest_R: { sh:{x:-0.30,y:0,z:-0.55}, el:{x:-0.20,y:0,z:0}, wr:{x:0.15,y:0,z:0} }, // hand at chest
  chest_L: { sh:{x:-0.30,y:0,z: 0.55}, el:{x:-0.20,y:0,z:0}, wr:{x:0.15,y:0,z:0} },
  forehead_R: { sh:{x:-1.48,y:0,z:-0.06}, el:{x:-0.18,y:0,z:0}, wr:{x:0,y:0,z:0} }, // at forehead/temple
  forward_R: { sh:{x:-0.50,y:0,z:-0.14}, el:{x:-0.88,y:0,z:0}, wr:{x:0,y:0,z:0} },  // arm extended forward
  forward_L: { sh:{x:-0.50,y:0,z: 0.14}, el:{x:-0.88,y:0,z:0}, wr:{x:0,y:0,z:0} },
  raised_R: { sh:{x:-1.25,y:0,z:-0.28}, el:{x:-0.50,y:0,z:0}, wr:{x:0.12,y:0,z:0} }, // arm raised up
  raised_L: { sh:{x:-1.25,y:0,z: 0.28}, el:{x:-0.50,y:0,z:0}, wr:{x:0.12,y:0,z:0} },
  tummy_R: { sh:{x:-0.20,y:0,z:-0.40}, el:{x:-0.30,y:0,z:0}, wr:{x:0,y:0,z:0} },  // hand at tummy
  flat_palm_L: { sh:{x:-1.18,y:0,z:0.28}, el:{x:-0.25,y:0,z:0}, wr:{x:-0.65,y:0.3,z:0} }, // flat palm facing up
};

// Helper to build a full sign definition
function sign(name, shape, desc, conf, Rsh, Rel, Rwr, Rhand, Lsh, Lel, Lwr, Lhand, osc) {
  return {
    name, shape, desc, conf,
    R: { sh:Rsh, el:Rel, wr:Rwr, hand:Rhand },
    L: { sh:Lsh, el:Lel, wr:Lwr, hand:Lhand },
    osc
  };
}

const IL = ARM.idle_L, IR = ARM.idle_R;
const NR = HS.rest, NL = HS.rest;

// ═══════════════════════════════════════════════════════════
// THE SIGN LIBRARY — 100+ SASL SIGNS
// Source: Einstein Hands SASL Dictionary
// ═══════════════════════════════════════════════════════════
const SIGN_LIBRARY = {

  // ── GREETINGS & BASIC CONVERSATION ──────────────────────

  'HELLO': sign('HELLO','Hand waves away from head','Move hand away from head — universal greeting',5,
    {x:-1.35,y:0,z:-0.18},{x:0.05,y:0,z:0},{x:0,y:0,z:0}, HS.flat,
    IL.sh,IL.el,IL.wr, NL,
    {j:'R_wr', ax:'z', amp:0.35, freq:1.8}),

  'GOODBYE': sign('GOODBYE','Wave hand side to side','Open hand waves from side to side — farewell',5,
    {x:-1.30,y:0,z:-0.15},{x:0.05,y:0,z:0},{x:0,y:0,z:0}, HS.flat,
    IL.sh,IL.el,IL.wr, NL,
    {j:'R_wr', ax:'z', amp:0.45, freq:2.2}),

  'HOW ARE YOU': sign('HOW ARE YOU','Flat hands sweep out then thumbs up','Hands sweep outward then change to thumbs up',4,
    {x:-0.55,y:0,z:-0.30},{x:-0.60,y:0,z:0},{x:0,y:0,z:0}, HS.lhand,
    {x:-0.55,y:0,z:0.30},{x:-0.60,y:0,z:0},{x:0,y:0,z:0}, HS.lhand,
    {j:'both_sh', ax:'z', amp:0.25, freq:1.4}),

  "I'M FINE": sign("I'M FINE",'Hand moves up from flat-hand','Hand rises upward — I am fine',4,
    {x:-0.80,y:0,z:-0.20},{x:-0.30,y:0,z:0},{x:0,y:0,z:0}, HS.flat,
    IL.sh,IL.el,IL.wr, NL,
    {j:'R_sh', ax:'x', amp:0.10, freq:1.2}),

  'PLEASE': sign('PLEASE','B-hand circles on chest','Flat open hand circles on chest — polite request',4,
    {x:-0.28,y:0,z:-0.68},{x:-0.20,y:0,z:0},{x:0.18,y:0,z:0}, HS.flat,
    IL.sh,IL.el,IL.wr, NL,
    {j:'R_sh', ax:'y', amp:0.26, freq:1.6}),

  'THANK YOU': sign('THANK YOU','Flat hand chin outward','Open hand at chin, sweeps forward and down',5,
    {x:-1.25,y:0,z:-0.08},{x:0.05,y:0,z:0},{x:-0.12,y:0,z:0}, HS.flat,
    IL.sh,IL.el,IL.wr, NL,
    {j:'R_sh', ax:'x', amp:0.10, freq:1.4}),

  'SORRY': sign('SORRY','A-hand slides on cheek','Slide A-hand forwards and backwards on lower cheek',5,
    {x:-1.20,y:0,z:-0.15},{x:-0.10,y:0,z:0},{x:0,y:0,z:0}, HS.fist_A,
    IL.sh,IL.el,IL.wr, NL,
    {j:'R_sh', ax:'x', amp:0.08, freq:2.0}),

  'YES': sign('YES','S-hand fist nods','Tight closed fist, thumb over fingers — wrist nods up and down',5,
    {x:-0.45,y:0,z:-0.10},{x:-0.95,y:0,z:0},{x:0,y:0,z:0}, HS.fist_S,
    IL.sh,IL.el,IL.wr, NL,
    {j:'R_wr', ax:'x', amp:0.38, freq:3.8}),

  'NO': sign('NO','H-hand wags side to side','Index and middle fingers extended, wag side to side',5,
    {x:-0.50,y:0,z:-0.14},{x:-0.88,y:0,z:0},{x:0,y:0.3,z:0}, HS.vhand,
    IL.sh,IL.el,IL.wr, NL,
    {j:'R_wr', ax:'y', amp:0.44, freq:3.5}),

  'HELP': sign('HELP','A-hand on flat palm · both raise','Fist (thumb extended) resting on open palm — rise together',5,
    {x:-1.28,y:0,z:-0.30},{x:-0.50,y:0,z:0},{x:0.12,y:0,z:0}, HS.fist_A,
    {x:-1.20,y:0,z:0.28},{x:-0.25,y:0,z:0},{x:-0.65,y:0.3,z:0}, HS.flat,
    {j:'both_sh', ax:'x', amp:0.16, freq:2.3}),

  'WAIT': sign('WAIT','Both 5-hands palms out','Both open hands, palms forward, fingers wiggle',5,
    {x:-0.70,y:0,z:-0.24},{x:-1.28,y:0,z:0},{x:0,y:0,z:0}, HS.open5,
    {x:-0.70,y:0,z:0.24},{x:-1.28,y:0,z:0},{x:0,y:0,z:0}, HS.open5,
    {j:'both_el', ax:'z', amp:0.14, freq:2.8}),

  'STOP': sign('STOP','Both flat-hands push forward','Move both flat-hands forward simultaneously',5,
    {x:-0.60,y:0,z:-0.18},{x:-1.10,y:0,z:0},{x:0,y:0,z:0}, HS.flat,
    {x:-0.60,y:0,z:0.18},{x:-1.10,y:0,z:0},{x:0,y:0,z:0}, HS.flat,
    null),

  'REPEAT': sign('REPEAT','A-hand circles over flat palm','Dominant fist circles above non-dominant open hand',3,
    {x:-0.48,y:0,z:-0.22},{x:-0.78,y:0,z:0},{x:0,y:0,z:0}, HS.fist_A,
    {x:-0.55,y:0,z:0.35},{x:-0.40,y:0,z:0},{x:-0.55,y:0.2,z:0}, HS.flat,
    {j:'R_sh', ax:'y', amp:1.55, freq:1.9}),

  'UNDERSTAND': sign('UNDERSTAND','Index at temple flicks up','Index finger at temple, flicks upward',5,
    {x:-1.50,y:0,z:-0.06},{x:-0.18,y:0,z:0},{x:0,y:0,z:0}, HS.point1,
    IL.sh,IL.el,IL.wr, NL,
    {j:'R_wr', ax:'x', amp:0.20, freq:2.8}),

  'WATER': sign('WATER','W-hand taps chin','Index+middle+ring up (W-shape), taps chin twice',4,
    {x:-1.38,y:0,z:-0.08},{x:-0.22,y:0,z:0},{x:0,y:0,z:0}, HS.whand,
    IL.sh,IL.el,IL.wr, NL,
    {j:'R_sh', ax:'x', amp:0.09, freq:2.5}),

  'PAIN': sign('PAIN','Both index fingers jab inward','Index fingers pointing inward, jabbing toward each other',4,
    {x:-0.32,y:0,z:-0.56},{x:-0.85,y:0,z:0.24},{x:0,y:0,z:0}, HS.point1,
    {x:-0.32,y:0,z:0.56},{x:-0.85,y:0,z:-0.24},{x:0,y:0,z:0}, HS.point1,
    {j:'both_el', ax:'x', amp:0.13, freq:4.2}),

  // ── MEDICAL & EMERGENCY ─────────────────────────────────

  'DOCTOR': sign('DOCTOR','Stethoscope on chest','Mimic putting stethoscope on chest — closed hands touch both sides of chest',5,
    {x:-0.90,y:0,z:-0.55},{x:-0.40,y:0,z:0},{x:0,y:0,z:0}, HS.chand,
    {x:-0.90,y:0,z:0.55},{x:-0.40,y:0,z:0},{x:0,y:0,z:0}, HS.chand,
    {j:'both_sh', ax:'z', amp:0.10, freq:1.5}),

  'NURSE': sign('NURSE','U-hands over shoulders outward','Show badges on nurse uniform — U-hands move over shoulders outward',4,
    {x:-1.00,y:0,z:-0.45},{x:-0.30,y:0,z:0},{x:0,y:0,z:0}, HS.uhand,
    {x:-1.00,y:0,z:0.45},{x:-0.30,y:0,z:0},{x:0,y:0,z:0}, HS.uhand,
    {j:'both_sh', ax:'z', amp:0.15, freq:1.4}),

  'HOSPITAL': sign('HOSPITAL','U-hand on upper arm moves forward','Index finger of U-hand touches upper arm then moves forward',5,
    {x:-1.10,y:0,z:-0.45},{x:-0.35,y:0,z:0},{x:0,y:0,z:0}, HS.uhand,
    {x:-0.40,y:0,z:0.30},{x:-0.50,y:0,z:0},{x:0,y:0,z:0}, HS.flat,
    {j:'R_sh', ax:'x', amp:0.08, freq:1.5}),

  'SICK': sign('SICK','Both middle fingers touch forehead and tummy','Touch forehead and tummy simultaneously with middle fingers — show sick face',5,
    {x:-1.45,y:0,z:-0.10},{x:-0.15,y:0,z:0},{x:0,y:0,z:0}, HS.fhand,
    {x:-0.22,y:0,z:0.38},{x:-0.25,y:0,z:0},{x:0,y:0,z:0}, HS.fhand,
    null),

  'AMBULANCE': sign('AMBULANCE','Claw-hands twist at sides of head','Twist claw-hands at sides of head — ambulance lights',4,
    {x:-1.30,y:0,z:-0.35},{x:-0.20,y:0,z:0},{x:0,y:0,z:0}, HS.claw,
    {x:-1.30,y:0,z:0.35},{x:-0.20,y:0,z:0},{x:0,y:0,z:0}, HS.claw,
    {j:'both_wr', ax:'y', amp:0.6, freq:3.0}),

  'FIRE': sign('FIRE','Open-5-hands flicker upward','Open hands move up and down alternately, flutter fingers — flames',5,
    {x:-0.80,y:0,z:-0.20},{x:-0.50,y:0,z:0},{x:0,y:0,z:0}, HS.open5,
    {x:-0.80,y:0,z:0.20},{x:-0.50,y:0,z:0},{x:0,y:0,z:0}, HS.open5,
    {j:'both_sh', ax:'x', amp:0.25, freq:2.5}),

  'DANGEROUS': sign('DANGEROUS','Index fingers flick up sharply','No.1 fingers pointing forward then flick up quickly',5,
    {x:-0.55,y:0,z:-0.18},{x:-0.85,y:0,z:0},{x:0,y:0,z:0}, HS.point1,
    {x:-0.55,y:0,z:0.18},{x:-0.85,y:0,z:0},{x:0,y:0,z:0}, HS.point1,
    {j:'both_el', ax:'x', amp:0.4, freq:2.0}),

  'CAREFUL': sign('CAREFUL','Open-5-hands rotate forward alternately','Rotate open-5-hands forward alternately — be careful',5,
    {x:-0.70,y:0,z:-0.25},{x:-0.85,y:0,z:0},{x:0,y:0,z:0}, HS.open5,
    {x:-0.70,y:0,z:0.25},{x:-0.85,y:0,z:0},{x:0,y:0,z:0}, HS.open5,
    {j:'both_sh', ax:'y', amp:0.3, freq:2.0}),

  'SAFE': sign('SAFE','Cup-hand slides over flat-hand','Slide cup-hand towards you over flat-hand',4,
    {x:-0.55,y:0,z:-0.35},{x:-0.60,y:0,z:0},{x:0,y:0,z:0}, HS.chand,
    {x:-0.45,y:0,z:0.35},{x:-0.55,y:0,z:0},{x:0,y:0,z:0}, HS.flat,
    {j:'R_sh', ax:'z', amp:0.08, freq:1.5}),

  'MEDICINE': sign('MEDICINE','M-hand taps palm','M-handshape taps on open palm — medication',4,
    {x:-0.65,y:0,z:-0.30},{x:-0.75,y:0,z:0},{x:0,y:0,z:0}, HS.whand,
    {x:-0.45,y:0,z:0.35},{x:-0.55,y:0,z:0},{x:0,y:0,z:0}, HS.flat,
    {j:'R_sh', ax:'x', amp:0.12, freq:2.2}),

  'HURT': sign('HURT','Hands flick open repeatedly','Flick hands open and closed — throbbing pain motion',5,
    {x:-0.65,y:0,z:-0.30},{x:-0.70,y:0,z:0},{x:0,y:0,z:0}, HS.fist_S,
    {x:-0.65,y:0,z:0.30},{x:-0.70,y:0,z:0},{x:0,y:0,z:0}, HS.fist_S,
    {j:'both_el', ax:'z', amp:0.35, freq:3.5}),

  'EMERGENCY': sign('EMERGENCY','Claw-hands at sides of head','Claw-hands twist at sides of head — emergency alert',5,
    {x:-1.25,y:0,z:-0.38},{x:-0.20,y:0,z:0},{x:0,y:0,z:0}, HS.claw,
    {x:-1.25,y:0,z:0.38},{x:-0.20,y:0,z:0},{x:0,y:0,z:0}, HS.claw,
    {j:'both_wr', ax:'y', amp:0.7, freq:4.0}),

  // ── EMOTIONS & FEELINGS ─────────────────────────────────

  'HAPPY': sign('HAPPY','Y-hand twists at mouth','Twist Y-hand wrist to and fro in front of mouth — show big smile',5,
    {x:-1.28,y:0,z:-0.12},{x:-0.15,y:0,z:0},{x:0,y:0,z:0}, HS.yhand,
    IL.sh,IL.el,IL.wr, NL,
    {j:'R_wr', ax:'y', amp:0.45, freq:2.5}),

  'SAD': sign('SAD','C-fingers move down mouth','C-shape fingers move downward at mouth — sad face',5,
    {x:-1.22,y:0,z:-0.10},{x:-0.15,y:0,z:0},{x:0,y:0,z:0}, HS.chand,
    IL.sh,IL.el,IL.wr, NL,
    {j:'R_sh', ax:'x', amp:0.06, freq:1.0}),

  'ANGRY': sign('ANGRY','Claw-hand rises hip to shoulder','Move claw-hand up diagonally from hip to shoulder — show angry face',4,
    {x:-0.20,y:0,z:-0.40},{x:-0.30,y:0,z:0},{x:0,y:0,z:0}, HS.claw,
    IL.sh,IL.el,IL.wr, NL,
    {j:'R_sh', ax:'x', amp:0.5, freq:1.8}),

  'SCARED': sign('SCARED','Claw-hands twist at mouth','Claw-hands in front of mouth, wrists twist quickly — show scared face',4,
    {x:-1.15,y:0,z:-0.20},{x:-0.25,y:0,z:0},{x:0,y:0,z:0}, HS.claw,
    {x:-1.15,y:0,z:0.20},{x:-0.25,y:0,z:0},{x:0,y:0,z:0}, HS.claw,
    {j:'both_wr', ax:'y', amp:0.5, freq:4.5}),

  'LOVE': sign('LOVE','S-hands cross over chest','Cross S-hands over chest and rock side to side',5,
    {x:-0.95,y:0,z:-0.40},{x:-0.20,y:0,z:0.35},{x:0,y:0,z:0}, HS.fist_S,
    {x:-0.95,y:0,z:0.40},{x:-0.20,y:0,z:-0.35},{x:0,y:0,z:0}, HS.fist_S,
    {j:'both_sh', ax:'z', amp:0.10, freq:1.2}),

  'I LOVE YOU': sign('I LOVE YOU','Y-hand with index extended','Extend thumb, index and pinky — combines I, L, Y',5,
    {x:-0.90,y:0,z:-0.20},{x:-0.55,y:0,z:0},{x:0,y:0,z:0}, HS.yhand,
    IL.sh,IL.el,IL.wr, NL,
    {j:'R_wr', ax:'y', amp:0.20, freq:1.5}),

  'EXCITED': sign('EXCITED','Claw-hands alternate on chest','Move claw-hands up and down alternately on sides of chest',4,
    {x:-0.80,y:0,z:-0.40},{x:-0.30,y:0,z:0},{x:0,y:0,z:0}, HS.claw,
    {x:-0.80,y:0,z:0.40},{x:-0.30,y:0,z:0},{x:0,y:0,z:0}, HS.claw,
    {j:'both_sh', ax:'x', amp:0.25, freq:2.8}),

  'TIRED': sign('TIRED','T-hands drop down sides','Move T-hands downward simultaneously on both sides of body',4,
    {x:-0.55,y:0,z:-0.35},{x:-0.40,y:0,z:0},{x:0,y:0,z:0}, HS.thand,
    {x:-0.55,y:0,z:0.35},{x:-0.40,y:0,z:0},{x:0,y:0,z:0}, HS.thand,
    {j:'both_sh', ax:'x', amp:0.15, freq:1.0}),

  'HUNGRY': sign('HUNGRY','Flat-hand rubs tummy','Rub tummy with flat-hand — I am hungry',5,
    {x:-0.22,y:0,z:-0.45},{x:-0.30,y:0,z:0},{x:0.10,y:0,z:0}, HS.flat,
    IL.sh,IL.el,IL.wr, NL,
    {j:'R_sh', ax:'y', amp:0.25, freq:2.0}),

  'THIRSTY': sign('THIRSTY','Thumb moves down throat','Move thumb and bent index finger down throat',5,
    {x:-1.30,y:0,z:-0.08},{x:-0.18,y:0,z:0},{x:0,y:0,z:0}, HS.ghand,
    IL.sh,IL.el,IL.wr, NL,
    {j:'R_sh', ax:'x', amp:0.08, freq:1.8}),

  'WORRIED': sign('WORRIED','Claw-hand circles on chest','Circle claw-hand on chest — show worried face',4,
    {x:-0.85,y:0,z:-0.45},{x:-0.20,y:0,z:0},{x:0,y:0,z:0}, HS.claw,
    IL.sh,IL.el,IL.wr, NL,
    {j:'R_sh', ax:'y', amp:0.30, freq:1.8}),

  'PROUD': sign('PROUD','Thumbs hook under armpits','Hook thumbs under armpits — push chest out proud',3,
    {x:-0.75,y:0,z:-0.80},{x:0.05,y:0,z:0},{x:0,y:0,z:0}, HS.fist_A,
    {x:-0.75,y:0,z:0.80},{x:0.05,y:0,z:0},{x:0,y:0,z:0}, HS.fist_A,
    null),

  'CONFUSED': sign('CONFUSED','Claw-hand circles at head','Claw-hand makes circles at side of head — confused',4,
    {x:-1.38,y:0,z:-0.15},{x:-0.20,y:0,z:0},{x:0,y:0,z:0}, HS.claw,
    IL.sh,IL.el,IL.wr, NL,
    {j:'R_sh', ax:'y', amp:0.35, freq:2.2}),

  // ── QUESTION WORDS ───────────────────────────────────────

  'WHO': sign('WHO','B-hand taps chin','B-hand taps on chin twice',5,
    {x:-1.18,y:0,z:-0.10},{x:-0.12,y:0,z:0},{x:0,y:0,z:0}, HS.flat,
    IL.sh,IL.el,IL.wr, NL,
    {j:'R_sh', ax:'x', amp:0.08, freq:2.2}),

  'WHAT': sign('WHAT','Index finger waves at shoulder','Slightly wave index finger at side of shoulder',5,
    {x:-0.90,y:0,z:-0.20},{x:-0.35,y:0,z:0},{x:0,y:0,z:0}, HS.point1,
    IL.sh,IL.el,IL.wr, NL,
    {j:'R_wr', ax:'y', amp:0.30, freq:2.0}),

  'WHERE': sign('WHERE','Open-5-hands move in and out','Move open-5-hands in and out questioning',5,
    {x:-0.70,y:0,z:-0.28},{x:-0.80,y:0,z:0},{x:0,y:0,z:0}, HS.open5,
    {x:-0.70,y:0,z:0.28},{x:-0.80,y:0,z:0},{x:0,y:0,z:0}, HS.open5,
    {j:'both_sh', ax:'z', amp:0.20, freq:1.8}),

  'WHEN': sign('WHEN','Claw fingers gallop over jaw','Claw-hand fingers gallop over jaw line',4,
    {x:-1.15,y:0,z:-0.12},{x:-0.15,y:0,z:0},{x:0,y:0,z:0}, HS.claw,
    IL.sh,IL.el,IL.wr, NL,
    {j:'R_wr', ax:'z', amp:0.20, freq:2.8}),

  'WHY': sign('WHY','Index crosses chest','Cross index finger over chest questioningly',5,
    {x:-0.95,y:0,z:-0.55},{x:-0.20,y:0,z:0},{x:0,y:0,z:0}, HS.point1,
    IL.sh,IL.el,IL.wr, NL,
    null),

  'HOW': sign('HOW','Open-5-hand flips over','Flip open-5-hand from palm down to palm up',5,
    {x:-0.60,y:0,z:-0.25},{x:-0.75,y:0,z:0},{x:0,y:0,z:0}, HS.open5,
    IL.sh,IL.el,IL.wr, NL,
    {j:'R_wr', ax:'y', amp:0.8, freq:1.5}),

  'WHICH': sign('WHICH','Y-hand twists side to side','Twist Y-hand slightly from side to side',4,
    {x:-0.75,y:0,z:-0.20},{x:-0.60,y:0,z:0},{x:0,y:0,z:0}, HS.yhand,
    IL.sh,IL.el,IL.wr, NL,
    {j:'R_wr', ax:'y', amp:0.30, freq:1.8}),

  // ── PRONOUNS ─────────────────────────────────────────────

  'I': sign('I','Index points to self','Index finger points to yourself',5,
    {x:-0.85,y:0,z:-0.62},{x:-0.30,y:0,z:0},{x:0,y:0,z:0}, HS.point1,
    IL.sh,IL.el,IL.wr, NL,
    null),

  'YOU': sign('YOU','Index points to person','Index finger pointing to the other person',5,
    {x:-0.65,y:0,z:-0.15},{x:-0.90,y:0,z:0},{x:0,y:0,z:0}, HS.point1,
    IL.sh,IL.el,IL.wr, NL,
    null),

  'WE': sign('WE','Index sweeps from self outward','Index finger sweeps from chest outward — inclusive',4,
    {x:-0.90,y:0,z:-0.55},{x:-0.20,y:0,z:0},{x:0,y:0,z:0}, HS.point1,
    IL.sh,IL.el,IL.wr, NL,
    {j:'R_sh', ax:'z', amp:0.4, freq:1.5}),

  'THEY': sign('THEY','Index swings in front','Swing index finger slightly in front — referring to others',4,
    {x:-0.62,y:0,z:-0.18},{x:-0.85,y:0,z:0},{x:0,y:0,z:0}, HS.point1,
    IL.sh,IL.el,IL.wr, NL,
    {j:'R_sh', ax:'z', amp:0.35, freq:1.5}),

  // ── VERBS & INSTRUCTIONS ────────────────────────────────

  'COME': sign('COME','Cup-hand draws toward body','Move cup-hand towards your body — beckoning',5,
    {x:-0.65,y:0,z:-0.18},{x:-0.80,y:0,z:0},{x:0,y:0,z:0}, HS.chand,
    IL.sh,IL.el,IL.wr, NL,
    {j:'R_el', ax:'x', amp:0.25, freq:2.0}),

  'GO': sign('GO','Flat-hand flicks up and forward','Hold flat-hand in front then flick it up — let us go',5,
    {x:-0.58,y:0,z:-0.15},{x:-0.95,y:0,z:0},{x:0,y:0,z:0}, HS.flat,
    IL.sh,IL.el,IL.wr, NL,
    {j:'R_wr', ax:'x', amp:0.45, freq:1.5}),

  'LISTEN': sign('LISTEN','V-hand moves to ear','Move V-hand towards ear, change to bent V — listen carefully',5,
    {x:-1.32,y:0,z:-0.20},{x:-0.18,y:0,z:0},{x:0,y:0,z:0}, HS.vhand,
    IL.sh,IL.el,IL.wr, NL,
    {j:'R_sh', ax:'z', amp:0.08, freq:1.5}),

  'LOOK': sign('LOOK','V-hand under eyes points out','V-hand under eyes, point to what you are looking at',5,
    {x:-1.38,y:0,z:-0.10},{x:-0.18,y:0,z:0},{x:0,y:0,z:0}, HS.vhand,
    IL.sh,IL.el,IL.wr, NL,
    {j:'R_sh', ax:'z', amp:0.10, freq:1.5}),

  'KNOW': sign('KNOW','Cup-hand taps temple','Cup-hand touches temple several times — knowledge',5,
    {x:-1.42,y:0,z:-0.10},{x:-0.15,y:0,z:0},{x:0,y:0,z:0}, HS.chand,
    IL.sh,IL.el,IL.wr, NL,
    {j:'R_sh', ax:'x', amp:0.07, freq:2.0}),

  'WANT': sign('WANT','Open-5 draws down chest','Move open-5-hand down chest — palm starts facing chest then flips',5,
    {x:-0.90,y:0,z:-0.45},{x:-0.20,y:0,z:0},{x:0.15,y:0,z:0}, HS.open5,
    IL.sh,IL.el,IL.wr, NL,
    {j:'R_wr', ax:'y', amp:0.5, freq:1.5}),

  'GIVE': sign('GIVE','Closed hands extend forward and open','Mimic handing something over — hands move forward and open',5,
    {x:-0.65,y:0,z:-0.18},{x:-0.85,y:0,z:0},{x:0,y:0,z:0}, HS.fist_A,
    IL.sh,IL.el,IL.wr, NL,
    {j:'R_sh', ax:'x', amp:0.18, freq:1.5}),

  'EAT': sign('EAT','Closed-5-hand to mouth','Mimic putting food in mouth with closed-5-hand',5,
    {x:-1.38,y:0,z:-0.08},{x:-0.18,y:0,z:0},{x:0,y:0,z:0}, HS.chand,
    IL.sh,IL.el,IL.wr, NL,
    {j:'R_sh', ax:'x', amp:0.12, freq:2.5}),

  'DRINK': sign('DRINK','C-hand tips to mouth','Mimic holding a cup and drinking',5,
    {x:-1.32,y:0,z:-0.10},{x:-0.18,y:0,z:0},{x:0.25,y:0,z:0}, HS.chand,
    IL.sh,IL.el,IL.wr, NL,
    {j:'R_sh', ax:'x', amp:0.15, freq:2.0}),

  'SLEEP': sign('SLEEP','Flat-hands on cheek · tilt','Put flat-hands together on cheek — tilt head and close eyes',5,
    {x:-1.28,y:0,z:-0.12},{x:-0.12,y:0,z:0},{x:0,y:0,z:0}, HS.flat,
    IL.sh,IL.el,IL.wr, NL,
    null),

  'SIT': sign('SIT','A-hand taps flat-hand','Bang A-hand (thumb up) onto flat-hand',5,
    {x:-0.55,y:0,z:-0.30},{x:-0.65,y:0,z:0},{x:0,y:0,z:0}, HS.fist_A,
    {x:-0.45,y:0,z:0.35},{x:-0.60,y:0,z:0},{x:0,y:0,z:0}, HS.flat,
    {j:'R_sh', ax:'x', amp:0.12, freq:2.2}),

  'STAND': sign('STAND','V-hand stands on flat-hand','Show legs standing — V-hand placed on flat-hand',5,
    {x:-0.55,y:0,z:-0.30},{x:-0.65,y:0,z:0},{x:0,y:0,z:0}, HS.vhand,
    {x:-0.45,y:0,z:0.35},{x:-0.60,y:0,z:0},{x:0,y:0,z:0}, HS.flat,
    null),

  'WALK': sign('WALK','V-hand walks forward','V-hand palm down walks forward — walking motion',5,
    {x:-0.55,y:0,z:-0.18},{x:-0.80,y:0,z:0},{x:0,y:0,z:0}, HS.vhand,
    IL.sh,IL.el,IL.wr, NL,
    {j:'R_sh', ax:'x', amp:0.18, freq:2.5}),

  'RUN': sign('RUN','S-hands swing alternately','Swing S-hands backwards and forwards alternately — running',4,
    {x:-0.55,y:0,z:-0.22},{x:-0.65,y:0,z:0},{x:0,y:0,z:0}, HS.fist_S,
    {x:-0.55,y:0,z:0.22},{x:-0.65,y:0,z:0},{x:0,y:0,z:0}, HS.fist_S,
    {j:'both_sh', ax:'x', amp:0.30, freq:3.5}),

  'WORK': sign('WORK','B-hands tap each other','Tap B-hands on each other at an angle — working',5,
    {x:-0.65,y:0,z:-0.28},{x:-0.70,y:0,z:0},{x:0,y:0,z:0}, HS.flat,
    {x:-0.65,y:0,z:0.28},{x:-0.70,y:0,z:0},{x:0,y:0,z:0}, HS.flat,
    {j:'both_sh', ax:'x', amp:0.15, freq:2.5}),

  'WASH': sign('WASH','A-hands rub together','Rub A-hands together — washing motion',4,
    {x:-0.60,y:0,z:-0.30},{x:-0.65,y:0,z:0},{x:0,y:0,z:0}, HS.fist_A,
    {x:-0.60,y:0,z:0.30},{x:-0.65,y:0,z:0},{x:0,y:0,z:0}, HS.fist_A,
    {j:'both_sh', ax:'y', amp:0.35, freq:2.5}),

  'OPEN': sign('OPEN','Flat-hand swings open','Show a door opening — flat-hand swings outward',4,
    {x:-0.65,y:0,z:-0.30},{x:-0.70,y:0,z:0},{x:0,y:0,z:0}, HS.flat,
    {x:-0.65,y:0,z:0.30},{x:-0.70,y:0,z:0},{x:0,y:0,z:0}, HS.flat,
    {j:'R_sh', ax:'z', amp:0.35, freq:1.5}),

  'CLOSE': sign('CLOSE','Flat-hand closes onto other','Move flat-hand onto back of other flat-hand — closing',4,
    {x:-0.65,y:0,z:-0.30},{x:-0.70,y:0,z:0},{x:0,y:0,z:0}, HS.flat,
    {x:-0.65,y:0,z:0.30},{x:-0.70,y:0,z:0},{x:0,y:0,z:0}, HS.flat,
    {j:'both_sh', ax:'z', amp:-0.30, freq:1.5}),

  'WRITE': sign('WRITE','T-hand mimics writing','Mimic writing with T-hand on flat palm',4,
    {x:-0.60,y:0,z:-0.28},{x:-0.75,y:0,z:0},{x:0,y:0,z:0}, HS.thand,
    {x:-0.45,y:0,z:0.35},{x:-0.55,y:0,z:0},{x:0,y:0,z:0}, HS.flat,
    {j:'R_wr', ax:'y', amp:0.25, freq:2.5}),

  'READ': sign('READ','V-hand moves over flat-hand','Move V-hand up and down over flat-hand — reading a book',4,
    {x:-0.60,y:0,z:-0.28},{x:-0.75,y:0,z:0},{x:0,y:0,z:0}, HS.vhand,
    {x:-0.45,y:0,z:0.35},{x:-0.55,y:0,z:0},{x:0,y:0,z:0}, HS.flat,
    {j:'R_sh', ax:'x', amp:0.12, freq:2.0}),

  'SIGN': sign('SIGN','Open-5-hands circle alternately','Circle open-5-hands alternately forward — sign language',5,
    {x:-0.70,y:0,z:-0.28},{x:-0.80,y:0,z:0},{x:0,y:0,z:0}, HS.open5,
    {x:-0.70,y:0,z:0.28},{x:-0.80,y:0,z:0},{x:0,y:0,z:0}, HS.open5,
    {j:'both_sh', ax:'y', amp:0.5, freq:2.0}),

  'TELL': sign('TELL','L-hand from chin moves forward','L-hand thumb touches chin then moves forward — I tell you',5,
    {x:-1.22,y:0,z:-0.10},{x:-0.15,y:0,z:0},{x:0,y:0,z:0}, HS.lhand,
    IL.sh,IL.el,IL.wr, NL,
    {j:'R_sh', ax:'x', amp:0.12, freq:1.5}),

  'LAUGH': sign('LAUGH','L-hand moves at mouth','Show big smile — move L-hand up and down at mouth',4,
    {x:-1.20,y:0,z:-0.12},{x:-0.18,y:0,z:0},{x:0,y:0,z:0}, HS.lhand,
    IL.sh,IL.el,IL.wr, NL,
    {j:'R_sh', ax:'x', amp:0.20, freq:3.0}),

  'CRY': sign('CRY','Index fingers trail down cheeks','Move index fingers down cheeks — show sad face',4,
    {x:-1.30,y:0,z:-0.18},{x:-0.18,y:0,z:0},{x:0,y:0,z:0}, HS.point1,
    {x:-1.30,y:0,z:0.18},{x:-0.18,y:0,z:0},{x:0,y:0,z:0}, HS.point1,
    {j:'both_sh', ax:'x', amp:0.06, freq:1.5}),

  'HUG': sign('HUG','S-hands cross over chest twist','Cross S-hands over chest and twist body side to side',5,
    {x:-0.95,y:0,z:-0.40},{x:-0.20,y:0,z:0.35},{x:0,y:0,z:0}, HS.fist_S,
    {x:-0.95,y:0,z:0.40},{x:-0.20,y:0,z:-0.35},{x:0,y:0,z:0}, HS.fist_S,
    {j:'both_sh', ax:'z', amp:0.08, freq:1.5}),

  // ── DESCRIPTIONS ────────────────────────────────────────

  'GOOD': sign('GOOD','Flat-hand from chin sweeps down','Put flat-hand on chin then sweep downward and forward',5,
    {x:-1.18,y:0,z:-0.10},{x:-0.12,y:0,z:0},{x:0,y:0,z:0}, HS.flat,
    IL.sh,IL.el,IL.wr, NL,
    {j:'R_sh', ax:'x', amp:0.10, freq:1.5}),

  'BAD': sign('BAD','Flat-hand from mouth flips down','Flat-hand at mouth flips downward — bad smell from mouth',5,
    {x:-1.15,y:0,z:-0.10},{x:-0.12,y:0,z:0},{x:0.30,y:0,z:0}, HS.flat,
    IL.sh,IL.el,IL.wr, NL,
    {j:'R_wr', ax:'y', amp:0.5, freq:1.5}),

  'BIG': sign('BIG','Both hands spread apart','Show something big — spread both hands apart widely',5,
    {x:-0.65,y:0,z:-0.55},{x:-0.65,y:0,z:0},{x:0,y:0,z:0}, HS.open5,
    {x:-0.65,y:0,z:0.55},{x:-0.65,y:0,z:0},{x:0,y:0,z:0}, HS.open5,
    {j:'both_sh', ax:'z', amp:0.20, freq:1.3}),

  'SMALL': sign('SMALL','Cup-hands close together','Bring cup-hands close together — showing small size',5,
    {x:-0.65,y:0,z:-0.28},{x:-0.70,y:0,z:0},{x:0,y:0,z:0}, HS.chand,
    {x:-0.65,y:0,z:0.28},{x:-0.70,y:0,z:0},{x:0,y:0,z:0}, HS.chand,
    {j:'both_sh', ax:'z', amp:-0.15, freq:1.5}),

  'HOT': sign('HOT','Flick index off forehead','Mimic wiping sweat off forehead — it is hot',4,
    {x:-1.45,y:0,z:-0.08},{x:-0.12,y:0,z:0},{x:0,y:0,z:0}, HS.point1,
    IL.sh,IL.el,IL.wr, NL,
    {j:'R_wr', ax:'y', amp:0.35, freq:2.0}),

  'COLD': sign('COLD','A-hands shake at chest','Mimic shivering — shake A-hands in and out at chest quickly',5,
    {x:-0.75,y:0,z:-0.38},{x:-0.35,y:0,z:0},{x:0,y:0,z:0}, HS.fist_A,
    {x:-0.75,y:0,z:0.38},{x:-0.35,y:0,z:0},{x:0,y:0,z:0}, HS.fist_A,
    {j:'both_sh', ax:'z', amp:0.15, freq:5.0}),

  'QUIET': sign('QUIET','Index on lips — shh','Put index finger on lips — quiet please',5,
    {x:-1.32,y:0,z:-0.08},{x:-0.12,y:0,z:0},{x:0,y:0,z:0}, HS.point1,
    IL.sh,IL.el,IL.wr, NL,
    null),

  'FAST': sign('FAST','Index fingers snap forward','Both index fingers pointing, snap forward quickly',4,
    {x:-0.62,y:0,z:-0.18},{x:-0.88,y:0,z:0},{x:0,y:0,z:0}, HS.point1,
    {x:-0.62,y:0,z:0.18},{x:-0.88,y:0,z:0},{x:0,y:0,z:0}, HS.point1,
    {j:'both_sh', ax:'x', amp:0.25, freq:3.0}),

  'SLOW': sign('SLOW','Claw-hand slides slowly over open-5','Claw-hand moves slowly over open-5-hand from fingers to wrist',4,
    {x:-0.60,y:0,z:-0.28},{x:-0.70,y:0,z:0},{x:0,y:0,z:0}, HS.claw,
    {x:-0.48,y:0,z:0.35},{x:-0.55,y:0,z:0},{x:0,y:0,z:0}, HS.open5,
    {j:'R_sh', ax:'x', amp:0.10, freq:0.8}),

  // ── PLACES & OCCUPATIONS ────────────────────────────────

  'SCHOOL': sign('SCHOOL','Book sign · taps little fingers','Show book — tap little fingers together twice',5,
    {x:-0.62,y:0,z:-0.30},{x:-0.70,y:0,z:0},{x:0,y:0,z:0}, HS.flat,
    {x:-0.62,y:0,z:0.30},{x:-0.70,y:0,z:0},{x:0,y:0,z:0}, HS.flat,
    {j:'both_sh', ax:'x', amp:0.10, freq:2.2}),

  'HOME': sign('HOME','F-hands link together','Link F-hands — home/family place',5,
    {x:-0.68,y:0,z:-0.28},{x:-0.70,y:0,z:0},{x:0,y:0,z:0}, HS.fhand,
    {x:-0.68,y:0,z:0.28},{x:-0.70,y:0,z:0},{x:0,y:0,z:0}, HS.fhand,
    null),

  'CHURCH': sign('CHURCH','Hands together as in prayer','Put hands together as if praying — church',4,
    {x:-1.00,y:0,z:-0.15},{x:-0.30,y:0,z:0},{x:0,y:0,z:0}, HS.flat,
    {x:-1.00,y:0,z:0.15},{x:-0.30,y:0,z:0},{x:0,y:0,z:0}, HS.flat,
    null),

  'POLICE': sign('POLICE','F-hand badge on forehead or S-hand cuffs','Show badge on hat — F-hand on forehead',4,
    {x:-1.45,y:0,z:-0.06},{x:-0.12,y:0,z:0},{x:0,y:0,z:0}, HS.fhand,
    IL.sh,IL.el,IL.wr, NL,
    null),

  'TEACHER': sign('TEACHER','Index taps left then right','Mimic a teacher — tap index finger left then right',5,
    {x:-1.10,y:0,z:-0.35},{x:-0.20,y:0,z:0},{x:0,y:0,z:0}, HS.point1,
    IL.sh,IL.el,IL.wr, NL,
    {j:'R_sh', ax:'z', amp:0.35, freq:2.0}),

  // ── MONEY & NUMBERS ─────────────────────────────────────

  'MONEY': sign('MONEY','Closed-5 rubs fingers together','Mimic rubbing coins — rub closed-5 fingers',5,
    {x:-0.65,y:0,z:-0.28},{x:-0.70,y:0,z:0},{x:0,y:0,z:0}, HS.chand,
    IL.sh,IL.el,IL.wr, NL,
    {j:'R_wr', ax:'y', amp:0.25, freq:2.5}),

  'FREE': sign('FREE','V-hand fingers cross then open out','Cross V-hand fingers then move them outwards — free of charge',4,
    {x:-0.65,y:0,z:-0.28},{x:-0.70,y:0,z:0},{x:0,y:0,z:0}, HS.vhand,
    {x:-0.65,y:0,z:0.28},{x:-0.70,y:0,z:0},{x:0,y:0,z:0}, HS.vhand,
    {j:'both_sh', ax:'z', amp:0.35, freq:1.5}),

  'EXPENSIVE': sign('EXPENSIVE','Flat-hand moves into neck','Flat-hand moves up into neck — too expensive',4,
    {x:-0.80,y:0,z:-0.20},{x:-0.40,y:0,z:0},{x:0,y:0,z:0}, HS.flat,
    IL.sh,IL.el,IL.wr, NL,
    {j:'R_sh', ax:'x', amp:0.20, freq:1.5}),

  // ── FAMILY ──────────────────────────────────────────────

  'FAMILY': sign('FAMILY','Closed-5 circles above other closed-5','Circle closed-5-hand above other closed-5 — family group',5,
    {x:-0.75,y:0,z:-0.28},{x:-0.70,y:0,z:0},{x:0,y:0,z:0}, HS.chand,
    {x:-0.65,y:0,z:0.28},{x:-0.55,y:0,z:0},{x:0,y:0,z:0}, HS.chand,
    {j:'R_sh', ax:'y', amp:0.5, freq:1.8}),

  'MOM': sign('MOM','B-hand slides across chest','Show mother — B-hand slides across chest at breast level',5,
    {x:-0.90,y:0,z:-0.50},{x:-0.20,y:0,z:0},{x:0.15,y:0,z:0}, HS.flat,
    IL.sh,IL.el,IL.wr, NL,
    {j:'R_sh', ax:'z', amp:0.35, freq:1.5}),

  'DAD': sign('DAD','Index rubs down thumb at mouth','Mimic moustache — rub index down thumb at side of mouth',5,
    {x:-1.22,y:0,z:-0.15},{x:-0.15,y:0,z:0},{x:0,y:0,z:0}, HS.thand,
    IL.sh,IL.el,IL.wr, NL,
    {j:'R_wr', ax:'y', amp:0.20, freq:2.2}),

  'BABY': sign('BABY','Arms rock a baby','Mimic rocking a baby — swing arms gently side to side',5,
    {x:-0.85,y:0,z:-0.35},{x:-0.50,y:0,z:0},{x:0,y:0,z:0}, HS.flat,
    {x:-0.85,y:0,z:0.35},{x:-0.50,y:0,z:0},{x:0,y:0,z:0}, HS.flat,
    {j:'both_sh', ax:'z', amp:0.20, freq:1.2}),

  'FRIEND': sign('FRIEND','B-hands clasp and shake','Mimic friend handshake — clasp B-hands and shake up and down',5,
    {x:-0.68,y:0,z:-0.28},{x:-0.70,y:0,z:0},{x:0,y:0,z:0}, HS.flat,
    {x:-0.68,y:0,z:0.28},{x:-0.70,y:0,z:0},{x:0,y:0,z:0}, HS.flat,
    {j:'both_sh', ax:'x', amp:0.20, freq:2.5}),

  'CHILD': sign('CHILD','Flat-hand shows height of child','Show the size of the child — flat-hand palm down at child height',4,
    {x:-0.42,y:0,z:-0.28},{x:-0.50,y:0,z:0},{x:0,y:0,z:0}, HS.flat,
    IL.sh,IL.el,IL.wr, NL,
    null),

  'PERSON': sign('PERSON','C-hand moves downward','Show the shape of a person — C-hand moves downward',4,
    {x:-0.68,y:0,z:-0.20},{x:-0.70,y:0,z:0},{x:0,y:0,z:0}, HS.chand,
    IL.sh,IL.el,IL.wr, NL,
    {j:'R_sh', ax:'x', amp:0.15, freq:1.5}),

  // ── NATURE & WEATHER ────────────────────────────────────

  'RAIN': sign('RAIN','Open-5-hands flutter downward','Flutter fingers of open-5-hands as you move hands downward',5,
    {x:-0.55,y:0,z:-0.22},{x:-0.65,y:0,z:0},{x:0,y:0,z:0}, HS.open5,
    {x:-0.55,y:0,z:0.22},{x:-0.65,y:0,z:0},{x:0,y:0,z:0}, HS.open5,
    {j:'both_sh', ax:'x', amp:0.20, freq:3.0}),

  'SUN': sign('SUN','S-hand flicks open above head','Flick S-hand open above side of head — sunshine',4,
    {x:-1.38,y:0,z:-0.22},{x:-0.18,y:0,z:0},{x:0,y:0,z:0}, HS.fist_S,
    IL.sh,IL.el,IL.wr, NL,
    {j:'R_wr', ax:'z', amp:0.6, freq:1.5}),

  'WIND': sign('WIND','Open-5-hands blow side to side','Move open-5-hands simultaneously left and right — wind',4,
    {x:-0.68,y:0,z:-0.25},{x:-0.75,y:0,z:0},{x:0,y:0,z:0}, HS.open5,
    {x:-0.68,y:0,z:0.25},{x:-0.75,y:0,z:0},{x:0,y:0,z:0}, HS.open5,
    {j:'both_sh', ax:'z', amp:0.35, freq:2.0}),

  'TREE': sign('TREE','Elbow on flat-hand · wave open-5','Place elbow on flat-hand, wave top open-5 — tree leaves',4,
    {x:-1.15,y:0,z:-0.12},{x:-0.20,y:0,z:0},{x:0,y:0,z:0}, HS.open5,
    {x:-0.38,y:0,z:0.28},{x:-0.50,y:0,z:0},{x:0,y:0,z:0}, HS.flat,
    {j:'R_wr', ax:'z', amp:0.30, freq:2.0}),

  // ── FOOD ────────────────────────────────────────────────

  'FOOD': sign('FOOD','Closed hand to mouth','Mimic putting food into your mouth',5,
    {x:-1.38,y:0,z:-0.08},{x:-0.18,y:0,z:0},{x:0,y:0,z:0}, HS.chand,
    IL.sh,IL.el,IL.wr, NL,
    {j:'R_sh', ax:'x', amp:0.10, freq:2.5}),

  'BREAD': sign('BREAD','Flat-hand slices over flat-hand','Show slices of bread — move flat-hand up and down on other',4,
    {x:-0.60,y:0,z:-0.28},{x:-0.70,y:0,z:0},{x:0,y:0,z:0}, HS.flat,
    {x:-0.48,y:0,z:0.35},{x:-0.55,y:0,z:0},{x:0,y:0,z:0}, HS.flat,
    {j:'R_sh', ax:'x', amp:0.15, freq:2.5}),

  // ── TRANSPORT ───────────────────────────────────────────

  'CAR': sign('CAR','S-hands steer wheel','Mimic holding steering wheel and driving',5,
    {x:-0.70,y:0,z:-0.35},{x:-0.65,y:0,z:0},{x:0,y:0,z:0}, HS.fist_S,
    {x:-0.70,y:0,z:0.35},{x:-0.65,y:0,z:0},{x:0,y:0,z:0}, HS.fist_S,
    {j:'both_sh', ax:'y', amp:0.25, freq:1.8}),

  'TAXI': sign('TAXI','Cross S-hands then flick index','Cross wrists of S-hands then flick index fingers up',4,
    {x:-0.65,y:0,z:-0.28},{x:-0.70,y:0,z:0},{x:0,y:0,z:0}, HS.fist_S,
    {x:-0.65,y:0,z:0.28},{x:-0.70,y:0,z:0},{x:0,y:0,z:0}, HS.fist_S,
    {j:'both_wr', ax:'x', amp:0.5, freq:2.0}),

  'BUS': sign('BUS','A-hands move forward and backward','Move A-hands alternately forwards and backwards at sides of head',4,
    {x:-1.28,y:0,z:-0.35},{x:-0.15,y:0,z:0},{x:0,y:0,z:0}, HS.fist_A,
    {x:-1.28,y:0,z:0.35},{x:-0.15,y:0,z:0},{x:0,y:0,z:0}, HS.fist_A,
    {j:'both_sh', ax:'x', amp:0.20, freq:2.2}),

  // ── RIGHTS & LEGAL ──────────────────────────────────────

  'RIGHTS': sign('RIGHTS','R-hand on flat palm','Show the letter R resting on flat palm — rights',4,
    {x:-0.62,y:0,z:-0.28},{x:-0.72,y:0,z:0},{x:0,y:0,z:0}, HS.vhand,
    {x:-0.48,y:0,z:0.35},{x:-0.55,y:0,z:0},{x:0,y:0,z:0}, HS.flat,
    null),

  'LAW': sign('LAW','L-hand taps flat palm','L-hand taps onto flat palm — law/rule',4,
    {x:-0.62,y:0,z:-0.28},{x:-0.72,y:0,z:0},{x:0,y:0,z:0}, HS.lhand,
    {x:-0.48,y:0,z:0.35},{x:-0.55,y:0,z:0},{x:0,y:0,z:0}, HS.flat,
    {j:'R_sh', ax:'x', amp:0.10, freq:2.0}),

  'EQUAL': sign('EQUAL','Both flat-hands level out','Level both flat-hands at same height — equality',5,
    {x:-0.65,y:0,z:-0.28},{x:-0.70,y:0,z:0},{x:0,y:0,z:0}, HS.flat,
    {x:-0.65,y:0,z:0.28},{x:-0.70,y:0,z:0},{x:0,y:0,z:0}, HS.flat,
    null),

  'SHARE': sign('SHARE','Top flat-hand sweeps over bottom','Top flat-hand sweeps forward and out over bottom flat-hand',4,
    {x:-0.62,y:0,z:-0.28},{x:-0.72,y:0,z:0},{x:0.10,y:0,z:0}, HS.flat,
    {x:-0.48,y:0,z:0.35},{x:-0.55,y:0,z:0},{x:0,y:0,z:0}, HS.flat,
    {j:'R_sh', ax:'z', amp:0.20, freq:2.0}),

  // ── TIME ────────────────────────────────────────────────

  'TODAY': sign('TODAY','Now sign — both Y-hands drop down','Both Y-hands drop downward — now/today',5,
    {x:-0.62,y:0,z:-0.28},{x:-0.72,y:0,z:0},{x:0,y:0,z:0}, HS.yhand,
    {x:-0.62,y:0,z:0.28},{x:-0.72,y:0,z:0},{x:0,y:0,z:0}, HS.yhand,
    {j:'both_sh', ax:'x', amp:0.20, freq:2.0}),

  'NOW': sign('NOW','Y-hands drop downward','Both Y-hands drop down simultaneously — now',5,
    {x:-0.62,y:0,z:-0.28},{x:-0.72,y:0,z:0},{x:0,y:0,z:0}, HS.yhand,
    {x:-0.62,y:0,z:0.28},{x:-0.72,y:0,z:0},{x:0,y:0,z:0}, HS.yhand,
    {j:'both_sh', ax:'x', amp:0.25, freq:2.0}),

  'MORNING': sign('MORNING','Flat-hand rises at forearm crook','Show sun rising — flat hand rises from elbow crook',4,
    {x:-0.45,y:0,z:0.35},{x:-0.55,y:0,z:0},{x:0,y:0,z:0}, HS.flat,
    {x:-0.80,y:0,z:-0.40},{x:-0.30,y:0,z:0},{x:0,y:0,z:0}, HS.flat,
    {j:'R_sh', ax:'x', amp:0.18, freq:1.2}),

  'NIGHT': sign('NIGHT','Bent hands show sun setting','Bent hands arc downward — nighttime',4,
    {x:-0.50,y:0,z:-0.28},{x:-0.65,y:0,z:0},{x:0,y:0,z:0}, HS.flat,
    {x:-0.50,y:0,z:0.28},{x:-0.65,y:0,z:0},{x:0,y:0,z:0}, HS.flat,
    {j:'both_sh', ax:'x', amp:0.15, freq:1.2}),

};

// ═══════════════════════════════════════════════════════════
// FINGERSPELLING — A to Z
// When a word is not in the library, spell it letter by letter
// Each letter = a brief arm position with the correct handshape
// ═══════════════════════════════════════════════════════════
const FINGERSPELL_POSITION = {
  sh:{x:-0.85,y:0,z:-0.28}, el:{x:-0.50,y:0,z:0}, wr:{x:0,y:0,z:0}
};

const ALPHABET = {
  'A': HS.fist_A,  'B': HS.flat,   'C': HS.chand,
  'D': HS.point1,  'E': HS.claw,   'F': HS.fhand,
  'G': HS.ghand,   'H': HS.uhand,  'I': HS.point1,
  'J': HS.yhand,   'K': HS.vhand,  'L': HS.lhand,
  'M': HS.whand,   'N': HS.vhand,  'O': HS.chand,
  'P': HS.point1,  'Q': HS.ghand,  'R': HS.vhand,
  'S': HS.fist_S,  'T': HS.thand,  'U': HS.uhand,
  'V': HS.vhand,   'W': HS.whand,  'X': HS.xhand,
  'Y': HS.yhand,   'Z': HS.point1,
};

// ═══════════════════════════════════════════════════════════
// WORD NORMALISATION MAP
// Maps variations, synonyms, contractions to library keys
// ═══════════════════════════════════════════════════════════
const WORD_MAP = {
  // Greetings
  'hi': 'HELLO', 'hey': 'HELLO', 'greetings': 'HELLO', 'howzit': 'HELLO',
  'bye': 'GOODBYE', 'see you': 'GOODBYE', 'take care': 'GOODBYE', 'farewell': 'GOODBYE',
  'thanks': 'THANK YOU', 'thank': 'THANK YOU', 'cheers': 'THANK YOU',
  'please': 'PLEASE', 'pls': 'PLEASE',
  'ok': 'YES', 'okay': 'YES', 'yep': 'YES', 'yup': 'YES', 'correct': 'YES', 'right': 'YES', 'affirmative': 'YES', 'sure': 'YES',
  'nope': 'NO', 'nah': 'NO', 'not': 'NO', 'never': 'NO', 'nobody': 'NO', 'nothing': 'NO',
  "don't": 'NO', 'dont': 'NO', "doesn't": 'NO', 'doesnt': 'NO',
  "didn't": 'NO', 'didnt': 'NO', "can't": 'NO', 'cant': 'NO',
  "won't": 'NO', 'wont': 'NO', "isn't": 'NO', "aren't": 'NO',
  "wasn't": 'NO', "weren't": 'NO', "shouldn't": 'NO', "wouldn't": 'NO', "couldn't": 'NO',
  'sorry': 'SORRY', 'apologies': 'SORRY', 'my bad': 'SORRY', 'excuse': 'SORRY',

  // Medical
  'doctor': 'DOCTOR', 'dr': 'DOCTOR', 'physician': 'DOCTOR',
  'nurse': 'NURSE', 'nursing': 'NURSE',
  'hospital': 'HOSPITAL', 'clinic': 'HOSPITAL', 'emergency room': 'HOSPITAL',
  'sick': 'SICK', 'ill': 'SICK', 'unwell': 'SICK', 'nauseous': 'SICK',
  'pain': 'PAIN', 'painful': 'PAIN', 'sore': 'PAIN', 'hurt': 'HURT', 'hurts': 'HURT', 'ache': 'PAIN',
  'ambulance': 'AMBULANCE',
  'medicine': 'MEDICINE', 'medication': 'MEDICINE', 'pills': 'MEDICINE', 'tablet': 'MEDICINE',
  'fire': 'FIRE', 'burning': 'FIRE',
  'dangerous': 'DANGEROUS', 'danger': 'DANGEROUS', 'hazard': 'DANGEROUS',
  'careful': 'CAREFUL', 'caution': 'CAREFUL', 'watch out': 'CAREFUL',
  'safe': 'SAFE', 'safety': 'SAFE',
  'emergency': 'EMERGENCY',
  'help': 'HELP', 'assist': 'HELP', 'assistance': 'HELP',

  // Emotions
  'happy': 'HAPPY', 'joyful': 'HAPPY', 'glad': 'HAPPY', 'joy': 'HAPPY', 'cheerful': 'HAPPY',
  'sad': 'SAD', 'unhappy': 'SAD', 'upset': 'SAD', 'depressed': 'SAD', 'miserable': 'SAD',
  'angry': 'ANGRY', 'mad': 'ANGRY', 'furious': 'ANGRY', 'annoyed': 'ANGRY',
  'scared': 'SCARED', 'afraid': 'SCARED', 'frightened': 'SCARED', 'fear': 'SCARED',
  'love': 'LOVE', 'loving': 'LOVE',
  'i love you': 'I LOVE YOU',
  'excited': 'EXCITED', 'exciting': 'EXCITED',
  'tired': 'TIRED', 'exhausted': 'TIRED', 'sleepy': 'TIRED', 'fatigue': 'TIRED',
  'hungry': 'HUNGRY', 'starving': 'HUNGRY',
  'thirsty': 'THIRSTY',
  'worried': 'WORRIED', 'anxious': 'WORRIED', 'nervous': 'WORRIED', 'stress': 'WORRIED',
  'proud': 'PROUD', 'confidence': 'PROUD',
  'confused': 'CONFUSED', 'confusing': 'CONFUSED',

  // Questions
  'who': 'WHO', 'what': 'WHAT', 'where': 'WHERE', 'when': 'WHEN', 'why': 'WHY', 'how': 'HOW', 'which': 'WHICH',

  // Pronouns
  'i': 'I', 'me': 'I', 'my': 'I', 'mine': 'I', 'myself': 'I',
  'you': 'YOU', 'your': 'YOU', 'yours': 'YOU',
  'we': 'WE', 'us': 'WE', 'our': 'WE',
  'they': 'THEY', 'them': 'THEY', 'their': 'THEY',

  // Actions
  'come': 'COME', 'comes': 'COME', 'coming': 'COME', 'came': 'COME',
  'bring': 'COME', 'brings': 'COME', 'brought': 'COME',
  'go': 'GO', 'goes': 'GO', 'going': 'GO', 'went': 'GO', 'gone': 'GO',
  'leave': 'GO', 'leaving': 'GO', 'left': 'GO',
  'stop': 'STOP', 'halt': 'STOP', 'stopping': 'STOP', 'stopped': 'STOP',
  'wait': 'WAIT', 'waiting': 'WAIT', 'hold on': 'WAIT', 'later': 'WAIT',
  'repeat': 'REPEAT', 'again': 'REPEAT', 'say again': 'REPEAT',
  'understand': 'UNDERSTAND', 'understood': 'UNDERSTAND', 'got it': 'UNDERSTAND', 'understanding': 'UNDERSTAND',
  'listen': 'LISTEN', 'listens': 'LISTEN', 'listening': 'LISTEN', 'listened': 'LISTEN', 'hear': 'LISTEN', 'heard': 'LISTEN',
  'look': 'LOOK', 'looks': 'LOOK', 'looking': 'LOOK', 'looked': 'LOOK',
  'see': 'LOOK', 'sees': 'LOOK', 'seeing': 'LOOK', 'saw': 'LOOK', 'seen': 'LOOK',
  'watch': 'LOOK', 'watching': 'LOOK', 'find': 'LOOK', 'found': 'LOOK',
  'know': 'KNOW', 'knows': 'KNOW', 'knowing': 'KNOW', 'knew': 'KNOW',
  'think': 'KNOW', 'thinks': 'KNOW', 'thinking': 'KNOW', 'thought': 'KNOW', 'believe': 'KNOW',
  'want': 'WANT', 'wants': 'WANT', 'wanting': 'WANT', 'wanted': 'WANT',
  'need': 'WANT', 'needs': 'WANT', 'needing': 'WANT', 'needed': 'WANT', 'require': 'WANT',
  'get': 'WANT', 'take': 'WANT', 'taking': 'WANT', 'took': 'WANT',
  'give': 'GIVE', 'gives': 'GIVE', 'giving': 'GIVE', 'gave': 'GIVE', 'given': 'GIVE',
  'eat': 'EAT', 'eats': 'EAT', 'eating': 'EAT', 'ate': 'EAT', 'eaten': 'EAT', 'food': 'FOOD',
  'drink': 'DRINK', 'drinks': 'DRINK', 'drinking': 'DRINK', 'drank': 'DRINK', 'water': 'WATER',
  'sleep': 'SLEEP', 'sleeps': 'SLEEP', 'sleeping': 'SLEEP', 'slept': 'SLEEP', 'rest': 'SLEEP',
  'sit': 'SIT', 'sits': 'SIT', 'sitting': 'SIT', 'sat': 'SIT', 'seat': 'SIT',
  'stand': 'STAND', 'stands': 'STAND', 'standing': 'STAND', 'stood': 'STAND',
  'walk': 'WALK', 'walks': 'WALK', 'walking': 'WALK', 'walked': 'WALK',
  'run': 'RUN', 'runs': 'RUN', 'running': 'RUN', 'ran': 'RUN',
  'work': 'WORK', 'works': 'WORK', 'working': 'WORK', 'worked': 'WORK', 'job': 'WORK',
  'wash': 'WASH', 'washes': 'WASH', 'washing': 'WASH', 'washed': 'WASH', 'clean': 'WASH', 'cleaning': 'WASH',
  'write': 'WRITE', 'writes': 'WRITE', 'writing': 'WRITE', 'wrote': 'WRITE', 'written': 'WRITE',
  'read': 'READ', 'reads': 'READ', 'reading': 'READ',
  'open': 'OPEN', 'opens': 'OPEN', 'opening': 'OPEN', 'opened': 'OPEN',
  'close': 'CLOSE', 'closes': 'CLOSE', 'closing': 'CLOSE', 'closed': 'CLOSE', 'shut': 'CLOSE',
  'tell': 'TELL', 'tells': 'TELL', 'telling': 'TELL', 'told': 'TELL',
  'say': 'TELL', 'says': 'TELL', 'saying': 'TELL', 'said': 'TELL',
  'speak': 'TELL', 'speaks': 'TELL', 'speaking': 'TELL', 'spoke': 'TELL',
  'talk': 'TELL', 'talks': 'TELL', 'talking': 'TELL', 'talked': 'TELL',
  'call': 'TELL',
  'laugh': 'LAUGH', 'laughs': 'LAUGH', 'laughing': 'LAUGH', 'laughed': 'LAUGH',
  'cry': 'CRY', 'cries': 'CRY', 'crying': 'CRY', 'cried': 'CRY', 'tears': 'CRY',
  'hug': 'HUG', 'hugs': 'HUG', 'hugging': 'HUG', 'hugged': 'HUG',
  'sign': 'SIGN', 'signs': 'SIGN', 'signing': 'SIGN', 'signed': 'SIGN',

  // Descriptions
  'good': 'GOOD', 'great': 'GOOD', 'nice': 'GOOD', 'fine': 'GOOD', 'well': 'GOOD', 'okay': 'GOOD',
  "i'm fine": "I'M FINE", 'im fine': "I'M FINE",
  'bad': 'BAD', 'terrible': 'BAD', 'awful': 'BAD', 'wrong': 'BAD',
  'big': 'BIG', 'large': 'BIG', 'huge': 'BIG',
  'small': 'SMALL', 'little': 'SMALL', 'tiny': 'SMALL',
  'hot': 'HOT', 'warm': 'HOT',
  'cold': 'COLD', 'cool': 'COLD', 'freezing': 'COLD',
  'quiet': 'QUIET', 'silent': 'QUIET', 'shh': 'QUIET',
  'fast': 'FAST', 'quick': 'FAST', 'quickly': 'FAST',
  'slow': 'SLOW', 'slowly': 'SLOW',
  'yes': 'YES', 'no': 'NO',

  // Places
  'school': 'SCHOOL', 'class': 'SCHOOL', 'classroom': 'SCHOOL',
  'home': 'HOME', 'house': 'HOME',
  'church': 'CHURCH',
  'police': 'POLICE', 'cop': 'POLICE',
  'teacher': 'TEACHER', 'instructor': 'TEACHER',

  // People / family
  'family': 'FAMILY',
  'mom': 'MOM', 'mother': 'MOM', 'mama': 'MOM', 'mum': 'MOM',
  'dad': 'DAD', 'father': 'DAD', 'papa': 'DAD',
  'baby': 'BABY', 'infant': 'BABY',
  'friend': 'FRIEND', 'buddy': 'FRIEND', 'mate': 'FRIEND',
  'child': 'CHILD', 'kid': 'CHILD', 'children': 'CHILD',
  'person': 'PERSON', 'people': 'PERSON', 'man': 'PERSON', 'woman': 'PERSON',

  // Nature
  'rain': 'RAIN', 'raining': 'RAIN', 'rainy': 'RAIN',
  'sun': 'SUN', 'sunny': 'SUN', 'sunshine': 'SUN',
  'wind': 'WIND', 'windy': 'WIND',
  'tree': 'TREE', 'trees': 'TREE',

  // Money
  'money': 'MONEY', 'cash': 'MONEY', 'rand': 'MONEY', 'cost': 'MONEY', 'pay': 'MONEY',
  'free': 'FREE', 'no charge': 'FREE',
  'expensive': 'EXPENSIVE', 'costly': 'EXPENSIVE',

  // Transport
  'car': 'CAR', 'vehicle': 'CAR', 'drive': 'CAR',
  'taxi': 'TAXI', 'minibus': 'TAXI', 'uber': 'TAXI',
  'bus': 'BUS',

  // Rights
  'rights': 'RIGHTS', 'right': 'RIGHTS',
  'law': 'LAW', 'legal': 'LAW', 'legislation': 'LAW',
  'equal': 'EQUAL', 'equality': 'EQUAL', 'fair': 'EQUAL',
  'share': 'SHARE', 'sharing': 'SHARE',

  // Time
  'today': 'TODAY', 'now': 'NOW', 'currently': 'NOW',
  'morning': 'MORNING', 'afternoon': 'MORNING', 'evening': 'NIGHT',
  'night': 'NIGHT', 'tonight': 'NIGHT',

  // Greetings continued
  "how are you": 'HOW ARE YOU', 'howzit': 'HOW ARE YOU',
};

// ═══════════════════════════════════════════════════════════
// SENTENCE TO SIGN SEQUENCE
// Takes transcribed text from Whisper, returns array of signs
// ═══════════════════════════════════════════════════════════

/**
 * Convert a transcribed sentence into an array of sign objects
 * ready to feed to the avatar animation system.
 * 
 * Usage:
 *   const signs = sentenceToSigns("Good morning, how are you?");
 *   signs.forEach(s => playSignObject(s));
 */
function sentenceToSigns(text) {
  if (!text) return [];

  const result = [];
  const lower = text.toLowerCase().trim();

  // Try multi-word phrases first (2-3 word phrases)
  // e.g. "how are you", "i love you", "i'm fine"
  const words = lower
    .replace(/[^a-z0-9'\s]/g, ' ')  // remove punctuation except apostrophes
    .split(/\s+/)
    .filter(w => w.length > 0);

  let i = 0;
  while (i < words.length) {
    // Try 3-word phrase
    if (i + 2 < words.length) {
      const phrase3 = words.slice(i, i+3).join(' ');
      const key3 = WORD_MAP[phrase3];
      if (key3 && SIGN_LIBRARY[key3]) {
        result.push(SIGN_LIBRARY[key3]);
        i += 3;
        continue;
      }
    }

    // Try 2-word phrase
    if (i + 1 < words.length) {
      const phrase2 = words.slice(i, i+2).join(' ');
      const key2 = WORD_MAP[phrase2];
      if (key2 && SIGN_LIBRARY[key2]) {
        result.push(SIGN_LIBRARY[key2]);
        i += 2;
        continue;
      }
    }

    // Single word
    const word = words[i];

    // Skip filler words
    if (['the','a','an','is','are','was','were','be','been',
         'of','to','in','for','on','with','at','by','as',
         'it','its','this','that','and','but','or','so',
         'um','uh','ah','oh','hmm'].includes(word)) {
      i++;
      continue;
    }

    // Look up in word map first
    const mapped = WORD_MAP[word];
    if (mapped && SIGN_LIBRARY[mapped]) {
      result.push(SIGN_LIBRARY[mapped]);
      i++;
      continue;
    }

    // Direct lookup in sign library
    const upper = word.toUpperCase();
    if (SIGN_LIBRARY[upper]) {
      result.push(SIGN_LIBRARY[upper]);
      i++;
      continue;
    }

    // Fingerspell unknown word
    const spelling = fingerspell(word);
    result.push(...spelling);
    i++;
  }

  return result;
}

/**
 * Fingerspell a word letter by letter
 * Returns array of sign objects, one per letter
 */
function fingerspell(word) {
  const result = [];
  for (const char of word.toUpperCase()) {
    if (ALPHABET[char]) {
      result.push({
        name: char,
        shape: `Letter ${char}`,
        desc: `Fingerspelling: ${char}`,
        conf: 3,
        R: {
          sh: FINGERSPELL_POSITION.sh,
          el: FINGERSPELL_POSITION.el,
          wr: FINGERSPELL_POSITION.wr,
          hand: ALPHABET[char]
        },
        L: {
          sh: ARM.idle_L.sh,
          el: ARM.idle_L.el,
          wr: ARM.idle_L.wr,
          hand: HS.rest
        },
        osc: null,
        isFingerspell: true
      });
    }
  }
  return result;
}

/**
 * Get a single sign by exact name or word
 * Returns the sign object or null
 */
function getSign(word) {
  if (!word) return null;
  const lower = word.toLowerCase().trim();

  // Check word map
  const mapped = WORD_MAP[lower];
  if (mapped) return SIGN_LIBRARY[mapped] || null;

  // Direct library lookup
  const upper = word.toUpperCase().trim();
  return SIGN_LIBRARY[upper] || null;
}

/**
 * Get all sign names in the library (for building UI)
 */
function getAllSignNames() {
  return Object.keys(SIGN_LIBRARY);
}

/**
 * Get signs by category
 */
function getSignsByCategory(category) {
  const categories = {
    MEDICAL:      ['DOCTOR','NURSE','HOSPITAL','SICK','PAIN','AMBULANCE','MEDICINE','HURT','EMERGENCY','CAREFUL','DANGEROUS','SAFE','FIRE'],
    GREETINGS:    ['HELLO','GOODBYE','HOW ARE YOU',"I'M FINE",'PLEASE','THANK YOU','SORRY','YES','NO'],
    EMOTIONS:     ['HAPPY','SAD','ANGRY','SCARED','LOVE','I LOVE YOU','EXCITED','TIRED','HUNGRY','THIRSTY','WORRIED','PROUD','CONFUSED'],
    QUESTIONS:    ['WHO','WHAT','WHERE','WHEN','WHY','HOW','WHICH'],
    ACTIONS:      ['HELP','WAIT','STOP','REPEAT','UNDERSTAND','COME','GO','LISTEN','LOOK','KNOW','WANT','GIVE','EAT','DRINK','SLEEP','SIT','STAND','WALK','RUN','WORK','WASH','WRITE','READ','SIGN','TELL','LAUGH','CRY','HUG','OPEN','CLOSE'],
    DESCRIPTIONS: ['GOOD','BAD','BIG','SMALL','HOT','COLD','QUIET','FAST','SLOW','WATER'],
    PLACES:       ['SCHOOL','HOME','HOSPITAL','CHURCH','POLICE'],
    FAMILY:       ['FAMILY','MOM','DAD','BABY','FRIEND','CHILD','PERSON'],
    RIGHTS:       ['RIGHTS','LAW','EQUAL','SHARE','FREE'],
    TRANSPORT:    ['CAR','TAXI','BUS'],
  };
  return (categories[category] || []).map(name => SIGN_LIBRARY[name]).filter(Boolean);
}

// ═══════════════════════════════════════════════════════════
// EXPORTS — for use in Electron renderer and Node.js
// ═══════════════════════════════════════════════════════════
if (typeof module !== 'undefined' && module.exports) {
  module.exports = { SIGN_LIBRARY, WORD_MAP, ALPHABET, HS, ARM,
    sentenceToSigns, fingerspell, getSign, getAllSignNames, getSignsByCategory };
}

// For browser / Electron renderer direct include
if (typeof window !== 'undefined') {
  window.AMANDLA_SIGNS = { SIGN_LIBRARY, WORD_MAP, ALPHABET, HS, ARM,
    sentenceToSigns, fingerspell, getSign, getAllSignNames, getSignsByCategory };
}
