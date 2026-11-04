export const SEVERITY_LEVELS = Array.from({ length: 10 }, (_, index) => index + 1);

// Display bands for colouring severity. They are not clinical categories.
export function severityBand(severity) {
  if (severity <= 3) {
    return 'mild';
  }
  return severity <= 6 ? 'moderate' : 'severe';
}

const BAND_LABELS = { mild: 'Mild', moderate: 'Moderate', severe: 'Severe' };

export function severityLabel(severity) {
  return BAND_LABELS[severityBand(severity)];
}

// Any two lines can cross on a chart, so these were validated as all pairs, not just neighbours.
const SYMPTOM_COLORS = ['#5b3fe0', '#0369a1', '#0ea5e9', '#059669', '#ea580c', '#92400e'];
const POINT_STYLES = ['circle', 'rect', 'triangle', 'rectRot'];
const DASHES = [[], [6, 4]];
const SLOT_COUNT = SYMPTOM_COLORS.length * DASHES.length;

function hashKey(key) {
  return [...key].reduce((total, character) => total + character.codePointAt(0), 0);
}

// Tries every color with solid lines before starting on dashed ones.
function freeSlot(hash, used) {
  for (let tier = 0; tier < DASHES.length; tier += 1) {
    for (let offset = 0; offset < SYMPTOM_COLORS.length; offset += 1) {
      const slot = tier * SYMPTOM_COLORS.length + ((hash + offset) % SYMPTOM_COLORS.length);
      if (!used.has(slot)) {
        return slot;
      }
    }
  }
  return 0;
}

// Gives each symptom a color, marker, and dash. Symptoms are assigned from the full list, so
// hiding or filtering others never repaints a line. Markers keep lines apart without color.
export function assignSymptomStyles(keys) {
  const used = new Set();
  const styles = new Map();
  for (const key of [...keys].sort()) {
    if (used.size === SLOT_COUNT) {
      used.clear();
    }
    const slot = freeSlot(hashKey(key), used);
    used.add(slot);
    const colorIndex = slot % SYMPTOM_COLORS.length;
    const tier = Math.floor(slot / SYMPTOM_COLORS.length);
    styles.set(key, {
      color: SYMPTOM_COLORS[colorIndex],
      pointStyle: POINT_STYLES[(colorIndex + tier) % POINT_STYLES.length],
      dash: DASHES[tier],
    });
  }
  return styles;
}
