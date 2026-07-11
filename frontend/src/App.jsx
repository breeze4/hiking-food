import {
  BrowserRouter, Routes, Route, NavLink, Navigate, Outlet, useParams,
} from 'react-router-dom';
import { useState, Suspense, lazy } from 'react';
import { TripProvider, useTrip } from './context/TripContext';
import TripSelector from './components/TripSelector';
import SettingsModal from './components/SettingsModal';

// Route pages are code-split so they load on demand and keep the entry chunk
// under Vite's size-warning threshold.
const IngredientsPage = lazy(() => import('./pages/IngredientsPage'));
const SnackCatalogPage = lazy(() => import('./pages/SnackCatalogPage'));
const IntakePage = lazy(() => import('./pages/IntakePage'));
const RecipesPage = lazy(() => import('./pages/RecipesPage'));
const RecipeEditPage = lazy(() => import('./pages/RecipeEditPage'));
const TripPlannerPage = lazy(() => import('./pages/TripPlannerPage'));
const PackingScreen = lazy(() => import('./pages/PackingScreen'));
const DailyPlanPage = lazy(() => import('./pages/DailyPlanPage'));
import { Button } from '@/components/ui/button';
import { Sheet, SheetContent, SheetTrigger } from '@/components/ui/sheet';
import { Separator } from '@/components/ui/separator';

function NavLinks({ onClick }) {
  const linkClass = ({ isActive }) =>
    `text-sm font-medium transition-colors hover:text-primary ${isActive ? 'text-foreground' : 'text-muted-foreground'}`;

  return (
    <>
      <PlannerLink className={linkClass} onClick={onClick} />
      <NavLink to="/recipes" className={linkClass} onClick={onClick}>Recipes</NavLink>
      <NavLink to="/snacks" className={linkClass} onClick={onClick}>Snack Catalog</NavLink>
      <NavLink to="/ingredients" className={linkClass} onClick={onClick}>Ingredients</NavLink>
      <NavLink to="/intake" className={linkClass} onClick={onClick}>Intake</NavLink>
      <DailyPlanLink onClick={onClick} />
      <PackingLink onClick={onClick} />
    </>
  );
}

function PlannerLink({ className, onClick }) {
  const { activeTripId } = useTrip();
  return (
    <NavLink
      to={activeTripId ? `/trips/${activeTripId}` : '/'}
      end
      className={className}
      onClick={onClick}
    >
      Trip Planner
    </NavLink>
  );
}

function DailyPlanLink({ onClick }) {
  const { activeTripId } = useTrip();
  const linkClass = ({ isActive }) =>
    `text-sm font-medium transition-colors hover:text-primary ${isActive ? 'text-foreground' : 'text-muted-foreground'}`;

  if (!activeTripId) return null;
  return (
    <NavLink to={`/trips/${activeTripId}/daily-plan`} className={linkClass} onClick={onClick}>
      Daily Plan
    </NavLink>
  );
}

function PackingLink({ onClick }) {
  const { activeTripId } = useTrip();
  const linkClass = ({ isActive }) =>
    `text-sm font-medium transition-colors hover:text-primary ${isActive ? 'text-foreground' : 'text-muted-foreground'}`;

  if (!activeTripId) return null;
  return (
    <NavLink to={`/trips/${activeTripId}/packing`} className={linkClass} onClick={onClick}>
      Packing
    </NavLink>
  );
}

function PackingRedirect() {
  const { activeTripId } = useTrip();
  if (!activeTripId) return <p className="text-muted-foreground p-8">Select a trip first.</p>;
  return <Navigate to={`/trips/${activeTripId}/packing`} replace />;
}

function TripIndexRedirect() {
  const { activeTripId, tripsLoaded } = useTrip();
  if (!tripsLoaded) return <p className="text-muted-foreground">Loading...</p>;
  if (!activeTripId) return <TripPlannerPage />;
  return <Navigate to={`/trips/${activeTripId}`} replace />;
}

function TripRouteBoundary() {
  const { tripId } = useParams();
  const { trips, tripsLoaded } = useTrip();
  const numericTripId = Number(tripId);
  const validId = Number.isSafeInteger(numericTripId) && numericTripId > 0;

  if (!tripsLoaded) return <p className="text-muted-foreground">Loading...</p>;
  if (!validId || !trips.some((trip) => trip.id === numericTripId)) {
    return <p className="text-destructive">Trip not found.</p>;
  }
  return <Outlet />;
}

function AppHeader() {
  const [open, setOpen] = useState(false);

  return (
    <header className="sticky top-0 z-50 w-full border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="flex h-14 items-center px-4 gap-4">
        {/* Mobile hamburger */}
        <Sheet open={open} onOpenChange={setOpen}>
          <SheetTrigger
            render={<Button variant="ghost" size="icon" className="md:hidden shrink-0" />}
          >
              <svg width="20" height="20" viewBox="0 0 15 15" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M1.5 3C1.22386 3 1 3.22386 1 3.5C1 3.77614 1.22386 4 1.5 4H13.5C13.7761 4 14 3.77614 14 3.5C14 3.22386 13.7761 3 13.5 3H1.5ZM1 7.5C1 7.22386 1.22386 7 1.5 7H13.5C13.7761 7 14 7.22386 14 7.5C14 7.77614 13.7761 8 13.5 8H1.5C1.22386 8 1 7.77614 1 7.5ZM1 11.5C1 11.2239 1.22386 11 1.5 11H13.5C13.7761 11 14 11.2239 14 11.5C14 11.7761 13.7761 12 13.5 12H1.5C1.22386 12 1 11.7761 1 11.5Z" fill="currentColor" fillRule="evenodd" clipRule="evenodd" />
              </svg>
          </SheetTrigger>
          <SheetContent side="left" className="w-64">
            <nav className="flex flex-col gap-4 mt-8 px-4">
              <NavLinks onClick={() => setOpen(false)} />
              <Separator />
              <TripSelector />
            </nav>
          </SheetContent>
        </Sheet>

        {/* Desktop nav */}
        <nav className="hidden md:flex items-center gap-6">
          <NavLinks />
        </nav>

        {/* Trip selector + settings - desktop */}
        <div className="hidden md:flex ml-auto items-center gap-2">
          <TripSelector />
          <SettingsModal />
        </div>

        {/* Settings icon - mobile (visible when sheet is closed) */}
        <div className="md:hidden ml-auto">
          <SettingsModal />
        </div>
      </div>
    </header>
  );
}

function App() {
  return (
    <BrowserRouter basename="/hiking-food">
      <TripProvider>
        <div className="min-h-screen bg-background font-sans antialiased">
          <AppHeader />
          <main className="p-4 md:p-6 max-w-7xl mx-auto">
            <Suspense fallback={<p className="text-muted-foreground p-4">Loading...</p>}>
              <Routes>
                <Route path="/" element={<TripIndexRedirect />} />
                <Route path="/ingredients" element={<IngredientsPage />} />
                <Route path="/snacks" element={<SnackCatalogPage />} />
                <Route path="/intake" element={<IntakePage />} />
                <Route path="/recipes" element={<RecipesPage />} />
                <Route path="/recipes/:id" element={<RecipeEditPage />} />
                <Route path="/trips/:tripId" element={<TripRouteBoundary />}>
                  <Route index element={<TripPlannerPage />} />
                  <Route path="daily-plan" element={<DailyPlanPage />} />
                  <Route path="packing" element={<PackingScreen />} />
                  <Route path="*" element={<p className="text-destructive">Trip page not found.</p>} />
                </Route>
                <Route path="/packing" element={<PackingRedirect />} />
              </Routes>
            </Suspense>
          </main>
        </div>
      </TripProvider>
    </BrowserRouter>
  );
}

export default App;
