"use client"

import { useState, useEffect } from "react"
import { Card, CardHeader, CardTitle, CardContent, CardDescription, CardFooter } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Switch } from "@/components/ui/switch"
import { Badge } from "@/components/ui/badge"
import { createClient } from "@/lib/supabase/client"
import {
  Bot,
  Calculator,
  FileCheck,
  Users,
  BarChart3,
  Bell,
  MessageCircle,
  Mail,
  Loader2,
  ChevronRight,
  Shield,
  Clock,
  Activity,
  Settings,
} from "lucide-react"
import { toast } from "sonner"

const API_URL = process.env.NEXT_PUBLIC_CREWAI_SERVICE_URL || "http://localhost:8003/v1"
const API_KEY = process.env.NEXT_PUBLIC_CREWAI_API_KEY || "demo-key"

interface AgentConfig {
  key: string
  type: string
  title: string
  titleFr: string
  description: string
  descriptionFr: string
  icon: React.ReactNode
  color: string
  gradientFrom: string
  gradientTo: string
  phase: "mvp" | "phase2"
  features: string[]
  whatsappExample: string
}

const AGENTS: AgentConfig[] = [
  {
    key: "financial",
    type: "financial_assistant",
    title: "Financial Assistant",
    titleFr: "Assistant Financier",
    description: "Analyzes bank transactions for anomalies, duplicates, and spending patterns. Tags transactions and generates insights.",
    descriptionFr: "Analyse vos transactions bancaires : anomalies, doublons, tendances de dépenses. Catégorise et génère des insights.",
    icon: <Calculator className="h-6 w-6" />,
    color: "text-blue-600 dark:text-blue-400",
    gradientFrom: "from-blue-500",
    gradientTo: "to-cyan-500",
    phase: "mvp",
    features: [
      "Duplicate and anomaly detection",
      "Transaction categorization (taxes, rent, subscriptions...)",
      "Monthly spending insights",
      "Unusual charge alerts",
    ],
    whatsappExample: "3 anomalies detected this month. Subscriptions up 20% vs. average. Monthly report ready for your accountant.",
  },
  {
    key: "tax",
    type: "tax_assistant",
    title: "Tax Assistant",
    titleFr: "Assistant Fiscal",
    description: "Never miss a tax deadline. Builds your obligation calendar, prepares draft figures, and sends anti-fine reminders.",
    descriptionFr: "Ne ratez plus aucune échéance fiscale. Calendrier d'obligations, chiffres préparés, rappels anti-amende.",
    icon: <Shield className="h-6 w-6" />,
    color: "text-emerald-600 dark:text-emerald-400",
    gradientFrom: "from-emerald-500",
    gradientTo: "to-teal-500",
    phase: "mvp",
    features: [
      "Personalized tax calendar (micro, SARL, SAS...)",
      "Draft turnover figures for declarations",
      "Anti-fine reminders (5 days before deadline)",
      "Direct links to impots.gouv.fr / URSSAF",
    ],
    whatsappExample: "Rappel: Déclaration CA T1 avant le 30 avril. CA estimé: 12 450€. Déclarer → autoentrepreneur.urssaf.fr",
  },
  {
    key: "document",
    type: "document_manager",
    title: "Document Manager",
    titleFr: "Gestionnaire de Documents",
    description: "Links invoices and receipts to bank transactions. Generates accountant-ready packages on demand.",
    descriptionFr: "Lie factures et reçus aux transactions bancaires. Génère des dossiers prêts pour votre expert-comptable.",
    icon: <FileCheck className="h-6 w-6" />,
    color: "text-violet-600 dark:text-violet-400",
    gradientFrom: "from-violet-500",
    gradientTo: "to-purple-500",
    phase: "mvp",
    features: [
      "Auto-match documents to transactions",
      "Unlinked document alerts",
      "Accountant package generator",
      "Document search by vendor/date/amount",
    ],
    whatsappExample: "5 documents linked automatically. 2 invoices need manual verification. Accountant package Q1 ready.",
  },
  {
    key: "client",
    type: "client_assistant",
    title: "Client Assistant",
    titleFr: "Assistant Client",
    description: "Handles client communications: gentle payment reminders, appointment confirmations, and simple marketing.",
    descriptionFr: "Gère vos communications clients : rappels de paiement, confirmations de RDV, mini-marketing.",
    icon: <Users className="h-6 w-6" />,
    color: "text-amber-600 dark:text-amber-400",
    gradientFrom: "from-amber-500",
    gradientTo: "to-orange-500",
    phase: "phase2",
    features: [
      "Gentle payment reminders (soft collection)",
      "Appointment confirmations",
      "Order status notifications",
      "Simple thank-you / promo campaigns",
    ],
    whatsappExample: "Bonjour, un petit rappel concernant la facture n°2024-089 de 1 200€. Merci de votre attention.",
  },
  {
    key: "operations",
    type: "operations_coordinator",
    title: "Weekly Briefing",
    titleFr: "Rapport Hebdomadaire",
    description: "Your virtual Chief of Staff. Delivers a concise weekly summary with priorities and action items every Monday.",
    descriptionFr: "Votre Chef de Cabinet virtuel. Résumé hebdomadaire avec priorités et actions à mener chaque lundi.",
    icon: <BarChart3 className="h-6 w-6" />,
    color: "text-rose-600 dark:text-rose-400",
    gradientFrom: "from-rose-500",
    gradientTo: "to-pink-500",
    phase: "mvp",
    features: [
      "Weekly priority briefing (Monday morning)",
      "Aggregated insights from all agents",
      "Action items with deadlines",
      "Financial health snapshot",
    ],
    whatsappExample: "Cette semaine: Déclaration CA avant vendredi (12 450€). 2 clients en retard >10j. Abonnements +30%. Tout le reste est en ordre.",
  },
]

export default function AgentsPage() {
  const [agentSettings, setAgentSettings] = useState<Record<string, any>>({})
  const [togglingAgent, setTogglingAgent] = useState<string | null>(null)
  const [triggeringFlow, setTriggeringFlow] = useState<string | null>(null)
  const [recentLogs, setRecentLogs] = useState<any[]>([])
  const [notifications, setNotifications] = useState<any[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [expandedAgent, setExpandedAgent] = useState<string | null>(null)
  const supabase = createClient()

  const getHeaders = async () => {
    const { data: { session } } = await supabase.auth.getSession()
    const accountId = session?.user?.id || "00000000-0000-0000-0000-000000000000"
    return {
      "X-API-Key": API_KEY,
      "X-Account-ID": accountId,
      "Content-Type": "application/json",
    }
  }

  useEffect(() => {
    fetchAgentSettings()
    fetchRecentLogs()
    fetchNotifications()
  }, [])

  const fetchAgentSettings = async () => {
    setIsLoading(true)
    try {
      const headers = await getHeaders()
      const res = await fetch(`${API_URL}/agents`, { headers })
      if (res.ok) {
        const data = await res.json()
        const settingsMap: Record<string, any> = {}
        for (const agent of (data.agents || [])) {
          settingsMap[agent.agent_type] = agent
        }
        setAgentSettings(settingsMap)
      }
    } catch (e) {
      console.error("Failed to fetch agent settings:", e)
    } finally {
      setIsLoading(false)
    }
  }

  const fetchRecentLogs = async () => {
    try {
      const headers = await getHeaders()
      const res = await fetch(`${API_URL}/agents/logs/recent?limit=5`, { headers })
      if (res.ok) {
        const data = await res.json()
        setRecentLogs(data.logs || [])
      }
    } catch (e) {
      console.error("Failed to fetch logs:", e)
    }
  }

  const fetchNotifications = async () => {
    try {
      const headers = await getHeaders()
      const res = await fetch(`${API_URL}/notifications?unread_only=true&limit=10`, { headers })
      if (res.ok) {
        const data = await res.json()
        setNotifications(data.notifications || [])
      }
    } catch (e) {
      console.error("Failed to fetch notifications:", e)
    }
  }

  const toggleAgent = async (agentType: string, newStatus: string) => {
    setTogglingAgent(agentType)
    try {
      const headers = await getHeaders()
      const res = await fetch(`${API_URL}/agents/${agentType}/toggle`, {
        method: "POST",
        headers,
        body: JSON.stringify({ status: newStatus }),
      })
      if (res.ok) {
        setAgentSettings(prev => ({
          ...prev,
          [agentType]: { ...prev[agentType], status: newStatus },
        }))
        toast.success(
          newStatus === "enabled"
            ? "Agent activated"
            : "Agent deactivated"
        )
      } else {
        throw new Error("Toggle failed")
      }
    } catch (e) {
      toast.error("Failed to update agent status")
      console.error(e)
    } finally {
      setTogglingAgent(null)
    }
  }

  const triggerFlow = async (flowName: string) => {
    setTriggeringFlow(flowName)
    try {
      const headers = await getHeaders()
      const res = await fetch(`${API_URL}/flows/${flowName}/trigger`, {
        method: "POST",
        headers,
        body: JSON.stringify({ flow_name: flowName, trigger_data: {} }),
      })
      if (res.ok) {
        const data = await res.json()
        toast.success(`Flow "${flowName}" started. Check logs for status.`)
        fetchRecentLogs()
      } else {
        const err = await res.json()
        toast.error(err.detail || "Failed to trigger flow")
      }
    } catch (e) {
      toast.error("Failed to trigger flow")
      console.error(e)
    } finally {
      setTriggeringFlow(null)
    }
  }

  const isEnabled = (agentType: string) => {
    return agentSettings[agentType]?.status === "enabled"
  }

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr)
    return date.toLocaleDateString("fr-FR", {
      day: "numeric",
      month: "short",
      hour: "2-digit",
      minute: "2-digit",
    })
  }

  return (
    <div className="container mx-auto py-10 space-y-10">
      {/* Header */}
      <div className="space-y-2">
        <h1 className="text-4xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-violet-600 via-purple-600 to-fuchsia-600">
          Mes Assistants IA
        </h1>
        <p className="text-muted-foreground text-lg max-w-2xl">
          Votre équipe virtuelle travaille 24/7. Activez les assistants dont vous avez besoin
          et recevez les résultats directement dans votre espace ou sur WhatsApp.
        </p>
      </div>

      {/* Notifications Banner */}
      {notifications.length > 0 && (
        <Card className="border-amber-200 dark:border-amber-800 bg-amber-50/50 dark:bg-amber-900/10">
          <CardContent className="py-4 flex items-center gap-3">
            <Bell className="h-5 w-5 text-amber-600 dark:text-amber-400 flex-shrink-0" />
            <div className="flex-1">
              <p className="text-sm font-medium">
                {notifications.length} notification{notifications.length > 1 ? "s" : ""} non lue{notifications.length > 1 ? "s" : ""}
              </p>
              <p className="text-xs text-muted-foreground">
                {notifications[0]?.title}
              </p>
            </div>
            <Badge variant="secondary">{notifications.length}</Badge>
          </CardContent>
        </Card>
      )}

      {/* Agent Cards Grid */}
      <div className="grid gap-6 md:grid-cols-2 xl:grid-cols-3">
        {AGENTS.map((agent) => {
          const enabled = isEnabled(agent.type)
          const isToggling = togglingAgent === agent.type
          const isTriggering = triggeringFlow === agent.key
          const isExpanded = expandedAgent === agent.key

          return (
            <Card
              key={agent.key}
              className={`group relative overflow-hidden transition-all duration-300 hover:shadow-lg hover:-translate-y-1 ${
                enabled
                  ? "border-primary/30 shadow-md shadow-primary/5"
                  : "opacity-80 hover:opacity-100"
              }`}
            >
              {/* Top gradient bar */}
              <div
                className={`absolute top-0 left-0 right-0 h-1 bg-gradient-to-r ${agent.gradientFrom} ${agent.gradientTo} ${
                  enabled ? "opacity-100" : "opacity-30"
                } transition-opacity`}
              />

              {/* Phase badge */}
              {agent.phase === "phase2" && (
                <div className="absolute top-3 right-3">
                  <Badge variant="outline" className="text-xs">
                    Phase 2
                  </Badge>
                </div>
              )}

              <CardHeader className="pb-3">
                <div className="flex items-start justify-between gap-3">
                  <div className="flex items-center gap-3">
                    <div
                      className={`p-2 rounded-lg bg-gradient-to-br ${agent.gradientFrom} ${agent.gradientTo} text-white`}
                    >
                      {agent.icon}
                    </div>
                    <div>
                      <CardTitle className="text-lg">{agent.titleFr}</CardTitle>
                      <CardDescription className="text-xs mt-0.5">
                        {agent.title}
                      </CardDescription>
                    </div>
                  </div>
                </div>
              </CardHeader>

              <CardContent className="space-y-4">
                <p className="text-sm text-muted-foreground leading-relaxed">
                  {agent.descriptionFr}
                </p>

                {/* Toggle */}
                <div className="flex items-center justify-between py-2 px-3 rounded-lg bg-muted/50">
                  <div className="flex items-center gap-2">
                    <Activity className={`h-4 w-4 ${enabled ? "text-emerald-500" : "text-muted-foreground"}`} />
                    <span className="text-sm font-medium">
                      {enabled ? "Actif" : "Inactif"}
                    </span>
                  </div>
                  {isToggling ? (
                    <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
                  ) : (
                    <Switch
                      checked={enabled}
                      onCheckedChange={(checked) =>
                        toggleAgent(agent.type, checked ? "enabled" : "disabled")
                      }
                    />
                  )}
                </div>

                {/* Expand/Collapse details */}
                <button
                  onClick={() => setExpandedAgent(isExpanded ? null : agent.key)}
                  className="w-full flex items-center justify-between text-xs text-muted-foreground hover:text-foreground transition-colors py-1"
                >
                  <span>{isExpanded ? "Masquer les détails" : "Voir les détails"}</span>
                  <ChevronRight
                    className={`h-3 w-3 transition-transform ${isExpanded ? "rotate-90" : ""}`}
                  />
                </button>

                {isExpanded && (
                  <div className="space-y-3 animate-in slide-in-from-top-2 duration-200">
                    {/* Features */}
                    <div className="space-y-1.5">
                      <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                        Fonctionnalités
                      </p>
                      <ul className="space-y-1">
                        {agent.features.map((feature, i) => (
                          <li key={i} className="text-xs text-muted-foreground flex items-start gap-1.5">
                            <span className="text-primary mt-0.5">•</span>
                            {feature}
                          </li>
                        ))}
                      </ul>
                    </div>

                    {/* WhatsApp Example */}
                    <div className="space-y-1.5">
                      <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider flex items-center gap-1">
                        <MessageCircle className="h-3 w-3" />
                        Exemple WhatsApp
                      </p>
                      <div className="bg-emerald-50 dark:bg-emerald-900/20 border border-emerald-200 dark:border-emerald-800 rounded-lg p-3">
                        <p className="text-xs text-emerald-800 dark:text-emerald-300 italic">
                          &ldquo;{agent.whatsappExample}&rdquo;
                        </p>
                      </div>
                    </div>

                    {/* Notification Channels */}
                    <div className="flex items-center gap-2">
                      <p className="text-xs text-muted-foreground">Canaux:</p>
                      <div className="flex gap-1.5">
                        <Badge variant="outline" className="text-[10px] gap-1 py-0">
                          <Bell className="h-2.5 w-2.5" /> In-app
                        </Badge>
                        <Badge variant="outline" className="text-[10px] gap-1 py-0">
                          <MessageCircle className="h-2.5 w-2.5" /> WhatsApp
                        </Badge>
                        <Badge variant="outline" className="text-[10px] gap-1 py-0">
                          <Mail className="h-2.5 w-2.5" /> Email
                        </Badge>
                      </div>
                    </div>
                  </div>
                )}
              </CardContent>

              {/* Footer with trigger button */}
              {enabled && (
                <CardFooter className="pt-0">
                  <Button
                    variant="outline"
                    size="sm"
                    className="w-full"
                    onClick={() => triggerFlow(agent.key)}
                    disabled={isTriggering}
                  >
                    {isTriggering ? (
                      <>
                        <Loader2 className="mr-2 h-3 w-3 animate-spin" />
                        Exécution en cours...
                      </>
                    ) : (
                      <>
                        <Bot className="mr-2 h-3 w-3" />
                        Lancer maintenant
                      </>
                    )}
                  </Button>
                </CardFooter>
              )}
            </Card>
          )
        })}
      </div>

      {/* Recent Activity */}
      {recentLogs.length > 0 && (
        <div className="space-y-4">
          <h2 className="text-2xl font-semibold flex items-center gap-2">
            <Clock className="h-6 w-6 text-primary" />
            Activité récente
          </h2>
          <div className="space-y-2">
            {recentLogs.map((log) => (
              <Card key={log.id} className="bg-card/50">
                <CardContent className="py-3 flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div
                      className={`w-2 h-2 rounded-full ${
                        log.status === "completed"
                          ? "bg-emerald-500"
                          : log.status === "failed"
                          ? "bg-red-500"
                          : "bg-blue-500 animate-pulse"
                      }`}
                    />
                    <div>
                      <p className="text-sm font-medium">{log.flow_name || log.agent_type}</p>
                      <p className="text-xs text-muted-foreground">{log.trigger}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge
                      variant={
                        log.status === "completed"
                          ? "default"
                          : log.status === "failed"
                          ? "destructive"
                          : "secondary"
                      }
                      className="text-xs"
                    >
                      {log.status}
                    </Badge>
                    {log.started_at && (
                      <span className="text-xs text-muted-foreground">
                        {formatDate(log.started_at)}
                      </span>
                    )}
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      )}

      {/* Loading state */}
      {isLoading && (
        <div className="flex items-center justify-center py-20">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
        </div>
      )}
    </div>
  )
}
