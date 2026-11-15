"""Exports are generated from the immutable saved prediction snapshot."""
import csv
import io
from xml.sax.saxutils import escape
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, LongTable, TableStyle
from app.schemas.traffic import AnalysisResponse


def csv_report(analysis: AnalysisResponse) -> bytes:
    output = io.StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow(["row_id", "label", "malicious_score", "source_ip", "destination_ip", "timestamp"])
    for row in analysis.predictions:
        writer.writerow([row.row_id, row.label, row.malicious_score, row.source or "",
                         row.destination or "", row.timestamp or ""])
    return output.getvalue().encode("utf-8-sig")


def pdf_report(analysis: AnalysisResponse) -> bytes:
    output = io.BytesIO()
    styles = getSampleStyleSheet()
    story = [Paragraph("NetSight AI | Traffic analysis", styles["Title"])]
    lines = [f"Analysis: {analysis.analysis_id}", f"Dataset: {analysis.filename}",
             f"Source: {analysis.source_type} (not live monitoring)", f"Created (UTC): {analysis.created_at}",
             f"Model: {analysis.model_version}", f"Decision threshold: {analysis.threshold:.6f}",
             f"Total flows: {analysis.total_flows} | Normal: {analysis.counts.normal} | Malicious: {analysis.counts.malicious}",
             f"Score definition: {analysis.score_definition}", analysis.message]
    context = analysis.model_context
    if context.get("dataset"):
        lines.append(f"Training benchmark: {context['dataset']}")
    metrics = context.get("evaluation") or {}
    for key, title in (("accuracy", "Held-out accuracy"), ("precision", "Held-out precision"),
                       ("recall", "Held-out malicious recall"), ("f1", "Held-out F1"),
                       ("false_positive_rate", "Held-out false-positive rate")):
        if key in metrics:
            lines.append(f"{title}: {metrics[key]:.2%}")
    policy = context.get("threshold_policy") or {}
    if "maximum_validation_false_positive_rate" in policy:
        lines.append(f"Threshold selection: maximize recall within a {policy['maximum_validation_false_positive_rate']:.0%} validation false-positive budget. This is not a guarantee on new traffic.")
    for limitation in context.get("limitations", []):
        lines.append(f"Limitation: {limitation}")
    for line in lines:
        story.extend([Paragraph(escape(line), styles["BodyText"]), Spacer(1, 9)])
    story.append(Paragraph("Classified records (all rows)", styles["Heading2"]))
    data = [["Row", "Classification", "Malicious score"]] + [
        [str(row.row_id), row.label, f"{row.malicious_score:.8f}"] for row in analysis.predictions]
    table = LongTable(data, repeatRows=1, colWidths=[75, 220, 170])
    table.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#173669")),
                               ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                               ("BOTTOMPADDING", (0, 0), (-1, 0), 10),
                               ("FONTSIZE", (0, 0), (-1, -1), 9),
                               ("LINEBELOW", (0, 1), (-1, -1), 0.25, colors.lightgrey)]))
    story.append(table)
    def footer(canvas, document):
        canvas.setFont("Helvetica", 9)
        canvas.drawString(40, 25, f"NetSight AI | Page {document.page} | Classification is a review signal, not proof.")
    SimpleDocTemplate(output, pagesize=A4, title="NetSight AI analysis report").build(story, onFirstPage=footer, onLaterPages=footer)
    return output.getvalue()
