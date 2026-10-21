import { useEffect, useRef } from "react";

// Decorative identifier for the illustration; it is not a real trace.
const ILLUSTRATION_ID = "9b074ca796634ff9bc061626760edfb3";
const BACKGROUND = "#070808";
const LENS_REST = { x: 0.375, y: 0.6 };

type Lens = { x: number; y: number; tx: number; ty: number; r: number };

function applyVignette(canvas: HTMLCanvasElement, w: number, h: number) {
  const g = canvas.getContext("2d");
  if (!g) return;
  g.save();
  g.globalCompositeOperation = "destination-in";
  g.translate(w / 2, h * 0.52);
  g.scale(1, h / w);
  const fade = g.createRadialGradient(0, 0, w * 0.3, 0, 0, w * 0.52);
  fade.addColorStop(0, "rgba(0,0,0,1)");
  fade.addColorStop(1, "rgba(0,0,0,0)");
  g.fillStyle = fade;
  g.fillRect(-w, -w, w * 2, w * 2);
  g.restore();
}

// Redraws the photo with the identifier's characters, brightness mapped to opacity.
function buildGlyphLayer(
  image: HTMLImageElement,
  w: number,
  h: number,
  dpr: number,
) {
  const layer = document.createElement("canvas");
  layer.width = Math.round(w * dpr);
  layer.height = Math.round(h * dpr);
  const g = layer.getContext("2d");
  if (!g) return null;
  g.scale(dpr, dpr);
  const cw = w < 500 ? 6 : 7.2;
  const ch = cw * 1.45;
  const cols = Math.floor(w / cw);
  const rows = Math.floor(h / ch);
  const sample = document.createElement("canvas");
  sample.width = cols;
  sample.height = rows;
  const s = sample.getContext("2d", { willReadFrequently: true });
  if (!s) return null;
  s.drawImage(image, 0, 0, cols, rows);
  const data = s.getImageData(0, 0, cols, rows).data;
  g.font = `500 ${cw * 1.32}px "IBM Plex Mono", monospace`;
  g.textBaseline = "top";
  let k = 0;
  for (let y = 0; y < rows; y++) {
    for (let x = 0; x < cols; x++, k++) {
      const i = (y * cols + x) * 4;
      const l =
        (0.2126 * data[i] + 0.7152 * data[i + 1] + 0.0722 * data[i + 2]) / 255;
      const alpha = Math.min(1, 0.07 + Math.pow(l, 0.85) * 1.5);
      g.fillStyle =
        l > 0.55 ? `rgba(236,235,230,${alpha})` : `rgba(95,224,208,${alpha})`;
      g.fillText(ILLUSTRATION_ID[k % ILLUSTRATION_ID.length], x * cw, y * ch);
    }
  }
  g.setTransform(1, 0, 0, 1, 0, 0);
  g.scale(dpr, dpr);
  applyVignette(layer, w, h);
  return layer;
}

export function TraceLens() {
  const stageRef = useRef<HTMLDivElement>(null);
  const imageRef = useRef<HTMLImageElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const stage = stageRef.current;
    const image = imageRef.current;
    const canvas = canvasRef.current;
    if (!stage || !image || !canvas) return;
    let ctx: CanvasRenderingContext2D | null = null;
    const reduceMotion = window.matchMedia?.(
      "(prefers-reduced-motion: reduce)",
    ).matches;
    const touchOnly = window.matchMedia?.("(hover: none)").matches;
    let glyphs: HTMLCanvasElement | null = null;
    let w = 0;
    let h = 0;
    let dpr = 1;
    let frame = 0;
    let hovering = false;
    let visible = true;
    let disposed = false;
    const lens: Lens = { x: 0, y: 0, tx: 0, ty: 0, r: 0 };

    const clampTarget = (x: number, y: number) => {
      const m = lens.r + 4;
      lens.tx = Math.max(m, Math.min(w - m, x));
      lens.ty = Math.max(m, Math.min(h - m, y));
    };
    const draw = () => {
      if (!ctx || !glyphs) return;
      ctx.setTransform(1, 0, 0, 1, 0, 0);
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      ctx.scale(dpr, dpr);
      ctx.beginPath();
      ctx.arc(lens.x, lens.y, lens.r, 0, Math.PI * 2);
      ctx.save();
      ctx.clip();
      ctx.fillStyle = BACKGROUND;
      ctx.fillRect(0, 0, w, h);
      ctx.drawImage(glyphs, 0, 0, w, h);
      ctx.restore();
      ctx.strokeStyle = "rgba(95,224,208,0.85)";
      ctx.lineWidth = 1;
      ctx.stroke();
      ctx.beginPath();
      for (const [dx, dy] of [
        [1, 0],
        [-1, 0],
        [0, 1],
        [0, -1],
      ]) {
        ctx.moveTo(lens.x + dx * (lens.r - 6), lens.y + dy * (lens.r - 6));
        ctx.lineTo(lens.x + dx * (lens.r + 6), lens.y + dy * (lens.r + 6));
      }
      ctx.stroke();
      const label = "trace layer · illustration";
      ctx.font = '500 10.5px "IBM Plex Mono", monospace';
      const tw = ctx.measureText(label).width + 12;
      const lx = Math.min(lens.x + lens.r * 0.72, w - tw - 2);
      const ly = Math.min(lens.y + lens.r * 0.72, h - 22);
      ctx.fillStyle = BACKGROUND;
      ctx.fillRect(lx, ly, tw, 20);
      ctx.strokeStyle = "rgba(95,224,208,0.35)";
      ctx.strokeRect(lx + 0.5, ly + 0.5, tw - 1, 19);
      ctx.fillStyle = "#5fe0d0";
      ctx.textBaseline = "middle";
      ctx.fillText(label, lx + 6, ly + 10.5);
    };
    const autoDrift = touchOnly && !reduceMotion;
    const tick = (t: number) => {
      frame = 0;
      if (disposed || !glyphs) return;
      if (autoDrift && !hovering) {
        clampTarget(
          w * (0.5 + 0.3 * Math.sin(t / 2200)),
          h * (0.55 + 0.18 * Math.cos(t / 1700)),
        );
      }
      const ease = reduceMotion ? 1 : 0.16;
      lens.x += (lens.tx - lens.x) * ease;
      lens.y += (lens.ty - lens.y) * ease;
      draw();
      const moving =
        Math.abs(lens.tx - lens.x) > 0.3 || Math.abs(lens.ty - lens.y) > 0.3;
      if (visible && (moving || autoDrift)) frame = requestAnimationFrame(tick);
    };
    const wake = () => {
      if (!frame && !disposed) frame = requestAnimationFrame(tick);
    };
    const layout = () => {
      w = stage.clientWidth;
      h = stage.clientHeight;
      if (!w || !h) return;
      ctx ??= canvas.getContext("2d");
      if (!ctx) return;
      dpr = Math.min(window.devicePixelRatio || 1, 2);
      canvas.width = Math.round(w * dpr);
      canvas.height = Math.round(h * dpr);
      lens.r = Math.min(w * 0.17, 130);
      if (!hovering) {
        clampTarget(w * LENS_REST.x, h * LENS_REST.y);
        lens.x = lens.tx;
        lens.y = lens.ty;
      }
      glyphs = buildGlyphLayer(image, w, h, dpr);
      wake();
    };
    // The photo shows immediately; the trace layer is built once the page is idle.
    const start = () => {
      const run = () => {
        if (disposed) return;
        const fonts = document.fonts?.load('500 10px "IBM Plex Mono"');
        void (fonts ?? Promise.resolve()).catch(() => undefined).then(layout);
      };
      if ("requestIdleCallback" in window)
        window.requestIdleCallback(run, { timeout: 800 });
      else setTimeout(run, 120);
    };
    if (image.complete && image.naturalWidth) start();
    else image.addEventListener("load", start, { once: true });

    const onMove = (event: PointerEvent) => {
      const box = stage.getBoundingClientRect();
      hovering = true;
      clampTarget(event.clientX - box.left, event.clientY - box.top);
      wake();
    };
    const onLeave = () => {
      hovering = false;
      clampTarget(w * LENS_REST.x, h * LENS_REST.y);
      wake();
    };
    stage.addEventListener("pointermove", onMove);
    stage.addEventListener("pointerleave", onLeave);
    const resize =
      typeof ResizeObserver === "undefined"
        ? null
        : new ResizeObserver(() => {
            if (glyphs) layout();
          });
    resize?.observe(stage);
    const seen =
      typeof IntersectionObserver === "undefined"
        ? null
        : new IntersectionObserver(([entry]) => {
            visible = entry.isIntersecting;
            if (visible) wake();
          });
    seen?.observe(stage);
    return () => {
      disposed = true;
      cancelAnimationFrame(frame);
      image.removeEventListener("load", start);
      stage.removeEventListener("pointermove", onMove);
      stage.removeEventListener("pointerleave", onLeave);
      resize?.disconnect();
      seen?.disconnect();
    };
  }, []);

  return (
    <figure className="trace-figure">
      <div className="trace-stage" ref={stageRef}>
        <picture>
          <source srcSet="/hero/camera.webp" type="image/webp" />
          <img
            ref={imageRef}
            src="/hero/camera.jpg"
            alt="A vintage Zenit-E film camera on a dark background"
            width="1200"
            height="900"
            fetchPriority="high"
            decoding="async"
          />
        </picture>
        <canvas ref={canvasRef} aria-hidden="true" />
      </div>
      <figcaption>
        <span>Fig. 1 — the identifier, woven through the pixels</span>
        <span>
          <b aria-hidden="true">●</b> Move over the image to see the trace layer
        </span>
      </figcaption>
    </figure>
  );
}
