import os

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import HRFlowable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

OUT = "E:/jarvis/funding/JARVIS_OS_OnePager.pdf"
CYAN = colors.HexColor("#00597a")
DARK = colors.HexColor("#0d2a33")
GREY = colors.HexColor("#55606b")
LINE = colors.HexColor("#c9d6dd")

s = getSampleStyleSheet()
T = ParagraphStyle("T", parent=s["Normal"], fontName="Helvetica-Bold", fontSize=15, leading=18, textColor=DARK)
S = ParagraphStyle("S", parent=s["Normal"], fontName="Helvetica", fontSize=8.6, leading=12, textColor=GREY)
H = ParagraphStyle("H", parent=s["Normal"], fontName="Helvetica-Bold", fontSize=9.2, leading=12,
                   textColor=CYAN, spaceBefore=9, spaceAfter=3)
B = ParagraphStyle("B", parent=s["Normal"], fontName="Helvetica", fontSize=8.4, leading=11.6,
                   textColor=colors.HexColor("#1d2b33"))
BD = ParagraphStyle("BD", parent=B, fontName="Helvetica-Bold")
TD = ParagraphStyle("TD", parent=B, fontSize=7.8, leading=10.2)
TH = ParagraphStyle("TH", parent=B, fontName="Helvetica-Bold", fontSize=7.8, textColor=colors.white, alignment=1)

E = []
E.append(Paragraph("JARVIS-OS — one page", T))
E.append(Paragraph("A voice-first AI assistant for smart glasses. Software finished. Hardware missing.", S))
E.append(Spacer(1, 6))
E.append(HRFlowable(width="100%", thickness=1.2, color=CYAN, spaceAfter=8))

E.append(Paragraph("THE ASK", H))
E.append(Paragraph("<b>₹1,71,709</b> (≈ US$1,960) for prototype hardware only. Non-dilutive. "
                   "Invoices filed for every rupee; unspent balance returned.", B))

E.append(Paragraph("WHAT ALREADY WORKS", H))
E.append(Paragraph(
    "Voice in → speech-to-text → decision → spoken reply → action on the machine. Four agent voices, "
    "permission-gated host automation with an append-only audit log, on-demand 3D holograms, real-time "
    "webcam hand-gesture control, and an OAuth model path that costs nothing per query. "
    "24 automated tests pass headless. A bootable image exists.", B))

E.append(Paragraph("WHAT IT IS NOT YET", H))
E.append(Paragraph(
    "It has never run on a wearable. No glasses-mounted build, no on-device inference, no field trial. "
    "Desk software ≈ TRL 6; the wearable product is ≈ TRL 3. That gap is what this money closes.", B))

E.append(Paragraph("WHERE THE MONEY GOES", H))
rows = [
    [Paragraph("Item", TH), Paragraph("Purpose", TH), Paragraph("₹", TH)],
    [Paragraph("Pixel 10a 8/256", TD), Paragraph("Pocket inference host — offline, zero per-query cost", TD), Paragraph("49,999", TD)],
    [Paragraph("Ray-Ban Meta Gen 2", TD), Paragraph("The wearable target: microphones, camera, open-ear audio", TD), Paragraph("42,100", TD)],
    [Paragraph("Jetson Orin Nano Super 8 GB", TD), Paragraph("30 FPS gesture tracking and hologram rendering", TD), Paragraph("42,000", TD)],
    [Paragraph("Quectel EC200U 4G + SIM", TD), Paragraph("Standalone cellular calling path", TD), Paragraph("3,500", TD)],
    [Paragraph("WebRTC TURN relay, 12 mo", TD), Paragraph("Two-way audio through NAT", TD), Paragraph("12,000", TD)],
    [Paragraph("Power & field rig", TD), Paragraph("A full demo day on battery", TD), Paragraph("6,500", TD)],
    [Paragraph("Contingency 10%", TD), Paragraph("Duty, price movement, one replacement", TD), Paragraph("15,610", TD)],
    [Paragraph("Total", TD), Paragraph("", TD), Paragraph("1,71,709", TD)],
]
t = Table(rows, colWidths=[136, 320, 60])
t.setStyle(TableStyle([
    ("BACKGROUND", (0, 0), (-1, 0), CYAN),
    ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ("ALIGN", (2, 1), (2, -1), "RIGHT"),
    ("GRID", (0, 0), (-1, -1), 0.35, LINE),
    ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#dff0f7")),
    ("TOPPADDING", (0, 0), (-1, -1), 3.5),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
]))
E.append(t)

E.append(Paragraph("SCHEMES THAT FIT (status verified 5 Nov 2026)", H))
E.append(Paragraph(
    "<b>NIDHI-PRAYAS 2.0, DST</b> — up to ₹20 L via a PRAYAS Centre. Priority areas name "
    "“Hardware-based Artificial Intelligence” and “assistive devices”. Individual innovator may apply "
    "without a company. No fee, no equity. <b>MeitY TIDE 2.0</b> — ₹7 L EiR / ₹25 L seed via 51 "
    "incubators, needs an incorporated entity. <b>TANSEED 9.0</b> — next window ≈ Dec 2026. "
    "<b>SISFS</b> — closed to new applications since 31 May 2026.", B))

E.append(Paragraph("WHAT I WANT FROM YOU", H))
E.append(Paragraph(
    "1. The date of your next innovator call, and the format you want the proposal in.<br/>"
    "2. A 15-minute slot. I will demonstrate the working system live, not slides.<br/>"
    "3. If this is out of scope for you — one introduction to someone it is in scope for.", B))

E.append(Spacer(1, 7))
E.append(HRFlowable(width="100%", thickness=0.7, color=LINE, spaceAfter=5))
E.append(Paragraph(
    "Applicant: individual innovator · DPIIT recognition in progress · No prior government grant above ₹40 L · "
    "IP fully owned by the applicant · Software contributed at no cost to the grant.",
    ParagraphStyle("F", parent=S, fontSize=7.2)))

SimpleDocTemplate(OUT, pagesize=A4, leftMargin=34, rightMargin=34, topMargin=30, bottomMargin=28).build(E)
print(f"OK {OUT} ({os.path.getsize(OUT)} bytes)")
