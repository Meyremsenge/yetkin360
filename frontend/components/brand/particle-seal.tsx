"use client";

import { useEffect, useRef, useState } from "react";
import { cn } from "@/lib/utils";
import { SealMark } from "./brand-mark";
import { useReducedMotion } from "./use-reduced-motion";
import {
  SEAL_CHECK_PATH,
  SEAL_CHECK_STROKE,
  SEAL_INNER_RING,
  SEAL_RING_PATH,
} from "./seal-geometry";

/*
 * Particle seal: scattered dots ("loose claims") gather into the Yetkin360
 * seal, breathe in place, tilt toward the pointer and part around it.
 * Clicking scatters them again. Plain 2D canvas with a light perspective
 * projection — no WebGL dependency.
 *
 * Gates: with `prefers-reduced-motion` (or no canvas) the static SVG mark is
 * shown instead and no animation loop ever starts. The loop pauses while the
 * scene is off-screen.
 */

// Palette (paper-ink-seal): pine shades for the seal, ochre for a few sparks.
const COLORS = [
  "#265445", // 0 pine — outer band
  "#3B7560", // 1 light pine — outer band highlights
  "#1C4236", // 2 deep pine — check mark
  "#6E9A7C", // 3 sage — inner ring
  "#B98330", // 4 ochre spark
  "#D9A85B", // 5 light ochre spark
] as const;

const SAMPLE_GRID = 200;
const FOCAL = 3.2;

interface Scene {
  count: number;
  floaters: number;
  tx: Float32Array;
  ty: Float32Array;
  tz: Float32Array;
  x: Float32Array;
  y: Float32Array;
  z: Float32Array;
  phase: Float32Array;
  speed: Float32Array;
  size: Float32Array;
  color: Uint8Array;
}

function makeSprite(color: string): HTMLCanvasElement {
  const size = 32;
  const canvas = document.createElement("canvas");
  canvas.width = size;
  canvas.height = size;
  const ctx = canvas.getContext("2d");
  if (!ctx) return canvas;
  const g = ctx.createRadialGradient(size / 2, size / 2, 0, size / 2, size / 2, size / 2);
  g.addColorStop(0, color);
  g.addColorStop(0.55, color);
  g.addColorStop(1, "rgba(255,255,255,0)");
  ctx.fillStyle = g;
  ctx.fillRect(0, 0, size, size);
  return canvas;
}

/** Rasterises the seal with one colour channel per part and samples it. */
function sampleSeal(): { x: number; y: number; part: 0 | 1 | 2 }[] {
  const canvas = document.createElement("canvas");
  canvas.width = SAMPLE_GRID;
  canvas.height = SAMPLE_GRID;
  const ctx = canvas.getContext("2d", { willReadFrequently: true });
  if (!ctx) return [];
  ctx.scale(SAMPLE_GRID / 100, SAMPLE_GRID / 100);

  ctx.fillStyle = "rgb(255,0,0)";
  ctx.fill(new Path2D(SEAL_RING_PATH), "evenodd");

  ctx.strokeStyle = "rgb(0,255,0)";
  ctx.lineWidth = SEAL_INNER_RING.strokeWidth * 1.4;
  ctx.beginPath();
  ctx.arc(50, 50, SEAL_INNER_RING.r, 0, Math.PI * 2);
  ctx.stroke();

  ctx.strokeStyle = "rgb(0,0,255)";
  ctx.lineWidth = SEAL_CHECK_STROKE;
  ctx.lineCap = "round";
  ctx.lineJoin = "round";
  ctx.stroke(new Path2D(SEAL_CHECK_PATH));

  const { data } = ctx.getImageData(0, 0, SAMPLE_GRID, SAMPLE_GRID);
  const points: { x: number; y: number; part: 0 | 1 | 2 }[] = [];
  for (let py = 0; py < SAMPLE_GRID; py += 1) {
    for (let px = 0; px < SAMPLE_GRID; px += 1) {
      const i = (py * SAMPLE_GRID + px) * 4;
      if (data[i + 3] < 128) continue;
      const r = data[i];
      const g = data[i + 1];
      const b = data[i + 2];
      const part = b >= r && b >= g ? 2 : g >= r ? 1 : 0;
      // Normalised to [-1, 1] with a sub-pixel jitter so no grid shows.
      points.push({
        x: ((px + Math.random()) / SAMPLE_GRID) * 2 - 1,
        y: ((py + Math.random()) / SAMPLE_GRID) * 2 - 1,
        part,
      });
    }
  }
  return points;
}

function buildScene(target: number): Scene | null {
  const sampled = sampleSeal();
  if (sampled.length === 0) return null;

  // Shuffle-free random pick: keep each point with probability target/len.
  const keep = Math.min(1, target / sampled.length);
  const chosen = sampled.filter(() => Math.random() < keep);
  const floaters = Math.round(target * 0.035);
  const count = chosen.length + floaters;

  const s: Scene = {
    count,
    floaters,
    tx: new Float32Array(count),
    ty: new Float32Array(count),
    tz: new Float32Array(count),
    x: new Float32Array(count),
    y: new Float32Array(count),
    z: new Float32Array(count),
    phase: new Float32Array(count),
    speed: new Float32Array(count),
    size: new Float32Array(count),
    color: new Uint8Array(count),
  };

  for (let i = 0; i < count; i += 1) {
    const floater = i >= chosen.length;
    const p = floater ? null : chosen[i];
    if (p) {
      s.tx[i] = p.x;
      s.ty[i] = p.y;
      s.tz[i] = (Math.random() - 0.5) * (p.part === 2 ? 0.08 : 0.16);
    } else {
      // Free floaters drift around the seal: alive, never part of the shape.
      const angle = Math.random() * Math.PI * 2;
      const radius = 1.15 + Math.random() * 0.55;
      s.tx[i] = Math.cos(angle) * radius;
      s.ty[i] = Math.sin(angle) * radius;
      s.tz[i] = (Math.random() - 0.5) * 0.8;
    }
    s.x[i] = (Math.random() - 0.5) * 5.5;
    s.y[i] = (Math.random() - 0.5) * 4;
    s.z[i] = (Math.random() - 0.5) * 2.4;
    s.phase[i] = Math.random() * Math.PI * 2;
    s.speed[i] = 0.5 + Math.random() * 0.7;

    const spark = Math.random() < 0.05;
    if (floater) {
      s.color[i] = Math.random() < 0.5 ? 4 : 3;
      s.size[i] = 0.9 + Math.random() * 0.8;
    } else if (spark) {
      s.color[i] = Math.random() < 0.5 ? 4 : 5;
      s.size[i] = 1.2 + Math.random() * 0.5;
    } else if (p?.part === 2) {
      s.color[i] = 2;
      s.size[i] = 0.95 + Math.random() * 0.3;
    } else if (p?.part === 1) {
      s.color[i] = 3;
      s.size[i] = 0.8 + Math.random() * 0.25;
    } else {
      s.color[i] = Math.random() < 0.22 ? 1 : 0;
      s.size[i] = 0.85 + Math.random() * 0.35;
    }
  }
  return s;
}

export function ParticleSeal({
  className,
  particles = 4200,
}: {
  className?: string;
  /** Desktop particle budget; halved on narrow screens. */
  particles?: number;
}) {
  const hostRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const reduced = useReducedMotion();
  const [failed, setFailed] = useState(false);
  const isStatic = reduced || failed;

  useEffect(() => {
    const host = hostRef.current;
    const canvas = canvasRef.current;
    if (!host || !canvas || reduced) return;

    const ctx = typeof Path2D === "undefined" ? null : canvas.getContext("2d");
    const narrow = window.matchMedia("(max-width: 767px)").matches;
    const scene = ctx ? buildScene(narrow ? Math.round(particles * 0.5) : particles) : null;
    if (!ctx || !scene) {
      const id = requestAnimationFrame(() => setFailed(true));
      return () => cancelAnimationFrame(id);
    }

    const sprites = COLORS.map(makeSprite);
    let width = 0;
    let height = 0;
    let dpr = 1;

    const resize = () => {
      width = host.clientWidth;
      height = host.clientHeight;
      dpr = Math.min(window.devicePixelRatio || 1, 2);
      canvas.width = Math.max(1, Math.round(width * dpr));
      canvas.height = Math.max(1, Math.round(height * dpr));
    };
    resize();
    const resizeObserver = new ResizeObserver(resize);
    resizeObserver.observe(host);

    // Pointer in container NDC ([-1, 1]); `inside` drives tilt and repel.
    const pointer = { x: 0, y: 0, inside: false };
    const tilt = { x: 0, y: 0 };
    let t = 0;
    let slowUntil = 2.6; // gather slowly at first: "the seal is forming"

    const onMove = (event: PointerEvent) => {
      const rect = host.getBoundingClientRect();
      pointer.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
      pointer.y = ((event.clientY - rect.top) / rect.height) * 2 - 1;
      pointer.inside = true;
    };
    const onLeave = () => {
      pointer.inside = false;
    };
    const onDown = () => {
      // Scatter: push every particle outward, then let them regather.
      for (let i = 0; i < scene.count; i += 1) {
        const angle = Math.atan2(scene.y[i], scene.x[i]) + (Math.random() - 0.5) * 1.2;
        const force = 1.2 + Math.random() * 2.2;
        scene.x[i] += Math.cos(angle) * force;
        scene.y[i] += Math.sin(angle) * force;
        scene.z[i] += (Math.random() - 0.5) * 2;
      }
      slowUntil = t + 1.6;
    };
    host.addEventListener("pointermove", onMove);
    host.addEventListener("pointerleave", onLeave);
    host.addEventListener("pointerdown", onDown);

    let frame = 0;
    let running = false;
    let last = 0;

    const draw = (now: number) => {
      const dt = Math.min(0.05, last ? (now - last) / 1000 : 0.016);
      last = now;
      t += dt;

      const scale = Math.min(width, height) * 0.42;
      const cx = width / 2;
      const cy = height / 2;

      // Tilt follows the pointer; idle sway keeps it alive when untouched.
      const wantX = pointer.inside ? pointer.y * 0.3 : Math.sin(t * 0.35) * 0.06;
      const wantY = pointer.inside ? pointer.x * 0.4 : Math.sin(t * 0.5) * 0.14;
      const tiltEase = 1 - Math.pow(0.92, dt * 60);
      tilt.x += (wantX - tilt.x) * tiltEase;
      tilt.y += (wantY - tilt.y) * tiltEase;
      const cosY = Math.cos(tilt.y);
      const sinY = Math.sin(tilt.y);
      const cosX = Math.cos(tilt.x);
      const sinX = Math.sin(tilt.x);

      // Pointer in seal units (z = 0 plane; tilt is small enough to ignore).
      const px = ((pointer.x * width) / 2) / scale;
      const py = ((pointer.y * height) / 2) / scale;
      const repelRadius = 0.24;
      const repelStrength = 0.22;

      const ease = 1 - Math.pow(1 - (t < slowUntil ? 0.035 : 0.11), dt * 60);
      const basePx = scale * 0.02;

      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      ctx.clearRect(0, 0, width, height);

      for (let i = 0; i < scene.count; i += 1) {
        const floater = i >= scene.count - scene.floaters;
        const amp = floater ? 0.09 : 0.012;
        const ph = scene.phase[i];
        const sp = scene.speed[i];
        let hx = scene.tx[i] + Math.sin(t * sp + ph) * amp;
        let hy = scene.ty[i] + Math.cos(t * sp * 0.8 + ph) * amp;
        const hz = scene.tz[i];

        if (pointer.inside) {
          const dx = hx - px;
          const dy = hy - py;
          const dist = Math.sqrt(dx * dx + dy * dy);
          if (dist < repelRadius && dist > 0.0001) {
            const push = (1 - dist / repelRadius) * repelStrength;
            hx += (dx / dist) * push;
            hy += (dy / dist) * push;
          }
        }

        scene.x[i] += (hx - scene.x[i]) * ease;
        scene.y[i] += (hy - scene.y[i]) * ease;
        scene.z[i] += (hz - scene.z[i]) * ease;

        // Rotate (Y then X) and project.
        const x1 = scene.x[i] * cosY + scene.z[i] * sinY;
        const z1 = -scene.x[i] * sinY + scene.z[i] * cosY;
        const y2 = scene.y[i] * cosX - z1 * sinX;
        const z2 = scene.y[i] * sinX + z1 * cosX;
        const persp = FOCAL / (FOCAL - z2);
        if (persp <= 0) continue;

        const sx = cx + x1 * persp * scale;
        const sy = cy + y2 * persp * scale;
        const size = basePx * scene.size[i] * persp;
        const alpha = floater ? 0.35 : Math.min(1, 0.62 + z2 * 0.9);

        ctx.globalAlpha = Math.max(0.15, alpha);
        ctx.drawImage(sprites[scene.color[i]], sx - size / 2, sy - size / 2, size, size);
      }
      ctx.globalAlpha = 1;
      frame = requestAnimationFrame(draw);
    };

    const start = () => {
      if (running) return;
      running = true;
      last = 0;
      frame = requestAnimationFrame(draw);
    };
    const stop = () => {
      running = false;
      cancelAnimationFrame(frame);
    };

    const visibility = new IntersectionObserver(([entry]) => {
      if (entry?.isIntersecting) start();
      else stop();
    });
    visibility.observe(host);

    return () => {
      stop();
      visibility.disconnect();
      resizeObserver.disconnect();
      host.removeEventListener("pointermove", onMove);
      host.removeEventListener("pointerleave", onLeave);
      host.removeEventListener("pointerdown", onDown);
    };
  }, [particles, reduced]);

  return (
    <div ref={hostRef} className={cn("relative touch-pan-y select-none", className)}>
      <canvas
        ref={canvasRef}
        aria-hidden="true"
        className={cn(
          "absolute inset-0 h-full w-full",
          isStatic ? "hidden" : "cursor-pointer"
        )}
      />
      {isStatic ? (
        <div className="absolute inset-0 flex items-center justify-center">
          <SealMark className="h-[78%] w-[78%]" />
        </div>
      ) : null}
    </div>
  );
}
