import type { Message } from '../conversation'
import { categoryLabel, urgencyLabel } from '../labels'

export default function MessageBubble({ message }: { message: Message }) {
  switch (message.kind) {
    case 'text':
      return <p className={`bubble ${message.from}`}>{message.text}</p>

    case 'problem':
      return (
        <p className="bubble bot problem" role="alert">
          {message.text}
        </p>
      )

    case 'review':
      return (
        <dl className="bubble bot details">
          <dt>Name</dt>
          <dd>{message.draft.name}</dd>
          <dt>Room</dt>
          <dd>{message.draft.room}</dd>
          <dt>Complaint</dt>
          <dd className="multiline">{message.draft.complaint}</dd>
        </dl>
      )

    case 'receipt': {
      const { id, category, urgency, summary } = message.receipt
      return (
        <div className="bubble bot receipt">
          <p className="receipt-label">Complaint ID</p>
          <p className="receipt-id">{id}</p>
          <dl className="details">
            <dt>Category</dt>
            <dd>{categoryLabel(category)}</dd>
            <dt>Urgency</dt>
            <dd>
              <span className={`urgency ${urgency}`}>{urgencyLabel(urgency)}</span>
            </dd>
            {summary && (
              <>
                <dt>Summary</dt>
                <dd>{summary}</dd>
              </>
            )}
          </dl>
        </div>
      )
    }
  }
}
