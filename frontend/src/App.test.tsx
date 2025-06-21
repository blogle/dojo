import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import '@testing-library/jest-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import App from './App'

vi.stubGlobal('fetch', () =>
  Promise.resolve({ ok: true, json: () => Promise.resolve({ available_to_budget: '100.00' }) })
)

describe('App', () => {
  it('renders available amount', async () => {
    const client = new QueryClient()
    render(
      <QueryClientProvider client={client}>
        <App />
      </QueryClientProvider>
    )
    expect(await screen.findByTestId('available')).toHaveTextContent('100.00')
  })
})
