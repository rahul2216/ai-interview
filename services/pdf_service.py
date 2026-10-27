import io
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT

class PDFReportService:
    @staticmethod
    def generate_interview_pdf(interview):
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=40,
            leftMargin=40,
            topMargin=40,
            bottomMargin=40
        )
        
        styles = getSampleStyleSheet()
        primary_color = colors.HexColor("#0f172a") # Navy
        accent_blue = colors.HexColor("#2563eb") # Blue
        text_dark = colors.HexColor("#334155")
        
        title_style = ParagraphStyle(
            "DocTitle",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=22,
            leading=26,
            textColor=primary_color,
            alignment=TA_LEFT
        )
        
        subtitle_style = ParagraphStyle(
            "DocSubtitle",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=11,
            leading=15,
            textColor=accent_blue,
            alignment=TA_LEFT
        )
        
        h2_style = ParagraphStyle(
            "Heading2Style",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=14,
            leading=18,
            textColor=primary_color,
            spaceBefore=14,
            spaceAfter=6
        )
        
        body_style = ParagraphStyle(
            "BodyDark",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=9.5,
            leading=13.5,
            textColor=text_dark
        )
        
        bold_style = ParagraphStyle(
            "BoldDark",
            parent=body_style,
            fontName="Helvetica-Bold"
        )

        elements = []

        # Header
        elements.append(Paragraph("AI MOCK INTERVIEW — PERFORMANCE REPORT", title_style))
        elements.append(Spacer(1, 4))
        elements.append(Paragraph(f"Official Job Simulation Evaluation for {interview.candidate_name}", subtitle_style))
        elements.append(Spacer(1, 10))
        elements.append(HRFlowable(width="100%", thickness=1.5, color=accent_blue, spaceBefore=4, spaceAfter=14))

        # Overview Table
        overview_data = [
            [
                Paragraph("<b>Target Role:</b>", body_style),
                Paragraph(str(interview.target_role), body_style),
                Paragraph("<b>Target Company:</b>", body_style),
                Paragraph(str(interview.target_company), body_style)
            ],
            [
                Paragraph("<b>Interview Type:</b>", body_style),
                Paragraph(str(interview.interview_type), body_style),
                Paragraph("<b>Difficulty:</b>", body_style),
                Paragraph(str(interview.difficulty), body_style)
            ],
            [
                Paragraph("<b>Candidate Type:</b>", body_style),
                Paragraph(f"{interview.candidate_type} ({interview.experience_years} yrs exp)", body_style),
                Paragraph("<b>Session ID:</b>", body_style),
                Paragraph(str(interview.session_id)[:16] + "...", body_style)
            ],
            [
                Paragraph("<b>Overall Score:</b>", bold_style),
                Paragraph(f"<b>{interview.percentage_score:.1f}%</b> ({interview.total_score:.1f}/{interview.max_score:.1f})", bold_style),
                Paragraph("<b>Readiness Level:</b>", bold_style),
                Paragraph(f"<b>{interview.readiness_estimate}</b>", bold_style)
            ]
        ]
        
        overview_table = Table(overview_data, colWidths=[110, 150, 110, 160])
        overview_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
            ('BOX', (0, 0), (-1, -1), 1, colors.HexColor("#e2e8f0")),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ]))
        elements.append(overview_table)
        elements.append(Spacer(1, 14))

        # Disclaimer Notice
        disclaimer_text = (
            "<i>Notice: This evaluation was generated using AI interview simulations for practice and readiness benchmarking. "
            "It does not guarantee employment or selection by the target company.</i>"
        )
        elements.append(Paragraph(disclaimer_text, ParagraphStyle("Disc", parent=body_style, fontSize=8, textColor=colors.HexColor("#64748b"))))
        elements.append(Spacer(1, 12))

        # Question by Question Detailed Feedback
        elements.append(Paragraph("Question-by-Question Evaluation", h2_style))
        elements.append(HRFlowable(width="100%", thickness=0.8, color=colors.HexColor("#cbd5e1"), spaceBefore=2, spaceAfter=8))

        for q in interview.questions:
            q_answer = q.answer
            status_color = "#16a34a" if (q_answer and q_answer.correctness_status == "correct") else ("#d97706" if (q_answer and q_answer.correctness_status == "partially_correct") else "#dc2626")
            score_display = f"{q_answer.score:.1f}/100" if q_answer else "0/100 (Unanswered)"
            
            elements.append(Paragraph(
                f"<b>Question {q.sequence_number}:</b> {q.question_text}",
                ParagraphStyle("QTitle", parent=body_style, fontName="Helvetica-Bold", fontSize=10, textColor=primary_color)
            ))
            elements.append(Spacer(1, 3))
            elements.append(Paragraph(
                f"Topic: <b>{q.topic}</b> | Type: {q.question_type.title()} | Score: <b>{score_display}</b> (<font color='{status_color}'>{q_answer.correctness_status.replace('_', ' ').title() if q_answer else 'Skipped'}</font>)",
                ParagraphStyle("QMeta", parent=body_style, fontSize=8.5, textColor=colors.HexColor("#475569"))
            ))
            elements.append(Spacer(1, 4))
            
            cand_resp = q_answer.answer_text if q_answer and q_answer.answer_text else "[Candidate skipped or left blank]"
            feedback = q_answer.feedback if q_answer else {}
            
            elements.append(Paragraph(f"<b>Candidate's Response:</b> \"{cand_resp}\"", body_style))
            elements.append(Spacer(1, 4))
            
            if feedback:
                if feedback.get("strengths"):
                    elements.append(Paragraph(f"<b>Key Strengths:</b> {'; '.join(feedback['strengths'])}", body_style))
                    elements.append(Spacer(1, 2))
                if feedback.get("missing_concepts"):
                    elements.append(Paragraph(f"<b>Missing Concepts:</b> {'; '.join(feedback['missing_concepts'])}", body_style))
                    elements.append(Spacer(1, 2))
                if feedback.get("model_answer"):
                    elements.append(Paragraph(f"<b>Model Answer:</b> {feedback['model_answer']}", ParagraphStyle("ModelAns", parent=body_style, fontName="Helvetica-Oblique", textColor=colors.HexColor("#1e293b"))))
                    elements.append(Spacer(1, 2))
                if feedback.get("improvement_tips"):
                    elements.append(Paragraph(f"<b>Actionable Tips:</b> {'; '.join(feedback['improvement_tips'])}", body_style))
            
            elements.append(Spacer(1, 10))
            elements.append(HRFlowable(width="100%", thickness=0.4, color=colors.HexColor("#e2e8f0"), spaceBefore=2, spaceAfter=8))

        doc.build(elements)
        buffer.seek(0)
        return buffer
