"use client";

import React, { useState, useEffect } from "react";
import { SeatLayout, Seat, ShowSeatStatus } from "@/lib/types";
import { FaChair } from "react-icons/fa";

interface SeatMapProps {
  seatLayout: SeatLayout;
  selectedSeats: Seat[];
  onSeatSelect: (seat: Seat) => void;
  onSeatDeselect: (seatId: number) => void;
}

export const SeatMap: React.FC<SeatMapProps> = ({
  seatLayout,
  selectedSeats,
  onSeatSelect,
  onSeatDeselect,
}) => {
  const [selectedSeatIds, setSelectedSeatIds] = useState<Set<number>>(
    new Set(selectedSeats.map((s) => s.id))
  );

  useEffect(() => {
    setSelectedSeatIds(new Set(selectedSeats.map((s) => s.id)));
  }, [selectedSeats]);

  const handleSeatClick = (seat: Seat) => {
    if (seat.status === ShowSeatStatus.BOOKED || seat.status === ShowSeatStatus.UNAVAILABLE) {
      return; // Cannot select booked or unavailable seats
    }

    if (seat.status === ShowSeatStatus.LOCKED) {
      return; // Cannot select locked seats
    }

    if (selectedSeatIds.has(seat.id)) {
      onSeatDeselect(seat.id);
    } else {
      onSeatSelect(seat);
    }
  };

  const getSeatColor = (seat: Seat, isSelected: boolean) => {
    if (isSelected) {
      return "bg-blue-500 hover:bg-blue-600 text-white";
    }
    switch (seat.status) {
      case ShowSeatStatus.AVAILABLE:
        return "bg-green-500 hover:bg-green-600 text-white cursor-pointer";
      case ShowSeatStatus.LOCKED:
        return "bg-yellow-500 hover:bg-yellow-600 text-white cursor-not-allowed";
      case ShowSeatStatus.BOOKED:
        return "bg-gray-400 cursor-not-allowed text-white";
      case ShowSeatStatus.UNAVAILABLE:
        return "bg-gray-600 cursor-not-allowed text-white";
      default:
        return "bg-gray-300";
    }
  };

  return (
    <div className="w-full">
      {/* Screen indicator */}
      <div className="mb-8 text-center">
        <div className="inline-block px-8 py-2 bg-gradient-to-r from-gray-300 to-gray-400 rounded-lg shadow-lg">
          <span className="text-gray-700 font-semibold text-lg">SCREEN</span>
        </div>
      </div>

      {/* Seat layout */}
      <div className="space-y-4">
        {seatLayout.layout.map((row) => (
          <div key={row.row} className="flex items-center gap-2">
            <div className="w-12 text-center font-bold text-gray-700">
              {row.row}
            </div>
            <div className="flex-1 flex flex-wrap gap-2 justify-center">
              {row.seats.map((seat) => {
                const isSelected = selectedSeatIds.has(seat.id);
                return (
                  <button
                    key={seat.id}
                    onClick={() => handleSeatClick(seat)}
                    disabled={
                      seat.status === ShowSeatStatus.BOOKED ||
                      seat.status === ShowSeatStatus.UNAVAILABLE ||
                      seat.status === ShowSeatStatus.LOCKED
                    }
                    className={`
                      w-10 h-10 rounded-md transition-all duration-200
                      flex items-center justify-center text-xs font-semibold
                      ${getSeatColor(seat, isSelected)}
                      ${isSelected ? "ring-2 ring-blue-700 ring-offset-2" : ""}
                    `}
                    title={`Seat ${row.row}${seat.seat_number} - ₹${seat.price.toFixed(2)}`}
                  >
                    <FaChair className="w-5 h-5" />
                  </button>
                );
              })}
            </div>
          </div>
        ))}
      </div>

      {/* Legend */}
      <div className="mt-8 flex flex-wrap justify-center gap-4 text-sm">
        <div className="flex items-center gap-2">
          <div className="w-6 h-6 bg-green-500 rounded"></div>
          <span>Available</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-6 h-6 bg-blue-500 rounded"></div>
          <span>Selected</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-6 h-6 bg-yellow-500 rounded"></div>
          <span>Locked</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-6 h-6 bg-gray-400 rounded"></div>
          <span>Booked</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-6 h-6 bg-gray-600 rounded"></div>
          <span>Unavailable</span>
        </div>
      </div>
    </div>
  );
};


