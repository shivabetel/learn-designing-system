import { apiClient } from "./client";
import { TheatreResponse, ScreenResponse } from "@/lib/types";

export const theatresApi = {
  getAllTheatres: async (): Promise<TheatreResponse[]> => {
    const response = await apiClient.get<TheatreResponse[]>("/theatre/");
    return response.data;
  },

  getTheatre: async (theatreId: number): Promise<TheatreResponse> => {
    const response = await apiClient.get<TheatreResponse>(`/theatre/${theatreId}`);
    return response.data;
  },

  getScreensByTheatre: async (theatreId: number): Promise<ScreenResponse[]> => {
    const response = await apiClient.get<ScreenResponse[]>(`/screen/theatre/${theatreId}`);
    return response.data;
  },
};


