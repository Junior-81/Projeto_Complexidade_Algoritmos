export const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export const ALL_MODES_KEY = "all";

export const MODAL_COLORS = {
  walk: "#2e7d32",
  bike: "#0288d1",
  car: "#546e7a",
  moto: "#ef6c00",
  bus: "#d32f2f",
  uber: "#212121",
  uber_car: "#212121",
  uber_moto: "#6d4c41",
};

export const MODAL_LABELS = {
  walk: "A pe",
  bike: "Bike",
  car: "Carro",
  moto: "Moto",
  bus: "Onibus",
  uber: "Uber",
  uber_car: "Uber Carro",
  uber_moto: "Uber Moto",
};

export const ROUTE_MODE_OPTIONS = [
  { value: "auto", label: "Automatico (multimodal)" },
  { value: "walk", label: "A pe" },
  { value: "bike", label: "Bike" },
  { value: "car", label: "Carro" },
  { value: "moto", label: "Moto" },
  { value: "bus", label: "Onibus" },
  { value: "uber_car", label: "Uber Carro" },
  { value: "uber_moto", label: "Uber Moto" },
];

export const ROUTE_RESTRICTION_OPTIONS = [
  { value: "none", label: "Sem restricao (deixa trocar modal)" },
  { value: "walk", label: "Forcar apenas A pe" },
  { value: "bike", label: "Forcar apenas Bike" },
  { value: "car", label: "Forcar apenas Carro" },
  { value: "moto", label: "Forcar apenas Moto" },
  { value: "bus", label: "Onibus (com acesso a pe)" },
  { value: "uber_car", label: "Forcar apenas Uber Carro" },
  { value: "uber_moto", label: "Forcar apenas Uber Moto" },
];

export const SEGMENT_DISPLAY_ORDER = [
  "origem",
  "destino",
  "distancia",
  "tempo",
  "custo",
  "esforco",
  "risco_medio",
  "velocidade_media_kmh",
  "quantidade_arestas",
  "linha",
  "gtfs_shape_id",
  "validacao_gtfs",
  "servico",
];

export const DEFAULT_CENTER = [-8.062742, -34.8739];
