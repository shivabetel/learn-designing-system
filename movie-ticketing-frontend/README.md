# Movie Ticket Booking Frontend

A modern, responsive Next.js application for booking movie tickets. Built with TypeScript, Tailwind CSS, and integrated with a FastAPI backend.

## Features

- 🎬 Browse available movies
- 🎭 Select theatres and screens
- ⏰ Choose show times
- 🪑 Interactive seat selection with real-time availability
- 💳 Complete booking flow with seat locking
- ✅ Booking confirmation

## Tech Stack

- **Framework**: Next.js 14+ (App Router)
- **Language**: TypeScript
- **Styling**: Tailwind CSS
- **HTTP Client**: Axios
- **Icons**: react-icons
- **Date Handling**: date-fns
- **State Management**: React Context API

## Getting Started

### Prerequisites

- Node.js 18+ and npm/yarn/pnpm
- Backend API running on `http://localhost:8000`

### Installation

1. Install dependencies:
```bash
npm install
# or
yarn install
# or
pnpm install
```

2. Set up environment variables (optional):
Create a `.env.local` file:
```
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
```

3. Run the development server:
```bash
npm run dev
# or
yarn dev
# or
pnpm dev
```

4. Open [http://localhost:3000](http://localhost:3000) in your browser.

## Project Structure

```
movie-ticketing-frontend/
├── app/                    # Next.js App Router pages
│   ├── layout.tsx         # Root layout with BookingProvider
│   ├── page.tsx          # Home page (movies list)
│   ├── movies/[id]/      # Movie details page
│   └── booking/          # Booking flow pages
├── components/           # React components
│   ├── ui/               # Base UI components
│   ├── MovieCard.tsx     # Movie display card
│   ├── SeatMap.tsx       # Interactive seat selection
│   ├── BookingSummary.tsx # Booking details summary
│   └── ShowTimeSelector.tsx # Show time selection
├── lib/
│   ├── api/              # API client functions
│   └── types/            # TypeScript type definitions
├── context/              # React Context providers
└── public/               # Static assets
```

## API Integration

The frontend integrates with the following backend endpoints:

- `GET /api/v1/theatre/` - List all theatres
- `GET /api/v1/theatre/{theatre_id}` - Get theatre details
- `GET /api/v1/screen/theatre/{theatre_id}` - Get screens for theatre
- `GET /api/v1/movie/{movie_id}` - Get movie details
- `GET /api/v1/show/{movie_id}/{screen_id}` - Get shows for movie/screen
- `GET /api/v1/show/{show_id}/seat-layout` - Get seat layout
- `POST /api/v1/booking/seats/{show_id}/lock` - Lock seats
- `POST /api/v1/booking/booking/{booking_id}/confirm` - Confirm booking

## Booking Flow

1. **Home Page**: Browse available movies
2. **Movie Details**: Select theatre, screen, and show time
3. **Seat Selection**: Choose seats from interactive seat map
4. **Booking Summary**: Review selection and confirm
5. **Confirmation**: View booking confirmation with booking ID

## Development

### Build for Production

```bash
npm run build
npm start
```

### Linting

```bash
npm run lint
```

## Notes

- The home page currently uses mock movie data. In production, you would implement a `GET /api/v1/movie/` endpoint to fetch all movies.
- Seat locking expires after 10 minutes (handled by backend).
- The app uses React Context for state management across the booking flow.

## License

MIT


