import { useQuery } from '@tanstack/react-query'
import api from '@/lib/api'
import type { DashboardStats } from '@/types'

/**
 * Estatísticas da semana atual do usuário (GET /dashboard).
 * queryKey: ['dashboard'] — invalide essa chave após criar/editar atividades
 * ou gerar um weekly para a Home refletir os números novos.
 */
export function useDashboard() {
  return useQuery({
    queryKey: ['dashboard'],
    queryFn: async () => {
      const { data } = await api.get<DashboardStats>('/dashboard')
      return data
    },
  })
}
