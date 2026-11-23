import type { Draft, Receipt } from './types'

const SERVER_UNREACHABLE =
  "I can't reach the server, so your complaint has not been saved. Make sure the server is running, then submit again."

/** An error whose message is written to be shown to the user. */
export class ApiError extends Error {}

export async function submitComplaint(draft: Draft): Promise<Receipt> {
  let response: Response
  try {
    response = await fetch('/api/v1/complaints/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(draft),
    })
  } catch {
    throw new ApiError(SERVER_UNREACHABLE)
  }
  if (!response.ok) throw new ApiError(await errorMessage(response))
  return (await response.json()) as Receipt
}

/**
 * The server reports errors as {"detail": "..."} or, for invalid fields,
 * {"field": ["message", ...]}. Anything else means the server itself is down
 * and the dev proxy answered instead.
 */
async function errorMessage(response: Response): Promise<string> {
  const body: unknown = await response.json().catch(() => null)

  if (typeof body === 'object' && body !== null && !Array.isArray(body)) {
    const fields = body as Record<string, unknown>
    if (response.status === 429) return 'Too many complaints were sent in a short time. Wait a minute and submit again.'
    if (typeof fields.detail === 'string') return fields.detail
    const messages = Object.values(fields)
      .flat()
      .filter((value): value is string => typeof value === 'string')
    if (messages.length > 0) return messages.join(' ')
  }
  return response.status >= 500 ? SERVER_UNREACHABLE : `The server did not accept the complaint (${response.status}).`
}
