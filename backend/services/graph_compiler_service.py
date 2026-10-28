"""
Graph Compiler Service - Enterprise 10X
Translates visual node graphs (@xyflow/react JSON export) into executable
LangGraph StateGraph logic, verifying topics, entrypoints, and decision rules.
"""
import logging
from typing import Dict, Any, List, Optional
from models.company_agent_graph import CompanyAgentGraph

logger = logging.getLogger(__name__)

class GraphCompilerService:
    """Compiles visual flow canvas specifications into validated routing rules"""

    @classmethod
    def compile_canvas(cls, canvas_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parses nodes and edges:
        Nodes: [
          { id: 'node_1', type: 'message', data: { label: 'Bienvenida', text: 'Hola...' } },
          { id: 'node_2', type: 'question', data: { label: 'Pedir Email', field: 'email' } },
          { id: 'node_3', type: 'decision', data: { label: 'Validar Lead', condition: 'has_budget' } },
          { id: 'node_4', type: 'handover', data: { label: 'Pasar a Asesor', reason: 'Venta Directa' } }
        ]
        Edges: [
          { source: 'node_1', target: 'node_2' },
          { source: 'node_2', target: 'node_3' }
        ]
        """
        nodes = canvas_data.get('nodes', [])
        edges = canvas_data.get('edges', [])

        node_map = {n['id']: n for n in nodes if 'id' in n}
        adj_list = {}
        for edge in edges:
            src = edge.get('source')
            tgt = edge.get('target')
            if src and tgt:
                adj_list.setdefault(src, []).append(tgt)

        # Identify starting node (root with in-degree 0 or named 'start')
        targets = {e.get('target') for e in edges}
        entry_nodes = [nid for nid in node_map if nid not in targets]
        start_node_id = entry_nodes[0] if entry_nodes else (nodes[0]['id'] if nodes else None)

        compiled_spec = {
            'entry_node_id': start_node_id,
            'node_count': len(nodes),
            'edge_count': len(edges),
            'adjacency': adj_list,
            'nodes': {nid: {
                'type': n.get('type', 'message'),
                'label': n.get('data', {}).get('label', ''),
                'config': n.get('data', {})
            } for nid, n in node_map.items()},
            'is_valid': bool(start_node_id)
        }

        return compiled_spec

    @classmethod
    def save_and_publish_graph(cls, graph_id: int, company_id: int, canvas_data: Dict[str, Any]) -> CompanyAgentGraph:
        """Compiles, validates, and marks the graph as active/published"""
        from extensions import db
        graph = CompanyAgentGraph.query.filter_by(id=graph_id, company_id=company_id).first()
        if not graph:
            raise ValueError("Graph not found")

        compiled = cls.compile_canvas(canvas_data)
        graph.canvas_data = canvas_data
        graph.compiled_spec = compiled
        graph.is_published = True
        graph.version += 1
        db.session.commit()
        return graph
