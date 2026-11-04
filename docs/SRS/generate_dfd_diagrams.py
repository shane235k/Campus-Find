"""Generate publication-quality, aesthetically pleasing academic Data Flow Diagrams (DFD Levels 0, 1, 2)
for the Campus Lost & Found Hub Software Requirements Specification (SRS).

Redesigned with:
- Spacious canvas and generous margins.
- Clean, mathematically aligned coordinate grids.
- Zero overlapping labels or crossing lines.
- Classic Gane-Sarson / academic standard shapes:
    * External Entity: Crisp double-bordered rectangle.
    * Process: Elegant rounded rectangle with distinct header.
    * Data Store: Classical parallel horizontal lines with partitioned ID box.
- Flow arrows with clean, padded label badges.
"""
import os
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch


# ---------------------------------------------------------------------------
# Visual Styling & Primitives
# ---------------------------------------------------------------------------

def draw_entity(ax, x, y, w, h, name, subtitle=""):
    """Draw External Entity: Crisp double-bordered rectangle."""
    # Outer box
    rect_outer = patches.Rectangle(
        (x - w / 2, y - h / 2), w, h,
        linewidth=1.6, edgecolor='#000000', facecolor='#FBFBFB', zorder=4
    )
    ax.add_patch(rect_outer)
    
    # Inner border
    p = 0.07
    rect_inner = patches.Rectangle(
        (x - w / 2 + p, y - h / 2 + p), w - 2 * p, h - 2 * p,
        linewidth=0.8, edgecolor='#000000', facecolor='none', zorder=5
    )
    ax.add_patch(rect_inner)
    
    # Text
    if subtitle:
        ax.text(x, y + 0.16 * h, name, ha='center', va='center',
                fontsize=9.5, fontweight='bold', fontfamily='serif', color='#000000', zorder=6)
        ax.text(x, y - 0.20 * h, subtitle, ha='center', va='center',
                fontsize=8.0, fontfamily='serif', color='#333333', zorder=6)
    else:
        ax.text(x, y, name, ha='center', va='center',
                fontsize=9.5, fontweight='bold', fontfamily='serif', color='#000000', zorder=6)


def draw_process(ax, x, y, w, h, proc_id, title, desc=""):
    """Draw Process box: Rounded rectangle with partitioned ID header."""
    bbox = FancyBboxPatch(
        (x - w / 2, y - h / 2), w, h,
        boxstyle="round,pad=0,rounding_size=0.12",
        linewidth=1.6, edgecolor='#000000', facecolor='#FFFFFF', zorder=4
    )
    ax.add_patch(bbox)
    
    # Partition line
    div_y = y + h / 2 - 0.32 * h
    ax.plot([x - w / 2, x + w / 2], [div_y, div_y], color='#000000', linewidth=1.2, zorder=5)
    
    # Header ID
    ax.text(x, y + h / 2 - 0.16 * h, f"PROCESS {proc_id}",
            ha='center', va='center', fontsize=8.5, fontweight='bold', fontfamily='serif', color='#000000', zorder=6)
    
    # Body text
    body_y = y - 0.14 * h
    if desc:
        ax.text(x, body_y + 0.12 * h, title,
                ha='center', va='center', fontsize=8.5, fontweight='bold', fontfamily='serif', color='#000000',
                multialignment='center', zorder=6)
        ax.text(x, body_y - 0.18 * h, desc,
                ha='center', va='center', fontsize=7.2, fontfamily='serif', color='#444444',
                multialignment='center', zorder=6)
    else:
        ax.text(x, body_y, title,
                ha='center', va='center', fontsize=8.5, fontweight='bold', fontfamily='serif', color='#000000',
                multialignment='center', zorder=6)


def draw_datastore(ax, x, y, w, h, store_id, name):
    """Draw Data Store: Classic parallel open lines with ID block."""
    rect = patches.Rectangle(
        (x - w / 2, y - h / 2), w, h,
        linewidth=0, facecolor='#FFFFFF', zorder=3
    )
    ax.add_patch(rect)
    
    ax.plot([x - w / 2, x + w / 2], [y + h / 2, y + h / 2], color='#000000', linewidth=1.8, zorder=5)
    ax.plot([x - w / 2, x + w / 2], [y - h / 2, y - h / 2], color='#000000', linewidth=1.8, zorder=5)
    ax.plot([x - w / 2, x - w / 2], [y - h / 2, y + h / 2], color='#000000', linewidth=1.8, zorder=5)
    
    id_w = 0.65
    ax.plot([x - w / 2 + id_w, x - w / 2 + id_w], [y - h / 2, y + h / 2], color='#000000', linewidth=1.2, zorder=5)
    
    ax.text(x - w / 2 + id_w / 2, y, store_id,
            ha='center', va='center', fontsize=8.5, fontweight='bold', fontfamily='serif', color='#000000', zorder=6)
    ax.text(x - w / 2 + id_w + (w - id_w) / 2, y, name,
            ha='center', va='center', fontsize=7.5, fontweight='bold', fontfamily='serif', color='#000000',
            multialignment='center', zorder=6)


def draw_arrow(ax, start, end, label="", label_pos=0.5, label_offset=(0, 0),
               connectionstyle="arc3,rad=0", ha='center', va='center', fontsize=7.5):
    """Draw directed flow arrow with white-padded text badge."""
    arrow = FancyArrowPatch(
        start, end,
        connectionstyle=connectionstyle,
        arrowstyle="-|>",
        mutation_scale=12,
        linewidth=1.2,
        color='#000000',
        zorder=3
    )
    ax.add_patch(arrow)
    
    if label:
        x1, y1 = start
        x2, y2 = end
        lx = x1 + (x2 - x1) * label_pos + label_offset[0]
        ly = y1 + (y2 - y1) * label_pos + label_offset[1]
        
        ax.text(
            lx, ly, label,
            ha=ha, va=va,
            fontsize=fontsize, fontfamily='serif', color='#000000',
            multialignment='center',
            bbox=dict(boxstyle='square,pad=0.22', facecolor='#FFFFFF', edgecolor='#BBBBBB', linewidth=0.5),
            zorder=7
        )


# ---------------------------------------------------------------------------
# 1. DFD Level 0: Context Diagram
# ---------------------------------------------------------------------------

def generate_dfd_level_0(output_path):
    fig, ax = plt.subplots(figsize=(16.0, 5.5), dpi=300)
    ax.set_xlim(0, 16)
    ax.set_ylim(0, 5.5)
    ax.axis('off')
    
    # Title
    ax.text(8.0, 5.0, "DFD Level 0: Context Diagram — Campus Lost & Found Hub",
            ha='center', va='center', fontsize=13, fontweight='bold', fontfamily='serif', color='#000000')
    
    # 1. Student Entity (Center: 1.5, w: 2.2 -> bounds: 0.4 to 2.6)
    draw_entity(ax, 1.5, 2.5, 2.2, 2.2, "STUDENT", "(Campus Community User)")
    
    # 2. Central Process 0.0 (Center: 8.0, w: 3.6 -> bounds: 6.2 to 9.8)
    draw_process(ax, 8.0, 2.5, 3.6, 2.5, "0.0", "Campus Lost & Found\nHub Platform", "Centralized Web & AI Matching System")
    
    # 3. Desk Moderator Entity (Center: 14.5, w: 2.2 -> bounds: 13.4 to 15.6)
    draw_entity(ax, 14.5, 2.5, 2.2, 2.2, "DESK MODERATOR", "(Security & Operations Staff)")
    
    # Flows Left: Student <-> System (Distance = 6.2 - 2.6 = 3.6)
    # Student -> System (Top)
    draw_arrow(
        ax, (2.6, 3.2), (6.2, 3.2),
        label="Lost & Found Reports, Photos,\nSearch Queries & Claims",
        label_pos=0.5, label_offset=(0, 0.40)
    )
    # System -> Student (Bottom)
    draw_arrow(
        ax, (6.2, 1.8), (2.6, 1.8),
        label="Catalog Listings, Match Alerts,\nStatus & Pickup Notices",
        label_pos=0.5, label_offset=(0, -0.40)
    )
    
    # Flows Right: System <-> Admin (Distance = 13.4 - 9.8 = 3.6)
    # System -> Admin (Top)
    draw_arrow(
        ax, (9.8, 3.2), (13.4, 3.2),
        label="Pending Claim Queue, Proof Evidence,\nAudit Logs & Telemetry",
        label_pos=0.5, label_offset=(0, 0.40)
    )
    # Admin -> System (Bottom)
    draw_arrow(
        ax, (13.4, 1.8), (9.8, 1.8),
        label="Adjudication Decisions (Approve/Reject),\nItem State Updates (RESOLVED)",
        label_pos=0.5, label_offset=(0, -0.40)
    )
    
    plt.tight_layout()
    plt.savefig(output_path, bbox_inches='tight', dpi=300)
    plt.close()
    print(f"[OK] Generated Clean DFD Level 0: {output_path}")


# ---------------------------------------------------------------------------
# 2. DFD Level 1: System-Level Data Flow Diagram
# ---------------------------------------------------------------------------

def generate_dfd_level_1(output_path):
    fig, ax = plt.subplots(figsize=(16.8, 11.0), dpi=300)
    ax.set_xlim(0, 16.8)
    ax.set_ylim(0, 11)
    ax.axis('off')
    
    # Title
    ax.text(8.4, 10.5, "DFD Level 1: System-Level Data Flow Diagram",
            ha='center', va='center', fontsize=13, fontweight='bold', fontfamily='serif', color='#000000')
    
    # Entities
    # Student: Left Entity at x = 1.3, y = 5.2, w = 1.8, h = 6.2
    draw_entity(ax, 1.3, 5.2, 1.8, 6.2, "STUDENT", "(Lost/Found User)")
    
    # Desk Moderator: Right Entity at x = 15.5, y = 5.0, w = 1.8, h = 3.0
    draw_entity(ax, 15.5, 5.0, 1.8, 3.0, "DESK MODERATOR", "(Security Staff)")
    
    # --- Column 1: Client-Facing Processes (x = 4.5, w = 2.6, h = 1.6) ---
    draw_process(ax, 4.5, 9.0, 2.6, 1.6, "1.0", "Authentication & Access", "Login & RBAC Validation")
    draw_process(ax, 4.5, 6.4, 2.6, 1.6, "2.0", "Item Reporting & Catalog", "Lost/Found Intake & Search")
    draw_process(ax, 4.5, 3.8, 2.6, 1.6, "4.0", "Claim Submission", "Ownership Proof Intake")
    draw_process(ax, 4.5, 1.2, 2.6, 1.6, "6.0", "Notification Engine", "Alert & Notice Dispatcher")
    
    # --- Column 2: Data Stores (x = 8.5, w = 2.6, h = 0.8) ---
    draw_datastore(ax, 8.5, 9.0, 2.6, 0.8, "D1", "User Accounts\n(CampusUser)")
    draw_datastore(ax, 8.5, 6.4, 2.6, 0.8, "D2", "Item Catalog\n(Items & Photos)")
    draw_datastore(ax, 8.5, 3.8, 2.6, 0.8, "D4", "Claim Records\n& Evidence Store")
    draw_datastore(ax, 8.5, 1.2, 2.6, 0.8, "D5", "Notifications\nLog Store")
    
    # --- Column 3: Engine & Administration Processes (x = 12.3, w = 2.6, h = 1.6) ---
    draw_process(ax, 12.3, 8.0, 2.6, 1.6, "3.0", "AI Semantic Matching", "Vector Embeddings & Hybrid")
    draw_process(ax, 12.3, 5.0, 2.6, 1.6, "5.0", "Verification & Resolution", "Desk Review & Handover")
    
    # Data Store D3 for Vector Embeddings (above 3.0)
    draw_datastore(ax, 12.3, 9.8, 2.6, 0.7, "D3", "Vector Embeddings\n& Similarity Index")
    
    # ----------------------------------------------------
    # Flows: Column 1 (Student <-> Processes 1.0, 2.0, 4.0, 6.0)
    # ----------------------------------------------------
    # 1. Credentials: Student -> 1.0
    draw_arrow(ax, (2.2, 8.8), (3.2, 8.8), label="Credentials", label_offset=(0, 0.20))
    # 2. Reports: Student -> 2.0
    draw_arrow(ax, (2.2, 6.4), (3.2, 6.4), label="Reports & Photos", label_offset=(0, 0.20))
    # 3. Claims: Student -> 4.0
    draw_arrow(ax, (2.2, 3.8), (3.2, 3.8), label="Claim Proof", label_offset=(0, 0.20))
    # 4. Notifications: 6.0 -> Student
    draw_arrow(ax, (3.2, 1.2), (2.2, 2.5), label="Pickup Notices & Alerts", connectionstyle="arc3,rad=-0.12", label_offset=(-0.1, -0.25))
    
    # ----------------------------------------------------
    # Flows: Column 1 -> Center Data Stores
    # ----------------------------------------------------
    # 1.0 <-> D1
    draw_arrow(ax, (5.8, 9.0), (7.2, 9.0), label="Validate User", label_offset=(0, 0.20))
    # 2.0 -> D2
    draw_arrow(ax, (5.8, 6.4), (7.2, 6.4), label="Store Item (OPEN)", label_offset=(0, 0.20))
    # 4.0 -> D4
    draw_arrow(ax, (5.8, 3.8), (7.2, 3.8), label="Save Claim (PENDING)", label_offset=(0, 0.20))
    # D4 -> D2 vertical update
    draw_arrow(ax, (8.5, 4.2), (8.5, 6.0), label="Lock Item: CLAIM_PENDING", label_offset=(1.30, 0))
    
    # ----------------------------------------------------
    # Flows: Center Data Stores <-> Column 3
    # ----------------------------------------------------
    # D2 -> 3.0 (Active items into AI matching)
    draw_arrow(ax, (9.8, 6.7), (11.0, 7.8), label="Active Reports", connectionstyle="arc3,rad=-0.08", label_offset=(-0.1, 0.22))
    # 3.0 <-> D3 (Vector store)
    draw_arrow(ax, (12.3, 8.8), (12.3, 9.45), label="384-d Vectors", label_offset=(0.65, 0))
    # 3.0 -> 5.0 (Matches into Verification)
    draw_arrow(ax, (12.3, 7.2), (12.3, 5.8), label="Suggested Matches", label_offset=(0.85, 0))
    
    # D4 -> 5.0 (Admin reads claim evidence)
    draw_arrow(ax, (9.8, 4.0), (11.0, 4.8), label="Claim Proof", connectionstyle="arc3,rad=-0.08", label_offset=(-0.1, 0.22))
    # 5.0 -> D2 (Admin resolves item)
    draw_arrow(ax, (11.0, 5.4), (9.8, 6.2), label="Item -> RESOLVED", connectionstyle="arc3,rad=0.08", label_offset=(0.1, 0.22))
    
    # ----------------------------------------------------
    # Flows: Right Entity (Admin) <-> Process 5.0
    # ----------------------------------------------------
    draw_arrow(ax, (14.6, 5.0), (13.6, 5.0), label="Review Decision\n(Approve / Reject)", label_offset=(0, 0.35))
    
    # ----------------------------------------------------
    # Flows: Notifications pipeline (5.0 -> D5 -> 6.0)
    # ----------------------------------------------------
    # 5.0 -> D5 (Log resolution event)
    draw_arrow(ax, (11.5, 4.2), (9.8, 1.4), label="Resolution Event", connectionstyle="arc3,rad=0.15", label_offset=(0.35, 0.25))
    # D5 -> 6.0 (Read event and dispatch)
    draw_arrow(ax, (7.2, 1.2), (5.8, 1.2), label="Dispatch Queue", label_offset=(0, 0.20))
    
    plt.tight_layout()
    plt.savefig(output_path, bbox_inches='tight', dpi=300)
    plt.close()
    print(f"[OK] Generated Clean DFD Level 1: {output_path}")


# ---------------------------------------------------------------------------
# 3. DFD Level 2: Ownership Claim & Verification Lifecycle
# ---------------------------------------------------------------------------

def generate_dfd_level_2(output_path):
    fig, ax = plt.subplots(figsize=(16.8, 10.5), dpi=300)
    ax.set_xlim(0, 16.8)
    ax.set_ylim(0, 10.5)
    ax.axis('off')
    
    # Title
    ax.text(8.4, 10.0, "DFD Level 2: Ownership Claim & Administrative Verification Lifecycle",
            ha='center', va='center', fontsize=13, fontweight='bold', fontfamily='serif', color='#000000')
    
    # -----------------------------------------------------------------------
    # Row 1 (y = 8.0): Claim Submission Pipeline (Student Side, Left-to-Right)
    # -----------------------------------------------------------------------
    # External Entity: Student at x = 1.3, y = 8.0, w = 1.8, h = 1.8
    draw_entity(ax, 1.3, 8.0, 1.8, 1.8, "STUDENT", "(Claimant)")
    
    # Processes 4.1, 4.2, 4.3 (w = 2.6, h = 1.6)
    draw_process(ax, 4.6, 8.0, 2.6, 1.6, "4.1", "Claim Initiation", "Select Item & Form Request")
    draw_process(ax, 8.5, 8.0, 2.6, 1.6, "4.2", "Evidence Intake", "Confidential Marks (>=15 chars)")
    draw_process(ax, 12.4, 8.0, 2.6, 1.6, "4.3", "Validation & Locking", "Anti-Spam & Status Guard")
    
    # -----------------------------------------------------------------------
    # Row 2 (y = 4.8): Data Stores (System Memory)
    # -----------------------------------------------------------------------
    draw_datastore(ax, 4.6, 4.8, 2.6, 0.8, "D3", "Potential Matches\nStore")
    draw_datastore(ax, 8.5, 4.8, 2.6, 0.8, "D2", "Item Catalog\n(Items Store)")
    draw_datastore(ax, 12.4, 4.8, 2.6, 0.8, "D4", "Claim Records\n& Evidence Store")
    
    # -----------------------------------------------------------------------
    # Row 3 (y = 1.8): Administrative Verification & Output Pipeline
    # -----------------------------------------------------------------------
    # External Entity: Desk Moderator at x = 15.5, y = 1.8, w = 1.8, h = 1.8
    draw_entity(ax, 15.5, 1.8, 1.8, 1.8, "DESK MODERATOR", "(Security Staff)")
    
    # Processes 5.1, 5.2 (w = 2.6, h = 1.6)
    draw_process(ax, 12.4, 1.8, 2.6, 1.6, "5.1", "Evidence Audit", "Inspect Physical & Secret Marks")
    draw_process(ax, 8.5, 1.8, 2.6, 1.6, "5.2", "Atomic Adjudication", "Approve/Reject & Cascade State")
    
    # Data Store D5 (Notifications Log) at x = 4.6, y = 1.8
    draw_datastore(ax, 4.6, 1.8, 2.6, 0.8, "D5", "Notifications\nLog Store")
    
    # Process 5.3 (Notice Dispatcher) at x = 1.3, y = 1.8 (directly under STUDENT!)
    draw_process(ax, 1.3, 1.8, 2.0, 1.6, "5.3", "Notice Dispatch", "Deliver Alert")
    
    # -----------------------------------------------------------------------
    # FLOW ARROWS: Top Row (Student Intake Pipeline)
    # -----------------------------------------------------------------------
    # Student -> 4.1
    draw_arrow(ax, (2.2, 8.0), (3.3, 8.0), label="Select Found Item", label_offset=(0, 0.20))
    # 4.1 -> 4.2
    draw_arrow(ax, (5.9, 8.0), (7.2, 8.0), label="Initiate Form", label_offset=(0, 0.20))
    # 4.2 -> 4.3
    draw_arrow(ax, (9.8, 8.0), (11.1, 8.0), label="Validate Proof", label_offset=(0, 0.20))
    
    # 4.1 queries D3 (Straight vertical arrow down)
    draw_arrow(ax, (4.6, 7.2), (4.6, 5.2), label="Match Context", label_offset=(0.7, 0))
    
    # 4.3 commits to D4 and D2:
    # 4.3 -> D4 (Save claim: Straight vertical arrow down)
    draw_arrow(ax, (12.4, 7.2), (12.4, 5.2), label="Save Claim (PENDING)", label_offset=(0.95, 0))
    # 4.3 -> D2 (Lock item: Gentle diagonal arrow)
    draw_arrow(ax, (11.5, 7.2), (9.8, 5.2), label="Lock: CLAIM_PENDING", connectionstyle="arc3,rad=0.08", label_offset=(-0.15, 0.22))
    
    # -----------------------------------------------------------------------
    # FLOW ARROWS: Bottom Row (Admin Adjudication Pipeline)
    # -----------------------------------------------------------------------
    # Desk Moderator -> 5.1 (Straight horizontal arrow left)
    draw_arrow(ax, (14.6, 1.8), (13.7, 1.8), label="Review Action", label_offset=(0, 0.20))
    
    # D4 -> 5.1 (Fetch claim evidence for audit: Straight vertical arrow down)
    draw_arrow(ax, (12.4, 4.4), (12.4, 2.6), label="Fetch Claim & Marks", label_offset=(0.95, 0))
    
    # 5.1 -> 5.2 (Forward audited evidence: Straight horizontal arrow left)
    draw_arrow(ax, (11.1, 1.8), (9.8, 1.8), label="Audit Evaluation", label_offset=(0, 0.20))
    
    # 5.2 commits decision to D2 and D4:
    # 5.2 -> D2 (Update item: Straight vertical arrow UP)
    draw_arrow(ax, (8.5, 2.6), (8.5, 4.4), label="Item -> RESOLVED", label_offset=(-0.95, 0))
    # 5.2 -> D4 (Update claim: Gentle diagonal arrow)
    draw_arrow(ax, (9.4, 2.6), (11.5, 4.4), label="Claim -> APPROVED", connectionstyle="arc3,rad=-0.08", label_offset=(0.15, -0.22))
    
    # 5.2 -> D5 (Log resolution event: Straight horizontal arrow left)
    draw_arrow(ax, (7.2, 1.8), (5.9, 1.8), label="Resolution Event", label_offset=(0, 0.20))
    
    # D5 -> 5.3 (Dispatch event: Straight horizontal arrow left)
    draw_arrow(ax, (3.3, 1.8), (2.3, 1.8), label="Dispatch Queue", label_offset=(0, 0.20))
    
    # 5.3 notifies Student (Claimant): PURE VERTICAL STRAIGHT ARROW UP TO STUDENT!
    draw_arrow(ax, (1.3, 2.6), (1.3, 7.1), label="Pickup Notice & Status Delivery", label_offset=(-1.25, 0))
    
    plt.tight_layout()
    plt.savefig(output_path, bbox_inches='tight', dpi=300)
    plt.close()
    print(f"[OK] Generated Clean DFD Level 2: {output_path}")


if __name__ == "__main__":
    out_dir = os.path.dirname(os.path.abspath(__file__))
    generate_dfd_level_0(os.path.join(out_dir, "dfd_level_0.png"))
    generate_dfd_level_1(os.path.join(out_dir, "dfd_level_1.png"))
    generate_dfd_level_2(os.path.join(out_dir, "dfd_level_2.png"))
