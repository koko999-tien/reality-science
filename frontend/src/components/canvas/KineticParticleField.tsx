"use client";

import React, { useEffect, useRef } from "react";

export interface KineticParticleFieldProps {
  className?: string;
  density?: number;
  interactive?: boolean;
  equationModulation?: boolean;
}

interface Particle {
  x: number;
  y: number;
  x0: number;
  y0: number;
  baseY0: number;
  vx: number;
  vy: number;
  mass: number;
  radius: number;
  phase: number;
  waveSpeed: number;
}

export const KineticParticleField: React.FC<KineticParticleFieldProps> = ({
  className = "",
  density = 1,
  interactive = true,
  equationModulation = true,
}) => {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext("2d", { alpha: true });
    if (!ctx) return;

    let animationFrameId: number;
    let width = (canvas.width = canvas.parentElement?.clientWidth || window.innerWidth);
    let height = (canvas.height = canvas.parentElement?.clientHeight || 600);

    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    canvas.width = width * dpr;
    canvas.height = height * dpr;
    ctx.scale(dpr, dpr);

    // Mouse tracking state
    const mouse = {
      x: -1000,
      y: -1000,
      prevX: -1000,
      prevY: -1000,
      vx: 0,
      vy: 0,
      active: false,
      lastMoveTime: 0,
    };

    // Calculate particle count according to surface area and density
    const particleCount = Math.max(
      35,
      Math.min(100, Math.floor(((width * height) / 14000) * density))
    );

    const particles: Particle[] = [];
    for (let i = 0; i < particleCount; i++) {
      const x = Math.random() * width;
      const y = Math.random() * height;
      particles.push({
        x,
        y,
        x0: x,
        y0: y,
        baseY0: y,
        vx: (Math.random() - 0.5) * 0.4,
        vy: (Math.random() - 0.5) * 0.4,
        mass: 0.8 + Math.random() * 0.4,
        radius: 1.5 + Math.random() * 1.5,
        phase: Math.random() * Math.PI * 2,
        waveSpeed: 0.0015 + Math.random() * 0.001,
      });
    }

    const handleResize = () => {
      if (!canvas || !canvas.parentElement) return;
      width = canvas.parentElement.clientWidth;
      height = canvas.parentElement.clientHeight || 600;
      canvas.width = width * dpr;
      canvas.height = height * dpr;
      ctx.scale(dpr, dpr);

      // Re-anchor particles gracefully across new bounds
      particles.forEach((p) => {
        p.x0 = (p.x0 / (width || 1)) * width;
        p.baseY0 = (p.baseY0 / (height || 1)) * height;
      });
    };

    const handleMouseMove = (e: MouseEvent) => {
      const rect = canvas.getBoundingClientRect();
      const currentX = e.clientX - rect.left;
      const currentY = e.clientY - rect.top;

      const now = performance.now();
      const dt = Math.max(16, now - (mouse.lastMoveTime || now));

      mouse.vx = ((currentX - mouse.x) / dt) * 16;
      mouse.vy = ((currentY - mouse.y) / dt) * 16;
      mouse.x = currentX;
      mouse.y = currentY;
      mouse.active = true;
      mouse.lastMoveTime = now;
    };

    const handleMouseLeave = () => {
      mouse.active = false;
      mouse.vx = 0;
      mouse.vy = 0;
    };

    window.addEventListener("resize", handleResize);
    if (interactive) {
      canvas.parentElement?.addEventListener("mousemove", handleMouseMove, { passive: true });
      canvas.parentElement?.addEventListener("mouseleave", handleMouseLeave, { passive: true });
    }

    // Physical constants
    const ks = 0.015; // Hooke's spring constant
    const damping = 0.04; // Viscous damping
    const influenceRadius = 160;
    const repelStrength = 0.8;
    const momentumCoupling = 0.15;
    const maxSpeed = 8;
    const connectDistance = 95;

    let startTime = performance.now();

    const render = (time: number) => {
      const elapsed = time - startTime;
      ctx.clearRect(0, 0, width, height);

      // Mouse velocity decay
      if (mouse.active) {
        mouse.vx *= 0.92;
        mouse.vy *= 0.92;
      }

      // Update particle physics
      for (let i = 0; i < particles.length; i++) {
        const p = particles[i];

        // 1. Quantum Wave Equation Modulation
        if (equationModulation) {
          const kx = (p.x0 / width) * Math.PI * 4;
          const wave =
            Math.sin(kx - elapsed * p.waveSpeed + p.phase) *
            14 *
            Math.exp(-Math.pow((p.x0 - width * 0.5) / (width * 0.4), 2));
          p.y0 = p.baseY0 + wave;
        }

        // 2. Harmonic Equilibrium Restitution (Hooke's Law: F = -k * (x - x0))
        const fxSpring = -ks * (p.x - p.x0);
        const fySpring = -ks * (p.y - p.y0);

        // 3. Cursor Momentum Transfer and Repulsion
        let fxMouse = 0;
        let fyMouse = 0;

        if (interactive && mouse.active) {
          const dx = p.x - mouse.x;
          const dy = p.y - mouse.y;
          const dist = Math.hypot(dx, dy);

          if (dist < influenceRadius && dist > 1) {
            const factor = 1 - dist / influenceRadius;
            const normX = dx / dist;
            const normY = dy / dist;

            // Repulsion force
            fxMouse += normX * factor * repelStrength * 10;
            fyMouse += normY * factor * repelStrength * 10;

            // Fluid momentum coupling from mouse velocity
            fxMouse += mouse.vx * factor * momentumCoupling;
            fyMouse += mouse.vy * factor * momentumCoupling;
          }
        }

        // Total force & acceleration
        const ax = (fxSpring + fxMouse) / p.mass;
        const ay = (fySpring + fyMouse) / p.mass;

        // Velocity integration with viscous damping
        p.vx = (p.vx + ax) * (1 - damping);
        p.vy = (p.vy + ay) * (1 - damping);

        // Clamp extreme velocity
        const speed = Math.hypot(p.vx, p.vy);
        if (speed > maxSpeed) {
          p.vx = (p.vx / speed) * maxSpeed;
          p.vy = (p.vy / speed) * maxSpeed;
        }

        // Position integration
        p.x += p.vx;
        p.y += p.vy;
      }

      // 4. Render Constellation Links
      ctx.lineWidth = 1;
      for (let i = 0; i < particles.length; i++) {
        for (let j = i + 1; j < particles.length; j++) {
          const p1 = particles[i];
          const p2 = particles[j];
          const dx = p1.x - p2.x;
          const dy = p1.y - p2.y;
          const dist = Math.hypot(dx, dy);

          if (dist < connectDistance) {
            const alpha = 0.22 * (1 - dist / connectDistance);
            ctx.strokeStyle = `rgba(14, 165, 233, ${alpha.toFixed(3)})`;
            ctx.beginPath();
            ctx.moveTo(p1.x, p1.y);
            ctx.lineTo(p2.x, p2.y);
            ctx.stroke();
          }
        }
      }

      // 5. Render Glowing Quantum Particles
      for (let i = 0; i < particles.length; i++) {
        const p = particles[i];
        const excitation = Math.min(1, Math.hypot(p.vx, p.vy) * 0.3);
        const alpha = Math.min(0.9, 0.45 + excitation * 0.45);

        // Particle core
        ctx.fillStyle = `rgba(56, 189, 248, ${alpha.toFixed(3)})`;
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.radius, 0, Math.PI * 2);
        ctx.fill();

        // High-energy excitation halo
        if (excitation > 0.25) {
          ctx.fillStyle = `rgba(14, 165, 233, ${(excitation * 0.25).toFixed(3)})`;
          ctx.beginPath();
          ctx.arc(p.x, p.y, p.radius * 2.8, 0, Math.PI * 2);
          ctx.fill();
        }
      }

      animationFrameId = requestAnimationFrame(render);
    };

    animationFrameId = requestAnimationFrame(render);

    return () => {
      cancelAnimationFrame(animationFrameId);
      window.removeEventListener("resize", handleResize);
      if (interactive && canvas.parentElement) {
        canvas.parentElement.removeEventListener("mousemove", handleMouseMove);
        canvas.parentElement.removeEventListener("mouseleave", handleMouseLeave);
      }
    };
  }, [density, interactive, equationModulation]);

  return (
    <canvas
      ref={canvasRef}
      className={`pointer-events-none absolute inset-0 -z-10 h-full w-full ${className}`}
      aria-hidden="true"
    />
  );
};
