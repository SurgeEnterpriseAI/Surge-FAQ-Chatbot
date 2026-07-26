import os
import matplotlib.pyplot as plt
import matplotlib.patches as patches

# Create target directory
output_dir = os.path.join(os.getcwd(), "docs", "assets")
os.makedirs(output_dir, exist_ok=True)

# Color Palette (Sleek Dark Theme)
BG_COLOR = "#0F172A"       # Dark Slate background
CARD_BG = "#1E293B"        # Dark Card fill
BORDER_COLOR = "#334155"   # Card Border
TEXT_COLOR = "#F8FAFC"     # Primary Text
SUBTEXT_COLOR = "#94A3B8"  # Secondary Text

# Accent Colors
BLUE_ACCENT = "#38BDF8"    # API / Service
GREEN_ACCENT = "#4ADE80"   # Success / Output
PURPLE_ACCENT = "#C084FC"  # AI / Agent Node
AMBER_ACCENT = "#FBBF24"   # Logic / Decision / Filter
RED_ACCENT = "#F87171"     # Error / Escalation
CYAN_ACCENT = "#2DD4BF"    # Database / Storage

def create_canvas(title, subtitle, width=16, height=9):
    fig, ax = plt.subplots(figsize=(width, height), dpi=200)
    fig.patch.set_facecolor(BG_COLOR)
    ax.set_facecolor(BG_COLOR)
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis("off")
    
    # Header Title
    ax.text(4, 94, title, fontsize=18, fontweight="bold", color=TEXT_COLOR, va="top", ha="left", family="sans-serif")
    ax.text(4, 89, subtitle, fontsize=10.5, color=SUBTEXT_COLOR, va="top", ha="left", family="sans-serif")
    
    # Subdued footer tag
    ax.text(96, 3, "Agentic-RAG Architecture Pipeline", fontsize=9, color="#475569", va="bottom", ha="right", family="sans-serif")
    return fig, ax

def draw_card(ax, x, y, w, h, title, subtitle="", badge="", accent_color=BLUE_ACCENT, bg_color=CARD_BG):
    rect = patches.FancyBboxPatch(
        (x, y), w, h,
        boxstyle="round,pad=0.3,rounding_size=1.5",
        ec=accent_color, fc=bg_color, lw=1.5
    )
    ax.add_patch(rect)
    
    # Title
    ax.text(x + w/2, y + h - 2.2, title, fontsize=9.5, fontweight="bold", color=TEXT_COLOR, va="center", ha="center", family="sans-serif")
    
    # Optional Badge
    if badge:
        ax.text(x + w/2, y + h - 5.0, f"[{badge}]", fontsize=7.5, fontweight="bold", color=accent_color, va="center", ha="center", family="sans-serif")
    
    if subtitle:
        sub_y = y + 2.5 if badge else y + 2.2
        ax.text(x + w/2, sub_y, subtitle, fontsize=8, color=SUBTEXT_COLOR, va="center", ha="center", family="sans-serif", multialignment="center")

def draw_decision(ax, x, y, size, title, subtitle="", accent_color=AMBER_ACCENT):
    # Diamond decision shape
    points = [[x, y + size/2], [x + size/2, y + size], [x + size, y + size/2], [x + size/2, y]]
    poly = patches.Polygon(points, closed=True, ec=accent_color, fc="#282218", lw=1.5)
    ax.add_patch(poly)
    
    ax.text(x + size/2, y + size/2 + 0.6, title, fontsize=9, fontweight="bold", color=TEXT_COLOR, va="center", ha="center")
    if subtitle:
        ax.text(x + size/2, y + size/2 - 1.2, subtitle, fontsize=7.5, color=AMBER_ACCENT, va="center", ha="center")

def draw_arrow(ax, x1, y1, x2, y2, label="", color="#64748B", style="-|>"):
    ax.annotate(
        "", xy=(x2, y2), xytext=(x1, y1),
        arrowprops=dict(arrowstyle=style, color=color, lw=1.8, mutation_scale=12)
    )
    if label:
        mx, my = (x1 + x2)/2, (y1 + y2)/2
        ax.text(mx, my + 1.2, label, fontsize=7.5, color=color, fontweight="bold", ha="center", va="center")

# ==============================================================================
# PIPELINE 1: Query & Answering Pipeline
# ==============================================================================
def gen_query_answering_pipeline():
    fig, ax = create_canvas(
        "1. Query & Answering Pipeline",
        "End-to-end execution flow from user input to SSE response streaming or human escalation"
    )
    
    draw_card(ax, 3, 42, 11, 14, "User Prompt", "React Web Client", badge="CLIENT", accent_color=BLUE_ACCENT)
    draw_arrow(ax, 14, 49, 18, 49, "POST /api/chat")
    
    draw_card(ax, 18, 42, 12, 14, "FastAPI & Auth", "JWT / Guest Verify\nContextVar Scoping", badge="API", accent_color=BLUE_ACCENT)
    draw_arrow(ax, 30, 49, 34, 49)
    
    draw_card(ax, 34, 42, 13, 14, "State Check", "AsyncPostgresSaver\nLookup thread_id", badge="CHECKPOINT", accent_color=CYAN_ACCENT)
    draw_arrow(ax, 47, 49, 51, 49, "New / Resume")
    
    draw_card(ax, 51, 42, 13, 14, "Query Rewriter", "summarize_history\nrewrite_query Node", badge="AI NODE", accent_color=PURPLE_ACCENT)
    draw_arrow(ax, 64, 49, 68, 49)
    
    draw_decision(ax, 68, 43, 12, "Query Clear?", "Requires clarification?", AMBER_ACCENT)
    
    # Clarification Branch (Down)
    draw_arrow(ax, 74, 43, 74, 26, "No", color=AMBER_ACCENT)
    draw_card(ax, 68, 14, 12, 12, "Clarification Pause", "interrupt_before\nrequest_clarification", badge="PAUSED", accent_color=AMBER_ACCENT)
    draw_arrow(ax, 68, 20, 14, 43, "User Explains", color=AMBER_ACCENT)
    
    # Yes Branch (Right)
    draw_arrow(ax, 80, 49, 84, 49, "Yes", color=GREEN_ACCENT)
    
    # Outer workflow nodes
    draw_card(ax, 84, 70, 12, 12, "Supervisor", "Intent Routing", badge="SUPERVISOR", accent_color=PURPLE_ACCENT)
    draw_card(ax, 84, 52, 12, 12, "Knowledge Agent", "Inner RAG Loop", badge="RAG SEARCH", accent_color=PURPLE_ACCENT)
    draw_card(ax, 84, 34, 12, 12, "Aggregator", "Merge Sub-Answers", badge="AGGREGATOR", accent_color=PURPLE_ACCENT)
    draw_card(ax, 84, 16, 12, 12, "Safety Agent", "5 Parallel Checks", badge="SAFETY", accent_color=RED_ACCENT)
    
    draw_arrow(ax, 90, 82, 90, 76)
    draw_arrow(ax, 90, 64, 90, 58)
    draw_arrow(ax, 90, 46, 90, 40)
    draw_arrow(ax, 90, 28, 90, 22)
    
    # Output Branch
    draw_arrow(ax, 84, 22, 14, 42, "Approved: SSE Stream", color=GREEN_ACCENT)
    
    plt.tight_layout()
    fig.savefig(os.path.join(output_dir, "pipeline-query-answering.png"), facecolor=BG_COLOR, edgecolor="none")
    plt.close(fig)

# ==============================================================================
# PIPELINE 2: Document Ingestion Pipeline
# ==============================================================================
def gen_document_ingestion_pipeline():
    fig, ax = create_canvas(
        "2. Document Ingestion Pipeline",
        "Multi-format parsing, parent-child chunking, PostgreSQL storage, and NVIDIA vector embedding"
    )
    
    draw_card(ax, 3, 44, 12, 14, "Document Upload", "PDF, DOCX, CSV,\nXLSX, TXT, MD", badge="UPLOAD", accent_color=BLUE_ACCENT)
    draw_arrow(ax, 15, 51, 19, 51, "POST /api/upload")
    
    draw_card(ax, 19, 44, 13, 14, "Validation & Temp", "Size check < 25MiB\nTemp Directory", badge="SERVICE", accent_color=BLUE_ACCENT)
    draw_arrow(ax, 32, 51, 36, 51)
    
    draw_card(ax, 36, 44, 13, 14, "MarkItDown / CSV", "Sniff dialect & parse\nConvert to Markdown", badge="PARSER", accent_color=AMBER_ACCENT)
    draw_arrow(ax, 49, 51, 53, 51)
    
    draw_card(ax, 53, 44, 14, 14, "Parent Chunker", "Header split H1-H3\n~2000 chars per parent", badge="CHUNKER", accent_color=PURPLE_ACCENT)
    
    # Split flow into Postgres Parent Store and Child Vector Store
    draw_arrow(ax, 67, 56, 73, 72, "Full Text")
    draw_card(ax, 73, 65, 18, 14, "PostgreSQL Store", "parent_chunks table\nFull Context Truth", badge="POSTGRES", accent_color=CYAN_ACCENT)
    
    draw_arrow(ax, 67, 46, 73, 30, "Child Snippets")
    draw_card(ax, 73, 23, 18, 14, "Child Chunker & Embed", "500 chars, 100 overlap\nNVIDIA nv-embedqa-e5-v5", badge="NVIDIA AI", accent_color=PURPLE_ACCENT)
    draw_arrow(ax, 91, 30, 95, 30)
    
    draw_card(ax, 95, 23, 4, 56, "Pinecone Index", "Embedded\nChild\nVectors", badge="PINECONE", accent_color=GREEN_ACCENT)
    
    plt.tight_layout()
    fig.savefig(os.path.join(output_dir, "pipeline-document-ingestion.png"), facecolor=BG_COLOR, edgecolor="none")
    plt.close(fig)

# ==============================================================================
# PIPELINE 3: Multi-Agent Search Pipeline
# ==============================================================================
def gen_multi_agent_search_pipeline():
    fig, ax = create_canvas(
        "3. Multi-Agent RAG Search Pipeline",
        "Sub-graph iterative retrieval loop, vector similarity, candidate re-ranking, and parent context hydration"
    )
    
    draw_card(ax, 3, 44, 12, 14, "Rewritten Query", "From Knowledge Agent", badge="QUERY", accent_color=BLUE_ACCENT)
    draw_arrow(ax, 15, 51, 19, 51)
    
    draw_card(ax, 19, 44, 13, 14, "Inner Orchestrator", "Check search budget\n(Max 10 rounds)", badge="ORCHESTRATOR", accent_color=PURPLE_ACCENT)
    draw_arrow(ax, 32, 51, 36, 51)
    
    draw_card(ax, 36, 44, 14, 14, "Pinecone Vector Search", "search_child_chunks\nCosine score >= 0.4", badge="VECTOR DB", accent_color=GREEN_ACCENT)
    draw_arrow(ax, 50, 51, 54, 51)
    
    draw_card(ax, 54, 44, 14, 14, "BGE / Cohere Reranker", "Fetch 20 candidates\nSelect top 5 reranked", badge="RERANKER", accent_color=AMBER_ACCENT)
    draw_arrow(ax, 68, 51, 72, 51)
    
    draw_decision(ax, 72, 44, 12, "Sufficient Context?", "Need full parent?", AMBER_ACCENT)
    
    # Needs parent hydration
    draw_arrow(ax, 78, 56, 78, 72, "No", color=AMBER_ACCENT)
    draw_card(ax, 72, 72, 12, 14, "Parent Hydration", "retrieve_parent_chunks\nFetch text from Postgres", badge="HYDRATE", accent_color=CYAN_ACCENT)
    draw_arrow(ax, 84, 79, 88, 51)
    
    # Yes -> Collect
    draw_arrow(ax, 84, 51, 88, 51, "Yes", color=GREEN_ACCENT)
    draw_card(ax, 88, 44, 10, 14, "Collect Answer", "Draft Sub-Response", badge="COLLECT", accent_color=GREEN_ACCENT)
    
    plt.tight_layout()
    fig.savefig(os.path.join(output_dir, "pipeline-multi-agent-search.png"), facecolor=BG_COLOR, edgecolor="none")
    plt.close(fig)

# ==============================================================================
# PIPELINE 4: Safety & Verification Pipeline
# ==============================================================================
def gen_safety_verification_pipeline():
    fig, ax = create_canvas(
        "4. Safety & Verification Pipeline",
        "Parallel 5-check evaluation suite enforcing groundedness, PII protection, injection defense, and policy compliance"
    )
    
    draw_card(ax, 3, 44, 12, 14, "Draft Answer", "From Aggregator Node", badge="INPUT", accent_color=BLUE_ACCENT)
    draw_arrow(ax, 15, 51, 22, 51)
    
    # 5 Parallel checks
    draw_card(ax, 22, 76, 16, 11, "1. Groundedness", "LLM Evaluation", badge="GROUNDEDNESS", accent_color=PURPLE_ACCENT)
    draw_card(ax, 22, 61, 16, 11, "2. Prompt Injection", "Regex + LLM Guard", badge="INJECTION", accent_color=RED_ACCENT)
    draw_card(ax, 22, 46, 16, 11, "3. PII Detection", "Regex (SSN/Card) + LLM", badge="PII CHECK", accent_color=AMBER_ACCENT)
    draw_card(ax, 22, 31, 16, 11, "4. Hallucination", "Fact Verification", badge="FACT CHECK", accent_color=PURPLE_ACCENT)
    draw_card(ax, 22, 16, 16, 11, "5. Policy Compliance", "Enterprise Guidelines", badge="POLICY", accent_color=BLUE_ACCENT)
    
    draw_arrow(ax, 15, 51, 22, 81)
    draw_arrow(ax, 15, 51, 22, 66)
    draw_arrow(ax, 15, 51, 22, 51)
    draw_arrow(ax, 15, 51, 22, 36)
    draw_arrow(ax, 15, 51, 22, 21)
    
    # Aggregation
    draw_card(ax, 44, 44, 14, 14, "Score Aggregator", "Takes minimum confidence\nAll 5 must approve", badge="AGGREGATE", accent_color=AMBER_ACCENT)
    draw_arrow(ax, 38, 81, 44, 51)
    draw_arrow(ax, 38, 66, 44, 51)
    draw_arrow(ax, 38, 51, 44, 51)
    draw_arrow(ax, 38, 36, 44, 51)
    draw_arrow(ax, 38, 21, 44, 51)
    
    draw_arrow(ax, 58, 51, 64, 51)
    draw_decision(ax, 64, 44, 12, "Approved?", "Conf >= 0.60?", AMBER_ACCENT)
    
    # Outputs
    draw_arrow(ax, 76, 51, 82, 68, "Yes", color=GREEN_ACCENT)
    draw_card(ax, 82, 61, 14, 14, "Stream Response", "SSE Event Stream", badge="APPROVED", accent_color=GREEN_ACCENT)
    
    draw_arrow(ax, 76, 51, 82, 34, "No", color=RED_ACCENT)
    draw_card(ax, 82, 27, 14, 14, "Human Escalation", "Create Support Ticket", badge="REJECTED", accent_color=RED_ACCENT)
    
    plt.tight_layout()
    fig.savefig(os.path.join(output_dir, "pipeline-safety-verification.png"), facecolor=BG_COLOR, edgecolor="none")
    plt.close(fig)

# ==============================================================================
# PIPELINE 5: Auth & Tenant Isolation Pipeline
# ==============================================================================
def gen_auth_tenant_isolation_pipeline():
    fig, ax = create_canvas(
        "5. Auth & Tenant Isolation Pipeline",
        "JWT / Guest token authentication, ContextVar tenant propagation, and scoped storage access"
    )
    
    draw_card(ax, 3, 44, 13, 14, "Incoming Request", "Bearer Token &\nX-Tenant-ID Header", badge="HTTP REQ", accent_color=BLUE_ACCENT)
    draw_arrow(ax, 16, 51, 21, 51)
    
    draw_card(ax, 21, 44, 14, 14, "Token Verification", "get_current_user\nSupabase JWT / Guest", badge="AUTH DEP", accent_color=BLUE_ACCENT)
    draw_arrow(ax, 35, 51, 40, 51)
    
    draw_card(ax, 40, 44, 15, 14, "ContextVar Injection", "Set TenantContext\nScoped to request thread", badge="CONTEXTVAR", accent_color=PURPLE_ACCENT)
    draw_arrow(ax, 55, 51, 61, 51)
    
    # Scoped storage channels
    draw_card(ax, 61, 70, 16, 12, "Pinecone Namespace", "tenant_{tenant_id}\n+ department filter", badge="VECTOR SCOPE", accent_color=GREEN_ACCENT)
    draw_card(ax, 61, 44, 16, 12, "PostgreSQL Prisma", "Scoped user_id &\ntenant_id query filters", badge="DB SCOPE", accent_color=CYAN_ACCENT)
    draw_card(ax, 61, 18, 16, 12, "Document Metadata", "Ingest tagged with\ntenant metadata", badge="TAGGING", accent_color=AMBER_ACCENT)
    
    draw_arrow(ax, 55, 51, 61, 76)
    draw_arrow(ax, 55, 51, 61, 50)
    draw_arrow(ax, 55, 51, 61, 24)
    
    draw_card(ax, 82, 44, 14, 14, "Isolated Response", "Zero cross-tenant leakage", badge="SECURE OUT", accent_color=GREEN_ACCENT)
    draw_arrow(ax, 77, 76, 82, 51)
    draw_arrow(ax, 77, 50, 82, 51)
    draw_arrow(ax, 77, 24, 82, 51)
    
    plt.tight_layout()
    fig.savefig(os.path.join(output_dir, "pipeline-auth-tenant-isolation.png"), facecolor=BG_COLOR, edgecolor="none")
    plt.close(fig)

# ==============================================================================
# PIPELINE 6: Telemetry & Tracing Pipeline
# ==============================================================================
def gen_telemetry_tracing_pipeline():
    fig, ax = create_canvas(
        "6. Telemetry & Tracing Pipeline",
        "Event tracing, retrieval logging, token cost tracking, and non-cascading audit history"
    )
    
    draw_card(ax, 3, 44, 13, 14, "Graph Node Event", "trace_id & retrieval_run_id", badge="TELEMETRY", accent_color=PURPLE_ACCENT)
    draw_arrow(ax, 16, 51, 22, 51)
    
    draw_card(ax, 22, 70, 16, 12, "agent_logs", "FK: chat_id\nNode timing & payloads", badge="POSTGRES FK", accent_color=BLUE_ACCENT)
    draw_card(ax, 22, 52, 16, 12, "conversation_traces", "Convention join trace_id\nStart / end latency", badge="TRACES", accent_color=AMBER_ACCENT)
    draw_card(ax, 22, 34, 16, 12, "retrieval_runs", "Queries, filters,\nretrieval_results links", badge="RETRIEVAL", accent_color=GREEN_ACCENT)
    draw_card(ax, 22, 16, 16, 12, "cost_usage", "Input/output tokens\nUSD cost calculation", badge="COSTS", accent_color=CYAN_ACCENT)
    
    draw_arrow(ax, 16, 51, 22, 76)
    draw_arrow(ax, 16, 51, 22, 58)
    draw_arrow(ax, 16, 51, 22, 40)
    draw_arrow(ax, 16, 51, 22, 22)
    
    draw_card(ax, 46, 44, 16, 14, "Metrics Collector", "System Metrics Service\nCPU, RAM, API latency", badge="METRICS", accent_color=PURPLE_ACCENT)
    draw_arrow(ax, 38, 76, 46, 51)
    draw_arrow(ax, 38, 58, 46, 51)
    draw_arrow(ax, 38, 40, 46, 51)
    draw_arrow(ax, 38, 22, 46, 51)
    
    draw_card(ax, 68, 44, 16, 14, "Chat Deletion", "DELETE /chats/{id}\nCascades ONLY to agent_logs", badge="DELETE", accent_color=RED_ACCENT)
    draw_arrow(ax, 62, 51, 68, 51)
    
    draw_card(ax, 88, 44, 10, 14, "Audit Logs", "Traces & costs\nPersist safely", badge="AUDIT PERSIST", accent_color=GREEN_ACCENT)
    draw_arrow(ax, 84, 51, 88, 51)
    
    plt.tight_layout()
    fig.savefig(os.path.join(output_dir, "pipeline-telemetry-tracing.png"), facecolor=BG_COLOR, edgecolor="none")
    plt.close(fig)

# ==============================================================================
# PIPELINE 7: Reindexing & Deletion Pipeline
# ==============================================================================
def gen_reindexing_deletion_pipeline():
    fig, ax = create_canvas(
        "7. Reindexing & Deletion Pipeline",
        "Pinecone namespace rebuilds from Postgres parent store and vector filter deletion error handling"
    )
    
    draw_card(ax, 3, 62, 14, 14, "POST /api/reindex", "Rebuild Pinecone index", badge="REINDEX API", accent_color=BLUE_ACCENT)
    draw_arrow(ax, 17, 69, 23, 69)
    draw_card(ax, 23, 62, 15, 14, "Clear Namespace", "Purge Pinecone collection", badge="PINECONE", accent_color=AMBER_ACCENT)
    draw_arrow(ax, 38, 69, 44, 69)
    draw_card(ax, 44, 62, 16, 14, "Fetch Postgres Parents", "Read parent_chunks table", badge="POSTGRES", accent_color=CYAN_ACCENT)
    draw_arrow(ax, 60, 69, 66, 69)
    draw_card(ax, 66, 62, 16, 14, "Re-chunk & Embed", "NVIDIA nv-embedqa-e5-v5", badge="NVIDIA AI", accent_color=PURPLE_ACCENT)
    draw_arrow(ax, 82, 69, 88, 69)
    draw_card(ax, 88, 62, 10, 14, "Pinecone", "Upsert vectors", badge="INDEX", accent_color=GREEN_ACCENT)
    
    draw_card(ax, 3, 20, 14, 14, "DELETE /documents", "Remove document", badge="DELETE API", accent_color=RED_ACCENT)
    draw_arrow(ax, 17, 27, 23, 27)
    draw_card(ax, 23, 20, 15, 14, "Delete DB Records", "Postgres parents & docs", badge="POSTGRES", accent_color=CYAN_ACCENT)
    draw_arrow(ax, 38, 27, 44, 27)
    draw_card(ax, 44, 20, 16, 14, "Pinecone Delete", "filter={source: doc_name}", badge="FILTER DELETE", accent_color=AMBER_ACCENT)
    draw_arrow(ax, 60, 27, 66, 27)
    
    draw_decision(ax, 66, 20, 12, "Filter Supported?", "Pinecone Tier Check", AMBER_ACCENT)
    draw_arrow(ax, 78, 26, 84, 34, "Yes", color=GREEN_ACCENT)
    draw_card(ax, 84, 27, 13, 12, "Success", "Vectors removed", badge="DELETED", accent_color=GREEN_ACCENT)
    
    draw_arrow(ax, 78, 26, 84, 18, "No / Tier Limit", color=RED_ACCENT)
    draw_card(ax, 84, 11, 13, 12, "Return 501", "Manual Reindex Req.", badge="WARNING 501", accent_color=RED_ACCENT)
    
    plt.tight_layout()
    fig.savefig(os.path.join(output_dir, "pipeline-reindexing-deletion.png"), facecolor=BG_COLOR, edgecolor="none")
    plt.close(fig)

if __name__ == "__main__":
    print("Generating pipeline PNG diagrams...")
    gen_query_answering_pipeline()
    gen_document_ingestion_pipeline()
    gen_multi_agent_search_pipeline()
    gen_safety_verification_pipeline()
    gen_auth_tenant_isolation_pipeline()
    gen_telemetry_tracing_pipeline()
    gen_reindexing_deletion_pipeline()
    print("All pipeline diagrams generated successfully in docs/assets/")
