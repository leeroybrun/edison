'use client'

import { useOptimistic } from 'react'

interface Message {
  id: string
  text: string
  author: string
}

// React 19 useOptimistic hook example - optimistic updates with server actions
export function MessageList({
  initialMessages,
  sendMessage,
}: {
  initialMessages: Message[]
  sendMessage: (text: string) => Promise<void>
}) {
  const [messages, optimisticMessages] = useOptimistic<Message[], string>(
    initialMessages,
    (state, newMessage) => [
      ...state,
      {
        id: Math.random().toString(),
        text: newMessage,
        author: 'You',
      },
    ]
  )

  async function handleSendMessage(formData: FormData) {
    const text = formData.get('message') as string
    
    // Update UI optimistically
    optimisticMessages(text)
    
    // Make server request
    await sendMessage(text)
  }

  return (
    <div className="space-y-4">
      <div className="max-h-96 overflow-y-auto space-y-2">
        {messages.map((msg) => (
          <div
            key={msg.id}
            className="p-2 bg-gray-100 rounded"
            style={{ opacity: msg.author === 'You' ? 0.7 : 1 }}
          >
            <p className="font-semibold text-sm">{msg.author}</p>
            <p>{msg.text}</p>
          </div>
        ))}
      </div>

      <form action={handleSendMessage} className="flex gap-2">
        <input
          name="message"
          type="text"
          placeholder="Type a message..."
          className="flex-1 px-3 py-2 border rounded"
          required
        />
        <button
          type="submit"
          className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
        >
          Send
        </button>
      </form>
    </div>
  )
}
