const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  AlignmentType, BorderStyle, WidthType, ShadingType, HeadingLevel,
  VerticalAlign
} = require("docx");
const fs = require("fs");
const path = require("path");

const QUESTIONS = [
  "What are the employee's key strengths demonstrated in this session?",
  "What areas of improvement or development gaps were identified?",
  "How effectively did the employee communicate and collaborate?",
  "What specific achievements or contributions did the employee make?",
  "How did the employee handle challenges or difficult situations?",
  "What is the overall performance rating and justification for this employee?",
  "What are the recommended next steps or action items for this employee?",
];

const PLACEHOLDERS = QUESTIONS.map((_, i) => `{{Q${i + 1}_ANSWER}}`);

// ── Helpers ──────────────────────────────────────────────────────────────────

const cellBorder = { style: BorderStyle.SINGLE, size: 1, color: "CCCCCC" };
const allBorders = { top: cellBorder, bottom: cellBorder, left: cellBorder, right: cellBorder };

function sectionHeader(text) {
  return new Paragraph({
    children: [new TextRun({ text, bold: true, size: 28, font: "Arial", color: "1F3864" })],
    spacing: { before: 480, after: 160 },
  });
}

function questionBlock(index, question, placeholder) {
  // Question label row (blue header)
  const labelRow = new TableRow({
    children: [
      new TableCell({
        borders: allBorders,
        shading: { fill: "D5E8F0", type: ShadingType.CLEAR },
        margins: { top: 80, bottom: 80, left: 160, right: 160 },
        width: { size: 9360, type: WidthType.DXA },
        children: [
          new Paragraph({
            children: [
              new TextRun({ text: `Q${index + 1}. `, bold: true, size: 22, font: "Arial", color: "1F3864" }),
              new TextRun({ text: question, bold: true, size: 22, font: "Arial", color: "1F3864" }),
            ],
          }),
        ],
      }),
    ],
  });

  // Answer box row (blank with placeholder)
  const answerRow = new TableRow({
    children: [
      new TableCell({
        borders: allBorders,
        margins: { top: 120, bottom: 120, left: 160, right: 160 },
        width: { size: 9360, type: WidthType.DXA },
        verticalAlign: VerticalAlign.TOP,
        children: [
          new Paragraph({
            children: [
              new TextRun({
                text: placeholder,
                size: 20,
                font: "Arial",
                color: "999999",
                italics: true,
              }),
            ],
          }),
          // Extra empty lines to make the answer box taller
          new Paragraph({ children: [new TextRun({ text: "", size: 20 })] }),
          new Paragraph({ children: [new TextRun({ text: "", size: 20 })] }),
          new Paragraph({ children: [new TextRun({ text: "", size: 20 })] }),
        ],
      }),
    ],
  });

  const table = new Table({
    width: { size: 9360, type: WidthType.DXA },
    columnWidths: [9360],
    rows: [labelRow, answerRow],
  });

  return [
    table,
    new Paragraph({ children: [new TextRun({ text: "" })], spacing: { after: 240 } }),
  ];
}

// ── Build document ────────────────────────────────────────────────────────────

const children = [
  // Title
  new Paragraph({
    children: [new TextRun({ text: "Employee Performance Review", bold: true, size: 40, font: "Arial", color: "1F3864" })],
    alignment: AlignmentType.CENTER,
    spacing: { after: 80 },
  }),
  new Paragraph({
    children: [new TextRun({ text: "AI-Generated Analysis Report", size: 24, font: "Arial", color: "4472C4" })],
    alignment: AlignmentType.CENTER,
    spacing: { after: 480 },
  }),

  // Employee info row
  new Table({
    width: { size: 9360, type: WidthType.DXA },
    columnWidths: [4680, 4680],
    rows: [
      new TableRow({
        children: [
          new TableCell({
            borders: allBorders,
            shading: { fill: "F2F2F2", type: ShadingType.CLEAR },
            margins: { top: 80, bottom: 80, left: 160, right: 160 },
            width: { size: 4680, type: WidthType.DXA },
            children: [new Paragraph({ children: [new TextRun({ text: "Employee ID:  _______________", size: 20, font: "Arial" })] })],
          }),
          new TableCell({
            borders: allBorders,
            shading: { fill: "F2F2F2", type: ShadingType.CLEAR },
            margins: { top: 80, bottom: 80, left: 160, right: 160 },
            width: { size: 4680, type: WidthType.DXA },
            children: [new Paragraph({ children: [new TextRun({ text: "Review Date:  _______________", size: 20, font: "Arial" })] })],
          }),
        ],
      }),
    ],
  }),

  new Paragraph({ children: [new TextRun({ text: "" })], spacing: { after: 320 } }),

  sectionHeader("Performance Review Questions & Answers"),
];

// Add all 7 question blocks
QUESTIONS.forEach((q, i) => {
  questionBlock(i, q, PLACEHOLDERS[i]).forEach(el => children.push(el));
});

// Instructions footer
children.push(
  new Paragraph({
    children: [
      new TextRun({
        text: "Note: Placeholder tokens (e.g. {{Q1_ANSWER}}) are automatically replaced by the emp-genai pipeline.",
        size: 16, font: "Arial", color: "999999", italics: true,
      }),
    ],
    spacing: { before: 480 },
  })
);

const doc = new Document({
  sections: [{
    properties: {
      page: {
        size: { width: 12240, height: 15840 },
        margin: { top: 1080, right: 1080, bottom: 1080, left: 1080 },
      },
    },
    children,
  }],
});

const outPath = path.join(__dirname, "templates", "template_answer.docx");
fs.mkdirSync(path.dirname(outPath), { recursive: true });

Packer.toBuffer(doc).then(buf => {
  fs.writeFileSync(outPath, buf);
  console.log("✓ template_answer.docx created at", outPath);
});
