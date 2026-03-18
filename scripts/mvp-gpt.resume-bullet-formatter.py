from copy import deepcopy
from docx import Document

input_doc = '/Users/alexandercarnevale/Library/CloudStorage/OneDrive-Personal/career/applications/2026-03-17 - Modulate/Resume - Modulate.docx'
output_doc = '/Users/alexandercarnevale/Library/CloudStorage/OneDrive-Personal/career/applications/2026-03-17 - Modulate/2026-03-12/3-18 output.docx'


CONSULTING_PLACEHOLDER = "[CONSULTING_BULLETS_HERE]"
ADP_PLACEHOLDER = "[ADP_BULLETS_HERE]"


RAW_CONSULTING_BULLETS = """
• Enabled faster, more confident leadership decisions by establishing a trusted source of truth across pipeline, conversion, and revenue performance data.
• Increased revenue team productivity by implementing automation and process improvements that reduced manual work, improved deal velocity, and enabled teams to focus on higher-value activities.
• Converted fragmented GTM data into actionable insights that improved conversion, reduced churn, and supported net revenue expansion.
• Improved revenue engine performance by standardizing lifecycle management, increasing forecast accuracy, and strengthening pipeline visibility across Sales, Marketing, and Customer Success.
• Built automation and AI leverage into the operating model to improve execution capacity, reduce process drag, and create a more scalable foundation for growth.
• Managed the revenue systems ecosystem as an operational backbone, aligning system design, governance, and reporting to support growth and cross-functional execution.
• Created the operating conditions for GTM teams to perform at their best by aligning systems, process discipline, and reporting around clearer execution and shared accountability.

""".strip()


RAW_ADP_BULLETS = """
• Built the operational foundation for sustainable scale by standardizing lifecycle processes, improving data governance, and implementing systems that supported growth with greater consistency and less friction.
• Increased revenue team productivity by implementing automation and process improvements that reduced manual work, improved deal velocity, and enabled teams to focus on higher-value activities.
• Converted analytical insight into operational action by linking reporting, process diagnosis, and cross-functional decision-making to measurable execution improvements.
• Built the data foundation for growth by standardizing revenue data, improving reporting accuracy, and creating visibility into pipeline, conversion, retention, and forecast performance.

""".strip()


def parse_bullets(raw_text: str) -> list[str]:
    raw_text = raw_text.strip()
    bullets = []

    for line in raw_text.splitlines():
        line = line.strip()
        if not line:
            continue

        for prefix in ("•", "-", "*"):
            if line.startswith(prefix):
                line = line[len(prefix):].strip()
                break

        if line:
            bullets.append(line)

    return bullets


def clone_paragraph_after(paragraph):
    new_p = deepcopy(paragraph._p)
    paragraph._p.addnext(new_p)
    return new_p


def clear_paragraph_runs(paragraph):
    for run in paragraph.runs:
        run.text = ""


def replace_placeholder_with_bullets(doc, placeholder, bullet_items):
    if not bullet_items:
        return  # skip silently for MVP

    target_para = None
    for para in doc.paragraphs:
        if para.text.strip() == placeholder:
            target_para = para
            break

    if target_para is None:
        print(f"Warning: placeholder not found -> {placeholder}")
        return

    # Replace placeholder with first bullet
    clear_paragraph_runs(target_para)
    if target_para.runs:
        target_para.runs[0].text = bullet_items[0]
    else:
        target_para.add_run(bullet_items[0])

    # Insert remaining bullets
    current_para = target_para
    for bullet_text in bullet_items[1:]:
        new_p_xml = clone_paragraph_after(current_para)
        new_para = current_para._parent.paragraphs[
            current_para._parent._element.index(new_p_xml)
        ]

        clear_paragraph_runs(new_para)
        if new_para.runs:
            new_para.runs[0].text = bullet_text
        else:
            new_para.add_run(bullet_text)

        current_para = new_para


def main():
    doc = Document(input_doc)

    placeholder_map = {
        CONSULTING_PLACEHOLDER: parse_bullets(RAW_CONSULTING_BULLETS),
        ADP_PLACEHOLDER: parse_bullets(RAW_ADP_BULLETS),
    }

    for placeholder, bullets in placeholder_map.items():
        replace_placeholder_with_bullets(doc, placeholder, bullets)

    doc.save(output_doc)
    print("Done.")


if __name__ == "__main__":
    main()