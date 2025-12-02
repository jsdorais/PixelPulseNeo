import React, { useState, useEffect } from 'react';
import { Box, IconButton, Typography, Tooltip, Chip } from '@mui/material';
import AddIcon from '@mui/icons-material/Add';
import RemoveIcon from '@mui/icons-material/Remove';
import BrightnessHighIcon from '@mui/icons-material/BrightnessHigh';
import AutoModeIcon from '@mui/icons-material/AutoMode';

const API_BASE = '/api';

function BrightnessControl() {
  const [brightness, setBrightness] = useState(50);
  const [mode, setMode] = useState('auto');
  const [loading, setLoading] = useState(false);

  const fetchBrightness = async () => {
    try {
      const response = await fetch(`${API_BASE}/brightness`);
      if (response.ok) {
        const data = await response.json();
        setBrightness(data.brightness);
        setMode(data.mode);
      }
    } catch (error) {
      console.error('Error fetching brightness:', error);
    }
  };

  useEffect(() => {
    fetchBrightness();
    const interval = setInterval(fetchBrightness, 5000);
    return () => clearInterval(interval);
  }, []);

  const adjustBrightness = async (delta) => {
    setLoading(true);
    try {
      const response = await fetch(`${API_BASE}/brightness/adjust`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ delta: delta })
      });
      if (response.ok) {
        const data = await response.json();
        setBrightness(data.brightness);
        setMode(data.mode);
      }
    } catch (error) {
      console.error('Error adjusting brightness:', error);
    }
    setLoading(false);
  };

  const setAutoBrightness = async () => {
    setLoading(true);
    try {
      const response = await fetch(`${API_BASE}/brightness`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ value: null })
      });
      if (response.ok) {
        const data = await response.json();
        setBrightness(data.brightness);
        setMode(data.mode);
      }
    } catch (error) {
      console.error('Error setting auto brightness:', error);
    }
    setLoading(false);
  };

  return (
    <Box sx={{ 
      display: 'flex', 
      alignItems: 'center', 
      gap: 1,
      p: 1,
      bgcolor: 'background.paper',
      borderRadius: 1,
      border: '1px solid',
      borderColor: 'divider'
    }}>
      <BrightnessHighIcon sx={{ color: 'warning.main' }} />
      
      <Tooltip title="Decrease brightness">
        <IconButton 
          size="small" 
          onClick={() => adjustBrightness(-10)}
          disabled={loading || brightness <= 5}
        >
          <RemoveIcon />
        </IconButton>
      </Tooltip>
      
      <Typography variant="body2" sx={{ minWidth: 40, textAlign: 'center' }}>
        {brightness}%
      </Typography>
      
      <Tooltip title="Increase brightness">
        <IconButton 
          size="small" 
          onClick={() => adjustBrightness(10)}
          disabled={loading || brightness >= 100}
        >
          <AddIcon />
        </IconButton>
      </Tooltip>
      
      <Chip 
        label={mode === 'auto' ? 'Auto' : 'Manual'}
        size="small"
        color={mode === 'auto' ? 'success' : 'warning'}
        onClick={mode === 'manual' ? setAutoBrightness : undefined}
        icon={mode === 'auto' ? <AutoModeIcon /> : null}
        sx={{ cursor: mode === 'manual' ? 'pointer' : 'default' }}
      />
    </Box>
  );
}

export default BrightnessControl;
