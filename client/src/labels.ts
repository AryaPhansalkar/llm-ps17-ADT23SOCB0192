// How the server's category and urgency values are shown to the student.
const CATEGORY_LABELS: Record<string, string> = {
  electrical: 'Electrical',
  water: 'Water and plumbing',
  mess: 'Mess and food',
  internet: 'Internet',
  cleanliness: 'Cleanliness',
  maintenance: 'Repairs and maintenance',
  security: 'Safety and security',
  other: 'Other',
  unclassified: 'Not sorted yet',
}

const URGENCY_LABELS: Record<string, string> = {
  high: 'High',
  medium: 'Medium',
  low: 'Low',
  unclassified: 'Not set yet',
}

export const categoryLabel = (category: string) => CATEGORY_LABELS[category] ?? category
export const urgencyLabel = (urgency: string) => URGENCY_LABELS[urgency] ?? urgency
