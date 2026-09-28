import { useEffect, useRef } from "react";
import * as THREE from "three";
import type { AssistantState } from "../data/mock-data";

export default function AssistantCore({ state }: { state: AssistantState }) {
  const mountRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const mount = mountRef.current;
    if (!mount || !window.WebGLRenderingContext || window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(38, 1, 0.1, 100);
    camera.position.z = 5;
    const renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true, powerPreference: "low-power" });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 1.5));
    mount.appendChild(renderer.domElement);
    const group = new THREE.Group();
    scene.add(group);
    const material = new THREE.MeshBasicMaterial({ color: state === "permission" ? 0xf2b84b : state === "error" ? 0xef6b64 : 0x54d8e8, wireframe: true, transparent: true, opacity: .46 });
    const core = new THREE.Mesh(new THREE.IcosahedronGeometry(1.04, 2), material);
    const ringA = new THREE.Mesh(new THREE.TorusGeometry(1.48, .012, 8, 128), new THREE.MeshBasicMaterial({ color: 0x54d8e8, transparent: true, opacity: .48 }));
    ringA.rotation.x = 1.15;
    const ringB = ringA.clone(); ringB.rotation.set(.4, 1.1, .3); ringB.scale.setScalar(.82);
    group.add(core, ringA, ringB);
    let frame = 0; let visible = !document.hidden;
    const resize = () => { const s = Math.min(mount.clientWidth, mount.clientHeight); renderer.setSize(s, s, false); camera.aspect = 1; camera.updateProjectionMatrix(); };
    const visibility = () => { visible = !document.hidden; if (visible) animate(); };
    const animate = () => { if (!visible) return; frame = requestAnimationFrame(animate); const speed = state === "thinking" ? .009 : state === "listening" ? .006 : .0025; group.rotation.y += speed; ringA.rotation.z += speed * .55; ringB.rotation.x -= speed * .35; const pulse = state === "listening" ? 1 + Math.sin(performance.now() / 280) * .035 : 1; core.scale.setScalar(pulse); renderer.render(scene, camera); };
    resize(); window.addEventListener("resize", resize); document.addEventListener("visibilitychange", visibility); animate();
    return () => { cancelAnimationFrame(frame); window.removeEventListener("resize", resize); document.removeEventListener("visibilitychange", visibility); renderer.dispose(); material.dispose(); mount.removeChild(renderer.domElement); };
  }, [state]);
  return <div ref={mountRef} className={`assistant-core core-${state}`} aria-hidden="true"><div className="core-fallback"><span /></div></div>;
}
