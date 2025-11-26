'use client'

import { useFormStatus } from 'react-dom'

// React 19 useFormStatus hook example
export function SubmitButton() {
  const { pending } = useFormStatus()
  
  return (
    <button
      disabled={pending}
      className="px-4 py-2 bg-blue-500 text-white rounded disabled:bg-gray-400"
      type="submit"
    >
      {pending ? 'Submitting...' : 'Submit'}
    </button>
  )
}

// Form component that uses the status
export function ContactForm({ onSubmit }: { onSubmit: (formData: FormData) => Promise<void> }) {
  return (
    <form action={onSubmit} className="space-y-4">
      <div>
        <label htmlFor="email" className="block text-sm font-medium">
          Email
        </label>
        <input
          id="email"
          name="email"
          type="email"
          className="w-full px-3 py-2 border rounded"
          required
        />
      </div>
      
      <div>
        <label htmlFor="message" className="block text-sm font-medium">
          Message
        </label>
        <textarea
          id="message"
          name="message"
          className="w-full px-3 py-2 border rounded"
          rows={4}
          required
        />
      </div>
      
      <SubmitButton />
    </form>
  )
}
