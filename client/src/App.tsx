import { useEffect, useReducer, useRef } from 'react'
import { ApiError, submitComplaint } from './api'
import Composer from './components/Composer'
import MessageBubble from './components/MessageBubble'
import { conversationReducer, initialConversation } from './conversation'

export default function App() {
  const [conversation, dispatch] = useReducer(conversationReducer, initialConversation)
  const { step, draft, messages } = conversation
  const end = useRef<HTMLDivElement>(null)

  // Keep the newest message in view.
  useEffect(() => {
    end.current?.scrollIntoView({ block: 'end' })
  }, [messages.length, step])

  async function submit() {
    dispatch({ type: 'submit' })
    try {
      dispatch({ type: 'saved', receipt: await submitComplaint(draft) })
    } catch (caught) {
      const message =
        caught instanceof ApiError
          ? caught.message
          : 'Something went wrong, so your complaint has not been saved. Please submit again.'
      dispatch({ type: 'failed', message })
    }
  }

  return (
    <div className="app">
      <header className="app-header">
        <div>
          <h1>Hostel Complaint Bot</h1>
          <p>Tell the bot what is wrong. It files the complaint and gives you an ID.</p>
        </div>
        {step !== 'name' && step !== 'submitting' && step !== 'done' && (
          <button
            type="button"
            className="link-button"
            onClick={() => dispatch({ type: 'restart', keepIdentity: false })}
          >
            Start over
          </button>
        )}
      </header>

      <main className="messages" role="log" aria-live="polite" aria-label="Conversation">
        {messages.map((message) => (
          <MessageBubble key={message.id} message={message} />
        ))}
        {step === 'submitting' && <p className="bubble bot pending">Saving your complaint…</p>}
        <div ref={end} />
      </main>

      <footer className="composer">
        {(step === 'name' || step === 'room' || step === 'complaint') && (
          <Composer key={step} step={step} onSend={(text) => dispatch({ type: 'answer', text })} />
        )}

        {(step === 'review' || step === 'submitting') && (
          <div className="choices">
            <button type="button" className="primary" onClick={submit} disabled={step === 'submitting'} autoFocus>
              {step === 'submitting' ? 'Submitting…' : 'Submit complaint'}
            </button>
          </div>
        )}

        {step === 'done' && (
          <div className="choices">
            <button
              type="button"
              className="secondary"
              onClick={() => dispatch({ type: 'restart', keepIdentity: true })}
            >
              Report another problem
            </button>
            <button
              type="button"
              className="secondary"
              onClick={() => dispatch({ type: 'restart', keepIdentity: false })}
            >
              New complaint for someone else
            </button>
          </div>
        )}
      </footer>
    </div>
  )
}
