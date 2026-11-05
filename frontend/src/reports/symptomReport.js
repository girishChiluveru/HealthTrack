import { Chart, LinearScale, LineController, LineElement, PointElement } from 'chart.js';
import { jsPDF } from 'jspdf';
import { autoTable } from 'jspdf-autotable';
import { buildChartData, buildChartOptions, PRINT_THEME } from '../symptoms/chartConfig.js';
import { formatDate } from '../symptoms/dates.js';

Chart.register(LinearScale, LineController, LineElement, PointElement);

const MAX_ENTRIES = 2000;
const FETCH_PAGE_SIZE = 100;
const MAX_CHART_SYMPTOMS = 6;
const MARGIN = 40;
const DETAIL_INDENT = 80;
const CHART_WIDTH_PX = 1400;
const CHART_HEIGHT_PX = 620;
const CHART_MARK_SCALE = 1.75;
const BRAND = [91, 63, 224];
const INK = [23, 20, 46];
const MUTED = [94, 91, 120];
const LINE = [231, 228, 243];
const TINT = [246, 245, 252];

// Built-in PDF fonts cover Western European text only, and anything else would print as
// garbage, so those characters become "?" and the report says that it happened.
function makeTextCleaner() {
  const state = { replaced: false };
  const clean = (text) =>
    String(text ?? '')
      .replace(/\s+/g, ' ')
      .replace(/[‘’]/g, "'")
      .replace(/[“”]/g, '"')
      .replace(/[^ -~¡-ÿ–—]/gu, () => {
        state.replaced = true;
        return '?';
      })
      .trim();
  return { clean, state };
}

async function fetchEntries(source, filters) {
  const entries = [];
  let total = 0;
  for (let page = 1; entries.length < MAX_ENTRIES; page += 1) {
    const result = await source.fetchHistory({ ...filters, page, pageSize: FETCH_PAGE_SIZE });
    total = result.total;
    entries.push(...result.entries);
    if (result.entries.length === 0 || entries.length >= total) {
      break;
    }
  }
  return { entries: entries.slice(0, MAX_ENTRIES), total };
}

function summarize(entries) {
  const bySymptom = new Map();
  for (const entry of entries) {
    const summary = bySymptom.get(entry.symptom_key) ?? {
      key: entry.symptom_key,
      // Entries arrive newest first, so this is the latest spelling and the latest date.
      name: entry.symptom_name,
      latest: entry.occurred_on,
      days: new Set(),
      count: 0,
      highest: entry.severity,
      lowest: entry.severity,
    };
    summary.days.add(entry.occurred_on);
    summary.count += 1;
    summary.highest = Math.max(summary.highest, entry.severity);
    summary.lowest = Math.min(summary.lowest, entry.severity);
    bySymptom.set(entry.symptom_key, summary);
  }
  return [...bySymptom.values()];
}

async function fetchChartSeries(source, symptoms, styles, { startDate, endDate }) {
  const charted = symptoms.slice(0, MAX_CHART_SYMPTOMS);
  const trends = await Promise.all(
    charted.map(({ key }) => source.fetchTrend({ symptom: key, startDate, endDate })),
  );
  return charted
    .map(({ key, name }, index) => ({
      key,
      name,
      points: trends[index].points,
      style: styles.get(key),
    }))
    .filter(({ points, style }) => points.length > 0 && style);
}

function renderChart(series, dateRange) {
  const canvas = document.createElement('canvas');
  canvas.width = CHART_WIDTH_PX;
  canvas.height = CHART_HEIGHT_PX;
  const chart = new Chart(canvas, {
    type: 'line',
    data: buildChartData(series, PRINT_THEME, CHART_MARK_SCALE),
    options: {
      ...buildChartOptions(series, dateRange, PRINT_THEME, { animate: false, fontSize: 22 }),
      responsive: false,
      devicePixelRatio: 1,
    },
  });
  const image = canvas.toDataURL('image/png');
  chart.destroy();
  return image;
}

function periodLabel({ startDate, endDate }) {
  if (!startDate && !endDate) {
    return 'All dates';
  }
  const start = startDate ? formatDate(startDate) : 'Earliest entry';
  const end = endDate ? formatDate(endDate) : 'latest entry';
  return `${start} to ${end}`;
}

function drawHeader(doc, pageWidth) {
  doc.setFillColor(...BRAND);
  doc.roundedRect(MARGIN, MARGIN - 6, 22, 22, 5, 5, 'F');
  doc.setDrawColor(255, 255, 255);
  doc.setLineWidth(1.6);
  doc.lines(
    [
      [4, 0],
      [2, -5],
      [3, 9],
      [2, -4],
      [4, 0],
    ],
    MARGIN + 3,
    MARGIN + 5,
  );
  doc.setFont('helvetica', 'bold');
  doc.setFontSize(16);
  doc.setTextColor(...INK);
  doc.text('HealthTrack', MARGIN + 30, MARGIN + 10);
  doc.setFont('helvetica', 'normal');
  doc.setFontSize(11);
  doc.setTextColor(...MUTED);
  doc.text('Symptom report', pageWidth - MARGIN, MARGIN + 10, { align: 'right' });
  doc.setDrawColor(...LINE);
  doc.setLineWidth(0.75);
  doc.line(MARGIN, MARGIN + 24, pageWidth - MARGIN, MARGIN + 24);
  return MARGIN + 44;
}

function drawDetails(doc, details, startY, width) {
  let y = startY;
  doc.setFontSize(10);
  for (const [label, value] of details) {
    doc.setFont('helvetica', 'bold');
    doc.setTextColor(...MUTED);
    doc.text(label, MARGIN, y);
    doc.setFont('helvetica', 'normal');
    doc.setTextColor(...INK);
    const lines = doc.splitTextToSize(value, width - DETAIL_INDENT);
    doc.text(lines, MARGIN + DETAIL_INDENT, y);
    y += lines.length * 15;
  }
  return y + 6;
}

function drawHeading(doc, text, y) {
  doc.setFont('helvetica', 'bold');
  doc.setFontSize(13);
  doc.setTextColor(...INK);
  doc.text(text, MARGIN, y);
  return y + 10;
}

function drawParagraph(doc, text, y, width) {
  doc.setFont('helvetica', 'normal');
  doc.setFontSize(10);
  doc.setTextColor(...MUTED);
  const lines = doc.splitTextToSize(text, width);
  doc.text(lines, MARGIN, y);
  return y + lines.length * 13 + 6;
}

function drawChartLegend(doc, series, clean, startY, pageWidth) {
  let x = MARGIN;
  let y = startY;
  doc.setFont('helvetica', 'normal');
  doc.setFontSize(9);
  doc.setTextColor(...INK);
  doc.setLineWidth(2);
  for (const { name, style } of series) {
    const label = doc.splitTextToSize(clean(name), 130)[0];
    const width = 26 + doc.getTextWidth(label) + 16;
    if (x + width > pageWidth - MARGIN) {
      x = MARGIN;
      y += 15;
    }
    doc.setDrawColor(PRINT_THEME.series[style.colorIndex]);
    doc.setLineDashPattern(style.dash, 0);
    doc.line(x, y - 3, x + 20, y - 3);
    doc.setLineDashPattern([], 0);
    doc.text(label, x + 26, y);
    x += width;
  }
  return y + 20;
}

function drawFooters(doc, pageWidth, pageHeight) {
  const pageCount = doc.getNumberOfPages();
  for (let page = 1; page <= pageCount; page += 1) {
    doc.setPage(page);
    doc.setFont('helvetica', 'normal');
    doc.setFontSize(8);
    doc.setTextColor(...MUTED);
    doc.text('Self-reported entries. Not a medical assessment.', MARGIN, pageHeight - 22);
    doc.text(`Page ${page} of ${pageCount}`, pageWidth - MARGIN, pageHeight - 22, {
      align: 'right',
    });
  }
}

const TABLE_STYLES = {
  theme: 'grid',
  margin: { left: MARGIN, right: MARGIN, bottom: 44 },
  styles: { font: 'helvetica', fontSize: 9, cellPadding: 5, textColor: INK, lineColor: LINE },
  headStyles: { fillColor: TINT, textColor: INK, fontStyle: 'bold' },
};

// Everything comes through `source`, the page's own authorized calls, so the API checks access.
export async function exportSymptomReport({
  source,
  filters,
  filterName,
  styles,
  patientName,
  generatedOn,
}) {
  const { entries, total } = await fetchEntries(source, filters);
  if (entries.length === 0) {
    return { included: 0, total };
  }
  const symptoms = summarize(entries);
  const series = await fetchChartSeries(source, symptoms, styles, filters);

  const { clean, state } = makeTextCleaner();
  const doc = new jsPDF({ unit: 'pt', format: 'a4' });
  doc.setProperties({ title: 'HealthTrack symptom report', creator: 'HealthTrack' });
  const pageWidth = doc.internal.pageSize.getWidth();
  const pageHeight = doc.internal.pageSize.getHeight();
  const contentWidth = pageWidth - MARGIN * 2;

  let y = drawHeader(doc, pageWidth);
  y = drawDetails(
    doc,
    [
      ['Patient', clean(patientName) || 'Not available'],
      ['Generated', formatDate(generatedOn)],
      ['Period', periodLabel(filters)],
      ['Symptom', filterName ? clean(filterName) : 'All symptoms'],
    ],
    y,
    contentWidth,
  );

  const first = formatDate(entries.at(-1).occurred_on);
  const last = formatDate(entries[0].occurred_on);
  const entryWord = entries.length === 1 ? 'entry' : 'entries';
  const symptomWord = symptoms.length === 1 ? 'symptom' : 'symptoms';
  y = drawHeading(doc, 'Summary', y + 4) + 6;
  y = drawParagraph(
    doc,
    `${entries.length} ${entryWord} for ${symptoms.length} ${symptomWord}, from ${first} to ` +
      `${last}. Severity is self-reported on a scale of 1 to 10.` +
      (total > entries.length
        ? ` This report is limited to the newest ${entries.length} of ${total} matching ` +
          'entries. Choose a shorter period to include earlier ones.'
        : ''),
    y,
    contentWidth,
  );

  autoTable(doc, {
    ...TABLE_STYLES,
    startY: y,
    head: [['Symptom', 'Entries', 'Days logged', 'Highest', 'Lowest', 'Latest entry']],
    body: symptoms.map((item) => [
      clean(item.name),
      item.count,
      item.days.size,
      `${item.highest}/10`,
      `${item.lowest}/10`,
      formatDate(item.latest),
    ]),
  });
  y = doc.lastAutoTable.finalY + 26;

  if (series.length > 0) {
    const imageHeight = (contentWidth * CHART_HEIGHT_PX) / CHART_WIDTH_PX;
    if (y + imageHeight + 70 > pageHeight - 44) {
      doc.addPage();
      y = MARGIN + 10;
    }
    y = drawHeading(doc, 'Severity over time', y) + 6;
    const note =
      'The highest severity each day. Breaks in a line are days with no entries.' +
      (symptoms.length > series.length
        ? ` Showing the ${series.length} most recently logged of ${symptoms.length} symptoms.`
        : '');
    y = drawParagraph(doc, note, y, contentWidth);
    doc.addImage(renderChart(series, filters), 'PNG', MARGIN, y, contentWidth, imageHeight);
    drawChartLegend(doc, series, clean, y + imageHeight + 14, pageWidth);
  }

  doc.addPage();
  y = drawHeading(doc, 'Entries', MARGIN + 10) + 6;
  autoTable(doc, {
    ...TABLE_STYLES,
    startY: y,
    showHead: 'everyPage',
    head: [['Date', 'Symptom', 'Severity', 'Notes']],
    columnStyles: {
      0: { cellWidth: 78 },
      1: { cellWidth: 130 },
      2: { cellWidth: 56 },
    },
    body: entries.map((entry) => [
      formatDate(entry.occurred_on),
      clean(entry.symptom_name),
      `${entry.severity}/10`,
      clean(entry.notes),
    ]),
  });

  if (state.replaced) {
    let noteY = doc.lastAutoTable.finalY + 18;
    doc.setPage(doc.getNumberOfPages());
    if (noteY + 30 > pageHeight - 44) {
      doc.addPage();
      noteY = MARGIN + 10;
    }
    drawParagraph(
      doc,
      'Characters this report cannot display are shown as "?". The original text is unchanged ' +
        'in HealthTrack.',
      noteY,
      contentWidth,
    );
  }

  drawFooters(doc, pageWidth, pageHeight);
  doc.save(`healthtrack-report-${generatedOn}.pdf`);
  return { included: entries.length, total };
}
