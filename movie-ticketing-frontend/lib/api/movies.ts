import { apiClient } from "./client";
import { MovieResponse } from "@/lib/types";

export const moviesApi = {
  getMovie: async (movieId: number): Promise<MovieResponse> => {
    const response = await apiClient.get<MovieResponse>(`/movie/${movieId}`);
    return response.data;
  },
};


