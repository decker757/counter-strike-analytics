export interface IntentPredictionPoint {
  horizon: string;   // "+1s" | "+2s" | "+3s"
  tick: number;
  x: number;
  y: number;
  z: number;
}

export type IntentAction = "holding" | "pushing" | "rotating" | "falling_back";

export interface IntentPlayerPrediction {
  steamid: string;
  name: string;
  team: "CT" | "T";
  current_position: { x: number; y: number; z: number };
  predictions: IntentPredictionPoint[];
  action: IntentAction;
  action_probs: Record<string, number>;
  confidence: number;
  current_zone: string | null;
  predicted_zone: string | null;
}

export interface IntentResponse {
  tick: number;
  players: IntentPlayerPrediction[];
  error?: string;
}

export interface IntentModelInfo {
  mode: string;
  status: string;
  description?: string;
  supported_maps?: string[];
}

export interface ZoneInfo {
  id: string;
  name: string;
  is_bombsite: boolean;
  is_ct_spawn: boolean;
  is_t_spawn: boolean;
  adjacent: string[];
  center: { x: number; y: number } | null;
}

export interface ZonesResponse {
  map: string;
  zones: ZoneInfo[];
  error?: string;
}
