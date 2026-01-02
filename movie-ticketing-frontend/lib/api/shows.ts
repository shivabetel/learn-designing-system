import { apiClient } from "./client";
import { ShowResponse, SeatLayout } from "@/lib/types";

export const showsApi = {
  getShowsByMovieAndScreen: async (
    movieId: number,
    screenId: number
  ): Promise<ShowResponse[]> => {
    const response = await apiClient.get<ShowResponse[]>(
      `/show/${movieId}/${screenId}`
    );
    return response.data;
  },

  getShowSeatLayout: async (showId: number): Promise<SeatLayout> => {
    const response = await apiClient.get<SeatLayout>(
      `/show/${showId}/seat-layout`
    );
    return response.data;
  },
};


