import { useQuery } from '@tanstack/react-query'

export interface Dashboard {
  available_to_budget: string
}

export function useDashboardQuery() {
  const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:3000'
  return useQuery({
    queryKey: ['dashboard'],
    queryFn: async () => {
      const res = await fetch(`${apiUrl}/dashboard`)
      if (!res.ok) throw new Error('Failed to fetch dashboard')
      return (await res.json()) as Dashboard
    },
  })
}
