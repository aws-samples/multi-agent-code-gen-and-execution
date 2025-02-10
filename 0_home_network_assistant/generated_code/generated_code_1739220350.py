import requests
import json

# Define the function to get the signal strength of the porch camera
def get_camera_signal_strength(device_id, auth_token):
    # API endpoint URL
    url = f"https://api.smarthomesecurity.example.com/v1/devices/cameras/{device_id}/status"
    
    # Headers including authorization
    headers = {
        "Authorization": f"Bearer {auth_token}",
        "Content-Type": "application/json"
    }
    
    try:
        # Make the GET request to retrieve camera status
        response = requests.get(url, headers=headers)
        
        # Check if the request was successful
        if response.status_code == 200:
            # Parse the JSON response
            camera_status = response.json()
            # Extract and return the signal strength
            return camera_status.get("signalStrength")
        else:
            # Handle errors
            response.raise_for_status()
    except requests.exceptions.RequestException as e:
        # Handle any exceptions that occur
        print(f"An error occurred: {e}")
        return None

# Main function to execute the code
if __name__ == "__main__":
    # Example device ID and authorization token
    device_id = "your-device-id"  # Replace with actual device ID
    auth_token = "your-custom-token"  # Replace with actual authorization token
    
    # Get the signal strength of the porch camera
    signal_strength = get_camera_signal_strength(device_id, auth_token)
    
    if signal_strength is not None:
        print(f"The signal strength of the porch camera is {signal_strength}%")
    else:
        print("Failed to retrieve the signal strength.")
