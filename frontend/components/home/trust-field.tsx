"use client";

import { Canvas, useFrame } from "@react-three/fiber";
import { Bloom, EffectComposer } from "@react-three/postprocessing";
import { useEffect, useMemo, useRef } from "react";
import * as THREE from "three";

/**
 * The Trust Field: a real sample of the synthetic UVERA world drawn as three layers.
 *   bottom = customers, middle = agents & shops, top = operations (linked cases).
 * Grey sparks are everyday payments. Volt sparks are scam transfers: each one stops at a pause ring
 * (UVERA asks the customer to pause before money moves) and then rises into the one case it belongs to.
 */

export type WorldCompact = {
  source: string;
  nodes: [number, number][];
  edges: [number, number, number, number, number, number][];
};

type Palette = { customer: string; agent: string; merchant: string; flagged: string; volt: string; line: string; dark: boolean };

const LAYER_Y = [-1.3, 0, 1.45];
const GOLDEN = Math.PI * (3 - Math.sqrt(5));
const SEG = 10;

function mulberry32(seed: number) {
  return () => {
    seed |= 0;
    seed = (seed + 0x6d2b79f5) | 0;
    let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

type Route = { a: THREE.Vector3; c: THREE.Vector3; b: THREE.Vector3; speed: number; offset: number };
type ScamRoute = Route & { pause: THREE.Vector3; up?: Route; caseNode: number };

function bezier(out: THREE.Vector3, r: { a: THREE.Vector3; c: THREE.Vector3; b: THREE.Vector3 }, t: number) {
  const u = 1 - t;
  out.set(
    u * u * r.a.x + 2 * u * t * r.c.x + t * t * r.b.x,
    u * u * r.a.y + 2 * u * t * r.c.y + t * t * r.b.y,
    u * u * r.a.z + 2 * u * t * r.c.z + t * t * r.b.z,
  );
  return out;
}

function control(a: THREE.Vector3, b: THREE.Vector3) {
  const mid = a.clone().add(b).multiplyScalar(0.5);
  mid.y += 0.25 + 0.12 * a.distanceTo(b);
  return mid;
}

function buildField(world: WorldCompact, mobile: boolean) {
  const rand = mulberry32(7);
  const n = world.nodes.length;
  const pos = new Float32Array(n * 3);
  const kind = new Uint8Array(n); // 0 customer, 1 agent, 2 merchant, 3 case, 4 flagged customer (mule), 5 flagged merchant
  const groups: number[][] = [[], [], [], []];
  world.nodes.forEach(([t, flag], i) => {
    if (t === 3) groups[3].push(i);
    else if (t === 0 && flag === 1) groups[2].push(i);
    else if (t === 0 || t === 4) groups[0].push(i);
    else groups[1].push(i);
    kind[i] = t === 3 ? 3 : t === 0 ? (flag === 1 ? 4 : 0) : t === 1 ? 1 : flag === 2 ? 5 : 2;
  });
  const spread = mobile ? 0.82 : 1;
  groups[0].forEach((i, k) => {
    const r = spread * 5.9 * Math.sqrt((k + 0.5) / groups[0].length);
    const th = k * GOLDEN;
    pos.set([r * Math.cos(th), LAYER_Y[0] + (rand() - 0.5) * 0.12, r * Math.sin(th)], i * 3);
  });
  groups[2].forEach((i, k) => {
    // money mules sit under the middle of the field, where the scam money converges
    const th = (k / groups[2].length) * Math.PI * 2 + 0.4;
    const r = spread * (0.9 + rand() * 0.5);
    pos.set([r * Math.cos(th), LAYER_Y[0] + 0.05, r * Math.sin(th)], i * 3);
  });
  groups[1].forEach((i, k) => {
    const r = spread * (1.3 + 2.9 * Math.sqrt((k + 0.5) / groups[1].length));
    const th = k * GOLDEN + 1.1;
    pos.set([r * Math.cos(th), LAYER_Y[1] + (rand() - 0.5) * 0.08, r * Math.sin(th)], i * 3);
  });
  groups[3].forEach((i, k) => {
    const th = (k / Math.max(1, groups[3].length)) * Math.PI * 2;
    pos.set([1.05 * Math.cos(th), LAYER_Y[2], 1.05 * Math.sin(th)], i * 3);
  });
  const P = (i: number) => new THREE.Vector3(pos[i * 3], pos[i * 3 + 1], pos[i * 3 + 2]);

  const caseNodeOf = new Map<number, number>();
  world.edges.forEach(([, t, type, , , c]) => {
    if (type === 3 && c >= 0) caseNodeOf.set(c, t);
  });

  const normal: number[] = [];
  const scamLine: number[] = [];
  const routes: Route[] = [];
  const scams: ScamRoute[] = [];
  const tmp = new THREE.Vector3();
  const pushCurve = (arr: number[], r: { a: THREE.Vector3; c: THREE.Vector3; b: THREE.Vector3 }) => {
    let prev = r.a.clone();
    for (let s = 1; s <= SEG; s++) {
      bezier(tmp, r, s / SEG);
      arr.push(prev.x, prev.y, prev.z, tmp.x, tmp.y, tmp.z);
      prev = tmp.clone();
    }
  };
  const maxPulses = mobile ? 140 : 320;
  world.edges.forEach(([s, t, type, , scam, c], k) => {
    if (type === 3) return;
    const a = P(s);
    const b = P(t);
    const r = { a, b, c: control(a, b) };
    if (scam) {
      pushCurve(scamLine, r);
      const caseNode = caseNodeOf.get(c) ?? -1;
      const pause = bezier(new THREE.Vector3(), r, 0.55);
      const sr: ScamRoute = { ...r, speed: 1, offset: rand(), pause, caseNode };
      if (caseNode >= 0) {
        const cb = P(caseNode);
        sr.up = { a: pause, b: cb, c: control(pause, cb), speed: 1, offset: 0 };
        pushCurve(scamLine, sr.up);
      }
      scams.push(sr);
    } else {
      pushCurve(normal, r);
      if (routes.length < maxPulses && (k * 7919) % 5 === 0) routes.push({ ...r, speed: 0.12 + rand() * 0.16, offset: rand() });
    }
  });
  return { pos, kind, n, normal: new Float32Array(normal), scamLine: new Float32Array(scamLine), routes, scams, caseCount: groups[3].length };
}

const POINT_VERT = /* glsl */ `
  attribute float size;
  attribute vec3 color;
  attribute float alpha;
  varying vec3 vColor;
  varying float vAlpha;
  uniform float uScale;
  void main() {
    vColor = color;
    vAlpha = alpha;
    vec4 mv = modelViewMatrix * vec4(position, 1.0);
    gl_PointSize = size * uScale / -mv.z;
    gl_Position = projectionMatrix * mv;
  }
`;
const POINT_FRAG = /* glsl */ `
  varying vec3 vColor;
  varying float vAlpha;
  void main() {
    float d = length(gl_PointCoord - 0.5);
    if (d > 0.5) discard;
    float a = smoothstep(0.5, 0.18, d);
    gl_FragColor = vec4(vColor, a * vAlpha);
  }
`;

function pointsMaterial(blending: THREE.Blending) {
  return new THREE.ShaderMaterial({
    vertexShader: POINT_VERT,
    fragmentShader: POINT_FRAG,
    uniforms: { uScale: { value: 300 } },
    transparent: true,
    depthWrite: false,
    blending,
  });
}

function Scene({ world, palette, animate, mobile }: { world: WorldCompact; palette: Palette; animate: boolean; mobile: boolean }) {
  const field = useMemo(() => buildField(world, mobile), [world, mobile]);
  const group = useRef<THREE.Group>(null);
  const nodes = useRef<THREE.Points>(null);
  const pulses = useRef<THREE.Points>(null);
  const glow = useRef<Float32Array | null>(null);
  const pointer = useRef({ x: 0, y: 0 });
  const clock = useRef(animate ? 0 : 3.1);

  // ---- nodes
  const nodeGeo = useMemo(() => {
    const g = new THREE.BufferGeometry();
    const col = new Float32Array(field.n * 3);
    const sz = new Float32Array(field.n);
    const al = new Float32Array(field.n);
    const c = new THREE.Color();
    for (let i = 0; i < field.n; i++) {
      const k = field.kind[i];
      const hex = k === 0 ? palette.customer : k === 1 ? palette.agent : k === 2 ? palette.merchant : k === 3 || k === 4 ? palette.volt : palette.flagged;
      c.set(hex);
      if (palette.dark && (k === 3 || k === 4)) c.multiplyScalar(1.6); // lets bloom catch only the meaningful nodes
      col.set([c.r, c.g, c.b], i * 3);
      sz[i] = k === 3 ? 26 : k === 4 ? 9 : k === 1 ? 7 : k === 5 ? 7 : k === 2 ? 4.6 : 4;
      al[i] = k === 0 ? 0.55 : k === 2 ? 0.65 : 0.95;
    }
    g.setAttribute("position", new THREE.BufferAttribute(field.pos, 3));
    g.setAttribute("color", new THREE.BufferAttribute(col, 3));
    g.setAttribute("size", new THREE.BufferAttribute(sz, 1));
    g.setAttribute("alpha", new THREE.BufferAttribute(al, 1));
    return g;
  }, [field, palette]);
  const nodeMat = useMemo(() => pointsMaterial(palette.dark ? THREE.AdditiveBlending : THREE.NormalBlending), [palette.dark]);

  // ---- edges
  const edgeGeo = useMemo(() => new THREE.BufferGeometry().setAttribute("position", new THREE.BufferAttribute(field.normal, 3)), [field]);
  const scamGeo = useMemo(() => new THREE.BufferGeometry().setAttribute("position", new THREE.BufferAttribute(field.scamLine, 3)), [field]);

  // ---- pulses (everyday payments + scam transfers)
  const nPulse = field.routes.length + field.scams.length;
  const pulseGeo = useMemo(() => {
    const g = new THREE.BufferGeometry();
    const col = new Float32Array(nPulse * 3);
    const c = new THREE.Color();
    for (let i = 0; i < nPulse; i++) {
      c.set(i < field.routes.length ? palette.agent : palette.volt);
      if (palette.dark && i >= field.routes.length) c.multiplyScalar(2);
      col.set([c.r, c.g, c.b], i * 3);
    }
    g.setAttribute("position", new THREE.BufferAttribute(new Float32Array(nPulse * 3), 3));
    g.setAttribute("color", new THREE.BufferAttribute(col, 3));
    g.setAttribute("size", new THREE.BufferAttribute(new Float32Array(nPulse).fill(5), 1));
    g.setAttribute("alpha", new THREE.BufferAttribute(new Float32Array(nPulse), 1));
    return g;
  }, [field, nPulse, palette]);
  const pulseMat = useMemo(() => pointsMaterial(palette.dark ? THREE.AdditiveBlending : THREE.NormalBlending), [palette.dark]);

  // ---- pause rings
  const rings = useRef<(THREE.Mesh | null)[]>([]);
  const ringGeo = useMemo(() => new THREE.RingGeometry(0.1, 0.122, 48), []);
  const ringMat = useMemo(
    () => new THREE.MeshBasicMaterial({ color: new THREE.Color(palette.volt).multiplyScalar(palette.dark ? 1.8 : 1), transparent: true, depthWrite: false, side: THREE.DoubleSide }),
    [palette],
  );
  const ringMats = useMemo(() => field.scams.map(() => ringMat.clone()), [field, ringMat]);

  useEffect(() => {
    const onMove = (e: PointerEvent) => {
      pointer.current.x = (e.clientX / window.innerWidth) * 2 - 1;
      pointer.current.y = (e.clientY / window.innerHeight) * 2 - 1;
    };
    window.addEventListener("pointermove", onMove, { passive: true });
    return () => window.removeEventListener("pointermove", onMove);
  }, []);

  const tmp = useRef(new THREE.Vector3());
  useFrame(({ camera, gl, size }, dt) => {
    const nodePts = nodes.current;
    const pulsePts = pulses.current;
    if (!nodePts || !pulsePts) return;
    const scale = gl.getPixelRatio() * Math.max(0.7, size.height / 800) * 6.5;
    (nodePts.material as THREE.ShaderMaterial).uniforms.uScale.value = scale;
    (pulsePts.material as THREE.ShaderMaterial).uniforms.uScale.value = scale;
    if (!glow.current || glow.current.length !== field.n) glow.current = new Float32Array(field.n);
    const caseGlow = glow.current;
    const v = tmp.current;
    if (animate) clock.current += Math.min(dt, 0.05);
    const t = clock.current;
    if (group.current) group.current.rotation.y = t * 0.035;
    if (animate) {
      const tx = pointer.current.x * 0.7;
      const ty = (mobile ? 4.6 : 3.7) - pointer.current.y * 0.35;
      camera.position.x += (tx - camera.position.x) * 0.03;
      camera.position.y += (ty - camera.position.y) * 0.03;
      camera.lookAt(0, 0.05, 0);
    }
    const pg = pulsePts.geometry;
    const p = pg.attributes.position.array as Float32Array;
    const a = pg.attributes.alpha.array as Float32Array;
    const s = pg.attributes.size.array as Float32Array;
    field.routes.forEach((r, i) => {
      const u = (t * r.speed + r.offset) % 1;
      bezier(v, r, u);
      p.set([v.x, v.y, v.z], i * 3);
      a[i] = Math.sin(Math.PI * u) * (palette.dark ? 0.55 : 0.6);
      s[i] = 3.6;
    });
    caseGlow.fill(0);
    field.scams.forEach((r, j) => {
      const i = field.routes.length + j;
      const phase = (t / 6.5 + r.offset) % 1; // travel, pause, rise into the case
      let ring = 0;
      if (phase < 0.42) {
        bezier(v, r, (phase / 0.42) * 0.55);
        a[i] = 0.95;
      } else if (phase < 0.72) {
        v.copy(r.pause);
        ring = Math.min(1, (phase - 0.42) / 0.06);
        a[i] = 1;
      } else if (r.up) {
        const u = (phase - 0.72) / 0.28;
        bezier(v, r.up, u);
        a[i] = 1 - u * 0.2;
        if (u > 0.85) caseGlow[r.caseNode] = Math.max(caseGlow[r.caseNode], (u - 0.85) / 0.15);
        ring = Math.max(0, 1 - u * 3);
      } else {
        v.copy(r.pause);
        a[i] = Math.max(0, 1 - (phase - 0.72) / 0.1);
      }
      p.set([v.x, v.y, v.z], i * 3);
      s[i] = 7.5;
      const m = rings.current[j];
      if (m) {
        m.position.copy(r.pause);
        m.quaternion.copy(camera.quaternion);
        const k = ring > 0 ? 0.6 + 0.4 * ring : 0.01;
        m.scale.setScalar(k);
        (m.material as THREE.MeshBasicMaterial).opacity = ring * 0.95;
        m.visible = ring > 0.01;
      }
    });
    const ns = nodePts.geometry.attributes.size.array as Float32Array;
    for (let i = 0; i < field.n; i++) if (field.kind[i] === 3) ns[i] = 26 + 22 * caseGlow[i];
    nodePts.geometry.attributes.size.needsUpdate = true;
    pg.attributes.position.needsUpdate = true;
    pg.attributes.alpha.needsUpdate = true;
    pg.attributes.size.needsUpdate = true;
  });

  return (
    <group ref={group} position={[mobile ? 0 : 1.4, 0, 0]}>
      <lineSegments geometry={edgeGeo}>
        <lineBasicMaterial color={palette.line} transparent opacity={palette.dark ? 0.045 : 0.08} depthWrite={false} />
      </lineSegments>
      <lineSegments geometry={scamGeo}>
        <lineBasicMaterial color={palette.volt} transparent opacity={palette.dark ? 0.35 : 0.6} depthWrite={false} />
      </lineSegments>
      <points ref={nodes} geometry={nodeGeo} material={nodeMat} />
      <points ref={pulses} geometry={pulseGeo} material={pulseMat} />
      {field.scams.map((_, j) => (
        <mesh key={j} ref={(m) => { rings.current[j] = m; }} geometry={ringGeo} material={ringMats[j]} visible={false} />
      ))}
    </group>
  );
}

export default function TrustField({ world, dark, animate, mobile }: { world: WorldCompact; dark: boolean; animate: boolean; mobile: boolean }) {
  const palette: Palette = dark
    ? { customer: "#9a9a9a", agent: "#f5f5f5", merchant: "#bdbdbd", flagged: "#a8c94a", volt: "#d7ff3a", line: "#ffffff", dark }
    : { customer: "#6b6b6b", agent: "#0a0a0a", merchant: "#3f3f46", flagged: "#4d7c0f", volt: "#4d7c0f", line: "#0a0a0a", dark };
  return (
    <Canvas
      dpr={[1, mobile ? 1.5 : 1.75]}
      camera={{ position: [0, mobile ? 4.6 : 3.7, mobile ? 11.5 : 9.2], fov: 42 }}
      gl={{ antialias: true, alpha: true, powerPreference: "high-performance" }}
      frameloop={animate ? "always" : "demand"}
      onCreated={({ camera }) => camera.lookAt(0, 0.05, 0)}
      fallback={null}
    >
      <Scene world={world} palette={palette} animate={animate} mobile={mobile} />
      {dark && !mobile && (
        <EffectComposer multisampling={0}>
          <Bloom intensity={0.9} luminanceThreshold={0.9} luminanceSmoothing={0.2} mipmapBlur />
        </EffectComposer>
      )}
    </Canvas>
  );
}
