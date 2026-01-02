"use client";

import React, { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { moviesApi } from "@/lib/api/movies";
import { theatresApi } from "@/lib/api/theatres";
import { showsApi } from "@/lib/api/shows";
import { useBooking } from "@/context/BookingContext";
import { Movie, TheatreResponse, ScreenResponse, ShowResponse } from "@/lib/types";
import { LoadingSpinner } from "@/components/ui/LoadingSpinner";
import { Button } from "@/components/ui/Button";
import { Card, CardBody } from "@/components/ui/Card";
import { ShowTimeSelector } from "@/components/ShowTimeSelector";
import { FaArrowLeft, FaClock, FaLanguage, FaMapMarkerAlt, FaTicketAlt } from "react-icons/fa";

export default function MovieDetailsPage() {
  const params = useParams();
  const router = useRouter();
  const movieId = parseInt(params.id as string);
  
  const { movie, setMovie, theatre, setTheatre, screen, setScreen, show, setShow } = useBooking();
  
  const [theatres, setTheatres] = useState<TheatreResponse[]>([]);
  const [screens, setScreens] = useState<ScreenResponse[]>([]);
  const [shows, setShows] = useState<ShowResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [loadingShows, setLoadingShows] = useState(false);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        const movieData = await moviesApi.getMovie(movieId);
        setMovie(movieData);
        
        const theatresData = await theatresApi.getAllTheatres();
        setTheatres(theatresData);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load movie details");
      } finally {
        setLoading(false);
      }
    };
    
    fetchData();
  }, [movieId, setMovie]);

  useEffect(() => {
    const fetchScreens = async () => {
      if (theatre?.id) {
        try {
          const screensData = await theatresApi.getScreensByTheatre(theatre.id);
          setScreens(screensData);
          setScreen(null); // Reset screen when theatre changes
          setShows([]); // Reset shows
        } catch (err) {
          setError(err instanceof Error ? err.message : "Failed to load screens");
        }
      }
    };
    
    fetchScreens();
  }, [theatre, setScreen]);

  useEffect(() => {
    const fetchShows = async () => {
      if (movie && screen && movie.id && screen.id) {
        try {
          setLoadingShows(true);
          const showsData = await showsApi.getShowsByMovieAndScreen(movie.id, screen.id);
          setShows(showsData);
          setShow(null); // Reset show when screen changes
        } catch (err) {
          setError(err instanceof Error ? err.message : "Failed to load shows");
        } finally {
          setLoadingShows(false);
        }
      }
    };
    
    fetchShows();
  }, [movie, screen, setShow]);

  const handleBookNow = () => {
    if (show) {
      router.push("/booking");
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  if (error || !movie) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <p className="text-red-600 mb-4">{error || "Movie not found"}</p>
          <Button onClick={() => router.push("/")}>Go Back Home</Button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-gradient-to-r from-primary-600 to-primary-800 text-white shadow-lg">
        <div className="container mx-auto px-4 py-6">
          <button
            onClick={() => router.push("/")}
            className="flex items-center gap-2 mb-4 hover:underline"
          >
            <FaArrowLeft />
            <span>Back to Movies</span>
          </button>
          <h1 className="text-3xl font-bold">{movie.title}</h1>
        </div>
      </header>

      <main className="container mx-auto px-4 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Movie Info */}
          <div className="lg:col-span-1">
            <Card>
              <div className="h-64 bg-gradient-to-br from-primary-500 to-primary-700 flex items-center justify-center">
                <FaTicketAlt className="w-32 h-32 text-white opacity-30" />
              </div>
              <CardBody>
                <h2 className="text-2xl font-bold text-gray-900 mb-4">{movie.title}</h2>
                <p className="text-gray-600 mb-4">{movie.description}</p>
                <div className="space-y-2">
                  <div className="flex items-center gap-2 text-gray-600">
                    <FaClock />
                    <span>{Math.floor(movie.duration_mins / 60)}h {movie.duration_mins % 60}m</span>
                  </div>
                  <div className="flex items-center gap-2 text-gray-600">
                    <FaLanguage />
                    <span>{movie.language}</span>
                  </div>
                  {movie.certificate && (
                    <div>
                      <span className="px-2 py-1 bg-gray-200 rounded text-sm font-semibold">
                        {movie.certificate}
                      </span>
                    </div>
                  )}
                </div>
              </CardBody>
            </Card>
          </div>

          {/* Booking Selection */}
          <div className="lg:col-span-2">
            <Card>
              <CardBody>
                <h3 className="text-xl font-bold text-gray-900 mb-6">Select Theatre & Show</h3>
                
                {/* Theatre Selection */}
                <div className="mb-6">
                  <label className="block text-sm font-semibold text-gray-700 mb-2">
                    Select Theatre
                  </label>
                  <select
                    value={theatre?.id?.toString() || ""}
                    onChange={(e) => {
                      const selectedId = e.target.value ? parseInt(e.target.value) : null;
                      const selectedTheatre = selectedId ? theatres.find(t => t.id === selectedId) : null;
                      setTheatre(selectedTheatre || null);
                    }}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                  >
                    <option value="">Choose a theatre...</option>
                    {theatres.map((t) => (
                      <option key={t.id} value={t.id}>
                        {t.name} - {t.city}
                      </option>
                    ))}
                  </select>
                </div>

                {/* Screen Selection */}
                {theatre && screens.length > 0 && (
                  <div className="mb-6">
                    <label className="block text-sm font-semibold text-gray-700 mb-2">
                      Select Screen
                    </label>
                    <select
                      value={screen?.id?.toString() || ""}
                      onChange={(e) => {
                        const selectedId = e.target.value ? parseInt(e.target.value) : null;
                        const selectedScreen = selectedId ? screens.find(s => s.id === selectedId) : null;
                        setScreen(selectedScreen || null);
                      }}
                      className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                    >
                      <option value="">Choose a screen...</option>
                      {screens.map((s) => (
                        <option key={s.id} value={s.id}>
                          {s.name} ({s.total_seats} seats)
                        </option>
                      ))}
                    </select>
                  </div>
                )}

                {/* Show Selection */}
                {screen && (
                  <div className="mb-6">
                    <label className="block text-sm font-semibold text-gray-700 mb-4">
                      Select Show Time
                    </label>
                    {loadingShows ? (
                      <div className="flex justify-center py-8">
                        <LoadingSpinner />
                      </div>
                    ) : (
                      <ShowTimeSelector
                        shows={shows}
                        selectedShow={show}
                        onSelectShow={setShow}
                      />
                    )}
                  </div>
                )}

                {/* Book Now Button */}
                {show && (
                  <div className="mt-6">
                    <Button onClick={handleBookNow} size="lg" className="w-full">
                      Book Now
                    </Button>
                  </div>
                )}
              </CardBody>
            </Card>
          </div>
        </div>
      </main>
    </div>
  );
}

