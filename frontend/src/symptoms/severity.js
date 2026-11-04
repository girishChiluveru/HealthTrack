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

const SYMPTOM_COLORS = ['#4f46e5', '#059669', '#7c3aed', '#d97706', '#0284c7', '#db2777'];

// Derived from the symptom itself, so a symptom keeps its colour as others come and go.
export function symptomColor(key) {
  const hash = [...key].reduce((total, character) => total + character.codePointAt(0), 0);
  return SYMPTOM_COLORS[hash % SYMPTOM_COLORS.length];
}
