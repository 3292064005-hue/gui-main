import { useRef } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { OrbitControls, Grid, Environment } from '@react-three/drei';
import * as THREE from 'three';
import { useTelemetryStore } from '../store/telemetryStore';

/** Animated probe mesh — bobs based on real force telemetry */
function UltrasoundProbe({ targetForce, maxForce }: { targetForce: number; maxForce: number }) {
  const meshRef = useRef<THREE.Mesh>(null);

  useFrame(() => {
    if (!meshRef.current) return;
    const force = useTelemetryStore.getState().force;
    // Subtle Z-axis displacement proportional to force (visual feedback)
    meshRef.current.position.y = -0.05 + (force / maxForce) * 0.08;
    // Slight tilt based on force deviation
    meshRef.current.rotation.x = (force - targetForce) * 0.02;
  });

  return (
    <group>
      {/* Probe body */}
      <mesh ref={meshRef} castShadow position={[0, 0, 0]}>
        <boxGeometry args={[0.05, 0.14, 0.035]} />
        <meshPhysicalMaterial color="#e0e0e0" metalness={0.15} roughness={0.15} clearcoat={1.0} />
      </mesh>
      {/* Probe tip (contact surface) */}
      <mesh position={[0, -0.08, 0]} castShadow>
        <boxGeometry args={[0.045, 0.02, 0.03]} />
        <meshPhysicalMaterial color="#00E5FF" metalness={0.8} roughness={0.1} emissive="#00E5FF" emissiveIntensity={0.3} />
      </mesh>
    </group>
  );
}

/** Translucent patient body cylinder for spatial context */
function PatientOutline() {
  return (
    <mesh position={[0, -0.25, 0]} rotation={[0, 0, Math.PI / 2]}>
      <capsuleGeometry args={[0.12, 0.6, 8, 16]} />
      <meshPhysicalMaterial
        color="#334455"
        transparent
        opacity={0.08}
        roughness={0.5}
        side={THREE.DoubleSide}
      />
    </mesh>
  );
}

export default function ThreeDView({
  targetForce = 10.0,
  maxForce = 35.0,
}: {
  targetForce?: number;
  maxForce?: number;
}) {
  return (
    <div className="w-full h-full bg-clinical-bg">
      <Canvas shadows camera={{ position: [0.6, 0.5, 0.9], fov: 42 }}>
        {/* Cinematic Lighting */}
        <ambientLight intensity={0.4} />
        <directionalLight castShadow position={[2, 4, 2]} intensity={1.2} shadow-mapSize={2048} />
        <pointLight position={[-2, -1, -2]} color="#00E5FF" intensity={0.6} />
        <pointLight position={[1, 0.5, -1]} color="#00FA9A" intensity={0.3} />

        {/* Scanning Grid */}
        <Grid
          renderOrder={-1}
          position={[0, -0.35, 0]}
          infiniteGrid
          fadeDistance={3}
          fadeStrength={1.5}
          cellColor="#00E5FF"
          sectionColor="#00FA9A"
          cellSize={0.08}
          sectionSize={0.4}
        />

        {/* Patient + Probe */}
        <PatientOutline />
        <UltrasoundProbe targetForce={targetForce} maxForce={maxForce} />

        {/* Coordinate Axes */}
        <axesHelper args={[0.3]} />

        <OrbitControls makeDefault enableDamping dampingFactor={0.05} />
        <Environment preset="studio" />
      </Canvas>

      {/* Vignette overlay */}
      <div className="absolute inset-0 pointer-events-none vignette-overlay" />
    </div>
  );
}
