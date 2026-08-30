export type AgentLog = {
  agent?: string;
  gen?: number;
  message?: string;
};

export type DemoStep = {
  type: "artifact" | "transfer";
  ts?: string;
  stage: number;
  title?: string;
  body?: string;
  llm?: boolean;
  amount?: number;
  sentinel_score?: number;
  sentinel_caught?: boolean;
  rules_caught?: boolean;
};

export type Alert = {
  ts?: string;
  txn_id?: string;
  src?: string;
  dst?: string;
  amount?: number;
  score?: number;
  is_fraud?: boolean;
  attack_id?: string;
  explanations?: { feature: string }[];
};

export type Artifact = {
  ts?: string;
  kind?: string;
  text?: string;
  forge_source?: string;
  attack_id?: string;
};

export type Genome = {
  id: string;
  name?: string;
  tier?: string;
  rails?: string[];
  surfaces?: string[];
  summary?: string;
};

export type HistoryRow = {
  generation: number;
  roc_auc?: number;
  frozen_auc?: number | null;
  recall?: number;
  fpr?: number;
  baseline_recall?: number;
  checklist_recall?: number;
  protocol?: Protocol;
};

export type Protocol = {
  lab_auc?: number | null;
  recall_at_base_rate?: number | null;
  family_holdout_auc?: number | null;
  fpr_at_base_rate?: number | null;
  occupant_iforest_auc?: number | null;
  joint_mmd?: number | null;
  headline?: string;
  ablation_auc?: Record<string, number | null>;
};

export type AtlasHole = {
  rail: string;
  surface: string;
  capability: string;
  note: string;
};

export type Atlas = {
  n_families?: number;
  n_tier_a?: number;
  coverage?: number;
  disclaimer?: string;
  holes?: AtlasHole[];
  diversity?: { score?: number; n_families?: number };
};

export type Shadow = {
  frozen_auc_curve?: (number | null)[];
  tte_generations?: number;
  note?: string;
};

export type TunnelState = {
  history: HistoryRow[];
  genomes: Genome[];
  alerts: Alert[];
  artifacts: Artifact[];
  agent_log: AgentLog[];
  vector_det_rates: Record<string, number>;
  demo_chains: Record<string, DemoStep[]>;
  atlas?: Atlas;
  protocol?: Protocol;
  shadow?: Shadow;
  league?: unknown[];
  tte_generations: number;
  loop_gain_auc: number;
  fidelity_mean: number;
  baseline_recall?: number;
  calibrated: boolean;
  llm_enabled: boolean;
  cloud?: boolean;
};

export type MuleGraph = {
  nodes?: { id: string }[];
  edges?: unknown[];
  sink?: string;
};

