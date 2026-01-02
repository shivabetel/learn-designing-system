"use client";

import React from "react";
import { Seat, ShowResponse, Movie } from "@/lib/types";
import { Card, CardBody, CardHeader } from "./ui/Card";
import { Button } from "./ui/Button";
import { format } from "date-fns";

interface BookingSummaryProps {
  movie: Movie;
  show: ShowResponse;
  selectedSeats: Seat[];
  onConfirm: () => void;
  isLoading?: boolean;
}

export const BookingSummary: React.FC<BookingSummaryProps> = ({
  movie,
  show,
  selectedSeats,
  onConfirm,
  isLoading = false,
}) => {
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
    <Card className="sticky top-4">
      <CardHeader>
        <h3 className="text-xl font-bold text-gray-900">Booking Summary</h3>
      </CardHeader>
      <CardBody>
        <div className="space-y-4">
          {/* Movie Info */}
          <div>
            <h4 className="font-semibold text-gray-900 mb-1">{movie.title}</h4>
            <p className="text-sm text-gray-600">
              {formatDateTime(show.start_time)}
            </p>
          </div>

          {/* Selected Seats */}
          <div>
            <h5 className="font-semibold text-gray-700 mb-2">Selected Seats</h5>
            {selectedSeats.length === 0 ? (
              <p className="text-sm text-gray-500">No seats selected</p>
            ) : (
              <div className="space-y-1">
                {selectedSeats.map((seat) => (
                  <div
                    key={seat.id}
                    className="flex justify-between text-sm text-gray-600"
                  >
                    <span>
                      Seat {seat.seat_number} - ₹{seat.price.toFixed(2)}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Price Breakdown */}
          <div className="border-t border-gray-200 pt-4">
            <div className="flex justify-between items-center mb-2">
              <span className="text-gray-600">Subtotal</span>
              <span className="text-gray-900 font-semibold">
                ₹{totalAmount.toFixed(2)}
              </span>
            </div>
            <div className="flex justify-between items-center text-lg font-bold text-gray-900 pt-2 border-t border-gray-200">
              <span>Total</span>
              <span>₹{totalAmount.toFixed(2)}</span>
            </div>
          </div>

          {/* Confirm Button */}
          <Button
            onClick={onConfirm}
            disabled={selectedSeats.length === 0 || isLoading}
            isLoading={isLoading}
            className="w-full"
            size="lg"
          >
            {selectedSeats.length === 0
              ? "Select Seats to Continue"
              : "Confirm Booking"}
          </Button>
        </div>
      </CardBody>
    </Card>
  );
};


