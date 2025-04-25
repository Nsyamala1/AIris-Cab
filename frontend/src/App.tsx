import React, { useState, useEffect } from 'react';
import {
  Container,
  Box,
  Stack,
  TextField,
  Button,
  Typography,
  Snackbar,
  Alert,
  Chip,
  Divider,
  Paper,
  Autocomplete,
  Tooltip,
  AppBar,
  Toolbar,
  Tab,
  Tabs
} from '@mui/material';
import {
  AccessTime as ClockIcon,
  Route as RouteIcon,
  DirectionsCar as CarIcon,
  AttachMoney as MoneyIcon,
} from '@mui/icons-material';
import axios from 'axios';
import { API_URL } from './config';
import FlightComparison from './components/FlightComparison';

interface PriceEstimate {
  service: string;
  price_estimate: string;
  duration: number;
  distance: number;
  pickup: string;
  dropoff: string;
  app_url: string;
  web_url: string;
  recommended: boolean;
  capacity: string;
}

interface TrackedRoute {
  id: number;
  pickup: string;
  dropoff: string;
  passenger_count: number;
  phone_number: string;
  target_price: number;
  is_active: boolean;
  created_at: string;
}

function App() {
  const [currentTab, setCurrentTab] = useState('cab');
  const [pickup, setPickup] = useState('');
  const [dropoff, setDropoff] = useState('');
  const [passengerCount, setPassengerCount] = useState(1);
  const [estimates, setEstimates] = useState<PriceEstimate[]>([]);
  const [loading, setLoading] = useState(false);
  const [pickupOptions, setPickupOptions] = useState<string[]>([]);
  const [dropoffOptions, setDropoffOptions] = useState<string[]>([]);
  const [snackbar, setSnackbar] = useState<{ open: boolean; message: string; severity: 'success' | 'error' }>(
    { open: false, message: '', severity: 'success' }
  );
  const [phoneNumber, setPhoneNumber] = useState('');
  const [targetPrice, setTargetPrice] = useState<number | ''>('');
  const [trackedRoutes, setTrackedRoutes] = useState<TrackedRoute[]>([]);
  const [showTrackedRoutes, setShowTrackedRoutes] = useState(false);
  const [errors, setErrors] = useState<{pickup?: string; dropoff?: string}>({});

  const handleSnackbarClose = () => {
    setSnackbar({ ...snackbar, open: false });
  };

  const trackRoute = async (estimate: PriceEstimate) => {
    try {
      // Validate phone number format
      if (!phoneNumber.match(/^\+[1-9]\d{10,14}$/)) {
        setSnackbar({
          open: true,
          message: 'Please enter a valid phone number in E.164 format (e.g., +1XXXXXXXXXX)',
          severity: 'error'
        });
        return;
      }

      await axios.post(`${API_URL}/track-route`, {
        pickup_address: estimate.pickup,
        dropoff_address: estimate.dropoff,
        passenger_count: passengerCount,
        phone_number: phoneNumber,
        target_price: parseFloat(estimate.price_estimate.replace('$', ''))
      });
      
      setSnackbar({
        open: true,
        message: 'Route tracking started! We\'ll notify you when the price drops below your target.',
        severity: 'success'
      });
      
      // Refresh tracked routes
      fetchTrackedRoutes();
    } catch (error) {
      setSnackbar({
        open: true,
        message: 'Failed to start route tracking',
        severity: 'error'
      });
    }
  };

  const fetchTrackedRoutes = async () => {
    if (!phoneNumber) return;
    
    try {
      // Make sure the phone number starts with + for E.164 format
      const formattedNumber = phoneNumber.startsWith('+') ? phoneNumber : `+${phoneNumber}`;
      const response = await axios.get(`${API_URL}/tracked-routes/${encodeURIComponent(formattedNumber)}`);
      setTrackedRoutes(response.data);
    } catch (error) {
      console.error('Failed to fetch tracked routes:', error);
      setSnackbar({
        open: true,
        message: 'Failed to fetch tracked routes. Please make sure your phone number is in E.164 format (+1XXXXXXXXXX)',
        severity: 'error'
      });
    }
  };

  const deleteTrackedRoute = async (routeId: number) => {
    try {
      await axios.delete(`${API_URL}/tracked-routes/${routeId}`);
      setSnackbar({
        open: true,
        message: 'Route tracking stopped and deleted',
        severity: 'success'
      });
      fetchTrackedRoutes();
    } catch (error) {
      setSnackbar({
        open: true,
        message: 'Failed to delete tracked route',
        severity: 'error'
      });
    }
  };

  // Fetch tracked routes when phone number changes or showTrackedRoutes is enabled
  useEffect(() => {
    if (phoneNumber && showTrackedRoutes) {
      fetchTrackedRoutes();
    }
  }, [phoneNumber, showTrackedRoutes]);

  const formatDuration = (seconds: number): string => {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    if (hours > 0) {
      return `${hours}h ${minutes}m`;
    }
    return `${minutes} minutes`;
  };

  const comparePrices = async () => {
    setErrors({});
    
    if (!pickup) {
      setErrors(prev => ({ ...prev, pickup: 'Please enter a pickup location' }));
      return;
    }
    if (!dropoff) {
      setErrors(prev => ({ ...prev, dropoff: 'Please enter a dropoff location' }));
      return;
    }
    setLoading(true);
    try {
      const response = await axios.post('http://localhost:8001/compare-prices', {
        pickup_address: pickup,
        dropoff_address: dropoff,
        passenger_count: passengerCount
      });
      setEstimates(response.data);
    } catch (error) {
      setSnackbar({
        open: true,
        message: 'Failed to fetch price estimates',
        severity: 'error'
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <Box>
      <AppBar position="static" color="default">
        <Toolbar sx={{ justifyContent: 'space-between' }}>
          <Typography variant="h6" component="div" sx={{ flexGrow: 0 }}>
            AIris Comparison
          </Typography>
          <Tabs 
            value={currentTab}
            onChange={(e, newValue) => setCurrentTab(newValue)}
            textColor="primary"
            indicatorColor="primary"
          >
            <Tab value="home" label="Home" />
            <Tab value="cab" label="Cab" />
            <Tab value="flights" label="Flights" />
          </Tabs>
        </Toolbar>
      </AppBar>

      <Container maxWidth="md" sx={{ py: 4 }}>
        {currentTab === 'cab' && (
        <Stack spacing={3}>
          <Typography variant="h3" align="center" color="primary" gutterBottom>
            AIris Cab Price Comparison
          </Typography>
          
          <Autocomplete
            freeSolo
            options={pickupOptions}
            value={pickup}
            onInputChange={async (_, newValue) => {
              setPickup(newValue);
              if (newValue.length >= 1) {
                try {
                  const response = await axios.get(`http://localhost:8001/cities/autocomplete?query=${newValue}`);
                  setPickupOptions(response.data);
                } catch (error) {
                  console.error('Failed to fetch city suggestions:', error);
                }
              }
            }}
            renderInput={(params) => (
              <TextField
                {...params}
                label="Pickup Location"
                placeholder="Enter pickup location (e.g., Manhattan)"
                variant="outlined"
                fullWidth
                required
                error={Boolean(errors?.pickup)}
                helperText={errors?.pickup}
              />
            )}
          />
          
          <Autocomplete
            freeSolo
            options={dropoffOptions}
            value={dropoff}
            onInputChange={async (_, newValue) => {
              setDropoff(newValue);
              if (newValue.length >= 1) {
                try {
                  const response = await axios.get(`http://localhost:8001/cities/autocomplete?query=${newValue}`);
                  setDropoffOptions(response.data);
                } catch (error) {
                  console.error('Failed to fetch city suggestions:', error);
                }
              }
            }}
            renderInput={(params) => (
              <TextField
                {...params}
                label="Dropoff Location"
                placeholder="Enter dropoff location (e.g., Brooklyn)"
                variant="outlined"
                fullWidth
                required
                error={Boolean(errors?.dropoff)}
                helperText={errors?.dropoff}
              />
            )}
          />
          
          <Box sx={{ display: 'flex', gap: 2, alignItems: 'center', flexWrap: 'wrap' }}>
            <TextField
              type="number"
              label="Number of Passengers"
              value={passengerCount}
              onChange={(e) => setPassengerCount(Math.max(1, Math.min(7, parseInt(e.target.value) || 1)))}
              inputProps={{ min: 1, max: 7 }}
              sx={{ width: 200 }}
            />
            <TextField
              type="tel"
              label="Phone Number for Price Alerts"
              placeholder="+1XXXXXXXXXX"
              value={phoneNumber}
              onChange={(e) => setPhoneNumber(e.target.value)}
              sx={{ width: 250 }}
            />
            <TextField
              type="number"
              label="Target Price"
              value={targetPrice}
              onChange={(e) => setTargetPrice(e.target.value === '' ? '' : Number(e.target.value))}
              inputProps={{ min: 0 }}
              sx={{ width: 150 }}
            />
            <Box>
              <Button
                variant="contained"
                onClick={comparePrices}
                disabled={loading}
                size="large"
                startIcon={<CarIcon />}
                sx={{ mr: 1 }}
              >
                Compare Prices
              </Button>
              <Button
                variant="outlined"
                onClick={() => setShowTrackedRoutes(!showTrackedRoutes)}
                size="large"
              >
                {showTrackedRoutes ? 'Hide Tracked Routes' : 'Show Tracked Routes'}
              </Button>
            </Box>
          </Box>

          {estimates.length > 0 && (
            <Box sx={{ mt: 4 }}>
              <Paper sx={{ p: 2, bgcolor: 'grey.50' }}>
                <Typography variant="body2" color="text.secondary" gutterBottom>
                  Route: {estimates[0].pickup} to {estimates[0].dropoff}
                </Typography>
                <Divider sx={{ my: 2 }} />

                {estimates.map((estimate) => (
                  <Tooltip key={estimate.service} title={`Book with ${estimate.service}`} arrow placement="top">
                    <Paper
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
                      onClick={() => {
                        // Try to open the app first
                        window.location.href = estimate.app_url;
                        
                        // If app doesn't open within 1 second, redirect to web URL
                        setTimeout(() => {
                          window.location.href = estimate.web_url;
                        }, 1000);
                      }}
                    >
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 2 }}>
                      <Box>
                        <Typography variant="h6" color="primary" sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                          {estimate.service}
                          {estimate.recommended && (
                            <Chip
                              label="Recommended"
                              color="success"
                              size="small"
                            />
                          )}
                        </Typography>
                        <Typography variant="caption" color="text.secondary">
                          {estimate.capacity}
                        </Typography>
                        {phoneNumber && targetPrice !== '' && (
                          <Button
                            size="small"
                            onClick={() => trackRoute(estimate)}
                            sx={{ mt: 1 }}
                          >
                            Track Price
                          </Button>
                        )}
                      </Box>
                      <Chip
                        label={estimate.price_estimate}
                        color={estimate.recommended ? 'success' : 'secondary'}
                      />
                    </Box>

                    <Stack spacing={2}>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <ClockIcon color="action" />
                        <Typography>Duration: {formatDuration(estimate.duration)}</Typography>
                      </Box>

                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <RouteIcon color="action" />
                        <Typography>Distance: {estimate.distance.toFixed(1)} miles</Typography>
                      </Box>

                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <MoneyIcon color="action" />
                        <Typography>
                          Rate: ${(parseFloat(estimate.price_estimate.slice(1)) / estimate.distance).toFixed(2)}/mile
                        </Typography>
                      </Box>
                    </Stack>
                    </Paper>
                  </Tooltip>
                ))}
              </Paper>
            </Box>
          )}

          <Snackbar
            open={snackbar.open}
            autoHideDuration={3000}
            onClose={handleSnackbarClose}
          >
            <Alert severity={snackbar.severity} onClose={handleSnackbarClose}>
              {snackbar.message}
            </Alert>
          </Snackbar>

          {showTrackedRoutes && phoneNumber && (
            <Box sx={{ mt: 4 }}>
              <Paper sx={{ p: 2, bgcolor: 'grey.50' }}>
                <Typography variant="h6" gutterBottom>
                  Your Tracked Routes
                </Typography>
                {trackedRoutes.map((route) => (
                  <Paper
                    key={route.id}
                    elevation={1}
                    sx={{ p: 2, mb: 2 }}
                  >
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <Box>
                        <Typography variant="subtitle1">
                          {route.pickup} to {route.dropoff}
                        </Typography>
                        <Typography variant="body2" color="text.secondary">
                          Target Price: ${route.target_price.toFixed(2)} • {route.passenger_count} passenger(s)
                        </Typography>
                        <Typography variant="caption" color="text.secondary">
                          Created: {new Date(route.created_at).toLocaleDateString()}
                        </Typography>
                      </Box>
                      <Box>
                        <Chip
                          label={route.is_active ? 'Active' : 'Notified'}
                          color={route.is_active ? 'primary' : 'success'}
                          sx={{ mr: 1 }}
                        />
                        <Button
                          size="small"
                          color="error"
                          onClick={() => deleteTrackedRoute(route.id)}
                        >
                          Delete
                        </Button>
                      </Box>
                    </Box>
                  </Paper>
                ))}
              </Paper>
            </Box>
          )}
        </Stack>
        )}
        {currentTab === 'home' && (
          <Box sx={{ py: 4 }}>
            <Typography variant="h4" gutterBottom>
              Welcome to AIris Comparison
            </Typography>
            <Typography variant="body1" paragraph>
              Estimate prices across different travel options to find the best deals.
            </Typography>
            <Stack direction="row" spacing={2}>
              <Button variant="contained" onClick={() => setCurrentTab('cab')}>Estimate Cab Prices</Button>
              <Button variant="contained" onClick={() => setCurrentTab('flights')}>Estimate Flight Prices</Button>
            </Stack>
          </Box>
        )}
        {currentTab === 'flights' && <FlightComparison />}
      </Container>
    </Box>
  );
}

export default App;
