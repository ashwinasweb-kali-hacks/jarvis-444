import os

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import (
    HRFlowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

PDF_PATH = "E:/jarvis/JARVIS_OS_India_Funding_Proposal_Nov10.pdf"

doc = SimpleDocTemplate(
    PDF_PATH,
    pagesize=A4,
    rightMargin=36,
    leftMargin=36,
    topMargin=34,
    bottomMargin=34,
)

styles = getSampleStyleSheet()

CYAN = colors.HexColor("#00597a")
DARK = colors.HexColor("#0d2a33")
GREY = colors.HexColor("#55606b")
LINE = colors.HexColor("#c9d6dd")

title_style = ParagraphStyle(
    "T", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=17, leading=21,
    textColor=DARK, alignment=0,
)
sub_style = ParagraphStyle(
    "S", parent=styles["Normal"], fontName="Helvetica", fontSize=10, leading=14,
    textColor=GREY,
)
h1_style = ParagraphStyle(
    "H1", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=11.5, leading=15,
    textColor=CYAN, spaceBefore=13, spaceAfter=5,
)
body_style = ParagraphStyle(
    "B", parent=styles["Normal"], fontName="Helvetica", fontSize=9.2, leading=13,
    textColor=colors.HexColor("#1d2b33"),
)
th = ParagraphStyle(
    "TH", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=8.2, leading=10.5,
    textColor=colors.white, alignment=1,
)
td = ParagraphStyle(
    "TD", parent=styles["Normal"], fontName="Helvetica", fontSize=8.0, leading=10.6,
    textColor=colors.HexColor("#1d2b33"),
)
tdb = ParagraphStyle("TDB", parent=td, fontName="Helvetica-Bold")

E = []

E.append(Paragraph("J.A.R.V.I.S. — OS", title_style))
E.append(Spacer(1, 2))
E.append(Paragraph(
    "Voice-first edge AI operating system for smart glasses · Funding request (India · INR)",
    sub_style,
))
E.append(Spacer(1, 5))
E.append(Paragraph(
    "<b>Submission target: 10 November 2026</b> &nbsp;|&nbsp; Proposal v5.0 (India edition) "
    "&nbsp;|&nbsp; Prices verified 5 November 2026",
    ParagraphStyle("D", parent=sub_style, fontSize=8.5, textColor=colors.HexColor("#b3261e")),
))
E.append(Spacer(1, 8))
E.append(HRFlowable(width="100%", thickness=1.4, color=CYAN, spaceAfter=10))

E.append(Paragraph("1. WHAT ALREADY EXISTS (NOT A CONCEPT)", h1_style))
E.append(Paragraph(
    "JARVIS-OS is a working software stack, not a slide deck. The following already runs on a "
    "standard Windows/Linux host and is covered by 24 automated tests:<br/>"
    "• <b>Voice pipeline:</b> 16 kHz dual-engine microphone capture, offline-capable speech-to-text, "
    "neural text-to-speech in four distinct agent voices (JARVIS / FRIDAY / EDITH / ULTRON).<br/>"
    "• <b>Brain:</b> OAuth-authenticated model routing (zero API-key handling, zero cloud spend), "
    "with voice-driven switching between models and a deterministic intent layer for common commands.<br/>"
    "• <b>Tool layer:</b> permission-gated host automation — launch applications, screenshot, volume, "
    "system telemetry, outbound telephony dispatch — with an append-only action log.<br/>"
    "• <b>Shell:</b> bootable image plus a kiosk HUD (glass panels, on-demand 3D holograms, "
    "real-time webcam gesture tracking with 12 gestures).<br/>"
    "The grant is requested for <b>hardware only</b> — to move this proven stack from a desktop "
    "prototype onto wearable, field-testable hardware.",
    body_style,
))
E.append(Spacer(1, 5))
E.append(Paragraph(
    "<b>Technology readiness, stated honestly.</b> The desk-bound software stack is at roughly "
    "<b>TRL 6</b> (working system demonstrated in a relevant environment). The <b>wearable product does "
    "not exist yet</b> — no glasses-mounted build, no on-device inference, no field trial. That wearable "
    "prototype is at <b>TRL 3</b>, which is exactly the stage these schemes exist to fund. This proposal "
    "asks for prototype hardware, not for money to finish software that is already finished.",
    ParagraphStyle("TRL", parent=body_style, backColor=colors.HexColor("#eef5f8"),
                   borderPadding=6, borderColor=LINE, borderWidth=0.5),
))
E.append(Spacer(1, 8))

E.append(Paragraph("2. ITEMISED BUDGET (INR, GST-INCLUSIVE ESTIMATES)", h1_style))

rows = [
    [
        Paragraph("#", th),
        Paragraph("Component", th),
        Paragraph("Role in the system", th),
        Paragraph("Cost (₹)", th),
    ],
    [
        Paragraph("1", tdb),
        Paragraph("<b>Google Pixel 10a</b><br/>8 GB / 256 GB", tdb),
        Paragraph("Pocket inference host. Tensor G4 NPU runs the quantised on-device model so the "
                  "assistant works fully offline with zero per-query cost.", td),
        Paragraph("49,999", td),
    ],
    [
        Paragraph("2", tdb),
        Paragraph("<b>Ray-Ban Meta (Gen 2)</b><br/>Wayfarer, clear lenses", tdb),
        Paragraph("Wearable camera + open-ear audio + dual microphones. The actual field-test target "
                  "for the glasses interface.", td),
        Paragraph("42,100", td),
    ],
    [
        Paragraph("3", tdb),
        Paragraph("<b>NVIDIA Jetson Orin Nano Super</b><br/>8 GB dev kit, 67 TOPS", tdb),
        Paragraph("Edge vision board. Sustains 30 FPS hand-gesture tracking and hologram rendering "
                  "without a desktop GPU.", td),
        Paragraph("42,000", td),
    ],
    [
        Paragraph("4", tdb),
        Paragraph("<b>Quectel EC200U 4G Cat-1 modem</b><br/>+ antenna, enclosure, SIM", tdb),
        Paragraph("Standalone cellular path for real voice calls independent of a paired phone.", td),
        Paragraph("3,500", td),
    ],
    [
        Paragraph("5", tdb),
        Paragraph("<b>WebRTC TURN relay</b><br/>India region VPS, 12 months", tdb),
        Paragraph("Full-duplex two-way audio between glasses, phone and host when NAT traversal fails.", td),
        Paragraph("12,000", td),
    ],
    [
        Paragraph("6", tdb),
        Paragraph("<b>Power &amp; field rig</b><br/>24,000 mAh PD 65 W, cabling, heatsinks", tdb),
        Paragraph("Continuous wearable operation for a full demo day.", td),
        Paragraph("6,500", td),
    ],
    [
        Paragraph("", tdb),
        Paragraph("<b>Sub-total</b>", tdb),
        Paragraph("", td),
        Paragraph("<b>1,56,099</b>", tdb),
    ],
    [
        Paragraph("7", tdb),
        Paragraph("<b>Contingency 10%</b>", tdb),
        Paragraph("Price movement, import duty, replacement of a failed unit during field trials.", td),
        Paragraph("15,610", tdb),
    ],
    [
        Paragraph("", tdb),
        Paragraph("<b>TOTAL REQUESTED</b>", tdb),
        Paragraph("<b>≈ US$ 1,960</b>", tdb),
        Paragraph("<b>₹1,71,709</b>", tdb),
    ],
]

t = Table(rows, colWidths=[22, 120, 260, 68], repeatRows=1)
t.setStyle(TableStyle([
    ("BACKGROUND", (0, 0), (-1, 0), CYAN),
    ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ("ALIGN", (3, 1), (3, -1), "RIGHT"),
    ("GRID", (0, 0), (-1, -1), 0.4, LINE),
    ("BACKGROUND", (0, -3), (-1, -3), colors.HexColor("#eef5f8")),
    ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#dff0f7")),
    ("TOPPADDING", (0, 0), (-1, -1), 5),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ("LEFTPADDING", (0, 0), (-1, -1), 5),
]))
E.append(t)
E.append(Spacer(1, 4))
E.append(Paragraph(
    "Indicative India retail prices captured on 5 November 2026 (Google Store India, Amazon.in, "
    "Robu.in, Indian Jetson distributors). Final invoices will be filed with the incubator; "
    "unspent contingency is returned.",
    ParagraphStyle("N", parent=body_style, fontSize=7.6, textColor=GREY),
))
E.append(Spacer(1, 8))

E.append(Paragraph("3. WHICH INDIA SCHEME THIS FITS", h1_style))

srows = [
    [
        Paragraph("Route", th),
        Paragraph("Ceiling", th),
        Paragraph("Status as of 5 Nov 2026", th),
        Paragraph("Fit for this project", th),
    ],
    [
        Paragraph("<b>NIDHI-PRAYAS 2.0</b><br/>DST, Govt. of India", tdb),
        Paragraph("₹20 L (PRAYAS Centre)<br/>₹40 L (Advance PC)", td),
        Paragraph("Open — rolling calls run by each PRAYAS Centre. No application fee, no equity taken.", td),
        Paragraph("<b>Primary.</b> Priority areas name “Hardware-based Artificial Intelligence and its "
                  "application to Indian problems” and “assistive devices”. An individual innovator may "
                  "apply without incorporating a company first.", tdb),
    ],
    [
        Paragraph("<b>MeitY TIDE 2.0</b><br/>MeitY Startup Hub", tdb),
        Paragraph("₹7 L EiR grant<br/>₹25 L seed", td),
        Paragraph("Open — delivered through 51 approved incubators; several are inviting applications now.", td),
        Paragraph("<b>Fallback in the same cycle.</b> Same prototype ask, but the seed tranche expects an "
                  "incorporated entity.", tdb),
    ],
    [
        Paragraph("<b>TANSEED 9.0</b><br/>StartupTN (Tamil Nadu)", tdb),
        Paragraph("₹10 L / ₹15 L", td),
        Paragraph("Closed for 2026 (round 8 shut Jan 2026). Next round expected Dec 2026.", td),
        Paragraph("Year-end follow-up, and only for a Tamil Nadu registered entity with DPIIT recognition.", td),
    ],
    [
        Paragraph("<b>Startup India Seed Fund (SISFS)</b>", tdb),
        Paragraph("₹20 L grant + ₹50 L debt", td),
        Paragraph("New applications closed 31 May 2026; existing grantees continue to be disbursed.", td),
        Paragraph("Not usable for a 2026 submission. Listed so no reviewer assumes it was overlooked.", td),
    ],
]
st = Table(srows, colWidths=[104, 78, 148, 140], repeatRows=1)
st.setStyle(TableStyle([
    ("BACKGROUND", (0, 0), (-1, 0), CYAN),
    ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ("GRID", (0, 0), (-1, -1), 0.4, LINE),
    ("BACKGROUND", (0, 1), (-1, 1), colors.HexColor("#e6f4ea")),
    ("TOPPADDING", (0, 0), (-1, -1), 5),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ("LEFTPADDING", (0, 0), (-1, -1), 5),
]))
E.append(st)
E.append(Spacer(1, 4))
E.append(Paragraph(
    "NIDHI-PRAYAS explicitly does <b>not</b> fund pure software, and does not fund products that have "
    "already crossed MVP. This application therefore covers only the <b>wearable hardware prototype</b> "
    "(glasses mount, on-device inference board, cellular modem, power rig) — the software it runs is "
    "already written and is contributed by the applicant at no cost to the grant.",
    ParagraphStyle("N2", parent=body_style, fontSize=7.8, textColor=GREY),
))
E.append(Spacer(1, 8))

E.append(Paragraph("4. WHY THIS DESERVES THE MONEY", h1_style))
E.append(Paragraph(
    "• <b>Indian-problem framing.</b> The same stack that controls a workshop desktop can give a "
    "visually impaired or motor-impaired user hands-free control of a phone, and can run fully "
    "offline in low-connectivity districts — voice in, voice out, no cloud bill.<br/>"
    "• <b>Zero recurring cost.</b> On-device inference on donated hardware means no subscription "
    "or API spend after the grant is closed, which is what most public-funding reviewers ask first.<br/>"
    "• <b>Auditable safety.</b> Every tool call is allow-listed and logged; destructive actions "
    "require explicit spoken confirmation. This is a design requirement, not a feature.<br/>"
    "• <b>Small, defensible ask.</b> ₹1.72 lakh buys the complete field kit. This is a "
    "prototype-validation request, not a payroll request.",
    body_style,
))
E.append(Spacer(1, 8))

E.append(Paragraph("5. MILESTONES TO 10 NOVEMBER 2026", h1_style))
mrows = [
    [Paragraph("Date", th), Paragraph("Deliverable", th), Paragraph("Evidence produced", th)],
    [Paragraph("5 Nov (done)", tdb),
     Paragraph("Working voice stack, 24/24 tests green, bootable image built.", td),
     Paragraph("Test log + commit history.", td)],
    [Paragraph("6–7 Nov", tdb),
     Paragraph("On-device model deployed and benchmarked on the target phone class.", td),
     Paragraph("Offline latency and token-rate table.", td)],
    [Paragraph("8 Nov", tdb),
     Paragraph("Full-duplex WebRTC call path, two-way audio verified.", td),
     Paragraph("Recorded call, < 200 ms one-way latency.", td)],
    [Paragraph("9 Nov", tdb),
     Paragraph("12-gesture recognition tuned under indoor and outdoor light.", td),
     Paragraph("30 FPS capture with per-gesture accuracy.", td)],
    [Paragraph("10 Nov", tdb),
     Paragraph("<b>Live demonstration + submission pack.</b>", td),
     Paragraph("<b>Grant reviewed against a running system.</b>", tdb)],
]
mt = Table(mrows, colWidths=[68, 240, 162], repeatRows=1)
mt.setStyle(TableStyle([
    ("BACKGROUND", (0, 0), (-1, 0), CYAN),
    ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ("GRID", (0, 0), (-1, -1), 0.4, LINE),
    ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#fdf0ef")),
    ("TOPPADDING", (0, 0), (-1, -1), 5),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ("LEFTPADDING", (0, 0), (-1, -1), 5),
]))
E.append(mt)
E.append(Spacer(1, 10))

E.append(HRFlowable(width="100%", thickness=0.8, color=LINE, spaceAfter=8))
E.append(Paragraph(
    "<b>Applicant:</b> JARVIS-OS project · <b>Entity type:</b> individual innovator / early-stage startup "
    "(DPIIT recognition in progress)<br/>"
    "<b>Seeking:</b> ₹1,71,709 non-dilutive hardware grant · <b>Deliverable:</b> field-tested wearable "
    "AI assistant, open documentation, and test suite<br/>"
    "<b>Contact channel:</b> via the incubator / PRAYAS Centre application portal",
    ParagraphStyle("F", parent=body_style, fontSize=8, textColor=GREY),
))

doc.build(E)
print(f"OK {PDF_PATH} ({os.path.getsize(PDF_PATH)} bytes)")
