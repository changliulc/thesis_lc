# Word Template Audit

Basis:
- Word template: `tmp/docs/xdu_template_2025_1.docx`
- Current thesis PDF: `xdupgthesis_template_lc.pdf`
- Current thesis source: `xdupgthesis_template_lc.tex`
- Current class file: `xdupgthesis.cls`

Scope checked:
- Cover
- Chinese title page
- Chinese abstract
- English abstract
- Main text
- Figure/table captions
- References
- Page numbers

Confirmed aligned or close:
- Main embedded fonts have been switched to `SimSun`, `SimHei`, and `Times New Roman`.
- Cover and Chinese title page are visually close to the Word template hierarchy after the font switch.
- Chinese abstract title/body/keywords use the expected font family route and 20 pt baseline setting.
- English abstract title/body/keywords use the expected `Times New Roman` route and 20 pt baseline setting.
- Main text uses small-four-size body text with 20 pt baseline and first-line indentation.
- Figure captions are below figures and table titles are above tables; representative pages look close to the Word template habit.
- Reference heading and bibliography environment in the class are set to the expected title-plus-entry hierarchy.

Confirmed remaining risks:
- Body Arabic page numbers are still rendered with the Latin font route, so in the PDF they appear to follow `Times New Roman`, while the Word template says body page numbers should be `宋体`.
- Online references `[1]` and `[3]` still lack access date / citation date even though they include URLs.

Notes:
- The font-name mismatch raised earlier is no longer the main problem after switching to `cjk-font = win` and `latin-font = tac`.
- I did not find a clear visual mismatch in cover/title-page structure after the font switch.
- The current remaining problems are more about strict rule interpretation than obvious visual breakage.
