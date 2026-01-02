"use client";

import React from "react";
import { ShowResponse } from "@/lib/types";
import { format } from "date-fns";
import { Card, CardBody } from "./ui/Card";

interface ShowTimeSelectorProps {
  shows: ShowResponse[];
  selectedShow: ShowResponse | null;
  onSelectShow: (show: ShowResponse) => void;
}

export const ShowTimeSelector: React.FC<ShowTimeSelectorProps> = ({
  shows,
  selectedShow,
  onSelectShow,
}) => {
  const formatTime = (dateString: string) => {
    try {
      const date = new Date(dateString);
      return format(date, "hh:mm a");
    } catch {
      return dateString;
    }
  };

  const formatDate = (dateString: string) => {
    try {
      const date = new Date(dateString);
      return format(date, "MMM dd, yyyy");
    } catch {
      return dateString;
    }
  };

  if (shows.length === 0) {
    return (
      <div className="text-center py-8 text-gray-500">
        No shows available for this movie and screen
      </div>
    );
  }

  // Group shows by date
  const showsByDate = shows.reduce((acc, show) => {
    const date = formatDate(show.start_time);
    if (!acc[date]) {
      acc[date] = [];
    }
    acc[date].push(show);
    return acc;
  }, {} as Record<string, ShowResponse[]>);

  return (
    <div className="space-y-6">
      {Object.entries(showsByDate).map(([date, dateShows]) => (
        <div key={date}>
          <h4 className="text-lg font-semibold text-gray-900 mb-3">{date}</h4>
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-3">
            {dateShows.map((show) => {
              const isSelected = selectedShow?.id === show.id;
              return (
                <button
                  key={show.id}
                  onClick={() => onSelectShow(show)}
                  className={`
                    p-3 rounded-lg border-2 transition-all duration-200
                    ${
                      isSelected
                        ? "border-primary-600 bg-primary-50 text-primary-900"
                        : "border-gray-300 hover:border-primary-400 bg-white text-gray-700"
                    }
                  `}
                >
                  <div className="font-semibold">{formatTime(show.start_time)}</div>
                  <div className="text-xs text-gray-500 mt-1">
                    ₹{show.base_price.toFixed(2)}
                  </div>
                </button>
              );
            })}
          </div>
        </div>
      ))}
    </div>
  );
};


