import { useState, useMemo } from "react";
import ReactFlow, { Background, Controls, Edge, Node, Position } from "reactflow";
import { Play, ShieldAlert, Cpu, Award, Zap, Search, PenLine } from "lucide-react";
import "reactflow/dist/style.css";

interface NodePayload {
  prompt?: string;
  input?: string;
  output?: string;
  latency?: string;
  confidence?: string;
  tools?: string[];
}

interface AgentWorkflowGraphProps {
  activeNode?: string | null;
  nodeStatuses?: Record<string, "running" | "waiting" | "failed" | "completed">;
  customPayloads?: Record<string, NodePayload>;
}

/** Static description of what each node does. Never a stand-in for trace data. */
const NODE_ROLES: Record<string, string> = {
  rewrite: "Rewrite the question into self-contained queries; pause for clarification if ambiguous.",
  supervisor: "Classify the request intent and route it to the knowledge agent.",
  knowledge: "Embed the query, search child chunks in Pinecone, and pull parent context.",
  aggregator: "Synthesize the retrieved answers into one customer-facing response.",
  safety: "Audit the response for hallucinations, injection, and unsafe content.",
  escalation: "Compile a handoff ticket when safety fails, confidence is low, or a human is requested.",
  response: "Stream the approved response back to the client over SSE.",
};

function nodeLabel(Icon: typeof Cpu | null, title: string, subtitle: string) {
  return (
    <div className="flex flex-col items-center gap-1 p-2">
      {Icon && <Icon className="h-4 w-4" />}
      <span className="text-[11px] font-bold">{title}</span>
      <span className="text-[9px] uppercase tracking-wider text-slate-500">{subtitle}</span>
    </div>
  );
}

export function AgentWorkflowGraph({
  activeNode = null,
  nodeStatuses = {},
  customPayloads = {},
}: AgentWorkflowGraphProps) {
  const [hoveredNode, setHoveredNode] = useState<string | null>(null);
  const [hoveredPayload, setHoveredPayload] = useState<NodePayload | null>(null);
  const [mousePos, setMousePos] = useState({ x: 0, y: 0 });

  const getNodeColor = (id: string) => {
    const status = nodeStatuses[id] || (activeNode === id ? "running" : "waiting");
    switch (status) {
      case "running":
        return "border-emerald-500/80 bg-emerald-950/20 text-emerald-400";
      case "failed":
        return "border-red-500/80 bg-red-950/20 text-red-400";
      case "completed":
        return "border-blue-500/80 bg-blue-950/20 text-blue-400";
      default:
        return "border-slate-800 bg-slate-900 text-slate-400";
    }
  };

  const initialNodes: Node[] = [
    {
      id: "rewrite",
      type: "default",
      data: { label: nodeLabel(PenLine, "Query Rewrite", "Clarify") },
      position: { x: 200, y: 10 },
      sourcePosition: Position.Bottom,
    },
    {
      id: "supervisor",
      type: "default",
      data: { label: nodeLabel(Cpu, "Supervisor", "Intent Router") },
      position: { x: 200, y: 130 },
      targetPosition: Position.Top,
      sourcePosition: Position.Bottom,
    },
    {
      id: "knowledge",
      type: "default",
      data: { label: nodeLabel(Search, "Knowledge RAG", "Pinecone") },
      position: { x: 200, y: 250 },
      targetPosition: Position.Top,
      sourcePosition: Position.Bottom,
    },
    {
      id: "aggregator",
      type: "default",
      data: { label: nodeLabel(Zap, "Aggregator", "Synthesis") },
      position: { x: 200, y: 370 },
      targetPosition: Position.Top,
      sourcePosition: Position.Bottom,
    },
    {
      id: "safety",
      type: "default",
      data: { label: nodeLabel(Award, "Safety Guard", "Audit") },
      position: { x: 200, y: 480 },
      targetPosition: Position.Top,
      sourcePosition: Position.Bottom,
    },
    {
      id: "escalation",
      type: "default",
      data: { label: nodeLabel(ShieldAlert, "Human Escalation", "Support Queue") },
      position: { x: 40, y: 590 },
      targetPosition: Position.Top,
    },
    {
      id: "response",
      type: "default",
      data: { label: nodeLabel(Play, "Client Output", "SSE Stream") },
      position: { x: 360, y: 590 },
      targetPosition: Position.Top,
    },
  ];

  const nodes = useMemo(() => {
    return initialNodes.map((n) => ({
      ...n,
      className: `border border-2 rounded-lg transition-colors font-sans ${getNodeColor(n.id)}`,
    }));
  }, [activeNode, nodeStatuses]);

  const edges: Edge[] = [
    { id: "e-rew-sup", source: "rewrite", target: "supervisor", animated: true },
    { id: "e-sup-know", source: "supervisor", target: "knowledge", animated: true },
    { id: "e-know-agg", source: "knowledge", target: "aggregator" },
    { id: "e-agg-safe", source: "aggregator", target: "safety", animated: true },
    { id: "e-safe-esc", source: "safety", target: "escalation", label: "unsafe / low conf" },
    { id: "e-safe-res", source: "safety", target: "response", label: "approved" },
  ];

  const handleNodeMouseEnter = (_: React.MouseEvent, node: Node) => {
    setHoveredNode(node.id);
    // Only live trace data is ever shown; absent fields render as "no data".
    setHoveredPayload(customPayloads[node.id] ?? null);
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    setMousePos({ x: e.clientX, y: e.clientY });
  };

  return (
    <div
      className="relative h-[700px] w-full rounded-lg border border-white/10 bg-slate-950 p-2"
      onMouseMove={handleMouseMove}
    >
      <div className="absolute left-4 top-4 z-10">
        <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400">
          LangGraph Workflow
        </h4>
        <p className="text-[10px] text-slate-500">
          Green: executing | Blue: completed | Gray: pending
        </p>
      </div>

      <ReactFlow
        nodes={nodes}
        edges={edges}
        fitView
        onNodeMouseEnter={handleNodeMouseEnter}
        onNodeMouseLeave={() => {
          setHoveredNode(null);
          setHoveredPayload(null);
        }}
        nodesDraggable={false}
        nodesConnectable={false}
        zoomOnScroll={false}
        panOnDrag={false}
      >
        <Background color="rgba(255, 255, 255, 0.03)" gap={16} />
        <Controls showInteractive={false} />
      </ReactFlow>

      {hoveredNode && (
        <div
          className="pointer-events-none fixed z-50 w-80 rounded-lg border border-white/10 bg-slate-950 p-4 text-xs"
          style={{ left: `${mousePos.x + 15}px`, top: `${mousePos.y + 15}px` }}
        >
          <div className="mb-2 flex items-center justify-between border-b border-white/10 pb-2">
            <span className="font-bold capitalize text-slate-200">{hoveredNode}</span>
            <span className="font-mono text-[10px] text-slate-500">
              {hoveredPayload?.latency ? `Latency: ${hoveredPayload.latency}` : "no trace"}
            </span>
          </div>

          <p className="leading-snug text-slate-400">{NODE_ROLES[hoveredNode]}</p>

          {hoveredPayload ? (
            <div className="mt-2 space-y-2 border-t border-white/10 pt-2 text-slate-300">
              <div>
                <span className="block text-[10px] font-bold uppercase tracking-wider text-slate-500">
                  Last Trace Input
                </span>
                <p className="mt-0.5 truncate font-mono text-[10px] text-slate-400">
                  {hoveredPayload.input || "—"}
                </p>
              </div>
              <div>
                <span className="block text-[10px] font-bold uppercase tracking-wider text-slate-500">
                  Last Trace Output
                </span>
                <p className="mt-0.5 truncate font-mono text-[10px] text-slate-400">
                  {hoveredPayload.output || "—"}
                </p>
              </div>
              {hoveredPayload.tools && hoveredPayload.tools.length > 0 && (
                <div className="border-t border-white/10 pt-2">
                  <span className="mb-1 block text-[10px] font-bold uppercase tracking-wider text-slate-500">
                    Tools Called
                  </span>
                  <div className="flex flex-wrap gap-1">
                    {hoveredPayload.tools.map((t, idx) => (
                      <span
                        key={idx}
                        className="rounded border border-white/10 px-1.5 py-0.5 font-mono text-[9px] text-slate-300"
                      >
                        {t}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ) : (
            <p className="mt-2 border-t border-white/10 pt-2 text-[10px] text-slate-500">
              No trace recorded for this node yet.
            </p>
          )}
        </div>
      )}
    </div>
  );
}
