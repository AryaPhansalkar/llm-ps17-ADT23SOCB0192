/** What the student tells the bot. */
export interface Draft {
  name: string
  room: string
  complaint: string
}

/** What the server sends back once a complaint is saved. */
export interface Receipt {
  id: string
  submitted_at: string
  category: string
  urgency: string
  summary: string
  /** False when the complaint was saved but could not be sorted automatically. */
  classified: boolean
  /** Why classification failed. Only sent by a server running in debug mode. */
  classification_problem?: string
}
