import { useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { History, LayoutTemplate, Sparkles } from 'lucide-react'
import { useI18n } from '@/i18n'
import { REPORTS } from '@/i18n/messages/reports'
import { PageContainer } from '@/components/layout/PageContainer'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { GenerateWeeklyWizard } from '@/components/reports/GenerateWeeklyWizard'
import { HistoryTab } from '@/components/reports/HistoryTab'
import { TemplatesTab } from '@/components/reports/TemplatesTab'
import type { WeekRef } from '@/lib/dates'

type TabValue = 'gerar' | 'historico' | 'templates'

/**
 * Central de Relatórios: gerar o weekly (fluxo em 3 passos com montagem e
 * ordenação animada dos slides), histórico de apresentações e templates.
 * A aba ativa fica na URL (?tab=) para permitir link direto.
 */
export function ReportsPage() {
  const { t } = useI18n()
  const [searchParams, setSearchParams] = useSearchParams()
  const tabParam = searchParams.get('tab')
  const tab: TabValue =
    tabParam === 'historico' || tabParam === 'templates' ? tabParam : 'gerar'

  const setTab = (value: string) => {
    setSearchParams(value === 'gerar' ? {} : { tab: value }, { replace: true })
  }

  /** Semana pré-selecionada ao pedir "Gerar nova versão" no histórico. */
  const [presetWeek, setPresetWeek] = useState<WeekRef | null>(null)

  return (
    <PageContainer title={t(REPORTS.title)} maxWidth="5xl">
      <Tabs value={tab} onValueChange={setTab}>
        <TabsList>
          <TabsTrigger value="gerar">
            <Sparkles className="h-4 w-4" aria-hidden="true" />
            {t(REPORTS.tabGenerate)}
          </TabsTrigger>
          <TabsTrigger value="historico">
            <History className="h-4 w-4" aria-hidden="true" />
            {t(REPORTS.tabHistory)}
          </TabsTrigger>
          <TabsTrigger value="templates">
            <LayoutTemplate className="h-4 w-4" aria-hidden="true" />
            {t(REPORTS.tabTemplates)}
          </TabsTrigger>
        </TabsList>

        <TabsContent value="gerar">
          <GenerateWeeklyWizard
            key={presetWeek ? `${presetWeek.year}-${presetWeek.week}` : 'default'}
            initialWeek={presetWeek ?? undefined}
            onViewHistory={() => setTab('historico')}
          />
        </TabsContent>

        <TabsContent value="historico">
          <HistoryTab
            onGenerate={() => setTab('gerar')}
            onRegenerate={(ref) => {
              setPresetWeek(ref)
              setTab('gerar')
            }}
          />
        </TabsContent>

        <TabsContent value="templates">
          <TemplatesTab />
        </TabsContent>
      </Tabs>
    </PageContainer>
  )
}
