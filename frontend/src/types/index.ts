// ── Core Types ─────────────────────────────────────────────────────────────

export type TravelMode = 'flight' | 'train' | 'bus' | 'hotel' | 'car' | 'general';
export type MessageRole = 'user' | 'assistant' | 'system';
export type CabinClass = 'economy' | 'premium_economy' | 'business' | 'first';

// ── Message ───────────────────────────────────────────────────────────────────

export interface Message {
  message_id: string;
  session_id: string;
  role: MessageRole;
  content: string;
  created_at: string;
  travel_intent?: TravelMode;
  // UI-only: pending / error states
  status?: 'sending' | 'sent' | 'error';
}

// ── Travel Context ─────────────────────────────────────────────────────────────

export interface TravelContext {
  origin?: string;
  destination?: string;
  travel_date?: string;
  return_date?: string;
  passengers: number;
  mode?: TravelMode;
  cabin_class?: CabinClass;
  train_class?: string;
  bus_type?: string;
  hotel_stars?: number;
  max_budget?: number;
  min_budget?: number;
  non_stop_only: boolean;
  amenities: string[];
}

// ── Flight Types ──────────────────────────────────────────────────────────────

export interface FlightSegment {
  flight_number: string;
  airline: string;
  airline_code: string;
  departure_airport: string;
  departure_city: string;
  departure_time: string;
  arrival_airport: string;
  arrival_city: string;
  arrival_time: string;
  duration: string;
  aircraft?: string;
}

export interface FlightResult {
  result_id: string;
  segments: FlightSegment[];
  total_duration: string;
  stops: number;
  cabin_class: CabinClass;
  price: number;
  currency: string;
  baggage_allowance: string;
  is_refundable: boolean;
  source: string;
  is_mock: boolean;
}

// ── Train Types ───────────────────────────────────────────────────────────────

export interface TrainClassInfo {
  class_code: string;
  class_name: string;
  available_seats: number;
  price: number;
  quota: string;
}

export interface TrainResult {
  result_id: string;
  train_number: string;
  train_name: string;
  origin_station: string;
  origin_code: string;
  destination_station: string;
  destination_code: string;
  departure_time: string;
  arrival_time: string;
  duration: string;
  travel_date: string;
  classes: TrainClassInfo[];
  runs_on: string[];
  source: string;
  is_mock: boolean;
}

// ── Bus Types ──────────────────────────────────────────────────────────────────

export interface BusResult {
  result_id: string;
  operator: string;
  bus_type: string;
  departure_city: string;
  arrival_city: string;
  departure_time: string;
  arrival_time: string;
  duration: string;
  available_seats: number;
  price: number;
  currency: string;
  amenities: string[];
  source: string;
  is_mock: boolean;
}

// ── Hotel Types ────────────────────────────────────────────────────────────────

export interface HotelResult {
  result_id: string;
  hotel_id: string;
  name: string;
  rating: number;
  stars: number;
  address: string;
  city: string;
  latitude?: number;
  longitude?: number;
  price_per_night: number;
  currency: string;
  amenities: string[];
  distance_from_center?: number;
  review_score?: number;
  review_count?: number;
  breakfast_included: boolean;
  free_cancellation: boolean;
  image_url?: string;
  source: string;
  is_mock: boolean;
}

// ── Car Types ──────────────────────────────────────────────────────────────────

export interface CarResult {
  result_id: string;
  vehicle_name: string;
  vehicle_type: string;
  vendor: string;
  fuel_type: string;
  seats: number;
  transmission: string;
  pickup_location: string;
  price_per_day: number;
  currency: string;
  features: string[];
  source: string;
  is_mock: boolean;
}

// ── Search Results ─────────────────────────────────────────────────────────────

export interface TravelSearchResult {
  search_id: string;
  session_id: string;
  search_type: TravelMode;
  origin?: string;
  destination?: string;
  travel_date?: string;
  flights?: FlightResult[];
  trains?: TrainResult[];
  buses?: BusResult[];
  hotels?: HotelResult[];
  cars?: CarResult[];
  is_partial_mock: boolean;
  mock_reason?: string;
  created_at: string;
}

// ── API Types ─────────────────────────────────────────────────────────────────

export interface ChatRequest {
  session_id?: string;
  message: string;
  timezone?: string;
}

export interface ChatResponse {
  session_id: string;
  message_id: string;
  reply: string;
  travel_results?: TravelSearchResult;
  travel_context?: TravelContext;
  suggestions: string[];
  is_travel_query: boolean;
}

export interface SessionSummary {
  session_id: string;
  created_at: string;
  updated_at: string;
  message_count: number;
  travel_context?: TravelContext;
}

// ── UI State ───────────────────────────────────────────────────────────────────

export interface UIMessage extends Message {
  travel_results?: TravelSearchResult;
  suggestions?: string[];
  isStreaming?: boolean;
}
