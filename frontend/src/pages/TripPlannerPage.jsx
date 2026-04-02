import { useNavigate } from 'react-router-dom';
import { useTrip } from '../context/TripContext';
import TripCalculator from '../components/TripCalculator';
import SnackSelection from '../components/SnackSelection';
import MealSelection from '../components/MealSelection';
import TripSummary from '../components/TripSummary';
import { Button } from '@/components/ui/button';

function TripPlannerPage() {
  const { tripDetail } = useTrip();
  const navigate = useNavigate();

  if (!tripDetail) {
    return <p className="text-muted-foreground">Select or create a trip to get started.</p>;
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-2xl font-semibold tracking-tight">{tripDetail.name}</h2>
        <Button variant="outline" onClick={() => navigate(`/trips/${tripDetail.id}/packing`)}>
          Packing Screen
        </Button>
      </div>

      <div className="space-y-4">
        <TripCalculator />
        <TripSummary />
        <MealSelection />
        <SnackSelection />
      </div>
    </div>
  );
}

export default TripPlannerPage;
