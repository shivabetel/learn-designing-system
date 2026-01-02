// Enums matching backend
export enum Certificate {
  U = "U",
  UA = "UA",
  A = "A",
  S = "S",
}

export enum SeatType {
  REGULAR = "REGULAR",
  PREMIUM = "PREMIUM",
  RECLINER = "RECLINER",
}

export enum ShowSeatStatus {
  AVAILABLE = "AVAILABLE",
  BOOKED = "BOOKED",
  LOCKED = "LOCKED",
  UNAVAILABLE = "UNAVAILABLE",
}

export enum BookingStatus {
  INITIATED = "INITIATED",
  CONFIRMED = "CONFIRMED",
  CANCELLED = "CANCELLED",
  EXPIRED = "EXPIRED",
}

// Movie types
export interface Movie {
  id: number;
  title: string;
  description: string;
  duration_mins: number;
  language: string;
  certificate: Certificate | null;
}

export interface MovieResponse extends Movie {}

// Theatre types
export interface Screen {
  id: number;
  name: string;
  total_seats: number;
  theatre_id: number;
}

export interface Theatre {
  name: string;
  city: string;
  address: string;
  screens: Screen[];
}

export interface TheatreResponse extends Theatre {
  id: number; // FastAPI includes id from model even if commented in schema due to from_attributes=True
}

export interface ScreenResponse extends Screen {}

// Show types
export interface Show {
  id: number;
  movie_id: number;
  screen_id: number;
  start_time: string; // ISO datetime string
  end_time: string; // ISO datetime string
  base_price: number;
}

export interface ShowResponse extends Show {}

// Seat types (matching API response structure)
export interface Seat {
  id: number; // show_seat_id from API
  seat_number: number;
  seat_type: SeatType;
  status: ShowSeatStatus;
  price: number;
}

export interface SeatRow {
  row: string;
  seat_type: SeatType;
  seats: Seat[];
}

export interface SeatLayout {
  show_id: number;
  layout: SeatRow[];
}

// Booking types
export interface Booking {
  id: number;
  status: BookingStatus;
  show_id: number;
  total_amount: number;
}

export interface BookingResponse extends Booking {}

export interface LockSeatPayload {
  show_seat_ids: number[];
}

// Booking context types
export interface BookingState {
  movie: Movie | null;
  theatre: TheatreResponse | null;
  screen: ScreenResponse | null;
  show: ShowResponse | null;
  selectedSeats: Seat[];
  bookingId: number | null;
  loading: boolean;
  error: string | null;
}

export interface BookingContextType extends BookingState {
  setMovie: (movie: Movie | null) => void;
  setTheatre: (theatre: TheatreResponse | null) => void;
  setScreen: (screen: ScreenResponse | null) => void;
  setShow: (show: ShowResponse | null) => void;
  setSelectedSeats: (seats: Seat[]) => void;
  setBookingId: (id: number | null) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  resetBooking: () => void;
}

