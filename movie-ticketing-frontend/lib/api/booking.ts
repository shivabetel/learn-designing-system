import { apiClient } from "./client";
import { LockSeatPayload, BookingResponse } from "@/lib/types";

export const bookingApi = {
  lockSeats: async (
    showId: number,
    seatIds: number[]
  ): Promise<number> => {
    const payload: LockSeatPayload = { show_seat_ids: seatIds };
    const response = await apiClient.post<number>(
      `/booking/seats/${showId}/lock`,
      payload
    );
    return response.data;
  },

  confirmBooking: async (bookingId: number): Promise<BookingResponse> => {
    const response = await apiClient.post<BookingResponse>(
      `/booking/booking/${bookingId}/confirm`
    );
    return response.data;
  },
};


