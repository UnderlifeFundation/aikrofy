'use client';

import { memo } from 'react';
import { 
  BaseEdge, 
  EdgeLabelRenderer, 
  getBezierPath, 
  EdgeProps 
} from '@xyflow/react';
import { X } from 'lucide-react';

export const DeletableEdge = memo(({
  id,
  sourceX,
  sourceY,
  targetX,
  targetY,
  sourcePosition,
  targetPosition,
  style = {},
  markerEnd,
  selected,
  data
}: EdgeProps) => {
  const [edgePath, labelX, labelY] = getBezierPath({
    sourceX,
    sourceY,
    sourcePosition,
    targetX,
    targetY,
    targetPosition,
  });

  const onEdgeDelete = (data as any)?.onDelete;

  return (
    <>
      <BaseEdge 
        path={edgePath} 
        markerEnd={markerEnd} 
        style={{
          ...style,
          strokeWidth: selected ? 3 : 2,
          stroke: selected ? '#ec4899' : (style.stroke || '#8b5cf6'),
        }} 
      />
      <EdgeLabelRenderer>
        <div
          style={{
            position: 'absolute',
            transform: `translate(-50%, -50%) translate(${labelX}px,${labelY}px)`,
            pointerEvents: 'all',
          }}
          className="nodrag nopan"
        >
          <button
            onClick={(event) => {
              event.stopPropagation();
              if (onEdgeDelete) {
                onEdgeDelete(id);
              }
            }}
            title="Desconectar enlace (o presiona Supr/Backspace)"
            className={`flex items-center justify-center w-5 h-5 rounded-full border shadow-md transition-all duration-200 cursor-pointer ${
              selected 
                ? 'bg-rose-500 border-white text-white scale-125 ring-2 ring-rose-300' 
                : 'bg-background hover:bg-rose-500 border-border hover:border-rose-500 text-muted-foreground hover:text-white opacity-70 hover:opacity-100 hover:scale-115'
            }`}
          >
            <X className="w-3 h-3" />
          </button>
        </div>
      </EdgeLabelRenderer>
    </>
  );
});

DeletableEdge.displayName = 'DeletableEdge';
