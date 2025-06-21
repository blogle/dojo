import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useDashboardQuery } from './services/api'
import './App.css'

const queryClient = new QueryClient()

function Dashboard() {
  const { data, isLoading, error } = useDashboardQuery()
  if (isLoading) return <p>Loading...</p>
  if (error) return <p>Error loading dashboard</p>
  return (
    <div className="card">
      <h1 className="text-lg font-bold">Available to Budget</h1>
      <p className="text-2xl" data-testid="available">{data?.available_to_budget}</p>
    </div>
  )
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <Dashboard />
    </QueryClientProvider>
  )
}

export default App
