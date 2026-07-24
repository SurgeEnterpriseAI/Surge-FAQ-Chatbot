import { motion } from "framer-motion";
import { CreditCard, Truck, AlertTriangle, BookOpen } from "lucide-react";

interface SuggestedPromptsProps {
  onSelect: (prompt: string) => void;
}

const PROMPTS = [
  {
    text: "Verify my latest billing payment",
    description: "Check transaction history & balance",
    icon: CreditCard,
    color: "text-blue-400 border-blue-500/20 bg-blue-500/5 hover:bg-blue-500/10",
  },
  {
    text: "Track package shipping status",
    description: "Locate shipment & check ETA",
    icon: Truck,
    color: "text-purple-400 border-purple-500/20 bg-purple-500/5 hover:bg-purple-500/10",
  },
  {
    text: "Diagnose database connection error",
    description: "Lookup technical error logs",
    icon: AlertTriangle,
    color: "text-amber-400 border-amber-500/20 bg-amber-500/5 hover:bg-amber-500/10",
  },
  {
    text: "Search knowledge base documentation",
    description: "Query indexed product manuals",
    icon: BookOpen,
    color: "text-emerald-400 border-emerald-500/20 bg-emerald-500/5 hover:bg-emerald-500/10",
  },
];

export function SuggestedPrompts({ onSelect }: SuggestedPromptsProps) {
  return (
    <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
      {PROMPTS.map((p, idx) => {
        const Icon = p.icon;
        return (
          <motion.button
            key={idx}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: idx * 0.1, duration: 0.4 }}
            onClick={() => onSelect(p.text)}
            className={`flex items-start gap-3 rounded-lg border p-3.5 text-left transition-all duration-200 ${p.color}`}
          >
            <Icon className="mt-0.5 h-5 w-5 shrink-0" />
            <div>
              <div className="text-sm font-semibold text-white">{p.text}</div>
              <div className="text-xs text-slate-400">{p.description}</div>
            </div>
          </motion.button>
        );
      })}
    </div>
  );
}
