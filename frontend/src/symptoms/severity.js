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

const COLOR_COUNT = 6;
const POINT_STYLES = ['circle', 'rect', 'triangle', 'rectRot'];
const DASHES = [[], [6, 4]];
const SLOT_COUNT = COLOR_COUNT * DASHES.length;

function hashKey(key) {
  return [...key].reduce((total, character) => total + character.codePointAt(0), 0);
}

function freeSlot(hash, used) {
  for (let tier = 0; tier < DASHES.length; tier += 1) {
    for (let offset = 0; offset < COLOR_COUNT; offset += 1) {
      const slot = tier * COLOR_COUNT + ((hash + offset) % COLOR_COUNT);
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
    const colorIndex = slot % COLOR_COUNT;
    const tier = Math.floor(slot / COLOR_COUNT);
    styles.set(key, {
      colorIndex,
      color: `var(--series-${colorIndex + 1})`,
      pointStyle: POINT_STYLES[(colorIndex + tier) % POINT_STYLES.length],
      dash: DASHES[tier],
    });
  }
  return styles;
}
