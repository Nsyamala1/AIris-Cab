import React, { useState } from 'react';
import {
  Box,
  Stack,
  TextField,
  Button,
  Typography,
  Paper,
  Autocomplete,
  Chip,
  Divider,
  Alert,
  Snackbar,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
} from '@mui/material';
import {
  Flight as FlightIcon,
  CalendarMonth as CalendarIcon,
  Person as PersonIcon,
} from '@mui/icons-material';
import { DatePicker } from '@mui/x-date-pickers/DatePicker';
import { LocalizationProvider } from '@mui/x-date-pickers/LocalizationProvider';
import { AdapterDateFns } from '@mui/x-date-pickers/AdapterDateFns';
import axios from 'axios';

interface FlightEstimate {
  airline: string;
  price: number;
  departure: string;
  arrival: string;
  duration: number;
  stops: number;
  recommended: boolean;
}

export default function FlightComparison() {
  const [origin, setOrigin] = useState('');
  const [destination, setDestination] = useState('');
  const [departureDate, setDepartureDate] = useState<Date | null>(null);
  const [returnDate, setReturnDate] = useState<Date | null>(null);
  const [passengers, setPassengers] = useState(1);
  const [cabinClass, setCabinClass] = useState('economy');
  const [estimates, setEstimates] = useState<FlightEstimate[]>([]);
  const [loading, setLoading] = useState(false);
  const [cityOptions, setCityOptions] = useState<string[]>([]);
  const [snackbar, setSnackbar] = useState({
    open: false,
    message: '',
    severity: 'success' as 'success' | 'error'
  });

  const handleSearch = async () => {
    if (!origin || !destination || !departureDate) {
      setSnackbar({
        open: true,
        message: 'Please fill in all required fields',
        severity: 'error'
      });
      return;
    }

    setLoading(true);
    try {
      const response = await axios.post('http://localhost:8000/compare-flights', {
        origin,
        destination,
        departure_date: departureDate.toISOString(),
        return_date: returnDate?.toISOString(),
        passengers,
        cabin_class: cabinClass
      });
      setEstimates(response.data);
    } catch (error: unknown) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to fetch flight prices';
      setSnackbar({
        open: true,
        message: `Error: ${errorMessage}`,
        severity: 'error'
      });
    } finally {
      setLoading(false);
    }
  };

  const handleCitySearch = async (query: string, type: 'origin' | 'destination'): Promise<void> => {
    if (query.length >= 2) {
      try {
        const response = await axios.get(`http://localhost:8000/cities/autocomplete?query=${query}`);
        setCityOptions(response.data);
      } catch (error) {
        console.error('Failed to fetch city suggestions:', error);
        setSnackbar({
          open: true,
          message: 'Failed to fetch city suggestions. Please try again.',
          severity: 'error'
        });
      }
    }
  };

  const formatDuration = (minutes: number) => {
    const hours = Math.floor(minutes / 60);
    const mins = minutes % 60;
    return `${hours}h ${mins}m`;
  };

  return (
    <LocalizationProvider dateAdapter={AdapterDateFns}>
      <Stack spacing={3}>
        <Typography variant="h3" align="center" color="primary" gutterBottom>
          AIris Flight Price Comparison
        </Typography>

        <Box sx={{ display: 'grid', gap: 2, gridTemplateColumns: { xs: '1fr', md: '1fr 1fr' } }}>
          <Box>
            <Autocomplete
              freeSolo
              options={cityOptions}
              value={origin}
              onInputChange={(_, newValue: string) => {
                setOrigin(newValue);
                handleCitySearch(newValue, 'origin');
              }}
              renderInput={(params) => (
                <TextField
                  {...params}
                  label="Origin Airport"
                  placeholder="Enter city or airport code"
                  required
                  fullWidth
                />
              )}
            />
          </Box>

          <Box>
            <Autocomplete
              freeSolo
              options={cityOptions}
              value={destination}
              onInputChange={(_, newValue: string) => {
                setDestination(newValue);
                handleCitySearch(newValue, 'destination');
              }}
              renderInput={(params) => (
                <TextField
                  {...params}
                  label="Destination Airport"
                  placeholder="Enter city or airport code"
                  required
                  fullWidth
                />
              )}
            />
          </Box>

          <Box>
            <DatePicker
              label="Departure Date"
              value={departureDate}
              onChange={(newValue: Date | null) => setDepartureDate(newValue)}
              disablePast
              slotProps={{
                textField: {
                  fullWidth: true,
                  required: true
                }
              }}
            />
          </Box>

          <Box>
            <DatePicker
              label="Return Date (Optional)"
              value={returnDate}
              onChange={(newValue: Date | null) => setReturnDate(newValue)}
              disablePast
              minDate={departureDate || undefined}
              slotProps={{
                textField: {
                  fullWidth: true
                }
              }}
            />
          </Box>

          <Box>
            <FormControl fullWidth>
              <InputLabel>Passengers</InputLabel>
              <Select
                value={passengers}
                label="Passengers"
                onChange={(e) => setPassengers(Number(e.target.value))}
              >
                {[1, 2, 3, 4, 5, 6].map((num) => (
                  <MenuItem key={num} value={num}>{num}</MenuItem>
                ))}
              </Select>
            </FormControl>
          </Box>

          <Box>
            <FormControl fullWidth>
              <InputLabel>Cabin Class</InputLabel>
              <Select
                value={cabinClass}
                label="Cabin Class"
                onChange={(e) => setCabinClass(e.target.value)}
              >
                <MenuItem value="economy">Economy</MenuItem>
                <MenuItem value="premium_economy">Premium Economy</MenuItem>
                <MenuItem value="business">Business</MenuItem>
                <MenuItem value="first">First Class</MenuItem>
              </Select>
            </FormControl>
          </Box>

          <Box sx={{ gridColumn: '1 / -1' }}>
            <Button
              variant="contained"
              onClick={handleSearch}
              disabled={loading}
              size="large"
              startIcon={<FlightIcon />}
              fullWidth
            >
              Search Flights
            </Button>
          </Box>
        </Box>

        {estimates.length > 0 && (
          <Box sx={{ mt: 4 }}>
            <Paper sx={{ p: 2, bgcolor: 'grey.50' }}>
              <Typography variant="body2" color="text.secondary" gutterBottom>
                {origin} → {destination}
                {returnDate && ` (Round Trip)`}
              </Typography>
              <Divider sx={{ my: 2 }} />

              {estimates.map((estimate, index) => (
                <Paper
                  key={index}
                  elevation={1}
                  sx={{
                    p: 3,
                    mb: 2,
                    cursor: 'pointer',
                    '&:hover': {
                      boxShadow: 3,
                      transition: 'box-shadow 0.2s'
                    }
                  }}
                >
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 2 }}>
                    <Box>
                      <Typography variant="h6" color="primary" sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        {estimate.airline}
                        {estimate.recommended && (
                          <Chip
                            label="Best Value"
                            color="success"
                            size="small"
                          />
                        )}
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        {estimate.stops === 0 ? 'Nonstop' : `${estimate.stops} stop${estimate.stops > 1 ? 's' : ''}`}
                      </Typography>
                    </Box>
                    <Typography variant="h6" color="primary">
                      ${estimate.price}
                    </Typography>
                  </Box>

                  <Box sx={{ display: 'flex', justifyContent: 'space-between', mt: 2 }}>
                    <Box>
                      <Typography variant="body2" color="text.secondary">
                        Departure
                      </Typography>
                      <Typography variant="body1">
                        {estimate.departure}
                      </Typography>
                    </Box>
                    <Box>
                      <Typography variant="body2" color="text.secondary" align="right">
                        Arrival
                      </Typography>
                      <Typography variant="body1">
                        {estimate.arrival}
                      </Typography>
                    </Box>
                  </Box>

                  <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                    Duration: {formatDuration(estimate.duration)}
                  </Typography>
                </Paper>
              ))}
            </Paper>
          </Box>
        )}

        <Snackbar
          open={snackbar.open}
          autoHideDuration={3000}
          onClose={() => setSnackbar({ ...snackbar, open: false })}
        >
          <Alert severity={snackbar.severity} onClose={() => setSnackbar({ ...snackbar, open: false })}>
            {snackbar.message}
          </Alert>
        </Snackbar>
      </Stack>
    </LocalizationProvider>
  );
}
