"use client";

import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { Bloom, EffectComposer } from "@react-three/postprocessing";
import { useEffect, useMemo, useRef } from "react";
import * as THREE from "three";

/**
 * The Trust Field, interactive. Every particle is a wallet from the synthetic world (real sample + the wider population).
 * The same particles morph between four views of the story:
 *   0 the network (a globe of everyday payments) · 1 the three layers (customers, agents & shops, operations)
 *   2 the pause (the field becomes the UVERA mark) · 3 one case (scattered alerts collapse into one case).
 * The mouse pushes particles aside; a click sends a shockwave.
 */

export type WorldCompact = {
  source: string;
  nodes: [number, number][];
  edges: [number, number, number, number, number, number][];
};

const GOLDEN = Math.PI * (3 - Math.sqrt(5));

function rng(seed: number) {
  return () => {
    seed |= 0;
    seed = (seed + 0x6d2b79f5) | 0;
    let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

type Field = {
  n: number;
  p: Float32Array[]; // 4 morph targets, xyz each
  hl: Float32Array; // highlight per state (vec4)
  color: Float32Array;
  size: Float32Array;
  alpha: Float32Array;
  seed: Float32Array;
  lines: Uint32Array; // pairs of particle indices
  scamLines: Uint32Array;
  pulses: { a: number; b: number; speed: number; offset: number; scam: boolean }[];
};

function buildField(world: WorldCompact, mobile: boolean): Field {
  const r = rng(11);
  const real = world.nodes.length;
  const ambient = mobile ? 1400 : 3600;
  const n = real + ambient;
  // kind: 0 customer, 1 agent, 2 merchant, 3 case, 4 mule, 5 disguised shop, 6 ambient customer
  const kind = new Uint8Array(n);
  world.nodes.forEach(([t, f], i) => {
    kind[i] = t === 3 ? 3 : t === 0 || t === 4 ? (f === 1 ? 4 : 0) : t === 1 ? 1 : f === 2 ? 5 : 2;
  });
  for (let i = real; i < n; i++) kind[i] = 6;

  const scamNode = new Uint8Array(n);
  world.edges.forEach(([s, t, , , scam]) => {
    if (scam) {
      scamNode[s] = 1;
      scamNode[t] = 1;
    }
  });

  const p = [0, 1, 2, 3].map(() => new Float32Array(n * 3));
  const hl = new Float32Array(n * 4);
  const color = new Float32Array(n * 3);
  const size = new Float32Array(n);
  const alpha = new Float32Array(n);
  const seed = new Float32Array(n);

  // ---- state 0: the network globe (random order on a Fibonacci sphere; cases at the core)
  const order = Array.from({ length: n }, (_, i) => i).sort(() => r() - 0.5);
  order.forEach((i, k) => {
    if (kind[i] === 3) {
      const v = new THREE.Vector3(r() - 0.5, r() - 0.5, r() - 0.5).normalize().multiplyScalar(0.35);
      p[0].set([v.x, v.y, v.z], i * 3);
      return;
    }
    const y = 1 - (k / (n - 1)) * 2;
    const rad = Math.sqrt(1 - y * y);
    const th = k * GOLDEN;
    const R = 3.05 + (r() - 0.5) * 0.12;
    p[0].set([Math.cos(th) * rad * R, y * R, Math.sin(th) * rad * R], i * 3);
  });

  // ---- state 1: three layers (customers bottom, agents & shops middle, linked cases top)
  const groups: number[][] = [[], [], [], []];
  for (let i = 0; i < n; i++) {
    const k = kind[i];
    groups[k === 3 ? 3 : k === 4 ? 2 : k === 0 || k === 6 ? 0 : 1].push(i);
  }
  groups[0].forEach((i, k) => {
    const rad = 3.6 * Math.sqrt((k + 0.5) / groups[0].length);
    const th = k * GOLDEN;
    p[1].set([rad * Math.cos(th), -1.35 + (r() - 0.5) * 0.1, rad * Math.sin(th)], i * 3);
  });
  groups[2].forEach((i, k) => {
    const th = (k / Math.max(1, groups[2].length)) * Math.PI * 2;
    p[1].set([0.7 * Math.cos(th), -1.25, 0.7 * Math.sin(th)], i * 3);
  });
  groups[1].forEach((i, k) => {
    const rad = 1.0 + 2.2 * Math.sqrt((k + 0.5) / groups[1].length);
    const th = k * GOLDEN + 1.1;
    p[1].set([rad * Math.cos(th), 0, rad * Math.sin(th)], i * 3);
  });
  groups[3].forEach((i, k) => {
    const th = (k / Math.max(1, groups[3].length)) * Math.PI * 2;
    p[1].set([0.85 * Math.cos(th), 1.45, 0.85 * Math.sin(th)], i * 3);
  });

  // ---- state 2: the UVERA mark (ring = customers, left bar = agents & shops, volt bar = the pause)
  const ringR = 2.45;
  const tube = 0.15;
  let rightBudget = mobile ? 380 : 900;
  for (let i = 0; i < n; i++) {
    const k = kind[i];
    let part: 0 | 1 | 2 = 0;
    if (k === 1 || k === 2 || k === 5) part = 1;
    else if (k === 3 || k === 4 || scamNode[i]) part = 2;
    else if (k === 6 && rightBudget > 0 && r() < 0.3) {
      part = 2;
      rightBudget--;
    }
    if (part === 0) {
      const th = r() * Math.PI * 2;
      const rr = ringR + (r() - 0.5) * tube * 2;
      p[2].set([rr * Math.cos(th), rr * Math.sin(th), (r() - 0.5) * 0.25], i * 3);
    } else {
      const x0 = part === 1 ? -0.82 : 0.31;
      p[2].set([x0 + r() * 0.51, (r() - 0.5) * 2.05, (r() - 0.5) * 0.3], i * 3);
      if (part === 2) hl[i * 4 + 2] = 1;
    }
  }

  // ---- state 3: one case (alerts collapse into one bright cluster; the rest settles into a quiet disc)
  let alertBudget = mobile ? 220 : 480;
  for (let i = 0; i < n; i++) {
    const k = kind[i];
    const alert = k === 3 || k === 4 || scamNode[i] || (k === 6 && alertBudget > 0 && r() < 0.14 && alertBudget--);
    if (alert) {
      const v = new THREE.Vector3(r() - 0.5, r() - 0.5, r() - 0.5).normalize().multiplyScalar(0.25 + Math.pow(r(), 2) * 0.55);
      p[3].set([v.x, v.y + 0.35, v.z], i * 3);
      hl[i * 4 + 3] = 1;
    } else {
      const th = r() * Math.PI * 2;
      const rad = 2.2 + Math.pow(r(), 0.7) * 1.4;
      p[3].set([rad * Math.cos(th), -0.6 + (r() - 0.5) * 0.35, rad * Math.sin(th)], i * 3);
    }
  }

  // ---- looks
  const c = new THREE.Color();
  for (let i = 0; i < n; i++) {
    const k = kind[i];
    c.set(k === 1 ? "#f5f5f5" : k === 2 ? "#c4c4c4" : k === 5 ? "#e5e5e5" : k === 3 || k === 4 ? "#d7ff3a" : k === 0 ? "#a3a3a3" : "#7a7a7a");
    color.set([c.r, c.g, c.b], i * 3);
    size[i] = k === 3 ? 22 : k === 4 ? 9 : k === 1 ? 7.5 : k === 2 || k === 5 ? 5.5 : k === 0 ? 4.6 : 3.4;
    alpha[i] = k === 6 ? 0.42 : k === 0 ? 0.62 : 0.9;
    seed[i] = r();
    if (k === 3 || k === 4) hl[i * 4 + 1] = 1; // linked cases and mules glow in the layers view
  }

  // ---- lines and pulses
  const lines: number[] = [];
  const scamLines: number[] = [];
  const pulses: Field["pulses"] = [];
  world.edges.forEach(([s, t, type, , scam], k) => {
    if (scam) scamLines.push(s, t);
    else if (type !== 3 && k % (mobile ? 3 : 2) === 0) lines.push(s, t);
    if (scam || (type !== 3 && k % (mobile ? 9 : 5) === 0)) pulses.push({ a: s, b: t, speed: 0.12 + r() * 0.18, offset: r(), scam: !!scam });
  });
  return { n, p, hl, color, size, alpha, seed, lines: new Uint32Array(lines), scamLines: new Uint32Array(scamLines), pulses };
}

const MORPH = /* glsl */ `
  attribute vec3 p0;
  attribute vec3 p1;
  attribute vec3 p2;
  attribute vec3 p3;
  attribute vec4 hl;
  attribute float seed;
  uniform float uState;
  uniform float uTime;
  uniform vec3 uMouse;
  uniform float uMouseOn;
  uniform vec3 uClick;
  uniform float uClickT;
  float wave;
  float hlv;
  vec3 morph() {
    float s = clamp(uState, 0.0, 3.0);
    float i = floor(min(s, 2.999));
    float f = s - i;
    float lf = smoothstep(0.0, 1.0, clamp((f - seed * 0.35) / 0.65, 0.0, 1.0));
    vec3 a = i < 0.5 ? p0 : i < 1.5 ? p1 : p2;
    vec3 b = i < 0.5 ? p1 : i < 1.5 ? p2 : p3;
    float ha = i < 0.5 ? hl.x : i < 1.5 ? hl.y : hl.z;
    float hb = i < 0.5 ? hl.y : i < 1.5 ? hl.z : hl.w;
    hlv = mix(ha, hb, lf);
    vec3 pos = mix(a, b, lf);
    pos += 0.035 * vec3(sin(uTime * 0.7 + seed * 40.0), cos(uTime * 0.6 + seed * 31.0), sin(uTime * 0.5 + seed * 23.0));
    vec3 d = pos - uMouse;
    float dist = length(d);
    pos += uMouseOn * (d / max(dist, 1e-3)) * 0.75 * exp(-dist * dist * 1.4);
    vec3 dc = pos - uClick;
    float rc = length(dc);
    wave = exp(-pow(rc - uClickT * 5.0, 2.0) * 5.0) * exp(-uClickT * 1.4);
    pos += (dc / max(rc, 1e-3)) * wave * 0.6;
    return pos;
  }
`;

const POINT_VERT = /* glsl */ `
  attribute vec3 color;
  attribute float size;
  attribute float alpha;
  uniform float uScale;
  uniform vec3 uVolt;
  varying vec3 vColor;
  varying float vAlpha;
  ${MORPH}
  void main() {
    vec3 pos = morph();
    float s3 = clamp(uState - 2.0, 0.0, 1.0);
    float s2 = max(0.0, 1.0 - abs(uState - 2.0));
    vColor = mix(color, uVolt, hlv) + wave * 0.6;
    float tw = 0.8 + 0.2 * sin(uTime * 2.0 + seed * 60.0);
    vAlpha = min(1.0, mix(alpha * tw * mix(1.0, 0.4, s3) * mix(1.0, 2.0, s2), 1.0, hlv));
    vec4 mv = modelViewMatrix * vec4(pos, 1.0);
    float shrink = mix(1.0, 0.45, s2 * step(15.0, size));
    gl_PointSize = size * shrink * (1.0 + hlv * 0.5 + wave * 1.5) * uScale / -mv.z;
    gl_Position = projectionMatrix * mv;
  }
`;

const POINT_FRAG = /* glsl */ `
  varying vec3 vColor;
  varying float vAlpha;
  void main() {
    float d = length(gl_PointCoord - 0.5);
    if (d > 0.5) discard;
    gl_FragColor = vec4(vColor, smoothstep(0.5, 0.15, d) * vAlpha);
  }
`;

const LINE_VERT = /* glsl */ `
  uniform float uLineAlpha;
  varying float vAlpha;
  ${MORPH}
  void main() {
    vec3 pos = morph();
    vAlpha = uLineAlpha;
    gl_Position = projectionMatrix * modelViewMatrix * vec4(pos, 1.0);
  }
`;

const LINE_FRAG = /* glsl */ `
  uniform vec3 uColor;
  varying float vAlpha;
  void main() { gl_FragColor = vec4(uColor, vAlpha); }
`;

function morphGeometry(field: Field, idx: Uint32Array | null) {
  const g = new THREE.BufferGeometry();
  const pick = (src: Float32Array, w: number) => {
    if (!idx) return src;
    const out = new Float32Array(idx.length * w);
    idx.forEach((v, j) => out.set(src.subarray(v * w, v * w + w), j * w));
    return out;
  };
  const count = idx ? idx.length : field.n;
  g.setAttribute("position", new THREE.BufferAttribute(pick(field.p[1], 3), 3));
  field.p.forEach((arr, k) => g.setAttribute(`p${k}`, new THREE.BufferAttribute(pick(arr, 3), 3)));
  g.setAttribute("hl", new THREE.BufferAttribute(pick(field.hl, 4), 4));
  g.setAttribute("seed", new THREE.BufferAttribute(pick(field.seed, 1), 1));
  if (!idx) {
    g.setAttribute("color", new THREE.BufferAttribute(field.color, 3));
    g.setAttribute("size", new THREE.BufferAttribute(field.size, 1));
    g.setAttribute("alpha", new THREE.BufferAttribute(field.alpha, 1));
  }
  g.boundingSphere = new THREE.Sphere(new THREE.Vector3(), 12);
  void count;
  return g;
}

const CAMERA: [number, number, number][] = [
  [0, 0.6, 9.4],
  [0, 3.8, 9.4],
  [0, 0.15, 8.2],
  [0, 2.6, 8.6],
];

function Scene({ world, mode, animate, mobile, dark }: { world: WorldCompact; mode: number; animate: boolean; mobile: boolean; dark: boolean }) {
  const field = useMemo(() => buildField(world, mobile), [world, mobile]);
  const group = useRef<THREE.Group>(null);
  const pts = useRef<THREE.Points>(null);
  const pulsePts = useRef<THREE.Points>(null);
  const lineRef = useRef<THREE.LineSegments>(null);
  const scamRef = useRef<THREE.LineSegments>(null);
  const live = useRef({ state: mode, time: 0, rot: 0, mouse: new THREE.Vector3(99, 99, 99), mouseOn: 0, click: new THREE.Vector3(99, 99, 99), clickT: 10, pointer: new THREE.Vector2(9, 9), pendingClick: false });
  const { gl, invalidate } = useThree();

  const volt = useMemo(() => new THREE.Color(dark ? "#d7ff3a" : "#4d7c0f").multiplyScalar(dark ? 1.5 : 1), [dark]);
  const uniforms = useMemo(
    () => ({
      uState: { value: 0 },
      uTime: { value: 0 },
      uMouse: { value: new THREE.Vector3(99, 99, 99) },
      uMouseOn: { value: 0 },
      uClick: { value: new THREE.Vector3(99, 99, 99) },
      uClickT: { value: 10 },
      uScale: { value: 6 },
      uVolt: { value: volt },
    }),
    [volt],
  );

  const pointMat = useMemo(
    () =>
      new THREE.ShaderMaterial({
        vertexShader: POINT_VERT,
        fragmentShader: POINT_FRAG,
        uniforms,
        transparent: true,
        depthWrite: false,
        blending: dark ? THREE.AdditiveBlending : THREE.NormalBlending,
      }),
    [uniforms, dark],
  );
  const lineMat = useMemo(
    () =>
      new THREE.ShaderMaterial({
        vertexShader: LINE_VERT,
        fragmentShader: LINE_FRAG,
        uniforms: { ...uniforms, uLineAlpha: { value: 0.06 }, uColor: { value: new THREE.Color(dark ? "#ffffff" : "#0a0a0a") } },
        transparent: true,
        depthWrite: false,
      }),
    [uniforms, dark],
  );
  const scamMat = useMemo(
    () =>
      new THREE.ShaderMaterial({
        vertexShader: LINE_VERT,
        fragmentShader: LINE_FRAG,
        uniforms: { ...uniforms, uLineAlpha: { value: 0.5 }, uColor: { value: volt } },
        transparent: true,
        depthWrite: false,
      }),
    [uniforms, volt],
  );

  const pointGeo = useMemo(() => morphGeometry(field, null), [field]);
  const lineGeo = useMemo(() => morphGeometry(field, field.lines), [field]);
  const scamGeo = useMemo(() => morphGeometry(field, field.scamLines), [field]);
  const pulseGeo = useMemo(() => {
    const g = new THREE.BufferGeometry();
    const m = field.pulses.length;
    const col = new Float32Array(m * 3);
    const c = new THREE.Color();
    field.pulses.forEach((q, i) => {
      c.set(q.scam ? (dark ? "#d7ff3a" : "#4d7c0f") : dark ? "#ffffff" : "#0a0a0a");
      if (q.scam && dark) c.multiplyScalar(1.8);
      col.set([c.r, c.g, c.b], i * 3);
    });
    g.setAttribute("position", new THREE.BufferAttribute(new Float32Array(m * 3), 3));
    g.setAttribute("color", new THREE.BufferAttribute(col, 3));
    g.setAttribute("size", new THREE.BufferAttribute(new Float32Array(m).fill(4), 1));
    g.setAttribute("alpha", new THREE.BufferAttribute(new Float32Array(m), 1));
    g.boundingSphere = new THREE.Sphere(new THREE.Vector3(), 12);
    return g;
  }, [field, dark]);
  const pulseMat = useMemo(
    () =>
      new THREE.ShaderMaterial({
        vertexShader: /* glsl */ `
          attribute vec3 color; attribute float size; attribute float alpha; uniform float uScale;
          varying vec3 vColor; varying float vAlpha;
          void main() { vColor = color; vAlpha = alpha; vec4 mv = modelViewMatrix * vec4(position, 1.0);
            gl_PointSize = size * uScale / -mv.z; gl_Position = projectionMatrix * mv; }`,
        fragmentShader: POINT_FRAG,
        uniforms: { uScale: uniforms.uScale },
        transparent: true,
        depthWrite: false,
        blending: dark ? THREE.AdditiveBlending : THREE.NormalBlending,
      }),
    [uniforms, dark],
  );

  // pointer + click in the plane facing the camera, converted to the group's local space
  useEffect(() => {
    const el = gl.domElement;
    const inside = (e: PointerEvent) => {
      const rect = el.getBoundingClientRect();
      return e.clientX >= rect.left && e.clientX <= rect.right && e.clientY >= rect.top && e.clientY <= rect.bottom;
    };
    const onMove = (e: PointerEvent) => {
      const rect = el.getBoundingClientRect();
      live.current.pointer.set(((e.clientX - rect.left) / rect.width) * 2 - 1, -((e.clientY - rect.top) / rect.height) * 2 + 1);
      live.current.mouseOn = inside(e) && e.pointerType === "mouse" ? 1 : 0;
      invalidate();
    };
    const onDown = (e: PointerEvent) => {
      if (!inside(e) || (e.target instanceof Element && e.target.closest("a,button,input,textarea,select,[role=tab]"))) return;
      const rect = el.getBoundingClientRect();
      live.current.pointer.set(((e.clientX - rect.left) / rect.width) * 2 - 1, -((e.clientY - rect.top) / rect.height) * 2 + 1);
      live.current.pendingClick = true;
      invalidate();
    };
    window.addEventListener("pointermove", onMove, { passive: true });
    window.addEventListener("pointerdown", onDown, { passive: true });
    return () => {
      window.removeEventListener("pointermove", onMove);
      window.removeEventListener("pointerdown", onDown);
    };
  }, [gl, invalidate]);

  useEffect(() => {
    if (!animate) live.current.state = mode;
    invalidate();
  }, [mode, animate, invalidate]);

  const scratch = useRef({ ray: new THREE.Raycaster(), plane: new THREE.Plane(), hit: new THREE.Vector3(), a: new THREE.Vector3(), b: new THREE.Vector3() });

  useFrame(({ camera, size }, dt) => {
    const L = live.current;
    const { ray, plane, hit, a: tmpA, b: tmpB } = scratch.current;
    const U = (pts.current?.material as THREE.ShaderMaterial | undefined)?.uniforms;
    if (!U) return;
    const step = animate ? Math.min(dt, 0.05) : 0;
    L.time += step;
    L.state += (mode - L.state) * (animate ? Math.min(1, step * 1.6) : 1);
    L.clickT = Math.min(10, L.clickT + (animate ? step : 10));
    const g = group.current;
    if (!g) return;

    // slow turn, facing the viewer when the field forms the mark
    const facing = Math.max(0, 1 - Math.abs(L.state - 2));
    const turn = Math.round(L.rot / (Math.PI * 2)) * Math.PI * 2;
    L.rot += step * 0.06 * (1 - facing);
    L.rot += (turn - L.rot) * facing * Math.min(1, step * 2);
    g.rotation.y = L.rot;

    // camera eases toward the view of the current mode
    const lo = Math.floor(Math.min(L.state, 2.999));
    const f = L.state - lo;
    const cam = CAMERA[lo].map((v, k) => v + (CAMERA[lo + 1][k] - v) * f);
    const half = Math.tan(((42 / 2) * Math.PI) / 180);
    const fitR = 3.6;
    const len = Math.hypot(cam[0], cam[1], cam[2]);
    const need = Math.max(len, (fitR * 1.05) / half, fitR / (half * (size.width / Math.max(1, size.height))));
    const zoom = need / len;
    camera.position.set(cam[0] * zoom + L.pointer.x * 0.25 * L.mouseOn, cam[1] * zoom, cam[2] * zoom);
    camera.lookAt(0, 0.1, 0);
    camera.updateMatrixWorld();

    // pointer ray onto the plane through the origin, facing the camera
    plane.setFromNormalAndCoplanarPoint(camera.getWorldDirection(tmpA).negate(), new THREE.Vector3());
    ray.setFromCamera(L.pointer, camera);
    if (ray.ray.intersectPlane(plane, hit)) L.mouse.copy(g.worldToLocal(hit.clone()));
    if (L.pendingClick) {
      L.click.copy(L.mouse);
      L.clickT = 0;
      L.pendingClick = false;
    }

    U.uState.value = L.state;
    U.uTime.value = L.time;
    U.uMouse.value.copy(L.mouse);
    U.uMouseOn.value += (L.mouseOn - U.uMouseOn.value) * 0.08;
    U.uClick.value.copy(L.click);
    U.uClickT.value = L.clickT;
    U.uScale.value = gl.getPixelRatio() * Math.max(0.7, size.height / 800) * 6.5;

    // lines: everyday links fade in the mark view; scam links stay
    const lm = lineRef.current?.material as THREE.ShaderMaterial | undefined;
    if (lm) lm.uniforms.uLineAlpha.value = (dark ? 0.06 : 0.08) * (1 - facing) * (1 - Math.max(0, L.state - 2) * 0.7);
    const sm = scamRef.current?.material as THREE.ShaderMaterial | undefined;
    if (sm) sm.uniforms.uLineAlpha.value = (dark ? 0.45 : 0.6) * (1 - facing * 0.8);

    // pulses travel along links (positions blended like the particles, without the per-particle stagger)
    const pp = pulsePts.current;
    if (!pp) return;
    const pos = pp.geometry.attributes.position.array as Float32Array;
    const al = pp.geometry.attributes.alpha.array as Float32Array;
    const sz = pp.geometry.attributes.size.array as Float32Array;
    const fs = f * f * (3 - 2 * f);
    const A = field.p[lo];
    const B = field.p[Math.min(3, lo + 1)];
    const at = (out: THREE.Vector3, i: number) =>
      out.set(A[i * 3] + (B[i * 3] - A[i * 3]) * fs, A[i * 3 + 1] + (B[i * 3 + 1] - A[i * 3 + 1]) * fs, A[i * 3 + 2] + (B[i * 3 + 2] - A[i * 3 + 2]) * fs);
    field.pulses.forEach((q, i) => {
      const u = (L.time * q.speed * (q.scam ? 0.6 : 1) + q.offset) % 1;
      at(tmpA, q.a);
      at(tmpB, q.b);
      // scam sparks stop halfway (the pause) in the layers view
      const stopAt = q.scam ? 0.55 + 0.45 * (1 - Math.max(0, 1 - Math.abs(L.state - 1))) : 1;
      const uu = Math.min(u, stopAt);
      tmpA.lerp(tmpB, uu);
      pos.set([tmpA.x, tmpA.y, tmpA.z], i * 3);
      al[i] = (q.scam ? 1 : 0.55 * Math.sin(Math.PI * u)) * (1 - facing);
      sz[i] = q.scam ? (u >= stopAt ? 9 + 3 * Math.sin(L.time * 6) : 7) : 3.6;
    });
    pp.geometry.attributes.position.needsUpdate = true;
    pp.geometry.attributes.alpha.needsUpdate = true;
    pp.geometry.attributes.size.needsUpdate = true;
  });

  return (
    <group ref={group}>
      <lineSegments ref={lineRef} geometry={lineGeo} material={lineMat} frustumCulled={false} />
      <lineSegments ref={scamRef} geometry={scamGeo} material={scamMat} frustumCulled={false} />
      <points ref={pts} geometry={pointGeo} material={pointMat} frustumCulled={false} />
      <points ref={pulsePts} geometry={pulseGeo} material={pulseMat} frustumCulled={false} />
    </group>
  );
}

export default function TrustScene({ world, mode, dark, animate, mobile }: { world: WorldCompact; mode: number; dark: boolean; animate: boolean; mobile: boolean }) {
  return (
    <Canvas
      dpr={[1, mobile ? 1.5 : 1.75]}
      camera={{ position: CAMERA[mode], fov: 42 }}
      gl={{ antialias: true, alpha: true, powerPreference: "high-performance" }}
      frameloop={animate ? "always" : "demand"}
      fallback={null}
      style={{ touchAction: "pan-y" }}
    >
      <Scene world={world} mode={mode} animate={animate} mobile={mobile} dark={dark} />
      {dark && !mobile && (
        <EffectComposer multisampling={0}>
          <Bloom intensity={0.85} luminanceThreshold={0.85} luminanceSmoothing={0.2} mipmapBlur />
        </EffectComposer>
      )}
    </Canvas>
  );
}
