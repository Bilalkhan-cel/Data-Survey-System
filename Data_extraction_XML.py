"""XML extraction utilities for the survey system.

This module preserves the original functions from the legacy project
(``extract_columns``, ``extract_images``, ``extract_questions_ans_value``) and
extends them with a single richer extractor (``extract_full_survey``) that the
new front-end consumes. The extension adds:

  * option-level image support (attribute form and child-element form),
  * question ``id``, ``type`` and section metadata,
  * survey title / description / section instructions.

Nothing about the original parsing behaviour was removed, so any future XML
changes that the old parser understood still work.
"""

import xml.etree.ElementTree as et

from AI_integration import change_sentence

coloums = []


# ---------------------------------------------------------------------------
# Legacy helpers (kept intact for backwards compatibility)
# ---------------------------------------------------------------------------
def extract_columns(path):
    """Return the ordered list of question ids (used as DB column names)."""
    try:
        mytree = et.parse(path)
        myroot = mytree.getroot()
        cols = []
        for x in myroot.findall("Section"):
            for y in x.findall("Question"):
                cols.append(y.get("id"))
        return cols
    except Exception as e:
        return f"Coloums Extraction Failed   Error={e}  Kindly check your XML format"


def extract_images(path):
    """Legacy: question-level <image> tags keyed by question id."""
    img = {}
    try:
        mytree = et.parse(path)
        myroot = mytree.getroot()
        for x in myroot.findall("Section"):
            for y in x.findall("Question"):
                for z in y.findall("image"):
                    img[y.get("id")] = {
                        "src": z.attrib["src"],
                        "width": z.attrib.get("width"),
                        "height": z.attrib.get("height"),
                    }
        return img
    except Exception as e:
        return f"Images Extraction Failed   Error={e}  Kindly check your XML format"


def extract_questions_ans_value(path):
    """Legacy: {question_text: [ {value: label}, ... ]} mapping."""
    try:
        mytree = et.parse(path)
        myroot = mytree.getroot()

        questions = {}

        for section in myroot.findall("Section"):
            options = []

            # Section-level options
            for z in section.findall("Options"):
                for w in z.findall("Option"):
                    options.append({w.get("value"): _option_label(w)})

            for question in section.findall("Question"):
                text = question.findtext("Text")
                for ai in question.findall("AI"):
                    if ai.text == "yes":
                        text = change_sentence(text)

                question_options = question.find("Options")
                if question_options is not None:
                    q_options = []
                    for w in question_options.findall("Option"):
                        q_options.append({w.get("value"): _option_label(w)})
                    questions[text] = q_options
                else:
                    questions[text] = options.copy()

        return questions
    except Exception as e:
        return f"Questions Extraction Failed. Error = {e}"


# ---------------------------------------------------------------------------
# Extended extraction (image support + full metadata)
# ---------------------------------------------------------------------------
def _option_label(option_el):
    """Read an option's label from either a <Text> child or inline text."""
    text_child = option_el.find("Text")
    if text_child is not None and text_child.text:
        return text_child.text.strip()
    return (option_el.text or "").strip()


def _option_image(option_el):
    """Read an option image path from the attribute form OR child-element form.

    Supported forms:
        <Option value="1" image="images/example.png">Label</Option>
        <Option value="1"><Text>Label</Text><Image>images/example.png</Image></Option>

    Returns None when the option has no image (options still work without one).
    """
    attr_img = option_el.get("image")
    if attr_img:
        return attr_img.strip()
    image_child = option_el.find("Image")
    if image_child is not None and image_child.text:
        return image_child.text.strip()
    return None


def _build_options(option_els):
    options = []
    for w in option_els:
        options.append(
            {
                "value": w.get("value"),
                "label": _option_label(w),
                "image": _option_image(w),
                "allowsOtherText": w.get("allowsOtherText") == "true",
            }
        )
    return options


def extract_full_survey(path):
    """Return a structured survey the front-end can render directly.

    Shape:
        {
          "title": str,
          "description": str,
          "questions": [
            {
              "id": str,
              "type": str,
              "section": str,
              "instruction": str | None,
              "text": str,
              "options": [
                {"value", "label", "image", "allowsOtherText"}, ...
              ],
            }, ...
          ],
        }
    """
    try:
        mytree = et.parse(path)
        myroot = mytree.getroot()

        survey = {
            "title": (myroot.findtext("Title") or "Survey").strip(),
            "description": (myroot.findtext("Description") or "").strip(),
            "questions": [],
        }

        for section in myroot.findall("Section"):
            section_name = section.get("name") or ""
            instruction = section.findtext("Instruction")
            if instruction:
                instruction = instruction.strip()

            # Section-level (shared) options.
            section_options_el = section.find("Options")
            section_options = (
                _build_options(section_options_el.findall("Option"))
                if section_options_el is not None
                else []
            )

            for question in section.findall("Question"):
                text = question.findtext("Text")
                for ai in question.findall("AI"):
                    if ai.text == "yes":
                        text = change_sentence(text)

                # Per-question options override section options when present.
                q_options_el = question.find("Options")
                if q_options_el is not None:
                    options = _build_options(q_options_el.findall("Option"))
                else:
                    options = [dict(o) for o in section_options]

                survey["questions"].append(
                    {
                        "id": question.get("id"),
                        "type": question.get("type") or "single-choice",
                        "section": section_name,
                        "instruction": instruction,
                        "text": (text or "").strip(),
                        "options": options,
                    }
                )

        return survey
    except Exception as e:
        return {"error": f"Survey Extraction Failed. Error = {e}"}
    
    
    
# print(extract_full_survey("data.xml")) 
