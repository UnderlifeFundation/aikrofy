'use client';

import { memo } from 'react';
import { Handle, Position, NodeProps } from '@xyflow/react';
import { 
  MessageSquare, 
  HelpCircle, 
  GitFork, 
  Wrench, 
  UserCheck, 
  Trash2,
  Sparkles,
  Zap
} from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';

export interface WorkflowNodeData {
  label: string;
  type: 'message' | 'question' | 'decision' | 'action' | 'handover';
  text?: string;
  field?: string;
  condition?: string;
  action_name?: string;
  reason?: string;
  target_role?: string;
  isStart?: boolean;
  onDelete?: (id: string) => void;
  [key: string]: unknown;
}

const TYPE_CONFIG = {
  message: {
    icon: MessageSquare,
    badge: 'Mensaje IA',
    color: 'from-sky-500/20 to-blue-600/20 border-sky-500/40 text-sky-500',
    text: 'text-sky-500',
    dot: 'bg-sky-500',
  },
  question: {
    icon: HelpCircle,
    badge: 'Calificación',
    color: 'from-indigo-500/20 to-purple-600/20 border-indigo-500/40 text-indigo-500',
    text: 'text-indigo-500',
    dot: 'bg-indigo-500',
  },
  decision: {
    icon: GitFork,
    badge: 'Bifurcación',
    color: 'from-amber-500/20 to-orange-600/20 border-amber-500/40 text-amber-500',
    text: 'text-amber-500',
    dot: 'bg-amber-500',
  },
  action: {
    icon: Wrench,
    badge: 'Acción REST',
    color: 'from-emerald-500/20 to-teal-600/20 border-emerald-500/40 text-emerald-500',
    text: 'text-emerald-500',
    dot: 'bg-emerald-500',
  },
  handover: {
    icon: UserCheck,
    badge: 'Handover',
    color: 'from-rose-500/20 to-pink-600/20 border-rose-500/40 text-rose-500',
    text: 'text-rose-500',
    dot: 'bg-rose-500',
  }
};

export const WorkflowNode = memo(({ id, data, selected }: NodeProps<any>) => {
  const nodeData = data as WorkflowNodeData;
  const config = TYPE_CONFIG[nodeData.type] || TYPE_CONFIG.message;
  const IconComponent = config.icon;

  return (
    <div
      className={`relative min-w-[260px] max-w-[320px] rounded-2xl bg-card/95 backdrop-blur-md border transition-all duration-200 shadow-lg ${
        selected
          ? 'ring-2 ring-violet-500 border-violet-500 shadow-violet-500/20'
          : 'border-border/80 hover:border-border hover:shadow-xl'
      }`}
    >
      {/* Target Connection Handle (Top) */}
      {!nodeData.isStart && (
        <Handle
          type="target"
          position={Position.Top}
          className="!w-3 !h-3 !bg-violet-500 !border-2 !border-background !-top-1.5 transition-transform hover:scale-125 shadow-sm"
        />
      )}

      {/* Header Bar */}
      <div className={`flex items-center justify-between px-3.5 py-2.5 rounded-t-2xl border-b bg-gradient-to-r ${config.color}`}>
        <div className="flex items-center gap-2">
          <div className={`p-1.5 rounded-lg bg-background/80 shadow-xs ${config.text || 'text-foreground'}`}>
            <IconComponent className="w-4 h-4" />
          </div>
          <span className="font-semibold text-xs text-foreground truncate max-w-[130px]">
            {nodeData.label || 'Paso'}
          </span>
        </div>

        <div className="flex items-center gap-1.5">
          {nodeData.isStart && (
            <Badge className="text-[9px] px-1.5 py-0 bg-violet-600 text-white font-mono uppercase">
              Start
            </Badge>
          )}
          <Badge variant="outline" className="text-[9px] px-1.5 py-0 border-muted-foreground/30 font-medium">
            {config.badge}
          </Badge>
          {nodeData.onDelete && !nodeData.isStart && (
            <button
              onClick={(e) => {
                e.stopPropagation();
                nodeData.onDelete?.(id);
              }}
              className="p-1 rounded-md text-muted-foreground hover:text-rose-500 hover:bg-rose-500/10 transition-colors"
              title="Eliminar nodo"
            >
              <Trash2 className="w-3 h-3" />
            </button>
          )}
        </div>
      </div>

      {/* Body Content */}
      <div className="p-3.5 space-y-2 text-xs">
        {nodeData.type === 'message' && (
          <p className="text-muted-foreground line-clamp-2 leading-relaxed">
            {nodeData.text || 'Mensaje no configurado...'}
          </p>
        )}

        {nodeData.type === 'question' && (
          <div className="space-y-1">
            <p className="text-muted-foreground line-clamp-2 leading-relaxed">
              {nodeData.text || 'Pregunta no definida...'}
            </p>
            <div className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-muted/60 text-[10px] font-mono text-foreground/80">
              <Zap className="w-2.5 h-2.5 text-indigo-500" />
              <span>var: {nodeData.field || 'interes'}</span>
            </div>
          </div>
        )}

        {nodeData.type === 'decision' && (
          <div className="space-y-1">
            <span className="text-[10px] text-muted-foreground uppercase tracking-wider font-semibold">Condición</span>
            <div className="p-1.5 rounded-lg bg-amber-500/10 border border-amber-500/20 font-mono text-[11px] text-amber-600 dark:text-amber-400 truncate">
              {nodeData.condition || 'default'}
            </div>
          </div>
        )}

        {nodeData.type === 'action' && (
          <div className="space-y-1">
            <span className="text-[10px] text-muted-foreground uppercase tracking-wider font-semibold">Tool REST</span>
            <div className="p-1.5 rounded-lg bg-emerald-500/10 border border-emerald-500/20 font-mono text-[11px] text-emerald-600 dark:text-emerald-400 truncate">
              {nodeData.action_name || 'custom_tool'}
            </div>
          </div>
        )}

        {nodeData.type === 'handover' && (
          <div className="space-y-1">
            <span className="text-[10px] text-muted-foreground uppercase tracking-wider font-semibold">Escalamiento</span>
            <p className="text-muted-foreground line-clamp-1">
              Motivo: {nodeData.reason || 'Atención prioritaria'}
            </p>
            <Badge variant="outline" className="text-[10px] bg-rose-500/10 text-rose-600 border-rose-300">
              {nodeData.target_role || 'Asesor Comercial'}
            </Badge>
          </div>
        )}
      </div>

      {/* Source Connection Handle (Bottom) */}
      <Handle
        type="source"
        position={Position.Bottom}
        className="!w-3 !h-3 !bg-violet-500 !border-2 !border-background !-bottom-1.5 transition-transform hover:scale-125 shadow-sm"
      />
    </div>
  );
});

WorkflowNode.displayName = 'WorkflowNode';
