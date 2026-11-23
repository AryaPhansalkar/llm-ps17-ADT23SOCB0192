// The conversation as a state machine. The bot asks for one thing at a time:
//
//   name -> room -> complaint -> review -> submitting -> done
//
// Everything the bot says while collecting details is decided here, in the
// browser, so replies are instant. The LLM is used once, on the server, to
// classify the finished complaint.
import {
  COMPLAINT_MAX_CHARS,
  COMPLAINT_MIN_CHARS,
  NAME_MAX_CHARS,
  NAME_MIN_CHARS,
  ROOM_MAX_CHARS,
} from './limits'
import type { Draft, Receipt } from './types'

export type Step = 'name' | 'room' | 'complaint' | 'review' | 'submitting' | 'done'

/** What a message says. A message in the conversation also has an id (see Message). */
type MessageBody =
  | { from: 'bot' | 'user'; kind: 'text'; text: string }
  | { from: 'bot'; kind: 'problem'; text: string }
  | { from: 'bot'; kind: 'review'; draft: Draft }
  | { from: 'bot'; kind: 'receipt'; receipt: Receipt }

export type Message = MessageBody & { id: number }

export interface Conversation {
  step: Step
  draft: Draft
  messages: Message[]
}

export type Action =
  | { type: 'answer'; text: string }
  | { type: 'submit' }
  | { type: 'saved'; receipt: Receipt }
  | { type: 'failed'; message: string }
  | { type: 'restart'; keepIdentity: boolean }

const EMPTY_DRAFT: Draft = { name: '', room: '', complaint: '' }

const GREETING =
  "Hi, I'm the hostel complaint assistant. I'll note your complaint and pass it to the hostel office. First, what's your name?"

const bot = (text: string): MessageBody => ({ from: 'bot', kind: 'text', text })

export const initialConversation: Conversation = {
  step: 'name',
  draft: EMPTY_DRAFT,
  messages: [{ id: 1, ...bot(GREETING) }],
}

export function conversationReducer(state: Conversation, action: Action): Conversation {
  switch (action.type) {
    case 'answer':
      return answer(state, action.text)

    case 'submit':
      return state.step === 'review' ? { ...state, step: 'submitting' } : state

    case 'saved':
      return add({ ...state, step: 'done' }, ...receiptMessages(state.draft, action.receipt))

    case 'failed':
      // Back to the review step, so the Submit button is there to try again.
      return add({ ...state, step: 'review' }, { from: 'bot', kind: 'problem', text: action.message })

    case 'restart':
      if (action.keepIdentity) {
        const { name, room } = state.draft
        return add(
          { ...state, step: 'complaint', draft: { name, room, complaint: '' } },
          bot(`Sure. I'll use the same details: ${name}, room ${room}. What's the next problem?`),
        )
      }
      return add({ ...state, step: 'name', draft: EMPTY_DRAFT }, bot("Let's start again. What's your name?"))
  }
}

/** Handles what the user typed, according to the question the bot last asked. */
function answer(state: Conversation, typed: string): Conversation {
  const text = typed.trim()
  if (text === '') return state
  const said = add(state, { from: 'user', kind: 'text', text })

  switch (state.step) {
    case 'name': {
      const name = singleSpaced(text)
      if (name.length < NAME_MIN_CHARS) {
        return add(said, bot('I need your name to register the complaint. What is your full name?'))
      }
      if (name.length > NAME_MAX_CHARS) {
        return add(said, bot("That's too long for a name. Please type just your name."))
      }
      return add(
        { ...said, step: 'room', draft: { ...said.draft, name } },
        bot(`Thanks, ${firstName(name)}. Which room are you in? Include the block if there is one, for example B-204.`),
      )
    }

    case 'room': {
      const room = singleSpaced(text)
      if (room.length > ROOM_MAX_CHARS) {
        return add(said, bot("That's too long for a room number. Something like B-204 is enough."))
      }
      return add(
        { ...said, step: 'complaint', draft: { ...said.draft, room } },
        bot("Got it. What's the problem? Say what is wrong and where, in a sentence or two."),
      )
    }

    case 'complaint': {
      if (text.length < COMPLAINT_MIN_CHARS) {
        return add(said, bot('Please describe the problem in a few more words, so the staff know what to fix.'))
      }
      if (text.length > COMPLAINT_MAX_CHARS) {
        return add(
          said,
          bot(`That's over ${COMPLAINT_MAX_CHARS.toLocaleString()} characters. Please shorten it to the main problem.`),
        )
      }
      const draft = { ...said.draft, complaint: text }
      return add(
        { ...said, step: 'review', draft },
        bot('Please check the details before I submit them.'),
        { from: 'bot', kind: 'review', draft },
      )
    }

    default:
      return state // nothing is being asked right now
  }
}

function receiptMessages(draft: Draft, receipt: Receipt): MessageBody[] {
  const messages: MessageBody[] = [
    bot(`Your complaint is registered, ${firstName(draft.name)}.`),
    { from: 'bot', kind: 'receipt', receipt },
  ]

  if (!receipt.classified) {
    const reason = receipt.classification_problem ? ` (${receipt.classification_problem})` : ''
    messages.push(
      bot(`It is saved, but I couldn't sort it automatically${reason}. The hostel office will sort it by hand.`),
    )
  } else if (receipt.urgency === 'high') {
    messages.push(
      bot(
        "I've marked this as high urgency. If anyone is in danger right now, don't wait for this complaint to be read: contact the warden or security directly.",
      ),
    )
  }
  messages.push(bot(`Keep the ID ${receipt.id}. Quote it if you need to follow up with the hostel office.`))
  return messages
}

function add(state: Conversation, ...messages: MessageBody[]): Conversation {
  const lastId = state.messages.at(-1)?.id ?? 0
  const numbered: Message[] = messages.map((message, index) => ({ ...message, id: lastId + index + 1 }))
  return { ...state, messages: [...state.messages, ...numbered] }
}

function singleSpaced(text: string): string {
  return text.split(/\s+/).filter(Boolean).join(' ')
}

function firstName(name: string): string {
  return name.split(' ')[0] ?? name
}
