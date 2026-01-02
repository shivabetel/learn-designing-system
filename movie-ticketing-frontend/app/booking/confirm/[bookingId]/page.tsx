"use client";

import React, { useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import { useBooking } from "@/context/BookingContext";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { FaCheckCircle, FaHome, FaTicketAlt } from "react-icons/fa";
import { format } from "date-fns";

export default function BookingConfirmationPage() {
  const params = useParams();
  const router = useRouter();
  const bookingId = parseInt(params.bookingId as string);
  const { movie, show, selectedSeats, resetBooking } = useBooking();

  useEffect(() => {
    // Reset booking context after showing confirmation
    const timer = setTimeout(() => {
      resetBooking();
    }, 5000);

    return () => clearTimeout(timer);
  }, [resetBooking]);

  const totalAmount = selectedSeats.reduce((sum, seat) => sum + seat.price, 0);

  const formatDateTime = (dateString: string) => {
    try {
      const date = new Date(dateString);
      return format(date, "MMM dd, yyyy 'at' hh:mm a");
    } catch {
      return dateString;
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center py-12">
      <div className="container mx-auto px-4 max-w-2xl">
        <Card>
          <CardBody>
            <div className="text-center mb-8">
              <div className="inline-flex items-center justify-center w-20 h-20 bg-green-100 rounded-full mb-4">
                <FaCheckCircle className="w-12 h-12 text-green-600" />
              </div>
              <h1 className="text-3xl font-bold text-gray-900 mb-2">
                Booking Confirmed!
              </h1>
              <p className="text-gray-600">
                Your tickets have been successfully booked
              </p>
            </div>

            <div className="space-y-6 mb-8">
              {/* Booking ID */}
              <div className="bg-gray-50 p-4 rounded-lg">
                <div className="text-sm text-gray-600 mb-1">Booking ID</div>
                <div className="text-2xl font-bold text-gray-900">
                  #{bookingId}
                </div>
              </div>

              {/* Movie Info */}
              {movie && (
                <div>
                  <h3 className="text-lg font-semibold text-gray-900 mb-2">
                    Movie Details
                  </h3>
                  <div className="bg-gray-50 p-4 rounded-lg">
                    <div className="font-semibold text-gray-900 mb-1">
                      {movie.title}
                    </div>
                    <div className="text-sm text-gray-600">
                      {movie.language} • {Math.floor(movie.duration_mins / 60)}h{" "}
                      {movie.duration_mins % 60}m
                    </div>
                  </div>
                </div>
              )}

              {/* Show Info */}
              {show && (
                <div>
                  <h3 className="text-lg font-semibold text-gray-900 mb-2">
                    Show Details
                  </h3>
                  <div className="bg-gray-50 p-4 rounded-lg">
                    <div className="text-gray-900">
                      {formatDateTime(show.start_time)}
                    </div>
                  </div>
                </div>
              )}

              {/* Seats */}
              {selectedSeats.length > 0 && (
                <div>
                  <h3 className="text-lg font-semibold text-gray-900 mb-2">
                    Seats
                  </h3>
                  <div className="bg-gray-50 p-4 rounded-lg">
                    <div className="flex flex-wrap gap-2">
                      {selectedSeats.map((seat) => (
                        <span
                          key={seat.id}
                          className="px-3 py-1 bg-primary-100 text-primary-800 rounded-md font-semibold"
                        >
                          Seat {seat.seat_number}
                        </span>
                      ))}
                    </div>
                  </div>
                </div>
              )}

              {/* Total Amount */}
              <div className="border-t border-gray-200 pt-4">
                <div className="flex justify-between items-center">
                  <span className="text-lg font-semibold text-gray-900">
                    Total Amount
                  </span>
                  <span className="text-2xl font-bold text-primary-600">
                    ₹{totalAmount.toFixed(2)}
                  </span>
                </div>
              </div>
            </div>

            {/* Actions */}
            <div className="flex flex-col sm:flex-row gap-4">
              <Button
                onClick={() => router.push("/")}
                variant="primary"
                className="flex-1"
                size="lg"
              >
                <FaHome className="mr-2" />
                Back to Home
              </Button>
              <Button
                onClick={() => window.print()}
                variant="outline"
                className="flex-1"
                size="lg"
              >
                <FaTicketAlt className="mr-2" />
                Print Ticket
              </Button>
            </div>
          </CardBody>
        </Card>
      </div>
    </div>
  );
}


