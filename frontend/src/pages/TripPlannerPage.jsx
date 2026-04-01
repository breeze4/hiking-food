import { useNavigate } from 'react-router-dom';
import { useTrip } from '../context/TripContext';
import TripCalculator from '../components/TripCalculator';
import SnackSelection from '../components/SnackSelection';
import MealSelection from '../components/MealSelection';
import TripSummary from '../components/TripSummary';

function TripPlannerPage() {
  const { tripDetail } = useTrip();
  const navigate = useNavigate();

  if (!tripDetail) {
    return <p>Select or create a trip to get started.</p>;
  }

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h2>{tripDetail.name}</h2>
        <button onClick={() => navigate(`/trips/${tripDetail.id}/packing`)}>
          Packing Screen
        </button>
      </div>
      <TripCalculator />
      <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
        <div style={{ flex: '1 1 600px' }}>
          <MealSelection />
          <SnackSelection />
        </div>
        <div style={{ flex: '0 0 400px' }}>
          <TripSummary />
        </div>
      </div>
    </div>
  );
}

export default TripPlannerPage;
