"use client";

import { Canvas, useFrame } from "@react-three/fiber";
import { Html, OrbitControls, Stars as DreiStars, useTexture } from "@react-three/drei";
import { Suspense, useRef } from "react";
import * as THREE from "three";

// R3F extended props (args, map, roughness, metalness, transparent, side, depthWrite, emissive, emissiveIntensity, position, geometry, color, intensity, distance, decay, attach) are valid React Three Fiber props
/* eslint-disable react/no-unknown-property */

interface GlobeNode {
  lat: number;
  lon: number;
  label: string;
  tipo: string;
  sat: number;
  highlight?: boolean;
}

interface GlobeQuake {
  lat: number;
  lon: number;
  mag: number;
  label: string;
}

interface Globe3DProps {
  nodes: GlobeNode[];
  quakes: GlobeQuake[];
  width?: number;
  height?: number;
  className?: string;
  autoRotate?: boolean;
  showAtmosphere?: boolean;
  showStars?: boolean;
}

function latLonToVector3(lat: number, lon: number, radius: number): THREE.Vector3 {
  const phi = (90 - lat) * (Math.PI / 180);
  const theta = (lon + 180) * (Math.PI / 180);
  return new THREE.Vector3(
    -radius * Math.sin(phi) * Math.cos(theta),
    radius * Math.cos(phi),
    radius * Math.sin(phi) * Math.sin(theta)
  );
}

function GlobeScene({ nodes, quakes, autoRotate, showAtmosphere }: Globe3DProps) {
  const globeRef = useRef<THREE.Group>(null);
  const rotationRef = useRef({ x: 0.15, y: 0 });
  const pulsesRef = useRef<Map<string, { mesh: THREE.Mesh; start: number; duration: number }>>(new Map());
  const pulseTimeRef = useRef(0);

  const earthTexture = useTexture("https://unpkg.com/three-globe/example/img/earth-blue-marble.jpg");

  useFrame((state) => {
    if (globeRef.current) {
      if (autoRotate) {
        rotationRef.current.y += state.clock.getDelta() * 0.08;
      }
      globeRef.current.rotation.x += (rotationRef.current.x - globeRef.current.rotation.x) * 0.05;
      globeRef.current.rotation.y += (rotationRef.current.y - globeRef.current.rotation.y) * 0.05;
    }

    const now = state.clock.getElapsedTime();
    pulsesRef.current.forEach((pulse, key) => {
      const elapsed = now - pulse.start;
      const progress = elapsed / pulse.duration;
      if (progress >= 1) {
        pulse.mesh.scale.setScalar(1);
        if (pulse.mesh.material instanceof THREE.Material) {
          pulse.mesh.material.opacity = 0;
        }
        pulsesRef.current.delete(key);
      } else {
        const scale = 1 + progress * 2;
        pulse.mesh.scale.setScalar(scale);
        if (pulse.mesh.material instanceof THREE.Material) {
          pulse.mesh.material.opacity = 1 - progress;
        }
      }
    });
  });

  const triggerPulse = (lat: number, lon: number, color: string, radius: number) => {
    const geometry = new THREE.RingGeometry(radius * 0.98, radius * 1.02, 64);
    const material = new THREE.MeshBasicMaterial({
      color,
      transparent: true,
      opacity: 0.8,
      side: THREE.DoubleSide,
      depthWrite: false,
    });
    const mesh = new THREE.Mesh(geometry, material);
    const pos = latLonToVector3(lat, lon, radius);
    mesh.position.copy(pos);
    mesh.lookAt(new THREE.Vector3(0, 0, 0));
    mesh.rotateX(-Math.PI / 2);
    if (globeRef.current) {
      globeRef.current.add(mesh);
      const now = pulseTimeRef.current;
      pulsesRef.current.set(`${lat}-${lon}-${now}`, { mesh, start: now, duration: 1.5 });
      pulseTimeRef.current += 0.001; // unique key increment
    }
  };

  const globeRadius = 3.5;

  return (
    <group ref={globeRef}>
      {/* Earth sphere */}
      <mesh>
        <sphereGeometry args={[globeRadius, 64, 64]} />
        <meshStandardMaterial
          map={earthTexture}
          roughness={0.8}
          metalness={0.1}
        />
      </mesh>

      {/* Atmosphere glow */}
      {showAtmosphere && (
        <mesh>
          <sphereGeometry args={[globeRadius * 1.08, 32, 32]} />
          <meshBasicMaterial
            color="#00d4ff"
            transparent
            opacity={0.06}
            side={THREE.BackSide}
            depthWrite={false}
          />
        </mesh>
      )}

      {/* Grid lines - latitudes */}
      <group>
        {Array.from({ length: 19 }, (_, i) => -90 + i * 10).map((lat) => (
          <mesh key={`lat-${lat}`}>
            <ringGeometry
              args={[
                globeRadius * Math.cos(lat * Math.PI / 180) * 1.001,
                globeRadius * Math.cos(lat * Math.PI / 180) * 1.003,
                64
              ]}
            />
            <meshBasicMaterial color="#00d4ff" transparent opacity={0.04} side={THREE.DoubleSide} />
          </mesh>
        ))}

        {/* Longitudes */}
        {Array.from({ length: 36 }, (_, i) => -180 + i * 10).map((lon) => {
          const points = Array.from({ length: 181 }, (_, j) => {
            const lat = -90 + j;
            const v = latLonToVector3(lat, lon, globeRadius * 1.002);
            return [v.x, v.y, v.z];
          }).flat();

          const geometry = new THREE.BufferGeometry();
          geometry.setAttribute("position", new THREE.Float32BufferAttribute(points, 3));

          return (
            <mesh key={`lon-${lon}`} geometry={geometry}>
              <lineBasicMaterial color="#00d4ff" transparent opacity={0.03} />
            </mesh>
          );
        })}
      </group>

      {/* Nodes */}
      <group>
        {nodes.map((node, i) => {
          const pos = latLonToVector3(node.lat, node.lon, globeRadius * 1.01);
          const satColor = node.sat > 0.8 ? "#ff1744" : node.sat > 0.6 ? "#ff9100" : node.sat > 0.3 ? "#ffc107" : "#10b981";
          const size = 0.06 + node.sat * 0.12;

          return (
            <group key={`node-${i}`} position={pos}>
              <mesh
                onPointerDown={() => triggerPulse(node.lat, node.lon, satColor, globeRadius)}
              >
                <sphereGeometry args={[size, 16, 16]} />
                <meshStandardMaterial
                  color={satColor}
                  emissive={satColor}
                  emissiveIntensity={node.sat * 0.8}
                  transparent
                  opacity={0.9}
                />
              </mesh>
              {node.highlight && (
                <mesh>
                  <ringGeometry args={[size * 1.8, size * 2.2, 32]} />
                  <meshBasicMaterial
                    color="#00d4ff"
                    transparent
                    opacity={0.4}
                    side={THREE.DoubleSide}
                  />
                </mesh>
              )}
              <Html
                transform
                position={[0, size + 0.1, 0]}
                style={{
                  fontSize: "10px",
                  color: "#f0f4f8",
                  textShadow: "0 0 8px #000",
                  whiteSpace: "nowrap",
                  pointerEvents: "none",
                }}
              >
                {node.label}
              </Html>
            </group>
          );
        })}
      </group>

      {/* Quakes */}
      <group>
        {quakes.slice(0, 50).map((quake, i) => {
          const pos = latLonToVector3(quake.lat, quake.lon, globeRadius * 1.005);
          const size = 0.03 + Math.min(quake.mag / 10, 0.08);
          return (
            <mesh key={`quake-${i}`} position={pos}>
              <sphereGeometry args={[size, 12, 12]} />
              <meshStandardMaterial
                color="#ff1744"
                emissive="#ff1744"
                emissiveIntensity={0.6}
                transparent
                opacity={0.8}
              />
            </mesh>
          );
        })}
      </group>

      {/* Tlaxcala anchor */}
      <group>
        {nodes.filter(n => n.highlight).map((node, i) => {
          const pos = latLonToVector3(node.lat, node.lon, globeRadius * 1.02);
          return (
            <group key={`anchor-${i}`} position={pos}>
              <mesh>
                <coneGeometry args={[0.08, 0.3, 16]} />
                <meshStandardMaterial color="#00d4ff" emissive="#00d4ff" emissiveIntensity={0.5} />
              </mesh>
              <Html
                transform
                position={[0, -0.5, 0]}
                style={{ fontSize: "11px", color: "#00d4ff", fontWeight: 600, textShadow: "0 0 8px #000" }}
              >
                TLAXCALA
              </Html>
            </group>
          );
        })}
      </group>

      {/* Lights */}
      <ambientLight color="#ffffff" intensity={0.6} />
      <directionalLight position={[5, 10, 7]} color="#ffffff" intensity={0.8} />
      <directionalLight position={[-5, -5, -5]} color="#00d4ff" intensity={0.3} />
      <pointLight position={[0, 0, 0]} color="#00d4ff" intensity={0.2} distance={10} decay={2} />
    </group>
  );
}

export function Globe3D({
  nodes,
  quakes,
  width = 400,
  height = 400,
  className = "",
  autoRotate = true,
  showAtmosphere = true,
  showStars = true,
}: Globe3DProps) {
  return (
    <div className={`relative overflow-hidden rounded-xl ${className}`} style={{ width, height, background: "#050607" }}>
      <Canvas
        camera={{ position: [0, 0, 10], fov: 45 }}
        style={{ width: "100%", height: "100%" }}
        gl={{ antialias: true, alpha: true, preserveDrawingBuffer: false }}
      >
        <color attach="background" args={["#050607"]} />
        {showStars && <DreiStars radius={100} depth={50} count={2000} factor={4} saturation={0} />}
        <OrbitControls
          enablePan={true}
          enableZoom={true}
          enableRotate={true}
          autoRotate={autoRotate}
          autoRotateSpeed={0.3}
          minDistance={6}
          maxDistance={18}
          target={[0, 0, 0]}
        />
        <Suspense fallback={<div className="absolute inset-0 flex items-center justify-center text-muted">Cargando globo…</div>}>
          <GlobeScene
            nodes={nodes}
            quakes={quakes}
            autoRotate={autoRotate}
            showAtmosphere={showAtmosphere}
          />
        </Suspense>
      </Canvas>
      <div className="absolute bottom-2 left-2 right-2 flex justify-between text-[10px] text-muted mono pointer-events-none">
        <span>Arrastra para rotar · Rueda para zoom</span>
        <span>Nodos: {nodes.length} · Sismos: {quakes.length}</span>
      </div>
    </div>
  );
}