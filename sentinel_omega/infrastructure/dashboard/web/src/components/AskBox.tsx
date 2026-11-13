import { useState, FormEvent } from "react"
import { api } from "@/lib/api"
import { Caption } from "@/components/TabIntro"

export function AskBox() {
  const [question, setQuestion] = useState("")
  const [answer, setAnswer] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    if (!question.trim()) return

    setLoading(true)
    setError(null)
    try {
      const res = await api.ask(question.trim())
      setAnswer(res.answer || res.respuesta || "Sin respuesta")
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error desconocido")
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-3">
      <form onSubmit={handleSubmit} className="flex gap-2">
        <input
          type="text"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="Pregunta al Concilio (ej: qu\u00e9 nodos alertan hoy?)"
          className="flex-1 rounded-lg border border-border bg-bg-card px-4 py-2 text-sm outline-none focus:ring-2 focus:ring-accent-cyan/50"
          disabled={loading}
        />
        <button
          type="submit"
          disabled={loading || !question.trim()}
          className="rounded-lg bg-accent-cyan/20 px-4 py-2 text-sm font-medium text-accent-cyan hover:bg-accent-cyan/30 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {loading ? "Consultando..." : "Preguntar"}
        </button>
      </form>

      {error && (
        <div className="rounded-lg bg-red-500/10 border border-red-500/30 p-3 text-sm text-red-400">
          Error: {error}
        </div>
      )}

      {answer && (
        <div className="rounded-xl border border-border bg-bg-card p-4 text-sm">
          <div className="font-medium text-accent-cyan mb-2">Concilio:</div>
          <pre className="whitespace-pre-wrap text-muted">{answer}</pre>
        </div>
      )}

      <Caption>
        El Concilio lee la base de datos en vivo (overview, ciclos, alertas, bots, consenso) y responde en
        lenguaje natural. Modelo: nemotron &gt; deepseek &gt; gemma3 (orden de preferencia).
      </Caption>
    </div>
  )
}
