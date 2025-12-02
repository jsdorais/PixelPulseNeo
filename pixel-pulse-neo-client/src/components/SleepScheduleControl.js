import React, { useState, useEffect } from 'react';
import { 
  Box, Typography, Paper, Grid, Switch, TextField,
  FormControlLabel, Divider
} from '@mui/material';
import BedtimeIcon from '@mui/icons-material/Bedtime';
import AlarmIcon from '@mui/icons-material/Alarm';

const API_BASE = '/api';

const DAY_NAMES = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];

function SleepScheduleControl() {
  const [schedule, setSchedule] = useState({});
  const [loading, setLoading] = useState(false);

  const fetchSchedule = async () => {
    try {
      const response = await fetch(`${API_BASE}/sleep-schedule`);
      if (response.ok) {
        const data = await response.json();
        setSchedule(data.schedule || {});
      }
    } catch (error) {
      console.error('Error fetching sleep schedule:', error);
    }
  };

  useEffect(() => {
    fetchSchedule();
  }, []);

  const updateDaySchedule = async (day, field, value) => {
    setLoading(true);
    try {
      const currentDay = schedule[day] || {};
      const updates = { ...currentDay, [field]: value };
      
      const response = await fetch(`${API_BASE}/sleep-schedule/${day}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updates)
      });
      
      if (response.ok) {
        const data = await response.json();
        setSchedule(data.schedule || {});
      }
    } catch (error) {
      console.error('Error updating schedule:', error);
    }
    setLoading(false);
  };

  return (
    <Paper elevation={2} sx={{ p: 2, mt: 2 }}>
      <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
        <BedtimeIcon /> Sleep Schedule
      </Typography>
      <Divider sx={{ mb: 2 }} />
      
      <Grid container spacing={1}>
        {/* Header */}
        <Grid item xs={3}>
          <Typography variant="subtitle2" fontWeight="bold">Day</Typography>
        </Grid>
        <Grid item xs={3}>
          <Typography variant="subtitle2" fontWeight="bold">
            <AlarmIcon fontSize="small" sx={{ verticalAlign: 'middle', mr: 0.5 }} />
            Wake
          </Typography>
        </Grid>
        <Grid item xs={3}>
          <Typography variant="subtitle2" fontWeight="bold">
            <BedtimeIcon fontSize="small" sx={{ verticalAlign: 'middle', mr: 0.5 }} />
            Sleep
          </Typography>
        </Grid>
        <Grid item xs={3}>
          <Typography variant="subtitle2" fontWeight="bold">Enabled</Typography>
        </Grid>
        
        {/* Days */}
        {DAY_NAMES.map((dayName, index) => {
          const daySchedule = schedule[index] || { wake: '07:00', sleep: '23:00', enabled: true };
          return (
            <React.Fragment key={index}>
              <Grid item xs={3} sx={{ display: 'flex', alignItems: 'center' }}>
                <Typography variant="body2">{dayName}</Typography>
              </Grid>
              <Grid item xs={3}>
                <TextField
                  type="time"
                  size="small"
                  value={daySchedule.wake || '07:00'}
                  onChange={(e) => updateDaySchedule(index, 'wake', e.target.value)}
                  disabled={loading || !daySchedule.enabled}
                  sx={{ width: '100%' }}
                  inputProps={{ style: { fontSize: '0.875rem' } }}
                />
              </Grid>
              <Grid item xs={3}>
                <TextField
                  type="time"
                  size="small"
                  value={daySchedule.sleep || '23:00'}
                  onChange={(e) => updateDaySchedule(index, 'sleep', e.target.value)}
                  disabled={loading || !daySchedule.enabled}
                  sx={{ width: '100%' }}
                  inputProps={{ style: { fontSize: '0.875rem' } }}
                />
              </Grid>
              <Grid item xs={3} sx={{ display: 'flex', alignItems: 'center' }}>
                <Switch
                  checked={daySchedule.enabled}
                  onChange={(e) => updateDaySchedule(index, 'enabled', e.target.checked)}
                  disabled={loading}
                  size="small"
                />
              </Grid>
            </React.Fragment>
          );
        })}
      </Grid>
    </Paper>
  );
}

export default SleepScheduleControl;
