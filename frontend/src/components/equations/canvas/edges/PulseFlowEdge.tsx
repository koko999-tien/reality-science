"use client";

import React from "react";
import {
  BaseEdge,
  getSmoothStepPath,
  Position,
  type EdgeProps,
} from "@xyflow/react";

export interface PulseFlowEdgeProps extends Partial<EdgeProps> {
  id?: string;
  sourceX: number;
  sourceY: number;
  targetX: number;
  targetY: number;
  sourcePosition?: Position;
  targetPosition?: Position;
  markerEnd?: string;
  style?: React.CSSProperties;
  className?: string;
  selected?: boolean;
}

export const PulseFlowEdge: React.FC<PulseFlowEdgeProps> = ({
  id = "pulse-edge",
  sourceX,
  sourceY,
  targetX,
  targetY,
  sourcePosition = Position.Right,
  targetPosition = Position.Left,
  markerEnd,
  style = {},
  className = "",
  selected = false,
}) => {
  const [edgePath] = getSmoothStepPath({
    sourceX,
    sourceY,
    sourcePosition,
    targetX,
    targetY,
    targetPosition,
    borderRadius: 16,
  });

  const gradId = `pulse-grad-${id}`;
  const filterId = `photon-glow-${id}`;

  return (
    <>
      <defs>
        <linearGradient id={gradId} x1="0%" y1="0%" x2="100%" y2="0%">
          <stop offset="0%" stopColor="#0ea5e9" stopOpacity={0.9} />
          <stop offset="50%" stopColor="#38bdf8" stopOpacity={1} />
          <stop offset="100%" stopColor="#818cf8" stopOpacity={0.9} />
        </linearGradient>

        <filter id={filterId} x="-30%" y="-30%" width="160%" height="160%">
          <feGaussianBlur stdDeviation="3" result="blur" />
          <feMerge>
            <feMergeNode in="blur" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
      </defs>

      {/* Ambient background glow path */}
      <path
        d={edgePath}
        fill="none"
        stroke="#0ea5e9"
        strokeWidth={selected ? 6 : 4}
        strokeOpacity={selected ? 0.35 : 0.2}
        className="transition-all duration-300"
      />

      {/* Base reactive smoothstep edge with cyan glow pulse */}
      <BaseEdge
        id={id}
        path={edgePath}
        markerEnd={markerEnd}
        style={{
          stroke: `url(#${gradId})`,
          strokeWidth: selected ? 2.5 : 2,
          ...style,
        }}
        className={`stroke-cyan-400 stroke-2 fill-none animate-pulse-flow shadow-glow-cyan ${className}`}
      />

      {/* High-speed animated photon / energy quantum traversing the DAG pipeline */}
      <circle r={3.5} fill="#38bdf8" filter={`url(#${filterId})`}>
        <animateMotion dur="2.5s" repeatCount="indefinite" path={edgePath} />
      </circle>
    </>
  );
};
