// ─────────────────────────────────────────────────────────────────────────────
// Core Types
// ─────────────────────────────────────────────────────────────────────────────

export type TravelMode =
  | 'flight'
  | 'train'
  | 'bus'
  | 'hotel'
  | 'car'
  | 'general';

export type MessageRole = 'user' | 'assistant' | 'system';
export interface Company {
  company_id: string;
  name: string;
  allowed_services: string[];
}
export type CabinClass =
  | 'economy'
  | 'premium_economy'
  | 'business'
  | 'first';

// New
export type ServiceType =
  | 'flight'
  | 'hotel'
  | 'train'
  | 'car'
  | 'bus';

export type IntentType =
  | 'meeting_plan'
  | 'travel_search'
  | 'general_chat'
  | 'filter_refine'
  | 'journey_status';

// ─────────────────────────────────────────────────────────────────────────────
// Message
// ─────────────────────────────────────────────────────────────────────────────

export interface Message {
  message_id: string;
  session_id: string;
  role: MessageRole;
  content: string;
  created_at: string;

  travel_intent?: TravelMode;

  // UI state
  status?: 'sending' | 'sent' | 'error';
}

// ─────────────────────────────────────────────────────────────────────────────
// Meeting / Journey Planning (NEW)
// ─────────────────────────────────────────────────────────────────────────────

export interface MeetingInfo {
  meeting_time?: string;
  meeting_date?: string;
  meeting_location?: string;
  meeting_city?: string;

  meeting_lat?: number;
  meeting_lng?: number;

  meeting_duration_hours: number;

  current_city?: string;

  return_required: boolean;
  return_time?: string;

  hotel_required: boolean;

  traveller_count: number;
}

export interface JourneyLeg {
  leg_type: string;
  description: string;

  from_location: string;
  to_location: string;

  depart_time?: string;
  arrive_time?: string;

  duration_minutes?: number;

  price?: number;
  currency: string;

  is_mock: boolean;
}

export interface JourneyPlan {
  journey_id: string;
  session_id: string;

  meeting?: MeetingInfo;

  legs: JourneyLeg[];

  total_estimated_cost: number;
  currency: string;

  timeline_summary: string;

  created_at: string;
}

// ─────────────────────────────────────────────────────────────────────────────
// Travel Context
// ─────────────────────────────────────────────────────────────────────────────

export interface TravelContext {
  origin?: string;
  destination?: string;

  travel_date?: string;
  return_date?: string;

  passengers: number;

  mode?: TravelMode;

  cabin_class?: CabinClass;

  // Preserved from old version
  train_class?: string;
  bus_type?: string;
  hotel_stars?: number;

  max_budget?: number;
  min_budget?: number;

  non_stop_only: boolean;

  // Preserved from old version
  amenities: string[];

  // New fields
  meeting?: MeetingInfo;
  journey_plan?: JourneyPlan;

  company_id?: string;
  user_id?: string;

  allowed_services: ServiceType[];

  home_city?: string;

  profile_complete: boolean;

  required_arrival_by?: string;
}

// ─────────────────────────────────────────────────────────────────────────────
// Flight Types
// ─────────────────────────────────────────────────────────────────────────────

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
// ─────────────────────────────────────────────────────────────────────────────
// Train Types
// ─────────────────────────────────────────────────────────────────────────────

export interface TrainClassInfo {
  class_code: string;
  class_name: string;
  available_seats: number;
  price: number;

  // Preserved from old version
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

// ─────────────────────────────────────────────────────────────────────────────
// Bus Types
// ─────────────────────────────────────────────────────────────────────────────

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

  // New
  cancellation_policy?: string;

  source: string;

  is_mock: boolean;
}

// ─────────────────────────────────────────────────────────────────────────────
// Hotel Types
// ─────────────────────────────────────────────────────────────────────────────

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

  // New
  distance_from_meeting?: number;

  review_score?: number;
  review_count?: number;

  breakfast_included: boolean;

  free_cancellation: boolean;

  image_url?: string;

  source: string;

  is_mock: boolean;
}

// ─────────────────────────────────────────────────────────────────────────────
// Car Types
// ─────────────────────────────────────────────────────────────────────────────

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

// ─────────────────────────────────────────────────────────────────────────────
// Search Results
// ─────────────────────────────────────────────────────────────────────────────

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
// ─────────────────────────────────────────────────────────────────────────────
// API Types
// ─────────────────────────────────────────────────────────────────────────────

export interface ChatRequest {
  session_id?: string;
  message: string;

  // New
  user_id?: string;
  company_id?: string;

  timezone?: string;
}

export interface ChatResponse {
  session_id: string;
  message_id: string;

  reply: string;

  // New
  intent_type?: IntentType;

  travel_results?: TravelSearchResult;

  // New
  journey_plan?: JourneyPlan;

  travel_context?: TravelContext;

  suggestions: string[];

  is_travel_query: boolean;

  // New
  permission_denied: boolean;
  denied_service?: string;
}

// ─────────────────────────────────────────────────────────────────────────────
// Session Types
// ─────────────────────────────────────────────────────────────────────────────

export interface SessionSummary {
  session_id: string;

  created_at: string;
  updated_at: string;

  message_count: number;

  travel_context?: TravelContext;
}

// ─────────────────────────────────────────────────────────────────────────────
// UI Types
// ─────────────────────────────────────────────────────────────────────────────

export interface UIMessage extends Message {
  travel_results?: TravelSearchResult;

  // New
  journey_plan?: JourneyPlan;

  suggestions?: string[];

  isStreaming?: boolean;

  // New
  intent_type?: IntentType;

  permission_denied?: boolean;
  denied_service?: string;
}

export interface Company {
  company_id: string;
  name: string;
  allowed_services: string[];
}