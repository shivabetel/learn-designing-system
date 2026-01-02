"use client";

import React, { useEffect, useState } from "react";
import { MovieCard } from "@/components/MovieCard";
import { LoadingSpinner } from "@/components/ui/LoadingSpinner";
import { Movie } from "@/lib/types";
import { moviesApi } from "@/lib/api/movies";
import { FaFilm, FaSpinner } from "react-icons/fa";

// Mock data for demonstration - in production, you'd fetch from an API
const MOCK_MOVIES: Movie[] = [
  {
    id: 1,
    title: "The Dark Knight",
    description: "When the menace known as the Joker wreaks havoc on Gotham, Batman must accept one of the greatest psychological and physical tests of his ability to fight injustice.",
    duration_mins: 152,
    language: "English",
    certificate: "A",
  },
  {
    id: 2,
    title: "Inception",
    description: "A skilled thief is given a chance at redemption if he can successfully perform inception - planting an idea in someone's mind.",
    duration_mins: 148,
    language: "English",
    certificate: "UA",
  },
  {
    id: 3,
    title: "Interstellar",
    description: "A team of explorers travel through a wormhole in space in an attempt to ensure humanity's survival.",
    duration_mins: 169,
    language: "English",
    certificate: "UA",
  },
];

export default function Home() {
  const [movies, setMovies] = useState<Movie[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // For now, use mock data since there's no GET all movies endpoint
    // In production, you'd call: const data = await moviesApi.getAllMovies();
    setTimeout(() => {
      setMovies(MOCK_MOVIES);
      setLoading(false);
    }, 500);
  }, []);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <p className="text-red-600 mb-4">{error}</p>
          <button
            onClick={() => window.location.reload()}
            className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-gradient-to-r from-primary-600 to-primary-800 text-white shadow-lg">
        <div className="container mx-auto px-4 py-6">
          <div className="flex items-center gap-3">
            <FaFilm className="w-8 h-8" />
            <h1 className="text-3xl font-bold">Movie Ticket Booking</h1>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="container mx-auto px-4 py-8">
        <div className="mb-8">
          <h2 className="text-2xl font-bold text-gray-900 mb-2">
            Now Showing
          </h2>
          <p className="text-gray-600">
            Select a movie to book your tickets
          </p>
        </div>

        {movies.length === 0 ? (
          <div className="text-center py-12">
            <p className="text-gray-500 text-lg">No movies available at the moment</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {movies.map((movie) => (
              <MovieCard key={movie.id} movie={movie} />
            ))}
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="bg-gray-800 text-white mt-12">
        <div className="container mx-auto px-4 py-6 text-center">
          <p>&copy; 2024 Movie Ticket Booking. All rights reserved.</p>
        </div>
      </footer>
    </div>
  );
}


