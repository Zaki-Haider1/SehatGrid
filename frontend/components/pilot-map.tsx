"use client";
import { useEffect, useRef, useState } from "react";
import { Compass, Minus, Plus, RotateCcw } from "lucide-react";
import type { State } from "@/lib/api";
type Block = {
  x: number;
  z: number;
  w: number;
  d: number;
  h: number;
  color: string;
  id?: string;
};
export type MapLayer = "capacity" | "demand" | "funding";
export function hospitalColor(state: State, id: string, layer: MapLayer) {
  const f = state.facilities.find((f) => f.id === id)!;
  if (f.participation !== "ACTIVE") return "#b9c1ce";
  if (layer === "funding") return f.subsidy_required ? "#e68c92" : "#7397f6";
  if (layer === "demand")
    return (state.summary?.zones.find((z) => z.zone === f.zone)?.count || 0) > 0
      ? "#e68c92"
      : "#7397f6";
  return (
    (
      {
        AVAILABLE: "#7397f6",
        LIMITED: "#e7bd83",
        EXHAUSTED: "#e68c92",
      } as Record<string, string>
    )[f.capacities[0]?.status] || "#b9c1ce"
  );
}
// Public campus coordinates locate hospitals approximately. Context buildings are procedural.
function city(state: State, layer: MapLayer): Block[] {
  const fs = state.facilities,
    xs = fs.map((f) => f.longitude),
    zs = fs.map((f) => f.latitude),
    occupied = new Set<string>();
  const hospitals = fs.map((f, i) => {
    let x =
      Math.round(
        ((f.longitude - Math.min(...xs)) /
          (Math.max(...xs) - Math.min(...xs) || 1)) *
          5,
      ) - 2;
    let z =
      2 -
      Math.round(
        ((f.latitude - Math.min(...zs)) /
          (Math.max(...zs) - Math.min(...zs) || 1)) *
          4,
      );
    while (occupied.has(`${x}:${z}`)) {
      x++;
      if (x > 3) {
        x = -2;
        z++;
      }
    }
    occupied.add(`${x}:${z}`);
    return {
      x: x * 6,
      z: z * 6,
      w: 4.2,
      d: 3.4,
      h: 3.2 + (i % 3) * 1.2,
      color: hospitalColor(state, f.id, layer),
      id: f.id,
    };
  });
  const blocks: Block[] = [];
  for (let x = -6; x <= 6; x++)
    for (let z = -6; z <= 6; z++)
      if (!occupied.has(`${x}:${z}`)) {
        const n = Math.abs(x * 31 + z * 67 + 151);
        blocks.push({
          x: x * 6 - 0.9,
          z: z * 6,
          w: 1.8 + (n % 3) * 0.25,
          d: 2.7,
          h: 1 + (n % 5) * 0.58,
          color: n % 4 === 0 ? "#e1e6ec" : "#eef1f5",
        });
        blocks.push({
          x: x * 6 + 1.4,
          z: z * 6 + 0.3,
          w: 1.4,
          d: 1.8,
          h: 0.7 + (n % 3) * 0.45,
          color: "#e8edf2",
        });
      }
  return [...blocks, ...hospitals];
}
export function PilotMap({
  state,
  selected,
  onSelect,
  layer = "capacity",
}: {
  state: State;
  selected: string | null;
  onSelect: (id: string) => void;
  layer?: MapLayer;
}) {
  const host = useRef<HTMLDivElement>(null),
    pins = useRef<HTMLDivElement>(null),
    choose = useRef(onSelect);
  choose.current = onSelect;
  const controls = useRef<{
    zoom: (n: number) => void;
    reset: () => void;
    rotate: () => void;
  } | null>(null);
  const [engine, setEngine] = useState("loading");
  useEffect(() => {
    if (!host.current) return;
    const container = host.current,
      blocks = city(state, layer);
    let disposed = false,
      cleanup = () => {};
    const placePins = (
      project: (x: number, y: number, z: number) => { x: number; y: number },
    ) =>
      blocks
        .filter((b) => b.id)
        .forEach((b) => {
          const el = pins.current?.querySelector<HTMLElement>(
            `[data-hospital="${b.id}"]`,
          );
          if (el) {
            const p = project(b.x, b.h + 0.6, b.z);
            el.style.left = `${p.x}px`;
            el.style.top = `${p.y}px`;
          }
        });
    function software() {
      if (disposed) return;
      setEngine("software-3d");
      const canvas = document.createElement("canvas");
      container.append(canvas);
      const ctx = canvas.getContext("2d")!;
      let yaw = Math.PI / 4,
        zoom = 1,
        dragging = false,
        last = 0;
      const project = (x: number, y: number, z: number) => {
        const s =
          Math.min(container.clientWidth / 53, container.clientHeight / 40) *
          zoom;
        return {
          x:
            container.clientWidth * 0.53 +
            (x * Math.cos(yaw) - z * Math.sin(yaw)) * s,
          y:
            container.clientHeight * 0.5 +
            ((x * Math.sin(yaw) + z * Math.cos(yaw)) * 0.55 - y * 0.84) * s,
        };
      };
      function draw() {
        const w = container.clientWidth,
          h = container.clientHeight,
          r = Math.min(devicePixelRatio, 2);
        canvas.width = w * r;
        canvas.height = h * r;
        canvas.style.width = `${w}px`;
        canvas.style.height = `${h}px`;
        ctx.setTransform(r, 0, 0, r, 0, 0);
        ctx.fillStyle = "#f0f3f7";
        ctx.fillRect(0, 0, w, h);
        const poly = (pts: number[][], color: string) => {
          ctx.beginPath();
          pts.forEach(([x, y, z], i) => {
            const p = project(x, y, z);
            if (i) ctx.lineTo(p.x, p.y);
            else ctx.moveTo(p.x, p.y);
          });
          ctx.closePath();
          ctx.fillStyle = color;
          ctx.fill();
        };
        for (let n = -7; n <= 7; n++) {
          poly(
            [
              [n * 6 - 3, 0, -46],
              [n * 6 - 2, 0, -46],
              [n * 6 - 2, 0, 46],
              [n * 6 - 3, 0, 46],
            ],
            "#dfe5ec",
          );
          poly(
            [
              [-46, 0, n * 6 - 3],
              [46, 0, n * 6 - 3],
              [46, 0, n * 6 - 2],
              [-46, 0, n * 6 - 2],
            ],
            "#dfe5ec",
          );
        }
        [...blocks]
          .sort(
            (a, b) => (a.x - b.x) * Math.sin(yaw) + (a.z - b.z) * Math.cos(yaw),
          )
          .forEach((b) => {
            const x = b.x - b.w / 2,
              z = b.z - b.d / 2,
              X = x + b.w,
              Z = z + b.d,
              H = b.h,
              rgb = b.color.match(/\w\w/g)!.map((v) => parseInt(v, 16)),
              shade = (n: number) =>
                `rgb(${rgb.map((v) => Math.round(v * n)).join(",")})`;
            poly(
              [
                [x, 0, z],
                [X, 0, z],
                [X, 0, Z],
                [x, 0, Z],
              ],
              "#d5dde7",
            );
            const faces = [
              {
                p: [
                  [x, 0, Z],
                  [X, 0, Z],
                  [X, H, Z],
                  [x, H, Z],
                ],
                s: 0.9,
                depth: b.x * Math.sin(yaw) + Z * Math.cos(yaw),
              },
              {
                p: [
                  [X, 0, z],
                  [X, 0, Z],
                  [X, H, Z],
                  [X, H, z],
                ],
                s: 0.76,
                depth: X * Math.sin(yaw) + b.z * Math.cos(yaw),
              },
              {
                p: [
                  [x, 0, z],
                  [X, 0, z],
                  [X, H, z],
                  [x, H, z],
                ],
                s: 0.82,
                depth: b.x * Math.sin(yaw) + z * Math.cos(yaw),
              },
              {
                p: [
                  [x, 0, z],
                  [x, 0, Z],
                  [x, H, Z],
                  [x, H, z],
                ],
                s: 0.88,
                depth: x * Math.sin(yaw) + b.z * Math.cos(yaw),
              },
            ];
            faces
              .sort((a, b) => a.depth - b.depth)
              .forEach((f) => poly(f.p, shade(f.s)));
            poly(
              [
                [x, H, z],
                [X, H, z],
                [X, H, Z],
                [x, H, Z],
              ],
              b.color,
            );
            if (b.id) {
              poly(
                [
                  [b.x - 0.65, H + 0.01, b.z - 0.16],
                  [b.x + 0.65, H + 0.01, b.z - 0.16],
                  [b.x + 0.65, H + 0.01, b.z + 0.16],
                  [b.x - 0.65, H + 0.01, b.z + 0.16],
                ],
                "white",
              );
              poly(
                [
                  [b.x - 0.16, H + 0.02, b.z - 0.65],
                  [b.x + 0.16, H + 0.02, b.z - 0.65],
                  [b.x + 0.16, H + 0.02, b.z + 0.65],
                  [b.x - 0.16, H + 0.02, b.z + 0.65],
                ],
                "white",
              );
            }
          });
        placePins(project);
      }
      const observer = new ResizeObserver(draw);
      observer.observe(container);
      canvas.onpointerdown = (e) => {
        dragging = true;
        last = e.clientX;
        canvas.setPointerCapture(e.pointerId);
      };
      canvas.onpointermove = (e) => {
        if (dragging) {
          yaw += (e.clientX - last) * 0.008;
          last = e.clientX;
          draw();
        }
      };
      canvas.onpointerup = () => {
        dragging = false;
      };
      canvas.addEventListener(
        "wheel",
        (e) => {
          e.preventDefault();
          zoom = Math.max(0.6, Math.min(2.2, zoom - e.deltaY * 0.001));
          draw();
        },
        { passive: false },
      );
      controls.current = {
        zoom: (n) => {
          zoom = Math.max(0.6, Math.min(2.2, zoom * n));
          draw();
        },
        reset: () => {
          yaw = Math.PI / 4;
          zoom = 1;
          draw();
        },
        rotate: () => {
          yaw += Math.PI / 4;
          draw();
        },
      };
      draw();
      cleanup = () => {
        observer.disconnect();
        canvas.remove();
      };
    }
    import("three")
      .then(async (T) => {
        if (disposed) return;
        let renderer: InstanceType<typeof T.WebGLRenderer>;
        try {
          renderer = new T.WebGLRenderer({ antialias: true });
        } catch {
          software();
          return;
        }
        const { OrbitControls } =
          await import("three/examples/jsm/controls/OrbitControls.js");
        if (disposed) {
          renderer.dispose();
          return;
        }
        setEngine("webgl-3d");
        renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
        renderer.setClearColor("#f0f3f7");
        renderer.toneMapping = T.ACESFilmicToneMapping;
        renderer.toneMappingExposure = 1.6;
        renderer.shadowMap.enabled = true;
        renderer.shadowMap.type = T.PCFSoftShadowMap;
        container.append(renderer.domElement);
        const scene = new T.Scene(),
          camera = new T.OrthographicCamera(-30, 30, 26, -26, 0.1, 250);
        camera.position.set(48, 52, 48);
        const homeZoom = container.clientWidth < 760 ? 0.78 : 1;
        camera.zoom = homeZoom;
        camera.lookAt(0, 0, 0);
        const orbit = new OrbitControls(camera, renderer.domElement);
        orbit.minZoom = 0.6;
        orbit.maxZoom = 2.2;
        orbit.minPolarAngle = 0.3;
        orbit.maxPolarAngle = 1.25;
        scene.add(new T.HemisphereLight(0xffffff, 0xc8d2e2, 1.6));
        const sun = new T.DirectionalLight(0xffffff, 1.8);
        sun.position.set(-25, 50, 20);
        sun.castShadow = true;
        sun.shadow.mapSize.set(2048, 2048);
        Object.assign(sun.shadow.camera, {
          left: -55,
          right: 55,
          top: 55,
          bottom: -55,
          near: 1,
          far: 150,
        });
        sun.shadow.bias = -0.001;
        scene.add(sun);
        const meshes: InstanceType<typeof T.Mesh>[] = [];
        const box = (b: Block) => {
          const m = new T.Mesh(
            new T.BoxGeometry(b.w, b.h, b.d),
            new T.MeshStandardMaterial({ color: b.color, roughness: 0.95 }),
          );
          m.position.set(b.x, b.h / 2, b.z);
          m.castShadow = true;
          m.receiveShadow = true;
          m.userData.id = b.id;
          scene.add(m);
          if (b.id) meshes.push(m);
          return m;
        };
        const floor = new T.Mesh(
          new T.PlaneGeometry(160, 160),
          new T.MeshStandardMaterial({ color: "#f1f4f8" }),
        );
        floor.rotation.x = -Math.PI / 2;
        floor.receiveShadow = true;
        scene.add(floor);
        for (let n = -7; n <= 7; n++) {
          box({
            x: n * 6 - 2.5,
            z: 0,
            w: 0.9,
            d: 90,
            h: 0.015,
            color: "#dfe5ec",
          });
          box({
            x: 0,
            z: n * 6 - 2.5,
            w: 90,
            d: 0.9,
            h: 0.015,
            color: "#dfe5ec",
          });
        }
        blocks.forEach((b) => {
          box(b);
          if (b.id) {
            box({
              x: b.x,
              z: b.z,
              w: 1.3,
              d: 0.3,
              h: 0.035,
              color: "#ffffff",
            }).position.y = b.h + 0.03;
            box({
              x: b.x,
              z: b.z,
              w: 0.3,
              d: 1.3,
              h: 0.035,
              color: "#ffffff",
            }).position.y = b.h + 0.035;
          }
        });
        for (let n = 0; n < 48; n++) {
          const x = ((n % 8) - 3.5) * 6 + 2.3,
            z = (Math.floor(n / 8) - 2.5) * 6 + 2;
          const trunk = new T.Mesh(
            new T.CylinderGeometry(0.06, 0.08, 0.6, 5),
            new T.MeshStandardMaterial({ color: "#c8cfce" }),
          );
          trunk.position.set(x, 0.3, z);
          scene.add(trunk);
          const crown = new T.Mesh(
            new T.IcosahedronGeometry(0.48, 1),
            new T.MeshStandardMaterial({ color: "#d8e2de", roughness: 1 }),
          );
          crown.position.set(x, 0.92, z);
          crown.castShadow = true;
          scene.add(crown);
        }
        const render = () => {
          // Render only when the view or inputs change.
          renderer.render(scene, camera);
          placePins((x, y, z) => {
            const p = new T.Vector3(x, y, z).project(camera);
            return {
              x: (p.x * 0.5 + 0.5) * container.clientWidth,
              y: (-0.5 * p.y + 0.5) * container.clientHeight,
            };
          });
        };
        const resize = () => {
          const w = container.clientWidth,
            h = container.clientHeight;
          renderer.setSize(w, h);
          camera.left = (-26 * w) / h;
          camera.right = (26 * w) / h;
          camera.updateProjectionMatrix();
          render();
        };
        const observer = new ResizeObserver(resize);
        observer.observe(container);
        orbit.addEventListener("change", render);
        const ray = new T.Raycaster();
        let startX = 0,
          startY = 0;
        renderer.domElement.onpointerdown = (e) => {
          startX = e.clientX;
          startY = e.clientY;
        };
        renderer.domElement.onpointerup = (e) => {
          if (Math.hypot(e.clientX - startX, e.clientY - startY) > 6) return;
          const rect = renderer.domElement.getBoundingClientRect();
          ray.setFromCamera(
            new T.Vector2(
              ((e.clientX - rect.left) / rect.width) * 2 - 1,
              -((e.clientY - rect.top) / rect.height) * 2 + 1,
            ),
            camera,
          );
          const hit = ray.intersectObjects(meshes)[0];
          if (hit) choose.current(hit.object.userData.id);
        };
        controls.current = {
          zoom: (n) => {
            camera.zoom = Math.max(0.6, Math.min(2.2, camera.zoom * n));
            camera.updateProjectionMatrix();
            render();
          },
          reset: () => {
            camera.position.set(48, 52, 48);
            orbit.target.set(0, 0, 0);
            camera.zoom = homeZoom;
            camera.updateProjectionMatrix();
            orbit.update();
            render();
          },
          rotate: () => {
            camera.position
              .sub(orbit.target)
              .applyAxisAngle(new T.Vector3(0, 1, 0), Math.PI / 4)
              .add(orbit.target);
            orbit.update();
            render();
          },
        };
        const lost = (e: Event) => {
          e.preventDefault();
          cleanup();
          software();
        };
        renderer.domElement.addEventListener("webglcontextlost", lost);
        cleanup = () => {
          observer.disconnect();
          orbit.dispose();
          scene.traverse((o) => {
            if (o instanceof T.Mesh) {
              o.geometry.dispose();
              (Array.isArray(o.material) ? o.material : [o.material]).forEach(
                (m) => m.dispose(),
              );
            }
          });
          renderer.domElement.removeEventListener("webglcontextlost", lost);
          renderer.dispose();
          renderer.domElement.remove();
        };
        resize();
      })
      .catch(software);
    return () => {
      disposed = true;
      cleanup();
      controls.current = null;
    };
  }, [state.facilities, state.summary, layer]);
  return (
    <div
      className="pilot-map"
      data-engine={engine}
      aria-label="Interactive 3D Islamabad hospital map"
    >
      <div ref={host} className="map-canvas" />
      <div ref={pins} className="city-pins">
        {state.facilities.map((f) => (
          <button
            key={f.id}
            data-hospital={f.id}
            className={`city-pin ${selected === f.id ? "selected" : ""}`}
            style={{ borderColor: hospitalColor(state, f.id, layer) }}
            onClick={() => onSelect(f.id)}
            aria-label={`Select ${f.name}`}
          >
            <span>{f.id}</span>
          </button>
        ))}
      </div>
      <div className="city-controls">
        <button
          aria-label="Zoom in"
          onClick={() => controls.current?.zoom(1.2)}
        >
          <Plus size={17} />
        </button>
        <button
          aria-label="Zoom out"
          onClick={() => controls.current?.zoom(0.83)}
        >
          <Minus size={17} />
        </button>
        <button
          aria-label="Rotate city"
          onClick={() => controls.current?.rotate()}
        >
          <Compass size={17} />
        </button>
        <button
          aria-label="Reset map view"
          onClick={() => controls.current?.reset()}
        >
          <RotateCcw size={16} />
        </button>
      </div>
      <div className="city-caption">
        <span className="live-dot" />
        Islamabad · illustrative 3D city
        <span>Drag to orbit · scroll to zoom</span>
      </div>
    </div>
  );
}
