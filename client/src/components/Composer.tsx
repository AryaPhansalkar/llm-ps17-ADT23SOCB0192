import { useState, type FormEvent, type KeyboardEvent } from 'react'

type AskingFor = 'name' | 'room' | 'complaint'

const PROMPTS: Record<AskingFor, { label: string; placeholder: string }> = {
  name: { label: 'Your name', placeholder: 'Your name' },
  room: { label: 'Your room number', placeholder: 'Room number, for example B-204' },
  complaint: { label: 'Your complaint', placeholder: 'Describe the problem' },
}

interface ComposerProps {
  step: AskingFor
  onSend: (text: string) => void
}

/** The box the user types answers into. Enter sends; in the complaint box, Shift+Enter adds a line. */
export default function Composer({ step, onSend }: ComposerProps) {
  const [text, setText] = useState('')
  const { label, placeholder } = PROMPTS[step]

  function send() {
    if (text.trim() === '') return
    onSend(text)
    setText('')
  }

  function handleSubmit(event: FormEvent) {
    event.preventDefault()
    send()
  }

  function handleKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing) {
      event.preventDefault()
      send()
    }
  }

  return (
    <form className="composer-form" onSubmit={handleSubmit}>
      {step === 'complaint' ? (
        <textarea
          rows={3}
          aria-label={label}
          placeholder={placeholder}
          value={text}
          onChange={(event) => setText(event.target.value)}
          onKeyDown={handleKeyDown}
          autoFocus
        />
      ) : (
        <input
          type="text"
          aria-label={label}
          placeholder={placeholder}
          autoComplete={step === 'name' ? 'name' : 'off'}
          value={text}
          onChange={(event) => setText(event.target.value)}
          autoFocus
        />
      )}
      <button type="submit" className="primary" disabled={text.trim() === ''}>
        Send
      </button>
    </form>
  )
}
