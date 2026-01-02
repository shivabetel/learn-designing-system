"use client";

import React, { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useBooking } from "@/context/BookingContext";
import { showsApi } from "@/lib/api/shows";
import { bookingApi } from "@/lib/api/booking";
import { SeatLayout, Seat } from "@/lib/types";
import { SeatMap } from "@/components/SeatMap";
import { BookingSummary } from "@/components/BookingSummary";
import { LoadingSpinner, LoadingOverlay } from "@/components/ui/LoadingSpinner";
import { Card, CardBody } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { FaArrowLeft, FaExclamationCircle } from "react-icons/fa";

export default function BookingPage() {
  const router = useRouter();
  const {
    movie,
    show,
    selectedSeats,
    setSelectedSeats,
    setBookingId,
    loading,
    setLoading,
    error,
    setError,
  } = useBooking();

  const [seatLayout, setSeatLayout] = useState<SeatLayout | null>(null);
  const [loadingLayout, setLoadingLayout] = useState(true);
  const [confirming, setConfirming] = useState(false);

  useEffect(() => {
    // Redirect if no movie or show selected
    if (!movie || !show) {
      router.push("/");
      return;
    }

    const fetchSeatLayout = async () => {
      try {
        setLoadingLayout(true);
        const layout = await showsApi.getShowSeatLayout(show.id);
        setSeatLayout(layout);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load seat layout");
      } finally {
        setLoadingLayout(false);
      }
    };

    fetchSeatLayout();
  }, [show, movie, router, setError]);

  const handleSeatSelect = (seat: Seat) => {
    setSelectedSeats([...selectedSeats, seat]);
  };

  const handleSeatDeselect = (seatId: number) => {
    setSelectedSeats(selectedSeats.filter((s) => s.id !== seatId));
  };

  const handleConfirmBooking = async () => {
    if (!show || selectedSeats.length === 0) return;

    try {
      setConfirming(true);
      setError(null);

      // Lock seats
      const seatIds = selectedSeats.map((s) => s.id);
      const bookingId = await bookingApi.lockSeats(show.id, seatIds);
      setBookingId(bookingId);

      // Confirm booking
      await bookingApi.confirmBooking(bookingId);

      // Redirect to confirmation page
      router.push(`/booking/confirm/${bookingId}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to confirm booking");
      setConfirming(false);
    }
  };

  if (!movie || !show) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  if (loadingLayout) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  if (error && !seatLayout) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Card>
          <CardBody>
            <div className="text-center">
              <FaExclamationCircle className="w-12 h-12 text-red-500 mx-auto mb-4" />
              <p className="text-red-600 mb-4">{error}</p>
              <Button onClick={() => router.push("/")}>Go Back</Button>
            </div>
          </CardBody>
        </Card>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {confirming && <LoadingOverlay message="Confirming your booking..." />}

      {/* Header */}
      <header className="bg-gradient-to-r from-primary-600 to-primary-800 text-white shadow-lg">
        <div className="container mx-auto px-4 py-6">
          <button
            onClick={() => router.back()}
            className="flex items-center gap-2 mb-4 hover:underline"
          >
            <FaArrowLeft />
            <span>Back</span>
          </button>
          <h1 className="text-3xl font-bold">Select Your Seats</h1>
          <p className="text-gray-200 mt-2">{movie.title}</p>
        </div>
      </header>

      <main className="container mx-auto px-4 py-8">
        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg flex items-center gap-2 text-red-700">
            <FaExclamationCircle />
            <span>{error}</span>
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Seat Map */}
          <div className="lg:col-span-2">
            <Card>
              <CardBody>
                {seatLayout ? (
                  <SeatMap
                    seatLayout={seatLayout}
                    selectedSeats={selectedSeats}
                    onSeatSelect={handleSeatSelect}
                    onSeatDeselect={handleSeatDeselect}
                  />
                ) : (
                  <div className="text-center py-12">
                    <LoadingSpinner />
                  </div>
                )}
              </CardBody>
            </Card>
          </div>

          {/* Booking Summary */}
          <div className="lg:col-span-1">
            <BookingSummary
              movie={movie}
              show={show}
              selectedSeats={selectedSeats}
              onConfirm={handleConfirmBooking}
              isLoading={confirming}
            />
          </div>
        </div>
      </main>
    </div>
  );
}


