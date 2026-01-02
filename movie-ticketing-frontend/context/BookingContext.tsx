"use client";

import React, { createContext, useContext, useState, useCallback } from "react";
import {
  BookingState,
  BookingContextType,
  Movie,
  TheatreResponse,
  ScreenResponse,
  ShowResponse,
  Seat,
} from "@/lib/types";

const initialState: BookingState = {
  movie: null,
  theatre: null,
  screen: null,
  show: null,
  selectedSeats: [],
  bookingId: null,
  loading: false,
  error: null,
};

const BookingContext = createContext<BookingContextType | undefined>(undefined);

export const BookingProvider: React.FC<{ children: React.ReactNode }> = ({
  children,
}) => {
  const [state, setState] = useState<BookingState>(initialState);

  const setMovie = useCallback((movie: Movie | null) => {
    setState((prev) => ({ ...prev, movie }));
  }, []);

  const setTheatre = useCallback((theatre: TheatreResponse | null) => {
    setState((prev) => ({ ...prev, theatre }));
  }, []);

  const setScreen = useCallback((screen: ScreenResponse | null) => {
    setState((prev) => ({ ...prev, screen }));
  }, []);

  const setShow = useCallback((show: ShowResponse | null) => {
    setState((prev) => ({ ...prev, show }));
  }, []);

  const setSelectedSeats = useCallback((seats: Seat[]) => {
    setState((prev) => ({ ...prev, selectedSeats: seats }));
  }, []);

  const setBookingId = useCallback((id: number | null) => {
    setState((prev) => ({ ...prev, bookingId: id }));
  }, []);

  const setLoading = useCallback((loading: boolean) => {
    setState((prev) => ({ ...prev, loading }));
  }, []);

  const setError = useCallback((error: string | null) => {
    setState((prev) => ({ ...prev, error }));
  }, []);

  const resetBooking = useCallback(() => {
    setState(initialState);
  }, []);

  const value: BookingContextType = {
    ...state,
    setMovie,
    setTheatre,
    setScreen,
    setShow,
    setSelectedSeats,
    setBookingId,
    setLoading,
    setError,
    resetBooking,
  };

  return (
    <BookingContext.Provider value={value}>{children}</BookingContext.Provider>
  );
};

export const useBooking = (): BookingContextType => {
  const context = useContext(BookingContext);
  if (context === undefined) {
    throw new Error("useBooking must be used within a BookingProvider");
  }
  return context;
};


