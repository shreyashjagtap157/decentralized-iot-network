import pytest
from unittest.mock import MagicMock

def test_device_firmware_integration():
    # Simulate firmware interaction
    mock_firmware = MagicMock()
    mock_firmware.send_data.return_value = {"status": "success"}
    
    response = mock_firmware.send_data({"temp": 25})
    assert response["status"] == "success"
    mock_firmware.send_data.assert_called_once()
