"use client";

import React from "react";
import Link from "next/link";
import { Card, CardBody } from "./ui/Card";
import { Movie } from "@/lib/types";
import { FaClock, FaLanguage, FaTicketAlt } from "react-icons/fa";

interface MovieCardProps {
  movie: Movie;
}

export const MovieCard: React.FC<MovieCardProps> = ({ movie }) => {
  const formatDuration = (minutes: number) => {
    const hours = Math.floor(minutes / 60);
    const mins = minutes % 60;
    return hours > 0 ? `${hours}h ${mins}m` : `${mins}m`;
  };

  return (
    <Link href={`/movies/${movie.id}`}>
      <Card hover className="h-full cursor-pointer">
        <div className="relative h-64 bg-gradient-to-br from-primary-500 to-primary-700 flex items-center justify-center">
          <FaTicketAlt className="w-24 h-24 text-white opacity-30" />
          <div className="absolute inset-0 flex items-center justify-center">
            <span className="text-white text-2xl font-bold">{movie.title}</span>
          </div>
        </div>
        <CardBody>
          <h3 className="text-xl font-bold text-gray-900 mb-2 line-clamp-1">
            {movie.title}
          </h3>
          <p className="text-gray-600 text-sm mb-4 line-clamp-2">
            {movie.description}
          </p>
          <div className="flex flex-wrap gap-3 text-sm text-gray-600">
            <div className="flex items-center gap-1">
              <FaClock className="w-4 h-4" />
              <span>{formatDuration(movie.duration_mins)}</span>
            </div>
            <div className="flex items-center gap-1">
              <FaLanguage className="w-4 h-4" />
              <span>{movie.language}</span>
            </div>
            {movie.certificate && (
              <div className="flex items-center gap-1">
                <span className="px-2 py-0.5 bg-gray-200 rounded text-xs font-semibold">
                  {movie.certificate}
                </span>
              </div>
            )}
          </div>
        </CardBody>
      </Card>
    </Link>
  );
};


